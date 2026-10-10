import uuid

from aiogram.types import CallbackQuery, Message
from aiogram_dialog import DialogManager, ShowMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.kbd import Button
from dishka import FromDishka
from dishka.integrations.aiogram_dialog import inject
from loguru import logger

from src.application.common import Notifier
from src.application.common.policy import Permission, PermissionPolicy
from src.application.dto import TelegramUserDto
from src.application.use_cases.fleet.commands.compensation import (
    COMPENSATION_DAYS_MAX,
    COMPENSATION_DAYS_MIN,
)
from src.application.use_cases.fleet.commands.settings import FleetOption, ToggleFleetOption
from src.core.constants import USER_KEY
from src.infrastructure.taskiq.tasks.fleet import check_fleet_now_task, compensate_outage_task
from src.telegram.states import DashboardFleet


@inject
async def on_fleet_toggle(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    toggle_fleet_option: FromDishka[ToggleFleetOption],
) -> None:
    user: TelegramUserDto = dialog_manager.middleware_data[USER_KEY]
    await toggle_fleet_option(user, FleetOption(widget.widget_id or ""))


@inject
async def on_fleet_check(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
) -> None:
    user: TelegramUserDto = dialog_manager.middleware_data[USER_KEY]
    # the check takes up to a minute: it runs in the worker, this window shows its result later
    await check_fleet_now_task.kiq()  # type: ignore[call-overload]
    logger.info(f"{user.log} Started a manual fleet check")
    await notifier.notify_user(user, i18n_key="ntf-fleet.check-started")


@inject
async def on_compensation_days_input(
    message: Message,
    widget: MessageInput,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
) -> None:
    dialog_manager.show_mode = ShowMode.EDIT
    user: TelegramUserDto = dialog_manager.middleware_data[USER_KEY]
    text = (message.text or "").strip()

    if not text.isdigit() or not COMPENSATION_DAYS_MIN <= int(text) <= COMPENSATION_DAYS_MAX:
        await notifier.notify_user(user, i18n_key="ntf-common.invalid-value")
        return

    dialog_manager.dialog_data["compensation_days"] = int(text)
    dialog_manager.show_mode = ShowMode.DELETE_AND_SEND
    await dialog_manager.switch_to(DashboardFleet.COMPENSATION_CONFIRM)


@inject
async def on_compensation_confirm(
    callback: CallbackQuery,
    widget: Button,
    dialog_manager: DialogManager,
    notifier: FromDishka[Notifier],
) -> None:
    user: TelegramUserDto = dialog_manager.middleware_data[USER_KEY]
    days = dialog_manager.dialog_data.pop("compensation_days", None)

    if not days or not PermissionPolicy.has_permission(user, Permission.COMPENSATION):
        await dialog_manager.switch_to(DashboardFleet.MAIN)
        return

    run_id = uuid.uuid4().hex
    await compensate_outage_task.kiq(run_id, int(days), True)  # type: ignore[call-overload]
    logger.info(f"{user.log} Started compensation '{run_id}' for '{days}' days")
    await notifier.notify_user(user, i18n_key="ntf-fleet.compensation-started")
    await dialog_manager.switch_to(DashboardFleet.MAIN)
