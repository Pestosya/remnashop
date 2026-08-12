import { ApiError, api } from "../api";
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

/** Turns the endpoint's 403 detail into a localized explanation. */
function gateReason(error: Error): string | null {
  if (!(error instanceof ApiError) || error.status !== 403) return null;

  const detail = error.message.toLowerCase();
  if (detail.includes("disabled")) return t("referralDisabled");
  if (detail.includes("subscription")) return t("referralNeedsSubscription");
  if (detail.includes("email")) return t("referralNeedsEmail");

  return t("referralDisabled");
}

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
    // A 403 here is a rule, not a failure: the program can be switched off, or
    // require an active subscription. Showing "retry" for those is misleading.
    const reason = gateReason(program.error);
    return (
      <div className="page">
        {reason ? (
          <Empty icon="🤝" title={reason} />
        ) : (
          <ErrorState onRetry={program.reload} />
        )}
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
            {t("copy")}
          </Button>
        </div>
      </Card>
    </div>
  );
}
