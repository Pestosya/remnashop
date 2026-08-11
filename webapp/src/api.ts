import { demoApi, isDemo } from "./demo";
import { initData } from "./telegram";
import type {
  DevicesResponse,
  MeResponse,
  PaymentGatewayType,
  PaymentInitResponse,
  PromocodeActivateResponse,
  ReferralProgramResponse,
  SubscriptionInfoResponse,
  SubscriptionOffersResponse,
  TrialActivateResponse,
} from "./types";

const BASE = "/api/v1/public";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** FastAPI reports failures as `detail`, either a string or a validation list. */
async function readError(response: Response): Promise<string> {
  try {
    const body = await response.json();
    const detail = body?.detail;

    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && detail.length) {
      const first = detail[0];
      if (typeof first?.msg === "string") return first.msg;
    }
  } catch {
    // Non-JSON body (proxy error page, empty 502); fall through to the status.
  }
  return `HTTP ${response.status}`;
}

let refreshing: Promise<boolean> | null = null;

/** Single-flight refresh so a burst of parallel 401s triggers one call. */
function refreshSession(): Promise<boolean> {
  if (!refreshing) {
    refreshing = request<unknown>("POST", "/auth/refresh", undefined, { retry: false })
      .then(() => true)
      .catch(() => false)
      .finally(() => {
        refreshing = null;
      });
  }
  return refreshing;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options: { retry?: boolean } = {},
): Promise<T> {
  const { retry = true } = options;

  const response = await fetch(BASE + path, {
    method,
    // Auth rides on httpOnly cookies set by the backend, so same-origin
    // credentials must be sent explicitly.
    credentials: "same-origin",
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 401 && retry) {
    // The access token lives 15 minutes; a long-open Mini App will hit this.
    const refreshed = await refreshSession();
    if (refreshed) return request<T>(method, path, body, { retry: false });

    const reauthed = await login();
    if (reauthed) return request<T>(method, path, body, { retry: false });
  }

  if (!response.ok) throw new ApiError(response.status, await readError(response));

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

/** Exchanges Telegram's signed initData for a session cookie. */
export async function login(): Promise<boolean> {
  const data = initData();
  if (!data) return false;

  try {
    await request("POST", "/auth/telegram/webapp", { init_data: data }, { retry: false });
    return true;
  } catch {
    return false;
  }
}

export const realApi = {
  me: () => request<MeResponse>("GET", "/auth/me"),

  subscription: {
    // The endpoint answers `null` when the user has no subscription yet.
    current: () => request<SubscriptionInfoResponse | null>("GET", "/subscription/current"),
    offers: () => request<SubscriptionOffersResponse>("GET", "/subscription/offers"),
    reissue: () => request<{ success: boolean }>("POST", "/subscription/reissue"),
    purchase: (plan_code: string, duration_days: number, gateway_type: PaymentGatewayType) =>
      request<PaymentInitResponse>("POST", "/subscription/purchase", {
        plan_code,
        duration_days,
        gateway_type,
      }),
    extend: (duration_days: number, gateway_type: PaymentGatewayType) =>
      request<PaymentInitResponse>("POST", "/subscription/extend", {
        duration_days,
        gateway_type,
      }),
    trial: () => request<TrialActivateResponse>("POST", "/subscription/trial"),
    trialPurchase: (gateway_type: PaymentGatewayType) =>
      request<PaymentInitResponse>("POST", "/subscription/trial/purchase", { gateway_type }),
    promocode: (code: string) =>
      request<PromocodeActivateResponse>("POST", "/subscription/promocode", { code }),
  },

  devices: {
    list: () => request<DevicesResponse>("GET", "/subscription/devices"),
    remove: (hwid: string) =>
      request<{ deleted: boolean }>("DELETE", `/subscription/devices/${encodeURIComponent(hwid)}`),
    removeAll: () => request<{ success: boolean }>("DELETE", "/subscription/devices"),
  },

  referral: () => request<ReferralProgramResponse>("GET", "/referral/program"),
};

// `demo.ts` only imports `realApi` as a type, so this is not a runtime cycle.
export const api: typeof realApi = isDemo() ? demoApi : realApi;
