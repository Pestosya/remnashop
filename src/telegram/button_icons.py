"""Animated icons on inline buttons.

A button whose text starts with an emoji listed in `ICONS` is sent with that emoji as an animated
custom emoji in front of the text (`icon_custom_emoji_id`) instead of the plain character. This
happens in one place, on the way out to Telegram, so every keyboard is covered: dialog windows,
notifications, the owner's menu buttons.

Telegram allows such icons only in private chats and only while the bot's owner has Telegram
Premium. If it ever refuses them, the request is repeated as it was written and icons stay off
for `PAUSE` seconds: the bot keeps working with ordinary emoji.
"""

import re
import time
from typing import Any, Final, Optional

from aiogram import Bot
from aiogram.client.session.middlewares.base import (
    BaseRequestMiddleware,
    NextRequestMiddlewareType,
)
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import Response, TelegramMethod
from aiogram.methods.base import TelegramType
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from loguru import logger

# Leading emoji (without the U+FE0F variation selector) -> custom emoji id.
# All ids are from Telegram's own "Animated Emoji" set (RestrictedEmoji), 🛟 from "Topic Icons".
ICONS: Final[dict[str, str]] = {
    "🚀": "5445284980978621387",
    "🎁": "5199749070830197566",
    "👑": "5467406098367521267",
    "📱": "5407025283456835913",
    "👥": "5372926953978341366",
    "🧑‍💻": "5190458330719461749",
    "👤": "5373012449597335010",
    "🛟": "5366577141183954305",
    "🧰": "5449428597922079323",
    "⌛": "5451646226975955576",
    "⏳": "5451732530048802485",
    "❗": "5467928559664242360",
    "💸": "5472030678633684592",
    "🔄": "5264727218734524899",
    "✏": "5334673106202010226",
    "🎟": "5377599075237502153",
    "💰": "5375296873982604963",
    "🛒": "5431499171045581032",
    "❌": "5465665476971471368",
    "✅": "5427009714745517609",
    "❓": "5467666648263564704",
    "🔗": "5375129357373165375",
    "📲": "5406809207947142040",
    "📨": "5406631276042002796",
    "💎": "5471952986970267163",
    "🪙": "5379600444098093058",
    "❤": "5449505950283078474",
    "💬": "5465300082628763143",
}

PAUSE: Final[int] = 3600
_VARIATION_SELECTOR: Final[str] = "️"
_LEAD: Final[re.Pattern[str]] = re.compile(r"^(\S+)\s+(\S.*)$", re.DOTALL)
# what a refusal of icons is expected to mention; anything else is not ours to handle
_REFUSAL_WORDS: Final[tuple[str, ...]] = ("emoji", "icon", "premium")


def with_icon(button: InlineKeyboardButton) -> Optional[InlineKeyboardButton]:
    """The button with its leading emoji turned into an icon, or None if there is nothing to do."""
    if button.icon_custom_emoji_id:
        return None
    match = _LEAD.match(button.text)
    if not match:
        return None
    icon = ICONS.get(match.group(1).replace(_VARIATION_SELECTOR, ""))
    if not icon:
        return None
    return button.model_copy(update={"text": match.group(2), "icon_custom_emoji_id": icon})


def iconize(markup: InlineKeyboardMarkup) -> Optional[InlineKeyboardMarkup]:
    """A copy of the keyboard with icons, or None when no button changes."""
    changed = False
    rows: list[list[InlineKeyboardButton]] = []
    for row in markup.inline_keyboard:
        new_row = []
        for button in row:
            replaced = with_icon(button)
            changed = changed or replaced is not None
            new_row.append(replaced or button)
        rows.append(new_row)
    return InlineKeyboardMarkup(inline_keyboard=rows) if changed else None


def _is_private_chat(method: TelegramMethod[Any]) -> bool:
    chat_id = getattr(method, "chat_id", None)
    return isinstance(chat_id, int) and chat_id > 0


def _icons_kept(result: Any) -> bool:
    """False when Telegram accepted the message but dropped the icons from its keyboard."""
    if not isinstance(result, Message) or not result.reply_markup:
        return True
    buttons = [b for row in result.reply_markup.inline_keyboard for b in row]
    return any(b.icon_custom_emoji_id for b in buttons)


class ButtonIconsMiddleware(BaseRequestMiddleware):
    def __init__(self) -> None:
        self._paused_until: float = 0.0

    @property
    def active(self) -> bool:
        return time.monotonic() >= self._paused_until

    def _pause(self, reason: str) -> None:
        self._paused_until = time.monotonic() + PAUSE
        logger.warning(f"Button icons are off for {PAUSE} s: {reason}")

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        markup = getattr(method, "reply_markup", None)
        if not (
            self.active and isinstance(markup, InlineKeyboardMarkup) and _is_private_chat(method)
        ):
            return await make_request(bot, method)

        iconized = iconize(markup)
        if iconized is None:
            return await make_request(bot, method)

        try:
            response = await make_request(bot, method.model_copy(update={"reply_markup": iconized}))
        except TelegramBadRequest as error:
            if not any(word in error.message.lower() for word in _REFUSAL_WORDS):
                raise
            self._pause(error.message)
            return await make_request(bot, method)

        if not _icons_kept(response.result):
            self._pause("Telegram dropped the icons from a sent keyboard")
        return response
