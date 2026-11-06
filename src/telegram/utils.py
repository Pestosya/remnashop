from datetime import datetime, timedelta
from typing import Callable, Optional

from aiogram_dialog import DialogManager
from aiogram_dialog.widgets.common.when import Whenable

from src.application.common import Notifier
from src.application.common.policy import Permission, PermissionPolicy
from src.application.dto import MessagePayloadDto, SubscriptionDto, TelegramUserDto, UserDto
from src.core.config.bot import BotConfig
from src.core.constants import USER_KEY
from src.core.enums import Role
from src.core.utils.time import datetime_now
from src.telegram.keyboards import get_connect_keyboard


async def notify_reissued(
    notifier: Notifier,
    user: UserDto,
    subscription: Optional[SubscriptionDto],
    bot_config: BotConfig,
) -> None:
    """A reissue changes the link and the keys: VPN stops on every device until it is added again.
    People who reissued kept refreshing the dead link and took the error for a broken server."""
    if not subscription or not subscription.url:
        await notifier.notify_user(user, i18n_key="ntf-devices.reissued")
        return
    await notifier.notify_user(
        user,
        MessagePayloadDto(
            i18n_key="ntf-devices.reissued-howto",
            reply_markup=get_connect_keyboard(bot_config, subscription.url),
            delete_after=None,  # the steps stay until the person closes them
            disable_default_markup=False,
        ),
    )


def is_double_click(dialog_manager: DialogManager, key: str, cooldown: int = 10) -> bool:
    now = datetime_now()
    last_click_str: Optional[str] = dialog_manager.dialog_data.get(key)
    if last_click_str:
        last_click = datetime.fromisoformat(last_click_str.replace("Z", "+00:00"))
        if now - last_click < timedelta(seconds=cooldown):
            return True

    dialog_manager.dialog_data[key] = now.isoformat()
    return False


def require_permission(permission: Permission) -> Callable:
    def checker(
        data: dict,
        widget: Whenable,
        manager: DialogManager,
    ) -> bool:
        user: TelegramUserDto = manager.middleware_data[USER_KEY]
        return PermissionPolicy.has_permission(user, permission)

    return checker


def require_role(role: Role) -> Callable:
    def checker(
        data: dict,
        widget: Whenable,
        manager: DialogManager,
    ) -> bool:
        user: TelegramUserDto = manager.middleware_data[USER_KEY]
        return user.role >= role

    return checker
