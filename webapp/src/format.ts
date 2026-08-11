import { t } from "./i18n";

const GB = 1024 ** 3;

/** `traffic_limit` and `device_limit` use 0 as "unlimited" across the backend. */
export const isUnlimited = (limit: number): boolean => limit <= 0;

export function formatBytes(bytes: number): string {
  if (bytes <= 0) return "0 B";

  const units = ["B", "KB", "MB", "GB", "TB"];
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  const value = bytes / 1024 ** exponent;
  const digits = value >= 100 || exponent === 0 ? 0 : 1;

  return `${value.toFixed(digits)} ${units[exponent]}`;
}

/** Traffic limits are stored in whole gigabytes, usage in bytes. */
export const gbToBytes = (gb: number): number => gb * GB;

export function trafficRatio(usedBytes: number | null, limitGb: number): number | null {
  if (isUnlimited(limitGb) || usedBytes === null) return null;
  return Math.min(usedBytes / gbToBytes(limitGb), 1);
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleDateString(undefined, {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

/** Whole days left; negative once the subscription has lapsed. */
export function daysLeft(iso: string): number {
  const diff = new Date(iso).getTime() - Date.now();
  return Math.ceil(diff / 86_400_000);
}

export function formatExpiry(iso: string): string {
  // Year 2099 is the backend's sentinel for a never-expiring subscription.
  if (new Date(iso).getUTCFullYear() >= 2099) return t("unlimited");

  const days = daysLeft(iso);
  if (days < 0) return t("expiredOn", { date: formatDate(iso) });
  if (days === 0) return t("expiresToday");

  return t("daysLeft", { count: String(days), date: formatDate(iso) });
}

export function formatPrice(amount: string, symbol: string): string {
  const numeric = Number(amount);
  if (Number.isNaN(numeric)) return `${amount} ${symbol}`;

  // Trim the trailing ".00" that Decimal serialisation leaves behind.
  const shown = Number.isInteger(numeric) ? String(numeric) : numeric.toFixed(2);
  return `${shown} ${symbol}`;
}

export function formatDuration(days: number): string {
  if (days <= 0) return t("unlimited");
  if (days % 365 === 0) return t("years", { count: String(days / 365) });
  if (days % 30 === 0) return t("months", { count: String(days / 30) });
  return t("days", { count: String(days) });
}

const PLATFORM_ICONS: Record<string, string> = {
  ios: "🍎",
  iphone: "🍎",
  ipad: "🍎",
  macos: "💻",
  mac: "💻",
  android: "🤖",
  windows: "🪟",
  linux: "🐧",
};

export function platformIcon(platform: string | null): string {
  if (!platform) return "📱";
  return PLATFORM_ICONS[platform.toLowerCase()] ?? "📱";
}
