import { api } from "../api";
import { t } from "../i18n";
import { copy, shareLink } from "../telegram";
import {
  Button,
  Card,
  Empty,
  ErrorState,
  Skeleton,
  useAction,
  useResource,
  useToast,
} from "../ui";

export default function ReferralScreen() {
  const program = useResource(() => api.referral());
  const [busy, perform] = useAction();
  const toast = useToast();

  if (program.loading) {
    return (
      <div className="page">
        <Skeleton height={120} />
        <Skeleton height={90} />
      </div>
    );
  }

  if (program.error) {
    return (
      <div className="page">
        <ErrorState onRetry={program.reload} />
      </div>
    );
  }

  const data = program.data!;

  if (!data.enabled) {
    return (
      <div className="page">
        <Empty icon="🤝" title={t("referralDisabled")} />
      </div>
    );
  }

  const link = data.referral_link;

  const copyCode = () =>
    perform(async () => {
      const ok = await copy(link);
      toast(ok ? t("copied") : t("loadFailed"), ok ? "info" : "error");
    });

  return (
    <div className="page">
      <Card>
        <div className="hero">
          <span className="hero-plan">{t("referralTitle")}</span>
          <span className="hero-expiry">{t("referralHint")}</span>
        </div>

        <div className="stats">
          <div className="stat">
            <div className="stat-value">{data.invited_count}</div>
            <div className="stat-label">{t("invited")}</div>
          </div>
          <div className="stat">
            <div className="stat-value">{data.invited_with_payment_count}</div>
            <div className="stat-label">{t("invitedPaid")}</div>
          </div>
        </div>
      </Card>

      <Card title={t("yourLink")}>
        <div className="link-box">
          <span>{link}</span>
        </div>
        <div className="btn-row">
          <Button onClick={() => shareLink(link, t("referralHint"))}>{t("share")}</Button>
          <Button variant="secondary" onClick={copyCode} busy={busy}>
            {t("copyLink")}
          </Button>
        </div>
      </Card>
    </div>
  );
}
