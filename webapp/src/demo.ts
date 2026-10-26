import type { realApi } from "./api";
import type {
  DevicesResponse,
  MeResponse,
  PaymentInitResponse,
  PromocodeActivateResponse,
  ReferralProgramResponse,
  SubscriptionInfoResponse,
  SubscriptionOffersResponse,
  TrialActivateResponse,
} from "./types";

/**
 * Offline preview mode.
 *
 * The cabinet needs signed Telegram `initData` to log in, so a plain browser
 * can normally only reach the "open from the bot" screen. Adding `?demo=1`
 * swaps the API layer for fixtures so the whole UI can be reviewed — and
 * screenshotted — without a backend or a bot.
 *
 * It is opt-in via the query string only: a real Mini App session never sets
 * it, so production behaviour is untouched.
 */
export function isDemo(): boolean {
  return new URLSearchParams(window.location.search).get("demo") === "1";
}

const demoParam = (name: string): string | null =>
  new URLSearchParams(window.location.search).get(name);

function demoBonusBalance(): number | undefined {
  const value = demoParam("demo_balance");
  if (value === "missing") return undefined;
  if (value === null) return 2762;

  const numeric = Number(value);
  return Number.isInteger(numeric) && numeric >= 0 ? numeric : 2762;
}

function withDemoBalance<T extends object>(value: T): T & { available_bonus_balance?: number } {
  const balance = demoBonusBalance();
  return balance === undefined ? { ...value } : { ...value, available_bonus_balance: balance };
}

function forbidden(message: string): Promise<never> {
  return Promise.reject(Object.assign(new Error(message), { status: 403 }));
}

const delay = <T>(value: T, ms = 350): Promise<T> =>
  new Promise((resolve) => setTimeout(() => resolve(value), ms));

const daysFromNow = (days: number): string =>
  new Date(Date.now() + days * 86_400_000).toISOString();

const me: MeResponse = {
  telegram_id: 9_000_000_000_000_001,
  auth_type: "TELEGRAM",
  email: null,
  is_email_verified: true,
  pending_email: null,
  name: "Демо",
  username: "demo",
  language: "ru",
};

const subscription: SubscriptionInfoResponse = {
  user_remna_id: "demo-user-001",
  status: "ACTIVE",
  is_trial: false,
  traffic_limit: 100,
  device_limit: 3,
  traffic_limit_strategy: "MONTH",
  expire_at: daysFromNow(24),
  url: "https://sub.example.com/aB3xK9mQ7pLd",
  plan_name: "START",
  plan_duration_days: 30,
  used_traffic_bytes: 41_234_567_890,
  lifetime_used_traffic_bytes: 402_345_678_901,
  online_at: new Date().toISOString(),
};

function demoSubscription(): SubscriptionInfoResponse {
  if (demoParam("demo_subscription") !== "expired") return subscription;

  return {
    ...subscription,
    status: "EXPIRED",
    expire_at: daysFromNow(-2),
  };
}

const devices: DevicesResponse = {
  current_count: 2,
  max_count: 3,
  devices: [
    {
      hwid: "demo-ios-device-001",
      platform: "iOS",
      device_model: "iPhone 15 Pro",
      os_version: "18.2",
      user_agent: "Happ/2.1 iOS",
    },
    {
      hwid: "demo-windows-device-002",
      platform: "Windows",
      device_model: "PC",
      os_version: "11",
      user_agent: "Hiddify/1.4 Windows",
    },
  ],
};

const price = (amount: string, discount = 0) => ({
  gateway_type: "YOOKASSA" as const,
  currency: "RUB",
  currency_symbol: "₽",
  original_amount: amount,
  discount_percent: discount,
  final_amount:
    discount > 0 ? String(Math.round(Number(amount) * (1 - discount / 100))) : amount,
  is_free: false,
});

const offers: SubscriptionOffersResponse = {
  has_current_subscription: true,
  current_subscription_status: "ACTIVE",
  gateways: [{ gateway_type: "YOOKASSA", currency: "RUB", currency_symbol: "₽" }],
  plans: [
    {
      id: 1,
      public_code: "start",
      name: "START",
      description: "Базовый тариф для одного пользователя",
      traffic_limit: 100,
      device_limit: 3,
      type: "BOTH",
      recommended_purchase_type: "RENEW",
      durations: [
        { days: 30, prices: [price("199")] },
        { days: 90, prices: [price("597", 10)] },
        { days: 365, prices: [price("2388", 25)] },
      ],
    },
    {
      id: 2,
      public_code: "plus",
      name: "PLUS",
      description: "Больше трафика и устройств",
      traffic_limit: 500,
      device_limit: 5,
      type: "BOTH",
      recommended_purchase_type: "CHANGE",
      durations: [
        { days: 30, prices: [price("349")] },
        { days: 90, prices: [price("1047", 10)] },
      ],
    },
  ],
};

const referral: ReferralProgramResponse = {
  enabled: true,
  referral_code: "demo123",
  referral_link: "https://t.me/your_bot?start=ref_demo123",
  invited_count: 7,
  invited_with_payment_count: 3,
  reward_type: "POINTS",
  reward_strategy: "PERCENT",
  accrual_strategy: "ON_EACH_PAYMENT",
  max_level: 2,
  reward_levels: [
    { level: 1, value: 20 },
    { level: 2, value: 5 },
  ],
};

function demoReferral(): Promise<ReferralProgramResponse> {
  if (demoParam("demo_subscription") === "expired") {
    return forbidden("Referral program is available only for users with active subscription");
  }
  if (demoParam("demo_referral") === "403") {
    return forbidden("Referral program is disabled");
  }
  return delay(withDemoBalance(referral));
}

const payment: PaymentInitResponse = {
  payment_id: "demo-payment",
  payment_url: null,
  purchase_type: "RENEW",
  status: "PENDING",
  is_free: true,
  final_amount: "0",
  currency: "RUB",
};

// Typed against the real client so a signature change here fails the build.
export const demoApi: typeof realApi = {
  me: () => delay(withDemoBalance(me)),
  subscription: {
    current: () => delay(demoSubscription()),
    offers: () => delay(offers),
    reissue: () => delay({ success: true }),
    purchase: () => delay(payment),
    extend: () => delay(payment),
    trial: () =>
      delay<TrialActivateResponse>({
        is_free: true,
        activated: true,
        duration_days: 3,
        gateways: [],
      }),
    trialPurchase: () => delay(payment),
    promocode: () =>
      delay<PromocodeActivateResponse>({ success: true, reward_type: "DURATION" }),
  },
  devices: {
    list: () => delay(devices),
    remove: () => delay({ deleted: true }),
    removeAll: () => delay({ success: true }),
  },
  referral: demoReferral,
};
