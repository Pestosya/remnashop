from typing import Final
from uuid import UUID

import orjson
from adaptix import Retort
from loguru import logger
from redis.asyncio import Redis

from src.application.common import Interactor, PanelFleet
from src.application.common.policy import Permission
from src.application.dto import PanelHostDto, UserDto
from src.application.services.fleet import servers_for_squads
from src.core.constants import TTL_5M

PANEL_SERVERS_KEY: Final[str] = "panel_servers"


class GetPlanServers(Interactor[list[UUID], list[str]]):
    """The servers a plan gives access to, by the plan's internal squads, as the panel has
    them right now. The purchase screens show this list, so it follows the panel by itself.

    The hosts and squads are read from the panel at most once in five minutes; when the
    panel does not answer the list is simply empty: a purchase must not fail over it.
    """

    required_permission = Permission.PUBLIC

    def __init__(self, panel: PanelFleet, redis: Redis, retort: Retort) -> None:
        self.panel = panel
        self.redis = redis
        self.retort = retort

    async def _execute(self, actor: UserDto, squads: list[UUID]) -> list[str]:
        if not squads:
            return []

        try:
            hosts, squad_inbounds = await self._snapshot()
        except Exception as e:
            logger.warning(f"Could not read the servers from the panel: {e!r}")
            return []

        return servers_for_squads(hosts, squad_inbounds, [str(squad) for squad in squads])

    async def _snapshot(self) -> tuple[list[PanelHostDto], dict[str, list[str]]]:
        raw = await self.redis.get(PANEL_SERVERS_KEY)
        if raw:
            data = orjson.loads(raw)
            return self.retort.load(data["hosts"], list[PanelHostDto]), data["squads"]

        hosts = await self.panel.get_hosts()
        squad_inbounds = await self.panel.get_squad_inbounds()
        await self.redis.set(
            PANEL_SERVERS_KEY,
            orjson.dumps(
                {"hosts": self.retort.dump(hosts, list[PanelHostDto]), "squads": squad_inbounds}
            ),
            ex=TTL_5M,
        )
        return hosts, squad_inbounds
