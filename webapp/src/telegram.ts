// Thin typed wrapper over the Telegram WebApp bridge.
//
// Deliberately dependency-free: the official JS is loaded from index.html and
// its surface is small enough that an SDK package would only add version churn.
// Every method degrades to a no-op outside Telegram so the app can be opened in
// a plain browser during development.

type HapticStyle = "light" | "medium" | "heavy" | "rigid" | "soft";
type HapticNotification = "error" | "success" | "warning";

interface ThemeParams {
  bg_color?: string;
  text_color?: string;
  hint_color?: string;
  link_color?: string;
  button_color?: string;
  button_text_color?: string;
  secondary_bg_color?: string;
  section_bg_color?: string;
  section_separator_color?: string;
  destructive_text_color?: string;
}

interface BackButton {
  show(): void;
  hide(): void;
  onClick(cb: () => void): void;
  offClick(cb: () => void): void;
}

interface MainButton {
  text: string;
  isVisible: boolean;
  setParams(params: {
    text?: string;
    color?: string;
    text_color?: string;
    is_active?: boolean;
    is_visible?: boolean;
  }): void;
  show(): void;
  hide(): void;
  showProgress(leaveActive?: boolean): void;
  hideProgress(): void;
  onClick(cb: () => void): void;
  offClick(cb: () => void): void;
}

interface WebApp {
  initData: string;
  colorScheme: "light" | "dark";
  themeParams: ThemeParams;
  isExpanded: boolean;
  viewportStableHeight: number;
  BackButton: BackButton;
  MainButton: MainButton;
  HapticFeedback: {
    impactOccurred(style: HapticStyle): void;
    notificationOccurred(type: HapticNotification): void;
    selectionChanged(): void;
  };
  ready(): void;
  expand(): void;
  close(): void;
  openLink(url: string, options?: { try_instant_view?: boolean }): void;
  openTelegramLink(url: string): void;
  openInvoice(url: string, cb?: (status: string) => void): void;
  showAlert(message: string, cb?: () => void): void;
  showConfirm(message: string, cb?: (confirmed: boolean) => void): void;
  setHeaderColor(color: string): void;
  setBackgroundColor(color: string): void;
  onEvent(event: string, cb: () => void): void;
  offEvent(event: string, cb: () => void): void;
}

declare global {
  interface Window {
    Telegram?: { WebApp?: WebApp };
  }
}

const webApp = (): WebApp | undefined => window.Telegram?.WebApp;

export const isTelegram = (): boolean => Boolean(webApp()?.initData);

export const initData = (): string => webApp()?.initData ?? "";

export const colorScheme = (): "light" | "dark" => webApp()?.colorScheme ?? "dark";

/** Publishes Telegram's palette as CSS variables so styling stays in plain CSS. */
export function applyTheme(): void {
  const app = webApp();
  const root = document.documentElement;

  root.dataset.scheme = colorScheme();

  const params = app?.themeParams ?? {};
  for (const [key, value] of Object.entries(params)) {
    if (value) root.style.setProperty(`--tg-${key.replace(/_/g, "-")}`, value);
  }

  const bg = params.secondary_bg_color ?? params.bg_color;
  if (bg) {
    app?.setHeaderColor(bg);
    app?.setBackgroundColor(bg);
  }
}

export function ready(): void {
  const app = webApp();
  if (!app) return;
  app.ready();
  app.expand();
  applyTheme();
  app.onEvent("themeChanged", applyTheme);
}

export const haptic = {
  tap(): void {
    webApp()?.HapticFeedback.impactOccurred("light");
  },
  select(): void {
    webApp()?.HapticFeedback.selectionChanged();
  },
  success(): void {
    webApp()?.HapticFeedback.notificationOccurred("success");
  },
  error(): void {
    webApp()?.HapticFeedback.notificationOccurred("error");
  },
};

export function showBackButton(onClick: () => void): () => void {
  const app = webApp();
  if (!app) return () => {};

  app.BackButton.onClick(onClick);
  app.BackButton.show();

  return () => {
    app.BackButton.offClick(onClick);
    app.BackButton.hide();
  };
}

/** Native confirm when inside Telegram, browser confirm otherwise. */
export function confirm(message: string): Promise<boolean> {
  const app = webApp();
  if (!app) return Promise.resolve(window.confirm(message));
  return new Promise((resolve) => app.showConfirm(message, (ok) => resolve(Boolean(ok))));
}

export function alert(message: string): void {
  const app = webApp();
  if (!app) {
    window.alert(message);
    return;
  }
  app.showAlert(message);
}

/**
 * Opens a payment URL the right way for its kind.
 *
 * Telegram Stars invoices are `t.me/$<slug>` links that must go through
 * `openInvoice` to stay inside the app; everything else is an external payment
 * page. Returns the invoice status when Telegram reports one.
 */
export function openPayment(url: string): Promise<string | null> {
  const app = webApp();

  if (!app) {
    window.open(url, "_blank", "noopener");
    return Promise.resolve(null);
  }

  if (/^https:\/\/t\.me\/(\$|invoice\/)/.test(url)) {
    return new Promise((resolve) => app.openInvoice(url, (status) => resolve(status)));
  }

  if (/^https:\/\/t\.me\//.test(url)) {
    app.openTelegramLink(url);
    return Promise.resolve(null);
  }

  app.openLink(url);
  return Promise.resolve(null);
}

export function shareLink(url: string, text: string): void {
  const app = webApp();
  const share = `https://t.me/share/url?url=${encodeURIComponent(url)}&text=${encodeURIComponent(text)}`;

  if (app) {
    app.openTelegramLink(share);
    return;
  }
  window.open(share, "_blank", "noopener");
}

export async function copy(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    // Older Telegram WebViews expose no clipboard API over insecure contexts.
    const area = document.createElement("textarea");
    area.value = text;
    area.style.position = "fixed";
    area.style.opacity = "0";
    document.body.appendChild(area);
    area.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(area);
    return ok;
  }
}
