import { useEffect, useRef, useState } from "react";
import { ApiError, api } from "../api";
import { t, type MessageKey } from "../i18n";
import { Button, Card } from "../ui";

const BOT_URL = "https://t.me/H2O_FreeNet_bot";

type Mode = "login" | "register";

/** Backend replies → messages a buyer can act on. */
function authError(cause: unknown, mode: Mode): MessageKey {
  if (!(cause instanceof ApiError)) return "errGeneric";
  if (cause.status === 401) return "errBadLogin";
  if (cause.status === 403) return "errBlocked";
  if (cause.status === 409 && mode === "register") return "errEmailTaken";
  if (cause.status === 422) return "errInvalid";
  return "errGeneric";
}

function mailError(cause: unknown): MessageKey {
  if (cause instanceof ApiError && cause.status === 503) return "errMailOff";
  if (cause instanceof ApiError && cause.status === 502) return "errMailFailed";
  return "errGeneric";
}

function Brand() {
  return (
    <div className="auth-brand">
      <a href="/" className="auth-logo">
        <span className="auth-drop" aria-hidden="true" />
        H2O <b>FreeNet</b>
      </a>
      <a href="/" className="auth-home">
        {t("toSite")}
      </a>
    </div>
  );
}

/** Email sign-in and sign-up for buyers who do not use the Telegram bot. */
export function AuthScreen({ onDone }: { onDone: () => void }) {
  const [mode, setMode] = useState<Mode>("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<MessageKey | null>(null);

  const canSubmit = /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email.trim()) &&
    (mode === "login" ? password.length > 0 : password.length >= 8);

  const submit = async () => {
    if (!canSubmit || busy) return;
    setBusy(true);
    setError(null);
    try {
      if (mode === "register") {
        await api.auth.register(email.trim(), password);
        // The code is needed before any purchase. If it did not go out, the next screen
        // asks again on arrival and shows why.
        const sent = await api.auth.requestCode().then(
          () => true,
          () => false,
        );
        if (sent) sessionStorage.setItem("codeSentAt", String(Date.now()));
        else sessionStorage.removeItem("codeSentAt");
      } else {
        await api.auth.login(email.trim(), password);
      }
      onDone();
    } catch (cause) {
      setError(authError(cause, mode));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page page--auth">
      <Brand />
      <div className="auth-head">
        <h1>{t("authTitle")}</h1>
        <p>{t("authSubtitle")}</p>
      </div>

      <Card>
        <div className="segmented" role="tablist">
          {(["register", "login"] as const).map((item) => (
            <button
              key={item}
              type="button"
              role="tab"
              aria-selected={mode === item}
              className="segment"
              data-active={mode === item || undefined}
              onClick={() => {
                setMode(item);
                setError(null);
              }}
            >
              {t(item === "login" ? "signIn" : "signUp")}
            </button>
          ))}
        </div>

        <form
          className="auth-form"
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          <label className="field">
            <span>{t("email")}</span>
            <input
              className="input"
              type="email"
              inputMode="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@example.com"
              required
            />
          </label>
          <label className="field">
            <span>{t("password")}</span>
            <input
              className="input"
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              minLength={mode === "register" ? 8 : undefined}
              required
            />
            {mode === "register" && <small>{t("passwordHint")}</small>}
          </label>

          {error && (
            <p className="auth-error" role="alert">
              {t(error)}
            </p>
          )}

          <Button type="submit" busy={busy} disabled={!canSubmit}>
            {t(mode === "login" ? "enter" : "createAccount")}
          </Button>

          {mode === "register" && (
            <p className="auth-terms">
              {t("termsPrefix")} <a href="/oferta/">{t("termsOffer")}</a> {t("termsAnd")}{" "}
              <a href="/privacy/">{t("termsPrivacy")}</a>
            </p>
          )}
        </form>
      </Card>

      <p className="auth-alt">
        {t("orTelegram")}{" "}
        <a href={BOT_URL} rel="noopener">
          {t("openBot")}
        </a>
      </p>
    </div>
  );
}

const RESEND_SECONDS = 60;

/** A web account must confirm its address before it can buy (the backend enforces it). */
export function VerifyEmailScreen({
  email,
  onDone,
  onLogout,
}: {
  email: string;
  onDone: () => void;
  onLogout: () => void;
}) {
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<MessageKey | null>(null);
  const [info, setInfo] = useState<MessageKey | null>(null);
  const [wait, setWait] = useState(0);
  const timer = useRef<number>();

  const startCooldown = () => {
    sessionStorage.setItem("codeSentAt", String(Date.now()));
    setWait(RESEND_SECONDS);
  };

  const send = async () => {
    setError(null);
    try {
      await api.auth.requestCode();
      setInfo("verifySent");
      startCooldown();
    } catch (cause) {
      setError(mailError(cause));
    }
  };

  // Send a code on arrival unless one went out a moment ago (sign-up does it, reloads must not spam).
  useEffect(() => {
    const sentAt = Number(sessionStorage.getItem("codeSentAt") || 0);
    const passed = Math.floor((Date.now() - sentAt) / 1000);
    if (passed < RESEND_SECONDS) setWait(RESEND_SECONDS - passed);
    else send();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (wait <= 0) return;
    timer.current = window.setTimeout(() => setWait((value) => value - 1), 1000);
    return () => window.clearTimeout(timer.current);
  }, [wait]);

  const confirm = async () => {
    if (code.length !== 6 || busy) return;
    setBusy(true);
    setError(null);
    try {
      await api.auth.confirmCode(code);
      sessionStorage.removeItem("codeSentAt");
      onDone();
    } catch {
      setError("errCode");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page page--auth">
      <Brand />
      <div className="auth-head">
        <h1>{t("verifyTitle")}</h1>
        <p>{t("verifyHint", { email })}</p>
      </div>

      <Card>
        <form
          className="auth-form"
          onSubmit={(event) => {
            event.preventDefault();
            confirm();
          }}
        >
          <label className="field">
            <span>{t("verifyCode")}</span>
            <input
              className="input input--code"
              inputMode="numeric"
              autoComplete="one-time-code"
              pattern="\d{6}"
              maxLength={6}
              value={code}
              onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
              placeholder="000000"
            />
          </label>

          {error && (
            <p className="auth-error" role="alert">
              {t(error)}
            </p>
          )}
          {!error && info && <p className="auth-info">{t(info)}</p>}

          <Button type="submit" busy={busy} disabled={code.length !== 6}>
            {t("verifyConfirm")}
          </Button>
          <Button variant="ghost" onClick={send} disabled={wait > 0}>
            {wait > 0 ? t("verifyResendIn", { count: String(wait) }) : t("verifyResend")}
          </Button>
        </form>
      </Card>

      <p className="auth-alt">
        {t("orTelegram")}{" "}
        <a href={BOT_URL} rel="noopener">
          {t("openBot")}
        </a>
      </p>
      <p className="auth-alt">
        <button type="button" className="linklike" onClick={onLogout}>
          {t("logout")}
        </button>
      </p>
    </div>
  );
}
