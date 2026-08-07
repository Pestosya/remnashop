from typing import Optional
from urllib.parse import urlparse

from loguru import logger

from src.application.common import Interactor, Remnawave
from src.application.common.dao import SubscriptionDao, UserDao
from src.application.common.uow import UnitOfWork
from src.application.dto import SubscriptionDto, UserDto
from src.core.constants import RELINK_BATCH_SIZE


def extract_short_uuid(url: str) -> Optional[str]:
    """Pull the panel's `shortUuid` out of a stored subscription URL.

    Subscription URLs end in the short UUID (`https://sub.example.com/<short>`),
    possibly followed by a client-specific suffix the panel appends.
    """
    path = urlparse(url).path.strip("/")
    if not path:
        return None
    return path.split("/")[-1] or None


class RelinkSubscriptions(Interactor[None, int]):
    """Re-link subscriptions created against a Remnawave panel older than 3.0.

    Panel 3.x identifies users by a numeric id and no longer returns the UUID
    those rows were stored with, so the link has to be rebuilt from something
    both sides still agree on: the subscription's short UUID, or failing that
    the deterministic `rs_<telegram_id>` username.
    """

    required_permission = None

    def __init__(
        self,
        uow: UnitOfWork,
        user_dao: UserDao,
        subscription_dao: SubscriptionDao,
        remnawave: Remnawave,
    ) -> None:
        self.uow = uow
        self.user_dao = user_dao
        self.subscription_dao = subscription_dao
        self.remnawave = remnawave

    async def _execute(self, actor: UserDto, data: None) -> int:
        linked = 0
        unresolved = 0
        # Scan forward by id: rows that cannot be resolved stay NULL, so paging
        # by offset alone would keep re-reading them.
        after_id = 0

        while True:
            async with self.uow:
                subscriptions = await self.subscription_dao.get_unlinked(
                    RELINK_BATCH_SIZE,
                    after_id,
                )
                if not subscriptions:
                    break

                for subscription in subscriptions:
                    remna_id = await self._resolve(subscription)
                    if remna_id is None:
                        unresolved += 1
                        logger.warning(
                            f"Could not re-link subscription '{subscription.id}' "
                            f"(panel uuid '{subscription.remna_uuid}'): no matching panel user"
                        )
                        continue

                    await self.subscription_dao.set_remna_id(subscription.id, remna_id)
                    linked += 1

                after_id = subscriptions[-1].id
                await self.uow.commit()

        if linked or unresolved:
            logger.info(
                f"Re-linked {linked} subscription(s) to Remnawave panel user ids, "
                f"{unresolved} could not be resolved"
            )

        return linked

    async def _resolve(self, subscription: SubscriptionDto) -> Optional[int]:
        short_uuid = extract_short_uuid(subscription.url)
        if short_uuid:
            remna_user = await self.remnawave.get_user_by_short_uuid(short_uuid)
            if remna_user:
                return remna_user.id

        user = await self.user_dao.get_by_id(subscription.user_id)
        if not user:
            return None

        remna_user = await self.remnawave.get_user_by_username(user.remna_name)
        return remna_user.id if remna_user else None
