import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { t } from "../i18n";
import { formatBytes, formatDuration, formatPrice, gbToBytes, isUnlimited } from "../format";
import { haptic, openPayment } from "../telegram";
import {
  Button,
  Empty,
  ErrorState,
  Options,
  Row,
  Skeleton,
  useAction,
  useResource,
  useToast,
  type OptionItem,
} from "../ui";
import type {
  DurationGatewayPriceResponse,
  PaymentGatewayType,
  PaymentInitResponse,
  PlanOfferResponse,
  SubscriptionOffersResponse,
} from "../types";

const GATEWAY_LABELS: Partial<Record<PaymentGatewayType, string>> = {
  TELEGRAM_STARS: "Telegram Stars",
  YOOKASSA: "ЮKassa",
  YOOMONEY: "ЮMoney",
  CRYPTOMUS: "Cryptomus",
  CRYPTOPAY: "CryptoPay",
  HELEKET: "Heleket",
  FREEKASSA: "FreeKassa",
  MULENPAY: "MulenPay",
  PAYMASTER: "PayMaster",
  PLATEGA: "Platega",
  ROBOKASSA: "Robokassa",
  VALUTIX: "Valutix",
  URLPAY: "UrlPay",
  WATA: "Wata",
};

const gatewayLabel = (type: PaymentGatewayType): string => GATEWAY_LABELS[type] ?? type;

function StoreHeader() {
  return (
    <header className="store-header">
      <h1>{t("store")}</h1>
    </header>
  );
}

function PlanList({
  plans,
  selected,
  onSelect,
}: {
  plans: PlanOfferResponse[];
  selected: string;
  onSelect: (code: string) => void;
}) {
  return (
    <div className="plan-list">
      {plans.map((plan) => {
        const isSelected = plan.public_code === selected;
        const devices = isUnlimited(plan.device_limit)
          ? `${t("devices")}: ${t("unlimited")}`
          : t("deviceCount", { count: String(plan.device_limit) });
        const traffic = `${t("traffic")}: ${
          isUnlimited(plan.traffic_limit)
            ? t("unlimited")
            : formatBytes(gbToBytes(plan.traffic_limit))
        }`;

        return (
          <button
            key={plan.public_code}
            type="button"
            className="plan-card"
            aria-pressed={isSelected}
            onClick={() => {
              haptic.select();
              onSelect(plan.public_code);
            }}
          >
            <span className="plan-card-head">
              <span className="plan-card-name">{plan.name}</span>
              <span className="plan-selection-indicator" aria-hidden="true">
                <span />
              </span>
            </span>
            {plan.description && (
              <span className="plan-card-description">{plan.description}</span>
            )}
            <span className="plan-card-features">
              <span>{devices}</span>
              <span>{traffic}</span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

export default function StoreScreen() {
  const offers = useResource(() => api.subscription.offers());

  if (offers.loading) {
    return (
      <div className="page store-page">
        <StoreHeader />
        <Skeleton height={120} />
        <Skeleton height={160} />
      </div>
    );
  }

  if (offers.error) {
    return (
      <div className="page store-page">
        <StoreHeader />
        <ErrorState onRetry={offers.reload} />
      </div>
    );
  }

  const data = offers.data!;

  if (data.gateways.length === 0) {
    return (
      <div className="page store-page">
        <StoreHeader />
        <Empty icon="💳" title={t("noGateways")} />
      </div>
    );
  }

  if (data.plans.length === 0) {
    return (
      <div className="page store-page">
        <StoreHeader />
        <Empty icon="📦" title={t("noSubscription")} hint={t("noSubscriptionHint")} />
      </div>
    );
  }

  return <StoreForm offers={data} onDone={offers.reload} />;
}

function StoreForm({
  offers,
  onDone,
}: {
  offers: SubscriptionOffersResponse;
  onDone: () => void;
}) {
  const toast = useToast();
  const [busy, perform] = useAction();

  // Default to the plan the backend recommends renewing, else the first one.
  const defaultPlan =
    offers.plans.find((plan) => plan.recommended_purchase_type === "RENEW") ?? offers.plans[0]!;

  const [planCode, setPlanCode] = useState<string>(defaultPlan.public_code);
  const [gateway, setGateway] = useState<PaymentGatewayType>(offers.gateways[0]!.gateway_type);
  const [days, setDays] = useState<number | null>(null);

  const plan = offers.plans.find((item) => item.public_code === planCode) ?? defaultPlan;

  // Prices are per gateway, so a duration is only offered if the selected
  // method has a price for it.
  const durations = useMemo(
    () =>
      plan.durations
        .map((duration) => ({
          days: duration.days,
          price: duration.prices.find((price) => price.gateway_type === gateway),
        }))
        .filter((entry): entry is { days: number; price: DurationGatewayPriceResponse } =>
          Boolean(entry.price),
        ),
    [plan, gateway],
  );

  // Reset the duration whenever the current one stops being available.
  useEffect(() => {
    if (days !== null && durations.some((entry) => entry.days === days)) return;
    setDays(durations[0]?.days ?? null);
  }, [durations, days]);

  const selected = durations.find((entry) => entry.days === days) ?? null;

  const durationItems: OptionItem<number>[] = durations.map(({ days: value, price }) => ({
    value,
    main: formatDuration(value),
    sub: price.is_free ? t("free") : formatPrice(price.final_amount, price.currency_symbol),
    ...(price.discount_percent > 0
      ? { badge: t("discount", { percent: String(price.discount_percent) }) }
      : {}),
  }));

  const gatewayItems: OptionItem<PaymentGatewayType>[] = offers.gateways.map((item) => ({
    value: item.gateway_type,
    main: gatewayLabel(item.gateway_type),
    sub: item.currency,
  }));

  const isRenew = plan.recommended_purchase_type === "RENEW";

  const pay = () =>
    perform(async () => {
      if (days === null) return;

      const payment: PaymentInitResponse = isRenew
        ? await api.subscription.extend(days, gateway)
        : await api.subscription.purchase(plan.public_code, days, gateway);

      if (payment.is_free || !payment.payment_url) {
        toast(t("paymentPaid"));
        onDone();
        return;
      }

      const status = await openPayment(payment.payment_url);

      if (status === "paid") {
        toast(t("paymentPaid"));
        onDone();
      } else if (status === "failed") {
        toast(t("paymentFailed"), "error");
      } else {
        // External gateways complete out of band; the webhook updates the
        // subscription, so just tell the user where to look.
        toast(t("paymentOpened"));
      }
    });

  return (
    <div className="page store-page">
      <StoreHeader />

      <section className="store-section" aria-labelledby="plans-title">
        <h2 className="store-section-title" id="plans-title">
          {t("choosePlan")}
        </h2>
        <PlanList plans={offers.plans} selected={planCode} onSelect={setPlanCode} />
      </section>

      <section className="store-section">
        <h2 className="store-section-title">{t("duration")}</h2>
        <Options items={durationItems} selected={days} onSelect={setDays} />
      </section>

      {offers.gateways.length > 1 && (
        <section className="store-section">
          <h2 className="store-section-title">{t("payWith")}</h2>
          <Options items={gatewayItems} selected={gateway} onSelect={setGateway} />
        </section>
      )}

      {selected && (
        <section className="store-checkout-card">
          <Row label={t("plan")} value={plan.name} />
          <Row label={t("duration")} value={formatDuration(selected.days)} />
          {selected.price.discount_percent > 0 && (
            <Row
              label={t("discount", { percent: String(selected.price.discount_percent) })}
              value={formatPrice(selected.price.original_amount, selected.price.currency_symbol)}
            />
          )}
          <Row
            label={t("total")}
            value={
              selected.price.is_free
                ? t("free")
                : formatPrice(selected.price.final_amount, selected.price.currency_symbol)
            }
          />
          <Button onClick={pay} busy={busy} disabled={days === null}>
            {selected.price.is_free
              ? t("free")
              : `${isRenew ? t("extend") : t("buy")} · ${formatPrice(
                  selected.price.final_amount,
                  selected.price.currency_symbol,
                )}`}
          </Button>
        </section>
      )}
    </div>
  );
}
