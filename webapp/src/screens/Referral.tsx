import { ApiError, api } from "../api";
import { formatExtraDays, formatNumber, formatPoints, t } from "../i18n";
import { copy, shareLink } from "../telegram";
import type { ReferralProgramResponse, ReferralRewardLevelResponse } from "../types";
import {
  Button,
  Empty,
  ErrorState,
  Skeleton,
  useAction,
  useResource,
  useToast,
} from "../ui";

/** Turns the endpoint's 403 detail into a localized explanation. */
function gateReason(error: Error): string | null {
  const fallbackStatus = (error as Error & { status?: unknown }).status;
  const status = error instanceof ApiError ? error.status : fallbackStatus;
  if (status !== 403) return null;

  const detail = error.message.toLowerCase();
  if (detail.includes("disabled")) return t("referralDisabled");
  if (detail.includes("subscription")) return t("referralNeedsSubscription");
  if (detail.includes("email")) return t("referralNeedsEmail");

  return t("referralDisabled");
}

function readBonusBalance(value: number | undefined): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

/** Only labels reward units whose meaning is explicit in the API response. */
function formatReward(
  program: ReferralProgramResponse,
  level: ReferralRewardLevelResponse,
): string | null {
  const rewardStrategy = program.reward_strategy.toUpperCase();
  const rewardType = program.reward_type.toUpperCase();

  if (rewardStrategy === "PERCENT") return `${formatNumber(level.value)}%`;
  if (rewardStrategy !== "AMOUNT") return null;
  if (rewardType === "POINTS") return formatPoints(level.value);
  if (rewardType === "EXTRA_DAYS") return formatExtraDays(level.value);

  return null;
}

function accrualRule(strategy: string): string | null {
  if (strategy.toUpperCase() === "ON_EACH_PAYMENT") return t("referralRuleEachPayment");
  if (strategy.toUpperCase() === "ON_FIRST_PAYMENT") return t("referralRuleFirstPayment");
  return null;
}

function levelRule(level: ReferralRewardLevelResponse, reward: string): string {
  if (level.level === 1) return t("referralRuleFirstLevel", { reward });
  if (level.level === 2) return t("referralRuleSecondLevel", { reward });
  return t("referralRuleLevel", {
    level: formatNumber(level.level),
    reward,
  });
}

function CrystalIcon() {
  return (
    <svg
      className="referral-crystal-icon"
      viewBox="0 0 48 48"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="m14 8-7 10 17 22 17-22-7-10H14Z" />
      <path d="m7 18 17 6 17-6M14 8l10 16L34 8M24 24v16" />
    </svg>
  );
}

function ReferralHeader({ firstLevelReward }: { firstLevelReward?: string }) {
  return (
    <header className="referral-header">
      <span className="referral-eyebrow">{t("referralProgram")}</span>
      <h1>{t("referralTitle")}</h1>
      <p>{t("referralHint")}</p>
      {firstLevelReward && (
        <span className="referral-reward-summary">
          {t("referralRewardSummary", { reward: firstLevelReward })}
        </span>
      )}
    </header>
  );
}

function BalanceCard({ balance }: { balance: number }) {
  return (
    <article className="referral-balance-card">
      <span className="referral-crystal">
        <CrystalIcon />
      </span>
      <span className="referral-balance-copy">
        <span className="referral-stat-label">{t("availableBonusBalance")}</span>
        <strong>{formatPoints(balance)}</strong>
        <span className="referral-balance-hint">{t("bonusBalanceHint")}</span>
      </span>
    </article>
  );
}

export default function ReferralScreen() {
  const profile = useResource(() => api.me());
  const program = useResource(() => api.referral());
  const [busy, perform] = useAction();
  const toast = useToast();

  const profileBalance = readBonusBalance(profile.data?.available_bonus_balance);
  const programBalance = readBonusBalance(program.data?.available_bonus_balance);
  const bonusBalance = profileBalance ?? programBalance;

  if (program.loading) {
    return (
      <div className="page referral-page">
        <ReferralHeader />
        <div className="referral-loading-stats">
          <Skeleton height={112} />
          <Skeleton height={112} />
        </div>
        {bonusBalance !== undefined ? <BalanceCard balance={bonusBalance} /> : <Skeleton height={130} />}
        <Skeleton height={176} />
      </div>
    );
  }

  if (program.error) {
    // A 403 here is a rule, not a failure: the program can be switched off, or
    // require an active subscription. Showing "retry" for those is misleading.
    const reason = gateReason(program.error);
    return (
      <div className="page referral-page">
        <ReferralHeader />
        {bonusBalance !== undefined && <BalanceCard balance={bonusBalance} />}
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
      <div className="page referral-page">
        <ReferralHeader />
        {bonusBalance !== undefined && <BalanceCard balance={bonusBalance} />}
        <Empty icon="🤝" title={t("referralDisabled")} />
      </div>
    );
  }

  const link = data.referral_link;
  const rewardLevels = data.reward_levels
    .map((level) => ({ level, reward: formatReward(data, level) }))
    .filter((entry): entry is { level: ReferralRewardLevelResponse; reward: string } =>
      Boolean(entry.reward),
    );
  const firstLevelReward =
    rewardLevels.find((entry) => entry.level.level === 1)?.reward ?? rewardLevels[0]?.reward;
  const paymentRule = accrualRule(data.accrual_strategy);

  const copyCode = () =>
    perform(async () => {
      const ok = await copy(link);
      toast(ok ? t("copied") : t("loadFailed"), ok ? "info" : "error");
    });

  return (
    <div className="page referral-page">
      <ReferralHeader firstLevelReward={firstLevelReward} />

      <section className="referral-stats" aria-label={t("referralStats")}>
        <article className="referral-stat-card">
          <span className="referral-stat-label">{t("invited")}</span>
          <strong>{formatNumber(data.invited_count)}</strong>
        </article>
        <article className="referral-stat-card">
          <span className="referral-stat-label">{t("invitedPaid")}</span>
          <strong>{formatNumber(data.invited_with_payment_count)}</strong>
        </article>

        {bonusBalance !== undefined && <BalanceCard balance={bonusBalance} />}
      </section>

      <section className="referral-link-card">
        <div className="referral-card-heading">
          <h2>{t("yourLink")}</h2>
          <p>{t("referralLinkHint")}</p>
        </div>
        <div className="link-box referral-link-box" title={link}>
          <span>{link}</span>
        </div>
        <div className="referral-actions">
          <Button onClick={() => shareLink(link, t("referralHint"))}>{t("share")}</Button>
          <Button variant="secondary" onClick={copyCode} busy={busy}>
            {t("copy")}
          </Button>
        </div>
      </section>

      <section className="referral-rules-card">
        <div className="referral-card-heading">
          <h2>{t("referralRules")}</h2>
        </div>
        <ul className="referral-rules-list">
          <li>{t("referralRuleLink")}</li>
          {paymentRule && <li>{paymentRule}</li>}
          <li>{t("referralRuleLevels")}</li>
          {rewardLevels.map(({ level, reward }) => (
            <li key={level.level}>{levelRule(level, reward)}</li>
          ))}
          {rewardLevels.length === 0 && <li>{t("referralRuleProgram")}</li>}
          <li>{t("referralRuleFullPayment")}</li>
          <li>{t("referralRuleNoPartial")}</li>
          <li>{t("referralRuleBotPayment")}</li>
        </ul>
      </section>
    </div>
  );
}
