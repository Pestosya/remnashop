from datetime import datetime, timedelta

from loguru import logger
from redis.asyncio import Redis

from src.application.common import EventPublisher, Interactor
from src.application.common.dao import SettingsDao, UserDao
from src.application.common.uow import UnitOfWork
from src.application.dto import UserDto, WinbackStepDto
from src.application.events import SubscriptionWinbackEvent
from src.core.constants import TIME_1D
from src.core.utils.time import datetime_now


class SendWinbackSeries(Interactor[None, int]):
    """Daily follow-ups for users whose subscription or trial expired a while ago.

    Each step covers the users whose current subscription expired between `day` and `day + 1`
    days ago, so one daily run reaches every user exactly once per step. A step may grant a
    one-time discount on the next purchase; an existing bigger discount is never lowered.
    """

    required_permission = None

    def __init__(
        self,
        uow: UnitOfWork,
        user_dao: UserDao,
        settings_dao: SettingsDao,
        redis: Redis,
        event_publisher: EventPublisher,
    ) -> None:
        self.uow = uow
        self.user_dao = user_dao
        self.settings_dao = settings_dao
        self.redis = redis
        self.event_publisher = event_publisher

    async def _execute(self, actor: UserDto, data: None) -> int:
        events: list[SubscriptionWinbackEvent] = []

        async with self.uow:
            retention = (await self.settings_dao.get()).extra.retention
            now = datetime_now()

            for is_trial, steps in (
                (False, retention.winback_paid),
                (True, retention.winback_trial),
            ):
                for step in steps:
                    events += await self._collect(is_trial, step, now - timedelta(days=step.day))

            await self.uow.commit()

        for event in events:
            await self.event_publisher.publish(event)

        logger.info(f"Sent '{len(events)}' win-back messages")
        return len(events)

    async def _collect(
        self,
        is_trial: bool,
        step: WinbackStepDto,
        expired_before: datetime,
    ) -> list[SubscriptionWinbackEvent]:
        events: list[SubscriptionWinbackEvent] = []
        users = await self.user_dao.get_expired_between(
            start=expired_before - timedelta(days=1),
            end=expired_before,
            is_trial=is_trial,
        )

        for user in users:
            # survives a retry of the task and a second run on the same day
            key = f"winback_sent:{user.id}:{int(is_trial)}:{step.day}"
            if not await self.redis.set(key, "1", ex=TIME_1D * 3, nx=True):
                continue

            discount = min(max(step.discount, 0), 100)
            if discount > (user.purchase_discount or 0):
                user.purchase_discount = discount
                await self.user_dao.update(user)

            events.append(
                SubscriptionWinbackEvent(
                    user=user,
                    is_trial=is_trial,
                    day=step.day,
                    # the discount the user really has now: an earlier, bigger one stays
                    discount=max(user.purchase_discount or 0, user.personal_discount or 0),
                )
            )

        return events
