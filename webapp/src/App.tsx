import { useEffect, useState, type ReactNode } from "react";
import { NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { api, login } from "./api";
import { isDemo } from "./demo";
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
  { to: "/", icon: "shield", key: "subscription" },
  { to: "/devices", icon: "device", key: "devices" },
  { to: "/store", icon: "tag", key: "store" },
  { to: "/referral", icon: "friends", key: "referral" },
] as const;

type TabIconName = (typeof TABS)[number]["icon"];

const TAB_ICON_PATHS: Record<TabIconName, ReactNode> = {
  shield: (
    <>
      <path d="M12 3 4.75 6v5.25c0 4.45 2.95 7.55 7.25 9.75 4.3-2.2 7.25-5.3 7.25-9.75V6L12 3Z" />
      <path d="m8.8 12 2.05 2.05L15.5 9.4" />
    </>
  ),
  device: (
    <>
      <rect x="6.25" y="2.5" width="11.5" height="19" rx="2.5" />
      <path d="M10 5h4M10 18.5h4" />
    </>
  ),
  tag: (
    <>
      <path d="M20.5 13.25 13.25 20.5 3.5 10.75V3.5h7.25l9.75 9.75Z" />
      <circle cx="8" cy="8" r="1.25" />
    </>
  ),
  friends: (
    <>
      <circle cx="9" cy="8" r="3" />
      <path d="M3.75 19c.35-3.35 2.1-5 5.25-5s4.9 1.65 5.25 5" />
      <path d="M15.25 5.4a3 3 0 0 1 0 5.2M16.25 13.75c2.4.35 3.7 1.75 4 4.25" />
    </>
  ),
};

function TabIcon({ name }: { name: TabIconName }) {
  return (
    <svg
      className="tab-icon"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {TAB_ICON_PATHS[name]}
    </svg>
  );
}

function TabBar() {
  return (
    <nav className="tabs">
      {TABS.map((tab) => (
        <NavLink key={tab.to} to={tab.to} end={tab.to === "/"} className="tab">
          <TabIcon name={tab.icon} />
          <span className="tab-label">{t(tab.key)}</span>
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
    <SubscriptionScreen
      key={nonce}
      extra={({ showTrial }) => (
        <PromoScreen
          onChanged={() => setNonce((value) => value + 1)}
          showTrial={showTrial}
        />
      )}
    />
  );
}

export default function App() {
  const [boot, setBoot] = useState<Boot>("loading");

  useEffect(() => {
    ready();

    (async () => {
      // Offline preview: fixtures stand in for the API, so skip the handshake.
      if (isDemo()) {
        api.me().then((me) => setLocale(me.language));
        setBoot("ready");
        return;
      }

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
