from typing import Optional, Protocol, runtime_checkable

from src.application.dto import PanelHostDto, ProbeResultDto, ProbeTargetDto


@runtime_checkable
class PanelFleet(Protocol):
    """The part of the panel the reachability automation works with."""

    async def get_hosts(self) -> list[PanelHostDto]: ...

    async def set_host_disabled(self, uuid: str, disabled: bool) -> None: ...

    async def get_announce(self) -> Optional[str]: ...

    async def set_announce(self, text: str) -> None: ...


@runtime_checkable
class FleetProber(Protocol):
    async def probe(
        self,
        targets: list[ProbeTargetDto],
    ) -> dict[ProbeTargetDto, ProbeResultDto]: ...
