import { useState } from "react";
import { ApiError, api } from "../api";
import { t } from "../i18n";
import { openPayment } from "../telegram";
import { Button, Card, useAction, useToast } from "../ui";

/**
 * Promo code entry plus trial activation.
 *
 * The trial endpoint answers in two shapes: `is_free` means it was activated
 * outright, otherwise it returns the gateways a paid trial can be bought
 * through and a second call is needed.
 */
export default function PromoScreen({
  onChanged,
  showTrial,
}: {
  onChanged: () => void;
  showTrial: boolean;
}) {
  const toast = useToast();
  const [code, setCode] = useState("");
  const [trialUnavailable, setTrialUnavailable] = useState(false);
  const [busy, perform] = useAction();

  const applyPromocode = () =>
    perform(async () => {
      const trimmed = code.trim();
      if (!trimmed) return;

      await api.subscription.promocode(trimmed);
      toast(t("promocodeApplied"));
      setCode("");
      onChanged();
    });

  const startTrial = () =>
    perform(async () => {
      let trial;
      try {
        trial = await api.subscription.trial();
      } catch (cause) {
        if (cause instanceof ApiError && cause.status === 409) {
          setTrialUnavailable(true);
        }
        throw cause;
      }

      if (trial.activated) {
        toast(t("trialActivated"));
        onChanged();
        return;
      }

      const gateway = trial.gateways[0];
      if (!gateway) {
        toast(t("noGateways"), "error");
        return;
      }

      const payment = await api.subscription.trialPurchase(gateway.gateway_type);

      if (payment.is_free || !payment.payment_url) {
        toast(t("trialActivated"));
        onChanged();
        return;
      }

      const status = await openPayment(payment.payment_url);
      if (status === "paid") {
        toast(t("paymentPaid"));
        onChanged();
      } else {
        toast(t("paymentOpened"));
      }
    });

  return (
    <>
      <Card title={t("promocode")}>
        <form
          className="promocode-form"
          onSubmit={(event) => {
            event.preventDefault();
            applyPromocode();
          }}
        >
          <input
            className="input"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            placeholder={t("promocodePlaceholder")}
            autoCapitalize="characters"
            autoCorrect="off"
            spellCheck={false}
            enterKeyHint="done"
          />
          <Button type="submit" variant="secondary" busy={busy} disabled={!code.trim()}>
            {t("activate")}
          </Button>
        </form>
      </Card>

      {showTrial && !trialUnavailable && (
        <Card>
          <Button variant="ghost" onClick={startTrial} busy={busy}>
            {t("tryFree")}
          </Button>
        </Card>
      )}
    </>
  );
}
