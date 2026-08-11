import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { haptic } from "./telegram";
import { t } from "./i18n";

/* ---------------- toast ---------------- */

interface ToastState {
  message: string;
  tone: "info" | "error";
}

const ToastContext = createContext<(message: string, tone?: "info" | "error") => void>(() => {});

export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toast, setToast] = useState<ToastState | null>(null);
  const timer = useRef<number>();

  const show = useCallback((message: string, tone: "info" | "error" = "info") => {
    setToast({ message, tone });
    if (tone === "error") haptic.error();
    else haptic.success();

    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setToast(null), 2600);
  }, []);

  useEffect(() => () => window.clearTimeout(timer.current), []);

  return (
    <ToastContext.Provider value={show}>
      {children}
      {toast && (
        <div className="toast" data-tone={toast.tone} role="status" aria-live="polite">
          {toast.message}
        </div>
      )}
    </ToastContext.Provider>
  );
}

/* ---------------- primitives ---------------- */

export function Card({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <section className="card">
      {title && <h2 className="card-title">{title}</h2>}
      {children}
    </section>
  );
}

export function Row({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="row">
      <span className="row-label">{label}</span>
      <span className="row-value">{value}</span>
    </div>
  );
}

type ButtonProps = {
  children: ReactNode;
  onClick?: () => void;
  variant?: "primary" | "secondary" | "ghost" | "danger";
  disabled?: boolean;
  busy?: boolean;
  type?: "button" | "submit";
};

export function Button({
  children,
  onClick,
  variant = "primary",
  disabled,
  busy,
  type = "button",
}: ButtonProps) {
  return (
    <button
      type={type}
      className="btn"
      data-variant={variant}
      disabled={disabled || busy}
      onClick={
        onClick &&
        (() => {
          haptic.tap();
          onClick();
        })
      }
    >
      {busy ? "…" : children}
    </button>
  );
}

export function Status({ label, tone }: { label: string; tone: "ok" | "danger" | "muted" }) {
  return (
    <span className="status" data-tone={tone === "ok" ? undefined : tone}>
      <span className="status-dot" />
      {label}
    </span>
  );
}

export function Meter({
  label,
  detail,
  ratio,
}: {
  label: string;
  detail: string;
  ratio: number | null;
}) {
  return (
    <div className="meter">
      <div className="meter-head">
        <span className="row-label">{label}</span>
        <span>{detail}</span>
      </div>
      {ratio !== null && (
        <div className="meter-track">
          <div
            className="meter-fill"
            data-tone={ratio >= 0.9 ? "danger" : undefined}
            style={{ width: `${Math.round(ratio * 100)}%` }}
          />
        </div>
      )}
    </div>
  );
}

export function Empty({
  icon,
  title,
  hint,
  action,
}: {
  icon: string;
  title: string;
  hint?: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="empty-icon">{icon}</div>
      <div className="empty-title">{title}</div>
      {hint && <div>{hint}</div>}
      {action && <div style={{ marginTop: 12 }}>{action}</div>}
    </div>
  );
}

export function Skeleton({ height = 96 }: { height?: number }) {
  return <div className="skeleton" style={{ height }} />;
}

export function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <Empty
      icon="⚠️"
      title={t("loadFailed")}
      action={
        <Button variant="secondary" onClick={onRetry}>
          {t("retry")}
        </Button>
      }
    />
  );
}

/* ---------------- option pickers ---------------- */

export interface OptionItem<T> {
  value: T;
  main: string;
  sub?: string;
  badge?: string;
}

export function Options<T extends string | number>({
  items,
  selected,
  onSelect,
}: {
  items: OptionItem<T>[];
  selected: T | null;
  onSelect: (value: T) => void;
}) {
  return (
    <div className="options">
      {items.map((item) => (
        <button
          key={String(item.value)}
          type="button"
          className="option"
          aria-pressed={item.value === selected}
          onClick={() => {
            haptic.select();
            onSelect(item.value);
          }}
        >
          {item.badge && <span className="option-badge">{item.badge}</span>}
          <span className="option-main">{item.main}</span>
          {item.sub && <span className="option-sub">{item.sub}</span>}
        </button>
      ))}
    </div>
  );
}

/* ---------------- data loading ---------------- */

export interface Resource<T> {
  data: T | undefined;
  error: Error | undefined;
  loading: boolean;
  reload: () => void;
}

/**
 * Loads once on mount and on demand. Deliberately tiny: the cabinet has a
 * handful of endpoints and no cross-screen cache to justify a query library.
 */
export function useResource<T>(loader: () => Promise<T>, deps: unknown[] = []): Resource<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(true);
  const [nonce, setNonce] = useState(0);

  // Keeps the effect from depending on a fresh closure every render.
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    loaderRef
      .current()
      .then((value) => {
        if (cancelled) return;
        setData(value);
        setError(undefined);
      })
      .catch((cause: Error) => {
        if (!cancelled) setError(cause);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nonce, ...deps]);

  const reload = useCallback(() => setNonce((n) => n + 1), []);

  return useMemo(() => ({ data, error, loading, reload }), [data, error, loading, reload]);
}

/** Tracks an in-flight action and funnels failures into a toast. */
export function useAction(): [boolean, (run: () => Promise<void>) => Promise<void>] {
  const [busy, setBusy] = useState(false);
  const toast = useToast();

  const perform = useCallback(
    async (run: () => Promise<void>) => {
      if (busy) return;
      setBusy(true);
      try {
        await run();
      } catch (cause) {
        toast(cause instanceof Error ? cause.message : String(cause), "error");
      } finally {
        setBusy(false);
      }
    },
    [busy, toast],
  );

  return [busy, perform];
}
