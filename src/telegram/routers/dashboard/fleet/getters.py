from typing import Any

from aiogram_dialog import DialogManager
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject

from src.application.common import TranslatorRunner
from src.application.common.dao import SettingsDao, UserDao
from src.application.dto import TelegramUserDto
from src.application.services.fleet import utf16_len
from src.application.use_cases.fleet.queries.state import GetFleetState
from src.core.constants import DATETIME_VIEW_FORMAT, TEXT_MEDIA_MAX_LENGTH
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

    entries = []  # (works fine, line)
    for host in state.hosts:
        if host.status == FleetStatus.UNKNOWN:
            key = "msg-fleet-host.unknown"
        elif host.hidden:
            key = "msg-fleet-host.hidden"
        else:
            key = "msg-fleet-host.visible"
        line = i18n.get(
            key,
            status=host.status,
            remark=host.remark,
            passed=host.passed,
            total=host.total,
        )
        entries.append((host.status == FleetStatus.OK and not host.hidden, line))

    checked_at = state.checked_at.strftime(DATETIME_VIEW_FORMAT) if state.checked_at else ""
    # the screen is a banner caption: servers with trouble are always listed, working ones that
    # do not fit are counted in one line
    budget = (
        TEXT_MEDIA_MAX_LENGTH
        - utf16_len(i18n.get("msg-fleet.main", has_state=1, checked_at=checked_at, hosts=""))
        - utf16_len(i18n.get("msg-fleet-host.more-ok", count=len(entries)))
        - 1
    )
    lines = [line for _, line in entries]
    if utf16_len("\n".join(lines)) > budget:
        room = budget - sum(utf16_len(line) + 1 for ok, line in entries if not ok)
        lines, folded = [], 0
        for ok, line in entries:
            if not ok:
                lines.append(line)
            elif utf16_len(line) + 1 <= room:
                room -= utf16_len(line) + 1
                lines.append(line)
            else:
                folded += 1
        more_key = "msg-fleet-host.more-ok"
        while lines and utf16_len("\n".join(lines)) > budget:  # trouble alone does not fit
            lines.pop()
            folded += 1
            more_key = "msg-fleet-host.more"
        if folded:
            lines.append(i18n.get(more_key, count=folded))

    return {
        "has_state": int(state.checked_at is not None),
        "checked_at": checked_at,
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
