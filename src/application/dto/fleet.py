from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.core.enums import FleetStatus


@dataclass(frozen=True, kw_only=True)
class PanelHostDto:
    """A host of the panel, as far as the reachability check cares."""

    uuid: str
    remark: str
    address: str
    port: int
    sni: Optional[str] = None
    is_disabled: bool = False
    # an auto-select entry rendered from a template has no server of its own to probe
    is_virtual: bool = False
    # kept out of the subscriptions by the panel (only used inside auto-select entries)
    is_hidden: bool = False
    # the inbound the host belongs to: a squad gives access to a host through it
    inbound_uuid: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class ProbeTargetDto:
    """What actually gets probed. Several hosts may share one target."""

    address: str
    port: int
    sni: str


@dataclass(frozen=True, kw_only=True)
class ProbeResultDto:
    # TLS handshakes from remote probes in Russian networks
    passed: int = 0
    total: int = 0
    # the same handshake made from this server; None if it was not attempted
    direct_ok: Optional[bool] = None


@dataclass(kw_only=True)
class FleetHostStateDto:
    uuid: str
    remark: str
    address: str
    port: int
    status: FleetStatus = FleetStatus.UNKNOWN
    passed: int = 0
    total: int = 0
    direct_ok: Optional[bool] = None
    bad_streak: int = 0  # consecutive DOWN checks
    good_streak: int = 0  # consecutive OK / PARTIAL checks
    alerted: bool = False  # admins were told it is down
    hidden: bool = False  # disabled by the automation


@dataclass(kw_only=True)
class FleetStateDto:
    checked_at: Optional[datetime] = None
    hosts: list[FleetHostStateDto] = field(default_factory=list)

    def get(self, uuid: str) -> Optional[FleetHostStateDto]:
        return next((h for h in self.hosts if h.uuid == uuid), None)


@dataclass(kw_only=True)
class FleetChangesDto:
    """What one check changed; the lists hold host remarks."""

    down: list[str] = field(default_factory=list)
    recovered: list[str] = field(default_factory=list)
    hidden: list[str] = field(default_factory=list)
    restored: list[str] = field(default_factory=list)
    all_down: bool = False

    @property
    def is_empty(self) -> bool:
        return not (self.down or self.recovered or self.hidden or self.restored)
