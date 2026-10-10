from enum import StrEnum

from loguru import logger

from src.application.common import Interactor
from src.application.common.dao import SettingsDao
from src.application.common.policy import Permission
from src.application.common.uow import UnitOfWork
from src.application.dto import UserDto


class FleetOption(StrEnum):
    ENABLED = "enabled"
    AUTO_HIDE = "auto_hide"
    ANNOUNCE = "announce"


class ToggleFleetOption(Interactor[FleetOption, bool]):
    required_permission = Permission.SETTINGS_FLEET

    def __init__(self, uow: UnitOfWork, settings_dao: SettingsDao) -> None:
        self.uow = uow
        self.settings_dao = settings_dao

    async def _execute(self, actor: UserDto, option: FleetOption) -> bool:
        async with self.uow:
            settings = await self.settings_dao.get()
            fleet = settings.extra.fleet
            value = not getattr(fleet, option.value)
            setattr(fleet, option.value, value)
            await self.settings_dao.update(settings)
            await self.uow.commit()

        logger.info(f"{actor.log} Toggled fleet option '{option}': {value}")
        return value
