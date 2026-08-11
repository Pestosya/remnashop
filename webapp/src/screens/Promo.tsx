import { useState } from "react";
import { api } from "../api";
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
export default function PromoScreen({ onChanged }: { onChanged: () => void }) {
  const toast = useToast();
  const [code, setCode] = useState("");
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
      const trial = await api.subscription.trial();

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
          onSubmit={(event) => {
            event.preventDefault();
            applyPromocode();
          }}
          style={{ display: "flex", flexDirection: "column", gap: 10 }}
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

      <Card>
        <Button variant="ghost" onClick={startTrial} busy={busy}>
          {t("tryFree")}
        </Button>
      </Card>
    </>
  );
}
