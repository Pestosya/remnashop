from loguru import logger
from redis.asyncio import Redis

from src.application.common import EventPublisher, Interactor
from src.application.common.dao import SettingsDao, TransactionDao, UserDao
from src.application.common.uow import UnitOfWork
from src.application.dto import TransactionDto, UserDto
from src.application.events import PaymentAbandonedEvent
from src.core.constants import TIME_1H


class RemindAbandonedPayments(Interactor[None, int]):
    """Nudge users whose payment was started and never completed.

    Runs together with the periodic cleanup of pending transactions and looks at payments
    that are still unpaid or were cancelled (expired, declined) in the last two hours. A user
    gets at most one reminder per cooldown period, and none when they have already started
    or completed another payment since.
    """

    required_permission = None

    def __init__(
        self,
        uow: UnitOfWork,
        user_dao: UserDao,
        transaction_dao: TransactionDao,
        settings_dao: SettingsDao,
        redis: Redis,
        event_publisher: EventPublisher,
    ) -> None:
        self.uow = uow
        self.user_dao = user_dao
        self.transaction_dao = transaction_dao
        self.settings_dao = settings_dao
        self.redis = redis
        self.event_publisher = event_publisher

    async def _execute(self, actor: UserDto, data: None) -> int:
        events: list[PaymentAbandonedEvent] = []

        async with self.uow:
            settings = await self.settings_dao.get()
            cooldown = settings.extra.retention.abandoned_payment_cooldown_hours * TIME_1H

            # newest first: only the latest attempt of each user matters
            latest_by_user: dict[int, TransactionDto] = {}
            for transaction in await self.transaction_dao.get_abandoned():
                latest_by_user.setdefault(transaction.user_id, transaction)

            for user_id, transaction in latest_by_user.items():
                user = await self.user_dao.get_by_id(user_id)
                if not user or user.telegram_id is None or user.is_blocked or user.is_bot_blocked:
                    continue

                if transaction.created_at is None or await self.transaction_dao.has_activity_after(
                    user_id, transaction.created_at
                ):
                    continue

                if not await self.redis.set(self._key(user_id), "1", ex=cooldown, nx=True):
                    continue

                events.append(
                    PaymentAbandonedEvent(
                        user=user,
                        purchase_type=transaction.purchase_type,
                        plan_name=transaction.plan_snapshot.name,
                    )
                )

        for event in events:
            await self.event_publisher.publish(event)

        if events:
            logger.info(f"Sent '{len(events)}' abandoned payment reminders")
        return len(events)

    @staticmethod
    def _key(user_id: int) -> str:
        return f"abandoned_payment_reminder:{user_id}"
