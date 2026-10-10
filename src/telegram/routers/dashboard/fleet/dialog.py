from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, StartMode, Window
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.style import Style

from src.application.common.policy import Permission
from src.application.use_cases.fleet.commands.settings import FleetOption
from src.core.enums import BannerName
from src.telegram.states import Dashboard, DashboardFleet
from src.telegram.utils import require_permission
from src.telegram.widgets import Banner, I18nFormat, IgnoreUpdate
from src.telegram.widgets.kbd import Button, Row, Start, SwitchTo

from .getters import compensation_getter, fleet_getter
from .handlers import (
    on_compensation_confirm,
    on_compensation_days_input,
    on_fleet_check,
    on_fleet_toggle,
)

main = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-fleet.main"),
    Row(
        Button(
            text=I18nFormat("btn-fleet.enabled"),
            id=FleetOption.ENABLED,
            on_click=on_fleet_toggle,
            when=require_permission(Permission.SETTINGS_FLEET),
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-fleet.auto-hide"),
            id=FleetOption.AUTO_HIDE,
            on_click=on_fleet_toggle,
            when=require_permission(Permission.SETTINGS_FLEET),
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-fleet.announce"),
            id=FleetOption.ANNOUNCE,
            on_click=on_fleet_toggle,
            when=require_permission(Permission.SETTINGS_FLEET),
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-fleet.check"),
            id="check",
            on_click=on_fleet_check,
        ),
        Button(
            text=I18nFormat("btn-fleet.refresh"),
            id="refresh",
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-fleet.compensation"),
            id="compensation",
            state=DashboardFleet.COMPENSATION,
            when=require_permission(Permission.COMPENSATION),
        ),
    ),
    Row(
        Start(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=Dashboard.MAIN,
            mode=StartMode.RESET_STACK,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardFleet.MAIN,
    getter=fleet_getter,
)

compensation = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-fleet.compensation"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=DashboardFleet.MAIN,
        ),
    ),
    MessageInput(func=on_compensation_days_input),
    IgnoreUpdate(),
    state=DashboardFleet.COMPENSATION,
    getter=compensation_getter,
)

compensation_confirm = Window(
    Banner(BannerName.DASHBOARD),
    I18nFormat("msg-fleet.compensation-confirm"),
    Row(
        Button(
            text=I18nFormat("btn-fleet.compensation-confirm"),
            id="confirm",
            on_click=on_compensation_confirm,
            style=Style(ButtonStyle.SUCCESS),
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=DashboardFleet.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=DashboardFleet.COMPENSATION_CONFIRM,
    getter=compensation_getter,
)

router = Dialog(
    main,
    compensation,
    compensation_confirm,
)
