import asyncio
from dataclasses import dataclass
from datetime import timedelta

from loguru import logger
from redis.asyncio import Redis

from src.application.common import EventPublisher, Interactor, Notifier, Remnawave
from src.application.common.dao import SubscriptionDao, UserDao
from src.application.common.policy import Permission
from src.application.common.uow import UnitOfWork
from src.application.dto import MessagePayloadDto, UserDto
from src.application.events import CompensationFinishedEvent
from src.core.constants import BATCH_DELAY, BATCH_SIZE_20, TIME_1D
from src.core.enums import SubscriptionStatus
from src.core.utils.iterables import chunked

COMPENSATION_DAYS_MIN = 1
COMPENSATION_DAYS_MAX = 60


@dataclass(frozen=True)
class CompensateOutageDto:
    run_id: str
    days: int
    notify: bool = True


@dataclass(frozen=True)
class CompensationResultDto:
    extended: int
    failed: int
    notified: int


class CompensateOutage(Interactor[CompensateOutageDto, CompensationResultDto]):
    """Add days to every active paid subscription after an outage and tell the users.

    Trials and unlimited subscriptions are left alone. Every user is handled in a transaction
    of their own, and a per-run marker makes a repeated run with the same `run_id` skip the
    users that already got their days: nobody is extended twice.
    """

    required_permission = Permission.COMPENSATION

    def __init__(
        self,
        uow: UnitOfWork,
        user_dao: UserDao,
        subscription_dao: SubscriptionDao,
        remnawave: Remnawave,
        redis: Redis,
        notifier: Notifier,
        event_publisher: EventPublisher,
    ) -> None:
        self.uow = uow
        self.user_dao = user_dao
        self.subscription_dao = subscription_dao
        self.remnawave = remnawave
        self.redis = redis
        self.notifier = notifier
        self.event_publisher = event_publisher

    async def _execute(self, actor: UserDto, data: CompensateOutageDto) -> CompensationResultDto:
        if not COMPENSATION_DAYS_MIN <= data.days <= COMPENSATION_DAYS_MAX:
            raise ValueError(f"Invalid compensation days '{data.days}'")

        users = await self.user_dao.get_with_active_paid_subscription()
        compensated: list[UserDto] = []
        failed = 0

        for user in users:
            try:
                if await self._extend(user, data):
                    compensated.append(user)
            except Exception:
                failed += 1
                logger.exception(f"Compensation failed for user {user.log}")
            await asyncio.sleep(0.05)  # be gentle with the panel

        notified = await self._notify(compensated, data.days) if data.notify else 0

        logger.info(
            f"{actor.log} Compensation '{data.run_id}': +{data.days} days for "
            f"'{len(compensated)}' users, '{failed}' failed, '{notified}' notified"
        )
        await self.event_publisher.publish(
            CompensationFinishedEvent(
                days=data.days,
                extended=len(compensated),
                failed=failed,
                notified=notified,
            )
        )
        return CompensationResultDto(extended=len(compensated), failed=failed, notified=notified)

    async def _extend(self, user: UserDto, data: CompensateOutageDto) -> bool:
        marker = f"compensation:{data.run_id}:{user.id}"

        async with self.uow:
            subscription = await self.subscription_dao.get_current(user.id)
            if (
                not subscription
                or subscription.status != SubscriptionStatus.ACTIVE
                or subscription.is_trial
                or subscription.is_unlimited
                or not subscription.is_linked
            ):
                return False

            if not await self.redis.set(marker, "1", ex=TIME_1D * 7, nx=True):
                return False

            try:
                subscription.expire_at = subscription.expire_at + timedelta(days=data.days)
                await self.subscription_dao.update(subscription)
                await self.remnawave.update_user(
                    user=user,
                    remna_id=subscription.remna_id,
                    subscription=subscription,
                )
                await self.uow.commit()
            except Exception:
                # nothing was granted: let a repeated run try this user again
                await self.redis.delete(marker)
                raise

        return True

    async def _notify(self, users: list[UserDto], days: int) -> int:
        notified = 0
        for batch in chunked(users, BATCH_SIZE_20):
            results = await asyncio.gather(
                *(
                    self.notifier.notify_user(
                        user=user,
                        payload=MessagePayloadDto(
                            i18n_key="ntf-fleet.compensation",
                            i18n_kwargs={"value": days},
                            disable_default_markup=False,
                            delete_after=None,
                        ),
                    )
                    for user in batch
                ),
                return_exceptions=True,
            )
            notified += sum(1 for r in results if r is not None and not isinstance(r, Exception))
            await asyncio.sleep(BATCH_DELAY)
        return notified
