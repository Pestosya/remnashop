// Mirrors src/web/schemas/*.py. Keep in sync by hand — the backend does not
// publish an OpenAPI document (openapi_url is disabled in src/web/app.py).

export type PaymentGatewayType =
  | "TELEGRAM_STARS"
  | "YOOKASSA"
  | "YOOMONEY"
  | "VALUTIX"
  | "CRYPTOMUS"
  | "HELEKET"
  | "CRYPTOPAY"
  | "FREEKASSA"
  | "MULENPAY"
  | "PAYMASTER"
  | "PLATEGA"
  | "ROBOKASSA"
  | "URLPAY"
  | "WATA";

export interface MeResponse {
  telegram_id: number | null;
  auth_type: string;
  email: string | null;
  is_email_verified: boolean;
  pending_email: string | null;
  name: string;
  username: string | null;
  language: string;
}

export interface SubscriptionInfoResponse {
  user_remna_id: string;
  status: string;
  is_trial: boolean;
  traffic_limit: number;
  device_limit: number;
  traffic_limit_strategy: string;
  expire_at: string;
  url: string;
  plan_name: string;
  plan_duration_days: number;
  used_traffic_bytes: number | null;
  lifetime_used_traffic_bytes: number | null;
  online_at: string | null;
}

export interface DeviceResponse {
  hwid: string;
  platform: string | null;
  device_model: string | null;
  os_version: string | null;
  user_agent: string | null;
}

export interface DevicesResponse {
  devices: DeviceResponse[];
  current_count: number;
  max_count: number;
}

export interface DurationGatewayPriceResponse {
  gateway_type: PaymentGatewayType;
  currency: string;
  currency_symbol: string;
  original_amount: string;
  discount_percent: number;
  final_amount: string;
  is_free: boolean;
}

export interface DurationOfferResponse {
  days: number;
  prices: DurationGatewayPriceResponse[];
}

export interface PlanOfferResponse {
  id: number;
  public_code: string;
  name: string;
  description: string | null;
  traffic_limit: number;
  device_limit: number;
  type: string;
  recommended_purchase_type: string;
  durations: DurationOfferResponse[];
}

export interface GatewayOfferResponse {
  gateway_type: PaymentGatewayType;
  currency: string;
  currency_symbol: string;
}

export interface SubscriptionOffersResponse {
  gateways: GatewayOfferResponse[];
  plans: PlanOfferResponse[];
  has_current_subscription: boolean;
  current_subscription_status: string | null;
}

export interface PaymentInitResponse {
  payment_id: string;
  payment_url: string | null;
  purchase_type: string;
  status: string;
  is_free: boolean;
  final_amount: string;
  currency: string;
}

export interface TrialActivateResponse {
  is_free: boolean;
  activated: boolean;
  duration_days: number;
  gateways: DurationGatewayPriceResponse[];
}

export interface PromocodeActivateResponse {
  success: boolean;
  reward_type: string;
}

export interface ReferralRewardLevelResponse {
  level: number;
  value: number;
}

export interface ReferralProgramResponse {
  enabled: boolean;
  referral_code: string;
  referral_link: string;
  invited_count: number;
  invited_with_payment_count: number;
  reward_type: string;
  reward_strategy: string;
  accrual_strategy: string;
  max_level: number;
  reward_levels: ReferralRewardLevelResponse[];
}
