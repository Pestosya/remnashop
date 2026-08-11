import { api } from "../api";
import { t } from "../i18n";
import { isUnlimited, platformIcon } from "../format";
import { confirm } from "../telegram";
import {
  Button,
  Card,
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

export default function DevicesScreen() {
  const devices = useResource(() => api.devices.list());
  const [busy, perform] = useAction();
  const toast = useToast();

  if (devices.loading) {
    return (
      <div className="page">
        <Skeleton height={80} />
        <Skeleton height={180} />
      </div>
    );
  }

  if (devices.error) {
    return (
      <div className="page">
        <ErrorState onRetry={devices.reload} />
      </div>
    );
  }

  const data = devices.data!;
  const unlimited = isUnlimited(data.max_count);

  const remove = (hwid: string) =>
    perform(async () => {
      if (!(await confirm(t("removeDeviceConfirm")))) return;
      await api.devices.remove(hwid);
      toast(t("deviceRemoved"));
      devices.reload();
    });

  const removeAll = () =>
    perform(async () => {
      if (!(await confirm(t("removeAllConfirm")))) return;
      await api.devices.removeAll();
      toast(t("deviceRemoved"));
      devices.reload();
    });

  return (
    <div className="page">
      <Card>
        <Meter
          label={t("devices")}
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
      </Card>

      {data.devices.length === 0 ? (
        <Empty icon="📱" title={t("noDevices")} hint={t("noDevicesHint")} />
      ) : (
        <>
          <Card>
            {data.devices.map((device) => (
              <div className="row" key={device.hwid}>
                <div className="device">
                  <span className="device-icon">{platformIcon(device.platform)}</span>
                  <div className="device-body">
                    <div className="device-name">{deviceName(device)}</div>
                    <div className="device-meta">{deviceMeta(device)}</div>
                  </div>
                </div>
                <Button variant="danger" onClick={() => remove(device.hwid)} busy={busy}>
                  {t("removeDevice")}
                </Button>
              </div>
            ))}
          </Card>

          <Button variant="secondary" onClick={removeAll} busy={busy}>
            {t("removeAllDevices")}
          </Button>
        </>
      )}
    </div>
  );
}
