from typing import Final

import orjson
from adaptix import Retort
from loguru import logger
from redis.asyncio import Redis

from src.application.common import Interactor
from src.application.common.policy import Permission
from src.application.dto import FleetStateDto, UserDto
from src.core.constants import TIME_1D

FLEET_STATE_KEY: Final[str] = "fleet_state"
# a state older than this says nothing about the servers any more
FLEET_STATE_TTL: Final[int] = TIME_1D * 2


async def load_fleet_state(redis: Redis, retort: Retort) -> FleetStateDto:
    raw = await redis.get(FLEET_STATE_KEY)
    if not raw:
        return FleetStateDto()
    try:
        return retort.load(orjson.loads(raw), FleetStateDto)
    except Exception as e:  # a state written by another version: start over
        logger.warning(f"Stored fleet state is unreadable, ignoring it: {e!r}")
        return FleetStateDto()


async def save_fleet_state(redis: Redis, retort: Retort, state: FleetStateDto) -> None:
    await redis.set(FLEET_STATE_KEY, orjson.dumps(retort.dump(state)), ex=FLEET_STATE_TTL)


class GetFleetState(Interactor[None, FleetStateDto]):
    """The result of the last reachability check (empty when there was none recently)."""

    required_permission = Permission.PUBLIC

    def __init__(self, redis: Redis, retort: Retort) -> None:
        self.redis = redis
        self.retort = retort

    async def _execute(self, actor: UserDto, data: None) -> FleetStateDto:
        return await load_fleet_state(self.redis, self.retort)
