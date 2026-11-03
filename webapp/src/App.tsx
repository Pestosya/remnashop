import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, login } from "./api";
import type { MeResponse } from "./types";
import { isDemo } from "./demo";
import { setLocale, t } from "./i18n";
import { isTelegram, ready, showBackButton } from "./telegram";
import { Empty, Skeleton, ToastProvider, useToast } from "./ui";
import { AuthScreen, VerifyEmailScreen } from "./screens/Auth";
import SubscriptionScreen from "./screens/Subscription";
import DevicesScreen from "./screens/Devices";
import StoreScreen from "./screens/Store";
import ReferralScreen from "./screens/Referral";
import PromoScreen from "./screens/Promo";

type Boot = "loading" | "ready" | "unauthorized" | "signin";

const REFRESH_EVENT = "h2o:refresh";

const TABS = [
  { to: "/", icon: "🛡", key: "subscription" },
  { to: "/devices", icon: "📱", key: "devices" },
  { to: "/store", icon: "✨", key: "store" },
  { to: "/referral", icon: "🤝", key: "referral" },
] as const;

function TabBar() {
  return (
    <nav className="tabs">
      {TABS.map((tab) => (
        <NavLink key={tab.to} to={tab.to} end={tab.to === "/"} className="tab">
          <span className="tab-icon">{tab.icon}</span>
          <span>{t(tab.key)}</span>
        </NavLink>
      ))}
    </nav>
  );
}

/** Telegram's own back button drives navigation on every screen but the root. */
function BackButton() {
  const location = useLocation();
  const navigate = useNavigate();
  const isRoot = location.pathname === "/";

  useEffect(() => {
    if (isRoot) return;
    return showBackButton(() => navigate(-1));
  }, [isRoot, navigate]);

  return null;
}

/** The promo card lives on the subscription tab, below the current state. */
function SubscriptionTab() {
  const [nonce, setNonce] = useState(0);

  // Back from the payment page: the webhook lands a few seconds later, so look again.
  useEffect(() => {
    const bump = () => setNonce((value) => value + 1);
    window.addEventListener(REFRESH_EVENT, bump);
    return () => window.removeEventListener(REFRESH_EVENT, bump);
  }, []);

  return (
    <SubscriptionScreen
      key={nonce}
      extra={<PromoScreen onChanged={() => setNonce((value) => value + 1)} />}
    />
  );
}

/** `?paid=1`: the payment page sent a website buyer back. */
function PaidNotice() {
  const toast = useToast();
  const location = useLocation();
  const navigate = useNavigate();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    if (!params.has("paid")) return;
    toast(t("paymentReturned"));
    params.delete("paid");
    navigate({ search: params.toString() }, { replace: true });
    const timers = [3000, 8000, 15000].map((ms) =>
      window.setTimeout(() => window.dispatchEvent(new Event(REFRESH_EVENT)), ms),
    );
    return () => timers.forEach((id) => window.clearTimeout(id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return null;
}

/** Who is signed in on the website, and the way out. Telegram has its own chrome. */
function WebBar({ me, onLogout }: { me: MeResponse | null; onLogout: () => void }) {
  return (
    <div className="webbar">
      <a href="/" className="webbar-home">
        <span className="auth-drop" aria-hidden="true" />
        H2O
      </a>
      <span className="webbar-user">{me?.email ?? me?.name ?? ""}</span>
      <button type="button" className="linklike" onClick={onLogout}>
        {t("logout")}
      </button>
    </div>
  );
}

export default function App() {
  const [boot, setBoot] = useState<Boot>("loading");
  const [me, setMe] = useState<MeResponse | null>(null);
  const [nonce, setNonce] = useState(0);

  const restart = () => {
    setBoot("loading");
    setNonce((value) => value + 1);
  };

  const logout = async () => {
    await api.auth.logout().catch(() => undefined);
    setMe(null);
    restart();
  };

  useEffect(() => {
    ready();

    const signedIn = (profile: MeResponse) => {
      setMe(profile);
      setLocale(profile.language);
      setBoot("ready");
    };

    (async () => {
      // Offline preview: fixtures stand in for the API, so skip the handshake.
      if (isDemo()) {
        api.me().then(signedIn);
        setBoot("ready");
        return;
      }

      // The website: an email session from an earlier visit, or the sign-in screen.
      if (!isTelegram()) {
        try {
          signedIn(await api.me());
        } catch {
          setBoot("signin");
        }
        return;
      }

      // A cookie from an earlier visit may still be valid; only sign in anew
      // when it is not.
      try {
        signedIn(await api.me());
        return;
      } catch {
        // Fall through to a fresh initData login.
      }

      if (!(await login())) {
        setBoot("unauthorized");
        return;
      }

      try {
        signedIn(await api.me());
      } catch {
        // Session works even if the profile call hiccups; keep the default locale.
        setBoot("ready");
      }
    })();
  }, [nonce]);

  const onWebsite = !isTelegram() && !isDemo();

  if (boot === "loading") {
    return (
      <div className="page">
        <Skeleton height={150} />
        <Skeleton height={110} />
        <Skeleton height={110} />
      </div>
    );
  }

  if (boot === "signin") {
    return <AuthScreen onDone={restart} />;
  }

  // Buying needs a confirmed address; a Telegram account has none and needs none.
  if (onWebsite && me && !me.telegram_id && !me.is_email_verified && me.email) {
    return <VerifyEmailScreen email={me.email} onDone={restart} onLogout={logout} />;
  }

  if (boot === "unauthorized") {
    return (
      <div className="page">
        <Empty
          icon="🔐"
          title={t("openInTelegram")}
          hint="Для локального просмотра откройте страницу с ?demo=1"
        />
      </div>
    );
  }

  return (
    <ToastProvider>
      <BackButton />
      <PaidNotice />
      {onWebsite && <WebBar me={me} onLogout={logout} />}
      <Routes>
        <Route path="/" element={<SubscriptionTab />} />
        <Route path="/devices" element={<DevicesScreen />} />
        <Route path="/store" element={<StoreScreen />} />
        <Route path="/referral" element={<ReferralScreen />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <TabBar />
    </ToastProvider>
  );
}
