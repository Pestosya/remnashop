"""Animated icons on inline buttons.

A button whose text starts with an emoji listed in `ICONS` is sent with an animated outline icon
in front of the text (`icon_custom_emoji_id`) instead of that plain character. This
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
# The ids are from the "SF Symbols" set (t.me/addemoji/SFSymbols): animated outline icons that
# take the colour of the button text. The comment is the symbol each one shows.
ICONS: Final[dict[str, str]] = {
    "🚀": "6023761060786346622",  # bolt
    "🔗": "6021344879689341042",  # link
    "🎁": "6023826881160157558",  # gift
    "👑": "6021428854889913572",  # crown
    "📱": "6019245310696495518",  # devices
    "👥": "6021678620123077295",  # person.badge.plus
    "👤": "6021659919835469581",  # person.crop.circle
    "🔧": "6021787003622791696",  # wrench
    "🧑‍💻": "6023911174188308145",  # headset
    "💬": "6019151079114021083",  # bubbles
    "💰": "6030462253445160459",  # ruble
    "💸": "6030410254276106984",  # creditcard
    "🛒": "6030664675253820292",  # cart
    "🔄": "5807492110059838726",  # arrow.2.circlepath
    "✏": "6026080811277621020",  # square.and.pencil
    "🎟": "6021594546138257831",  # tag
    "✅": "6019175208240289774",  # checkmark.seal
    "❌": "5807692706507399432",  # xmark
    "🗑": "6021413766669801212",  # trash
    "❓": "5807800879553715710",  # questionmark.circle
    "📋": "6021445064096486884",  # doc.on.doc
    "📲": "6021757407003154108",  # viewfinder
    "📨": "6019461768458279173",  # paperplane
    "💎": "6028549648673675429",  # diamond
    "🪙": "6030352469786105758",  # banknote
    "⌛": "5807879906951960923",  # hourglass
    "⏳": "5807879906951960923",  # hourglass
    "❗": "6019102674832595118",  # exclamationmark.triangle
    "⚠": "6019102674832595118",  # exclamationmark.triangle
    "🧰": "6021582331251268218",  # gearshape
    "⬅": "5807899225714858124",  # arrowshape.turn.up.left
    "↩": "6023896773162967617",  # house
    "▶": "5807829874877930085",  # chevron.right
    "◀": "5807792908094413296",  # chevron.left
    "❤": "6023852792697854544",  # heart
    "📦": "6024106569430472546",  # shippingbox
    "🔒": "6019568309417023812",  # lock
    "🤝": "6021690418398239007",  # person.2
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

        # aiogram hands the method's result down the chain, not the Response its types promise
        if not _icons_kept(getattr(response, "result", response)):
            self._pause("Telegram dropped the icons from a sent keyboard")
        return response
