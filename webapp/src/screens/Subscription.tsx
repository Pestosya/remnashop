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
import { confirm, copy, haptic, openPayment } from "../telegram";
import {
  Button,
  Card,
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

export default function SubscriptionScreen({ extra }: { extra?: ReactNode }) {
  const navigate = useNavigate();
  const toast = useToast();
  const subscription = useResource(() => api.subscription.current());
  const [busy, perform] = useAction();

  if (subscription.loading) {
    return (
      <div className="page">
        <Skeleton height={150} />
        <Skeleton height={110} />
      </div>
    );
  }

  if (subscription.error) {
    return (
      <div className="page">
        <ErrorState onRetry={subscription.reload} />
        {extra}
      </div>
    );
  }

  const sub = subscription.data;

  if (!sub) {
    return (
      <div className="page">
        <Empty
          icon="🔒"
          title={t("noSubscription")}
          hint={t("noSubscriptionHint")}
          action={<Button onClick={() => navigate("/store")}>{t("choosePlan")}</Button>}
        />
        {extra}
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
      extra={extra}
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

  const connect = () =>
    perform(async () => {
      // The subscription URL is handled by the client apps, not by Telegram.
      await openPayment(sub.url);
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
    <div className="page">
      <Card>
        <div className="row">
          <div className="hero">
            <span className="hero-plan">{sub.plan_name}</span>
            <span className="hero-expiry">{formatExpiry(sub.expire_at)}</span>
          </div>
          <Status
            label={statusLabel(sub.status, expiresInPast)}
            tone={statusTone(sub.status, expiresInPast)}
          />
        </div>

        <Meter label={t("traffic")} detail={trafficDetail} ratio={ratio} />

        <div className="btn-row">
          <Button onClick={connect} busy={busy}>
            {t("connect")}
          </Button>
          <Button variant="secondary" onClick={() => navigate("/store")}>
            {t("extend")}
          </Button>
        </div>
      </Card>

      <Card title={t("subscription")}>
        <Row
          label={t("devices")}
          value={
            isUnlimited(sub.device_limit) ? t("unlimited") : String(sub.device_limit)
          }
        />
        <Row label={t("plan")} value={formatDuration(sub.plan_duration_days)} />
        {sub.is_trial && <Row label={t("trial")} value="✓" />}
      </Card>

      <Card title={t("yourLink")}>
        <div className="link-box">
          <span>{sub.url}</span>
        </div>
        <div className="btn-row">
          <Button variant="secondary" onClick={copyLink} busy={busy}>
            {t("copyLink")}
          </Button>
        </div>
        <Button variant="danger" onClick={reissue} busy={busy}>
          {t("reissue")}
        </Button>
      </Card>

      {extra}
    </div>
  );
}
