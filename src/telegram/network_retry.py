"""Repeat a request to Telegram when the connection to it could not be opened.

The bot's server is in Russia, where new connections to api.telegram.org are now and then reset
before they are set up. Such a request never reached Telegram, so sending it again cannot
duplicate a message or a payment: it is repeated after a short pause, a few times at most.

An error after the connection was set up is not repeated: Telegram may have done the job already.
"""

import asyncio
from typing import Final

from aiogram import Bot
from aiogram.client.session.middlewares.base import (
    BaseRequestMiddleware,
    NextRequestMiddlewareType,
)
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods import Response, TelegramMethod
from aiogram.methods.base import TelegramType
from aiohttp import ClientConnectorError
from loguru import logger

# Pause before each repeat, in seconds; the number of repeats is the length.
DELAYS: Final[tuple[float, ...]] = (0.3, 1.0)


def _not_connected(error: TelegramNetworkError) -> bool:
    return isinstance(error.__cause__, ClientConnectorError)


class ConnectRetryMiddleware(BaseRequestMiddleware):
    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        for delay in DELAYS:
            try:
                return await make_request(bot, method)
            except TelegramNetworkError as error:
                if not _not_connected(error):
                    raise
                logger.warning(
                    f"No connection to Telegram for '{type(method).__name__}', "
                    f"trying again in {delay} s: {error.message}"
                )
                await asyncio.sleep(delay)
        return await make_request(bot, method)
