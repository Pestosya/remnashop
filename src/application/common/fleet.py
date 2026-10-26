from typing import Optional, Protocol, runtime_checkable

from src.application.dto import PanelHostDto, ProbeQuotaDto, ProbeResultDto, ProbeTargetDto


@runtime_checkable
class PanelFleet(Protocol):
    """The part of the panel the reachability automation works with."""

    async def get_hosts(self) -> list[PanelHostDto]: ...

    async def get_squad_inbounds(self) -> dict[str, list[str]]:
        """Internal squad uuid -> uuids of the inbounds it gives access to."""
        ...

    async def set_host_disabled(self, uuid: str, disabled: bool) -> None: ...

    async def get_announce(self) -> Optional[str]: ...

    async def set_announce(self, text: str) -> None: ...


@runtime_checkable
class FleetProber(Protocol):
    async def probe(
        self,
        targets: list[ProbeTargetDto],
    ) -> dict[ProbeTargetDto, ProbeResultDto]: ...

    async def quota(self) -> Optional[ProbeQuotaDto]:
        """What the measuring service still allows this hour; None when it cannot be told."""
        ...
