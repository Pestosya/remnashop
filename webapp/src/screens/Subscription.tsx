import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { t } from "../i18n";
import {
  formatBytes,
  formatDuration,
  formatExpiry,
  gbToBytes,
  isUnlimited,
  trafficRatio,
} from "../format";
import { confirm, copy, haptic } from "../telegram";
import {
  Button,
  Empty,
  ErrorState,
  Meter,
  Row,
  Skeleton,
  Status,
  useAction,
  useResource,
  useToast,
} from "../ui";
import type { SubscriptionInfoResponse } from "../types";

type SubscriptionExtra = (options: { showTrial: boolean }) => ReactNode;

function SubscriptionHeader() {
  return (
    <header className="subscription-header">
      <img
        className="subscription-brand-mark"
        src="/app/h2o-logo.png"
        alt=""
        aria-hidden="true"
      />
      <span className="subscription-brand-name">H2O-FreeNet</span>
    </header>
  );
}

function statusTone(status: string, expiresInPast: boolean): "ok" | "danger" | "muted" {
  if (expiresInPast || status === "EXPIRED") return "danger";
  if (status === "LIMITED") return "danger";
  if (status === "DISABLED") return "muted";
  return "ok";
}

function statusLabel(status: string, expiresInPast: boolean): string {
  if (expiresInPast || status === "EXPIRED") return t("expired");
  if (status === "LIMITED") return t("limited");
  if (status === "DISABLED") return t("disabled");
  return t("active");
}

export default function SubscriptionScreen({ extra }: { extra?: SubscriptionExtra }) {
  const navigate = useNavigate();
  const toast = useToast();
  const subscription = useResource(() => api.subscription.current());
  const [busy, perform] = useAction();

  if (subscription.loading) {
    return (
      <div className="page subscription-page">
        <SubscriptionHeader />
        <Skeleton height={150} />
        <Skeleton height={110} />
      </div>
    );
  }

  if (subscription.error) {
    return (
      <div className="page subscription-page">
        <SubscriptionHeader />
        <ErrorState onRetry={subscription.reload} />
        {extra?.({ showTrial: false })}
      </div>
    );
  }

  const sub = subscription.data;

  if (!sub) {
    return (
      <div className="page subscription-page">
        <SubscriptionHeader />
        <Empty
          icon="🔒"
          title={t("noSubscription")}
          hint={t("noSubscriptionHint")}
          action={<Button onClick={() => navigate("/store")}>{t("choosePlan")}</Button>}
        />
        {extra?.({ showTrial: true })}
      </div>
    );
  }

  return (
    <SubscriptionView
      sub={sub}
      busy={busy}
      perform={perform}
      onChanged={subscription.reload}
      toast={toast}
      extra={extra?.({ showTrial: false })}
    />
  );
}

function SubscriptionView({
  sub,
  busy,
  perform,
  onChanged,
  toast,
  extra,
}: {
  sub: SubscriptionInfoResponse;
  busy: boolean;
  perform: (run: () => Promise<void>) => Promise<void>;
  onChanged: () => void;
  toast: (message: string, tone?: "info" | "error") => void;
  extra?: ReactNode;
}) {
  const navigate = useNavigate();
  const expiresInPast = new Date(sub.expire_at).getTime() < Date.now();
  const used = sub.used_traffic_bytes ?? 0;
  const ratio = trafficRatio(sub.used_traffic_bytes, sub.traffic_limit);

  const trafficDetail = isUnlimited(sub.traffic_limit)
    ? `${formatBytes(used)} · ${t("unlimited")}`
    : t("trafficUsed", {
        used: formatBytes(used),
        limit: formatBytes(gbToBytes(sub.traffic_limit)),
      });

  const copyLink = () =>
    perform(async () => {
      const ok = await copy(sub.url);
      toast(ok ? t("copied") : t("loadFailed"), ok ? "info" : "error");
    });

  const reissue = () =>
    perform(async () => {
      if (!(await confirm(t("reissueConfirm")))) return;
      await api.subscription.reissue();
      haptic.success();
      toast(t("reissued"));
      onChanged();
    });

  return (
    <div className="page subscription-page">
      <SubscriptionHeader />

      <section className="subscription-hero-card">
        <div className="subscription-hero-top">
          <div className="subscription-plan-summary">
            <span className="subscription-eyebrow">{t("plan")}</span>
            <span className="subscription-plan-name">{sub.plan_name}</span>
            <span className="subscription-expiry">{formatExpiry(sub.expire_at)}</span>
          </div>
          <Status
            label={statusLabel(sub.status, expiresInPast)}
            tone={statusTone(sub.status, expiresInPast)}
          />
        </div>

        <Meter label={t("traffic")} detail={trafficDetail} ratio={ratio} />

        <div className="subscription-renew-action">
          <Button onClick={() => navigate("/store")}>
            {t("extend")}
          </Button>
        </div>
      </section>

      <section className="subscription-card subscription-info-card">
        <h2 className="card-title">{t("subscription")}</h2>
        <Row
          label={t("devices")}
          value={
            isUnlimited(sub.device_limit) ? t("unlimited") : String(sub.device_limit)
          }
        />
        <Row label={t("plan")} value={sub.plan_name} />
        <Row label={t("duration")} value={formatDuration(sub.plan_duration_days)} />
        {sub.is_trial && <Row label={t("trial")} value="✓" />}
      </section>

      <section className="subscription-card subscription-link-card">
        <h2 className="card-title">{t("yourLink")}</h2>
        <div className="link-box subscription-link-box">
          <span>{sub.url}</span>
        </div>
        <div className="subscription-copy-action">
          <Button variant="secondary" onClick={copyLink} busy={busy}>
            {t("copy")}
          </Button>
        </div>
        <Button variant="danger" onClick={reissue} busy={busy}>
          {t("reissue")}
        </Button>
      </section>

      {extra}
    </div>
  );
}
