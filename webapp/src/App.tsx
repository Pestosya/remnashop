import { useEffect, useState } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, login } from "./api";
import { setLocale, t } from "./i18n";
import { isTelegram, ready, showBackButton } from "./telegram";
import { Empty, Skeleton, ToastProvider } from "./ui";
import SubscriptionScreen from "./screens/Subscription";
import DevicesScreen from "./screens/Devices";
import StoreScreen from "./screens/Store";
import ReferralScreen from "./screens/Referral";
import PromoScreen from "./screens/Promo";

type Boot = "loading" | "ready" | "unauthorized";

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

  return (
    <>
      <SubscriptionScreen key={nonce} />
      <div className="page" style={{ paddingTop: 0 }}>
        <PromoScreen onChanged={() => setNonce((value) => value + 1)} />
      </div>
    </>
  );
}

export default function App() {
  const [boot, setBoot] = useState<Boot>("loading");

  useEffect(() => {
    ready();

    (async () => {
      if (!isTelegram()) {
        setBoot("unauthorized");
        return;
      }

      // A cookie from an earlier visit may still be valid; only sign in anew
      // when it is not.
      try {
        const me = await api.me();
        setLocale(me.language);
        setBoot("ready");
        return;
      } catch {
        // Fall through to a fresh initData login.
      }

      if (!(await login())) {
        setBoot("unauthorized");
        return;
      }

      try {
        const me = await api.me();
        setLocale(me.language);
      } catch {
        // Session works even if the profile call hiccups; keep the default locale.
      }
      setBoot("ready");
    })();
  }, []);

  if (boot === "loading") {
    return (
      <div className="page">
        <Skeleton height={150} />
        <Skeleton height={110} />
        <Skeleton height={110} />
      </div>
    );
  }

  if (boot === "unauthorized") {
    return (
      <div className="page">
        <Empty icon="🔐" title={t("openInTelegram")} />
      </div>
    );
  }

  return (
    <ToastProvider>
      <BackButton />
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
