from typing import Any

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.application.common import TranslatorRunner
from src.application.common.dao import SettingsDao, UserDao
from src.application.dto import TelegramUserDto
from src.application.use_cases.fleet.queries.state import GetFleetState
from src.core.constants import DATETIME_VIEW_FORMAT
from src.core.enums import FleetStatus


@inject
async def fleet_getter(
    dialog_manager: DialogManager,
    user: TelegramUserDto,
    i18n: FromDishka[TranslatorRunner],
    settings_dao: FromDishka[SettingsDao],
    get_fleet_state: FromDishka[GetFleetState],
    **kwargs: Any,
) -> dict[str, Any]:
    settings = await settings_dao.get()
    fleet = settings.extra.fleet
    state = await get_fleet_state(user)

    lines = []
    for host in state.hosts:
        if host.status == FleetStatus.UNKNOWN:
            key = "msg-fleet-host.unknown"
        elif host.hidden:
            key = "msg-fleet-host.hidden"
        else:
            key = "msg-fleet-host.visible"
        lines.append(
            i18n.get(
                key,
                status=host.status,
                remark=host.remark,
                passed=host.passed,
                total=host.total,
            )
        )

    return {
        "has_state": int(state.checked_at is not None),
        "checked_at": state.checked_at.strftime(DATETIME_VIEW_FORMAT) if state.checked_at else "",
        "hosts": "\n".join(lines),
        "enabled": int(fleet.enabled),
        "auto_hide": int(fleet.auto_hide),
        "announce": int(fleet.announce),
    }


@inject
async def compensation_getter(
    dialog_manager: DialogManager,
    user_dao: FromDishka[UserDao],
    **kwargs: Any,
) -> dict[str, Any]:
    return {
        "value": dialog_manager.dialog_data.get("compensation_days", 0),
        "count": len(await user_dao.get_with_active_paid_subscription()),
    }
