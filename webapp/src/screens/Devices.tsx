import { api } from "../api";
import { t } from "../i18n";
import { isUnlimited, platformIcon } from "../format";
import { confirm, openPayment } from "../telegram";
import {
  Button,
  Empty,
  ErrorState,
  Meter,
  Skeleton,
  useAction,
  useResource,
  useToast,
} from "../ui";
import type { DeviceResponse } from "../types";

function deviceName(device: DeviceResponse): string {
  return device.device_model || device.platform || device.hwid.slice(0, 12);
}

function deviceMeta(device: DeviceResponse): string {
  return [device.platform, device.os_version].filter(Boolean).join(" · ");
}

function DevicesHeader() {
  return (
    <header className="devices-header">
      <h1>{t("myDevices")}</h1>
    </header>
  );
}

export default function DevicesScreen() {
  const devices = useResource(() => api.devices.list());
  const subscription = useResource(() => api.subscription.current());
  const [deviceBusy, performDeviceAction] = useAction();
  const [connectBusy, performConnect] = useAction();
  const toast = useToast();

  if (devices.loading || (devices.error && subscription.loading)) {
    return (
      <div className="page devices-page">
        <DevicesHeader />
        <Skeleton height={80} />
        <Skeleton height={180} />
      </div>
    );
  }

  if (devices.error) {
    if (subscription.data === null) {
      return (
        <div className="page devices-page">
          <DevicesHeader />
          <Empty
            icon="🔒"
            title={t("noSubscription")}
            hint={t("connectionNeedsSubscription")}
          />
        </div>
      );
    }

    return (
      <div className="page devices-page">
        <DevicesHeader />
        <ErrorState onRetry={devices.reload} />
      </div>
    );
  }

  const data = devices.data!;
  const unlimited = isUnlimited(data.max_count);
  const available = unlimited
    ? t("unlimited")
    : String(Math.max(data.max_count - data.current_count, 0));
  const connectionUrl = subscription.data?.url?.trim() || null;

  const connect = () =>
    performConnect(async () => {
      if (!connectionUrl) return;
      await openPayment(connectionUrl);
    });

  const remove = (hwid: string) =>
    performDeviceAction(async () => {
      if (!(await confirm(t("removeDeviceConfirm")))) return;
      await api.devices.remove(hwid);
      toast(t("deviceRemoved"));
      devices.reload();
    });

  const removeAll = () =>
    performDeviceAction(async () => {
      if (!(await confirm(t("removeAllConfirm")))) return;
      await api.devices.removeAll();
      toast(t("deviceRemoved"));
      devices.reload();
    });

  return (
    <div className="page devices-page">
      <DevicesHeader />

      <section className="devices-summary" aria-label={t("deviceUsage")}>
        <div className="devices-summary-grid">
          <div className="devices-summary-item">
            <span className="devices-summary-label">{t("connected")}</span>
            <strong>{data.current_count}</strong>
          </div>
          <div className="devices-summary-divider" />
          <div className="devices-summary-item">
            <span className="devices-summary-label">{t("available")}</span>
            <strong>{available}</strong>
          </div>
        </div>
        <Meter
          label={t("deviceUsage")}
          detail={
            unlimited
              ? `${data.current_count} · ${t("unlimited")}`
              : t("devicesUsed", {
                  used: String(data.current_count),
                  limit: String(data.max_count),
                })
          }
          ratio={unlimited ? null : Math.min(data.current_count / data.max_count, 1)}
        />
      </section>

      <div className="device-connect-action">
        {subscription.loading ? (
          <Skeleton height={56} />
        ) : (
          <Button onClick={connect} busy={connectBusy} disabled={!connectionUrl}>
            + {t("connectDevice")}
          </Button>
        )}
        {!subscription.loading && !connectionUrl && (
          <p className="device-connect-hint" role="status">
            {subscription.error || subscription.data
              ? t("connectionLinkUnavailable")
              : t("connectionNeedsSubscription")}
          </p>
        )}
      </div>

      {data.devices.length === 0 ? (
        <Empty icon="📱" title={t("noDevices")} hint={t("noDevicesHint")} />
      ) : (
        <section className="devices-list-section" aria-labelledby="connected-devices-title">
          <h2 id="connected-devices-title">{t("connectedDevices")}</h2>
          <div className="devices-list">
            {data.devices.map((device) => (
              <article className="device-card" key={device.hwid}>
                <div className="device">
                  <span className="device-icon">{platformIcon(device.platform)}</span>
                  <div className="device-body">
                    <div className="device-name">{deviceName(device)}</div>
                    <div className="device-meta">{deviceMeta(device)}</div>
                  </div>
                </div>
                <Button
                  variant="danger"
                  onClick={() => remove(device.hwid)}
                  busy={deviceBusy}
                >
                  {t("removeDevice")}
                </Button>
              </article>
            ))}
          </div>

          <div className="remove-all-action">
            <Button variant="secondary" onClick={removeAll} busy={deviceBusy}>
              {t("removeAllDevices")}
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}
