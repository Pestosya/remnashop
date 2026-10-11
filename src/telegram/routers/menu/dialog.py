from aiogram.enums import ButtonStyle
from aiogram_dialog import Dialog, StartMode
from aiogram_dialog.widgets.input import MessageInput
from aiogram_dialog.widgets.style import Style
from aiogram_dialog.widgets.text import Format
from magic_filter import F

from src.application.common.policy import Permission
from src.application.use_cases.points.exchange import PointsExchangeStatus
from src.core.constants import INLINE_QUERY_INVITE, PAYMENT_PREFIX
from src.core.enums import BannerName
from src.telegram.keyboards import build_buttons_row, connect_buttons
from src.telegram.routers.dashboard.handlers import on_smart_search
from src.telegram.states import Dashboard, MainMenu, Subscription
from src.telegram.utils import require_permission
from src.telegram.widgets import Banner, I18nFormat, IgnoreUpdate
from src.telegram.widgets.kbd import (
    Button,
    Column,
    CopyText,
    Group,
    ListGroup,
    Row,
    Select,
    Start,
    SwitchInlineQueryChosenChatButton,
    SwitchTo,
    Url,
    WebApp,
)
from src.telegram.window import Window

from .getters import (
    device_confirm_delete_getter,
    devices_getter,
    help_getter,
    invite_about_getter,
    invite_getter,
    menu_getter,
    points_confirm_getter,
    points_getter,
)
from .handlers import (
    on_device_delete_all_confirm,
    on_device_delete_confirm,
    on_device_delete_request,
    on_get_trial,
    on_invite,
    on_points_duration_select,
    on_points_exchange_confirm,
    on_points_plan_select,
    on_points_plans_back,
    on_reissue_subscription_confirm,
    on_reset_referral_code,
    on_show_qr,
    on_text_button_click,
    on_withdraw_points,
    show_reason,
)

custom_buttons = (
    build_buttons_row(1, text_on_click=on_text_button_click),
    build_buttons_row(2, text_on_click=on_text_button_click),
    build_buttons_row(3, text_on_click=on_text_button_click),
)

menu = Window(
    Banner(BannerName.MENU),
    I18nFormat("msg-main-menu"),
    *connect_buttons,
    Row(
        Button(
            text=I18nFormat("btn-menu.connect-not-available"),
            id="not_available",
            on_click=show_reason,
        ),
        when=F["has_subscription"] & ~F["connectable"],
    ),
    Row(
        Button(
            text=I18nFormat("btn-menu.trial"),
            id="trial_free",
            on_click=on_get_trial,
            when=F["trial_available"] & F["trial_is_free"],
            style=Style(ButtonStyle.SUCCESS),
        ),
        Button(
            text=I18nFormat("btn-menu.trial-paid"),
            id="trial_paid",
            on_click=on_get_trial,
            when=F["trial_available"] & ~F["trial_is_free"],
            style=Style(ButtonStyle.SUCCESS),
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-menu.devices"),
            id="devices",
            state=MainMenu.DEVICES,
            when=F["has_device_limit"],
        ),
        Start(
            text=I18nFormat("btn-menu.subscription"),
            id=f"{PAYMENT_PREFIX}subscription",
            state=Subscription.MAIN,
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-menu.help"),
            id="help",
            state=MainMenu.HELP,
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-menu.invite"),
            id="invite",
            on_click=on_invite,
            when=F["referral_enabled"],
        ),
        SwitchInlineQueryChosenChatButton(
            text=I18nFormat("btn-menu.invite"),
            query=Format(INLINE_QUERY_INVITE),
            allow_user_chats=True,
            allow_group_chats=True,
            allow_channel_chats=True,
            id="send",
            when=~F["referral_enabled"],
        ),
        Url(
            text=I18nFormat("btn-menu.support"),
            id="support",
            url=Format("{support_url}"),
        ),
    ),
    Row(
        WebApp(
            text=I18nFormat("btn-menu.web-cabinet"),
            url=Format("{web_cabinet_url}"),
        ),
        when=F["web_enabled"],
    ),
    *custom_buttons,
    Row(
        Start(
            text=I18nFormat("btn-menu.dashboard"),
            id="dashboard",
            state=Dashboard.MAIN,
            mode=StartMode.RESET_STACK,
            when=require_permission(Permission.VIEW_DASHBOARD),
        ),
    ),
    MessageInput(func=on_smart_search),
    IgnoreUpdate(),
    state=MainMenu.MAIN,
    getter=menu_getter,
)

devices = Window(
    Banner(BannerName.DEVICES),
    I18nFormat("msg-menu-devices"),
    Row(
        Button(
            text=I18nFormat("btn-common.devices-empty"),
            id="devices_empty",
            when=~F["has_devices"],
        ),
    ),
    ListGroup(
        Row(
            Button(
                text=Format("{item[label]}"),
                id="device_item",
                on_click=on_device_delete_request,
                when=F["data"]["device_single_enabled"],
            ),
            Button(
                text=Format("{item[label]}"),
                id="device_item_display",
                when=~F["data"]["device_single_enabled"],
            ),
        ),
        id="devices_list",
        item_id_getter=lambda item: item["index"],
        items="devices",
        when=F["has_devices"],
    ),
    Row(
        Start(
            text=I18nFormat("btn-devices.delete-all"),
            id="delete_all",
            state=MainMenu.DEVICE_CONFIRM_DELETE_ALL,
            when=F["has_devices"] & F["device_all_enabled"],
            style=Style(ButtonStyle.DANGER),
        ),
    ),
    Row(
        Start(
            text=I18nFormat("btn-devices.reissue"),
            id="reissue",
            state=MainMenu.DEVICE_CONFIRM_REISSUE,
            style=Style(ButtonStyle.PRIMARY),
            when=F["link_reset_enabled"],
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=MainMenu.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.DEVICES,
    getter=devices_getter,
)

device_confirm_delete = Window(
    Banner(BannerName.MENU),
    I18nFormat("msg-menu-devices-confirm-delete"),
    Row(
        Button(
            text=I18nFormat("btn-devices.confirm-delete"),
            id="confirm_delete",
            on_click=on_device_delete_confirm,
            style=Style(ButtonStyle.DANGER),
        ),
        SwitchTo(
            text=I18nFormat("btn-common.cancel"),
            id="cancel",
            state=MainMenu.DEVICES,
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.DEVICE_CONFIRM_DELETE,
    getter=device_confirm_delete_getter,
)

device_confirm_delete_all = Window(
    Banner(BannerName.MENU),
    I18nFormat("msg-menu-devices-confirm-delete-all"),
    Row(
        Button(
            text=I18nFormat("btn-devices.confirm-delete"),
            id="confirm_delete_all",
            on_click=on_device_delete_all_confirm,
            style=Style(ButtonStyle.DANGER),
        ),
        SwitchTo(
            text=I18nFormat("btn-common.cancel"),
            id="cancel",
            state=MainMenu.DEVICES,
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.DEVICE_CONFIRM_DELETE_ALL,
    getter=device_confirm_delete_getter,
)

invite = Window(
    Banner(BannerName.REFERRAL),
    I18nFormat("msg-menu-invite"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-invite.about"),
            id="about",
            state=MainMenu.INVITE_ABOUT,
        ),
    ),
    Row(
        CopyText(
            text=I18nFormat("btn-invite.copy"),
            copy_text=Format("{referral_url}"),
        ),
    ),
    Row(
        Button(
            text=I18nFormat("btn-invite.qr"),
            id="qr",
            on_click=on_show_qr,
        ),
        SwitchInlineQueryChosenChatButton(
            text=I18nFormat("btn-invite.send"),
            query=Format(INLINE_QUERY_INVITE),
            allow_user_chats=True,
            allow_group_chats=True,
            allow_channel_chats=True,
            id="send",
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-invite.exchange-points"),
            id="exchange_points",
            state=MainMenu.POINTS,
            when=F["has_points"] & F["exchange_enabled"],
        ),
        Button(
            text=I18nFormat("btn-invite.exchange-points"),
            id="exchange_points_empty",
            on_click=on_withdraw_points,
            when=~F["has_points"] & F["exchange_enabled"],
        ),
        # points earned earlier stay usable even if the reward type is changed later
        when=F["is_points_reward"] | F["has_points"],
    ),
    Row(
        Url(
            text=I18nFormat("btn-invite.withdraw-points"),
            id="withdraw_points",
            url=Format("{withdraw}"),
        ),
        when=F["has_points"],
    ),
    Row(
        Button(
            text=I18nFormat("btn-invite.reset-referral"),
            id="reset_referral",
            on_click=on_reset_referral_code,
            when=F["referral_reset_enabled"],
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=MainMenu.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.INVITE,
    getter=invite_getter,
)

invite_about = Window(
    Banner(BannerName.REFERRAL),
    I18nFormat("msg-menu-invite-about"),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=MainMenu.INVITE,
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.INVITE_ABOUT,
    getter=invite_about_getter,
)


device_confirm_reissue = Window(
    Banner(BannerName.MENU),
    I18nFormat("msg-menu-devices-confirm-reissue"),
    Row(
        Button(
            text=I18nFormat("btn-devices.confirm-reissue"),
            id="confirm_reissue",
            on_click=on_reissue_subscription_confirm,
            style=Style(ButtonStyle.DANGER),
        ),
        SwitchTo(
            text=I18nFormat("btn-devices.cancel-reissue"),
            id="cancel_reissue",
            state=MainMenu.DEVICES,
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.DEVICE_CONFIRM_REISSUE,
    getter=device_confirm_delete_getter,
)

points = Window(
    Banner(BannerName.REFERRAL),
    I18nFormat("msg-menu-points.main"),
    Column(
        Select(
            text=Format("{item[name]}"),
            id="points_plan",
            item_id_getter=lambda item: item["id"],
            items="plans",
            type_factory=int,
            on_click=on_points_plan_select,
        ),
        when=F["status"] == PointsExchangeStatus.CHOOSE_PLAN,
    ),
    Group(
        Select(
            text=I18nFormat(
                "btn-points.duration",
                period=F["item"]["period"],
                cost=F["item"]["cost"],
                affordable=F["item"]["affordable"],
            ),
            id="points_duration",
            item_id_getter=lambda item: item["days"],
            items="offers",
            type_factory=int,
            on_click=on_points_duration_select,
        ),
        width=2,
        when=F["status"] == PointsExchangeStatus.AVAILABLE,
    ),
    Row(
        Button(
            text=I18nFormat("btn-points.other-plan"),
            id="points_other_plan",
            on_click=on_points_plans_back,
            when=F["plan_chosen"],
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=MainMenu.INVITE,
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.POINTS,
    getter=points_getter,
)

points_confirm = Window(
    Banner(BannerName.REFERRAL),
    I18nFormat("msg-menu-points.confirm"),
    Row(
        Button(
            text=I18nFormat("btn-points.confirm"),
            id="points_confirm",
            on_click=on_points_exchange_confirm,
            when=F["available"],
            style=Style(ButtonStyle.SUCCESS),
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=MainMenu.POINTS,
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.POINTS_CONFIRM,
    getter=points_confirm_getter,
)

help_window = Window(
    Banner(BannerName.MENU),
    I18nFormat("msg-menu-help.main"),
    Row(
        Url(
            text=I18nFormat("btn-menu.support"),
            id="support",
            url=Format("{support_url}"),
        ),
    ),
    Row(
        SwitchTo(
            text=I18nFormat("btn-back.general"),
            id="back",
            state=MainMenu.MAIN,
        ),
    ),
    IgnoreUpdate(),
    state=MainMenu.HELP,
    getter=help_getter,
)

router = Dialog(
    menu,
    help_window,
    devices,
    device_confirm_delete,
    device_confirm_delete_all,
    device_confirm_reissue,
    invite,
    invite_about,
    points,
    points_confirm,
)
