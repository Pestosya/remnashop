import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from enum import auto
from typing import Optional
from uuid import UUID

from loguru import logger
from redis.asyncio import Redis

from src.application.common import Interactor
from src.application.common.dao import SettingsDao, SubscriptionDao, TransactionDao, UserDao
from src.application.common.policy import Permission
from src.application.common.uow import UnitOfWork
from src.application.dto import (
    PlanDto,
    PlanSnapshotDto,
    PriceDetailsDto,
    TransactionDto,
    UserDto,
)
from src.application.services import PricingService
from src.application.use_cases.gateways.commands.payment import ProcessPayment, ProcessPaymentDto
from src.application.use_cases.plan.queries.match import MatchPlan, MatchPlanDto
from src.application.use_cases.user.queries.plans import GetAvailablePlans
from src.core.enums import (
    Currency,
    PaymentGatewayType,
    PurchaseType,
    TransactionStatus,
    UpperStrEnum,
)
from src.core.exceptions import InsufficientPointsError, PointsExchangeUnavailableError

# a second tap on "exchange" within this time is ignored
EXCHANGE_LOCK_SECONDS = 15


class PointsExchangeStatus(UpperStrEnum):
    AVAILABLE = auto()  # a plan is set: pick a duration
    CHOOSE_PLAN = auto()  # no paid subscription yet: pick a plan first
    DISABLED = auto()  # switched off in the settings
    UNLIMITED = auto()  # the subscription never ends: nothing to renew
    PLAN_UNAVAILABLE = auto()  # the current plan is no longer sold
    NO_PLANS = auto()  # nothing to buy at all


@dataclass(frozen=True, kw_only=True)
class PointsOfferDto:
    days: int
    cost: int  # points
    original_amount: Decimal  # rubles before the user's discount
    discount_percent: int
    affordable: bool


@dataclass(kw_only=True)
class PointsExchangeDto:
    points: int
    status: PointsExchangeStatus
    purchase_type: PurchaseType = PurchaseType.NEW
    plan: Optional[PlanDto] = None
    plans: list[PlanDto] = field(default_factory=list)
    offers: list[PointsOfferDto] = field(default_factory=list)

    def get_offer(self, days: int) -> Optional[PointsOfferDto]:
        return next((offer for offer in self.offers if offer.days == days), None)

    def offer_for(
        self, plan_id: int, days: int, purchase_type: PurchaseType
    ) -> Optional[PointsOfferDto]:
        """The offer for a purchase chosen in the regular flow, if points can pay for it: the
        same plan, duration and kind of purchase. Switching plans is never paid with points."""
        if self.status != PointsExchangeStatus.AVAILABLE or self.plan is None:
            return None
        if self.plan.id != plan_id or self.purchase_type != purchase_type:
            return None
        return self.get_offer(days)


class GetPointsExchange(Interactor[Optional[int], PointsExchangeDto]):
    """What a user can get for their points right now.

    A user with a paid subscription renews it: same plan, any of its durations. A user
    without one (never bought, or on a trial) buys a plan; `plan_id` is their choice when
    several are on sale. Switching to another plan is left to the regular purchase flow: it
    drops the days left, which nobody should lose by tapping "exchange".

    A duration costs its ruble price (with the user's discounts) times the rate.
    """

    required_permission = Permission.PUBLIC

    def __init__(
        self,
        settings_dao: SettingsDao,
        user_dao: UserDao,
        subscription_dao: SubscriptionDao,
        pricing_service: PricingService,
        get_available_plans: GetAvailablePlans,
        match_plan: MatchPlan,
    ) -> None:
        self.settings_dao = settings_dao
        self.user_dao = user_dao
        self.subscription_dao = subscription_dao
        self.pricing_service = pricing_service
        self.get_available_plans = get_available_plans
        self.match_plan = match_plan

    async def _execute(self, actor: UserDto, plan_id: Optional[int]) -> PointsExchangeDto:
        user = await self.user_dao.get_by_id(actor.id) or actor  # the balance as it is now
        settings = await self.settings_dao.get()
        result = PointsExchangeDto(points=user.points, status=PointsExchangeStatus.DISABLED)

        if not settings.extra.points.exchange_enabled:
            return result

        plans = [p for p in await self.get_available_plans.system(user) if not p.is_trial]
        subscription = await self.subscription_dao.get_current(user.id)

        if subscription and not subscription.is_trial:
            result.purchase_type = PurchaseType.RENEW
            if subscription.is_unlimited:
                result.status = PointsExchangeStatus.UNLIMITED
                return result

            # the same rule as the regular renewal: the plan as bought, or as it is sold now
            snapshot = subscription.plan_snapshot
            result.plan = await self.match_plan.system(
                MatchPlanDto(plan_snapshot=snapshot, plans=plans)
            ) or next((p for p in plans if p.id == snapshot.id), None)
            if result.plan is None:
                result.status = PointsExchangeStatus.PLAN_UNAVAILABLE
                return result
        else:
            result.purchase_type = PurchaseType.NEW
            if not plans:
                result.status = PointsExchangeStatus.NO_PLANS
                return result
            if len(plans) == 1:
                result.plan = plans[0]
            else:
                result.plan = next((p for p in plans if p.id == plan_id), None)
            if result.plan is None:
                result.plans = plans
                result.status = PointsExchangeStatus.CHOOSE_PLAN
                return result

        result.offers = self._offers(user, result.plan, settings.extra.points.points_per_ruble)
        result.status = (
            PointsExchangeStatus.AVAILABLE if result.offers else PointsExchangeStatus.NO_PLANS
        )
        return result

    def _offers(self, user: UserDto, plan: PlanDto, rate: int) -> list[PointsOfferDto]:
        offers: list[PointsOfferDto] = []
        for duration in plan.durations:
            # an endless duration and one without a ruble price cannot be priced in points
            if duration.days <= 0 or not any(p.currency == Currency.RUB for p in duration.prices):
                continue
            pricing = self.pricing_service.calculate_for_duration(user, duration, Currency.RUB)
            cost = int(pricing.final_amount) * rate
            if cost <= 0:
                continue
            offers.append(
                PointsOfferDto(
                    days=duration.days,
                    cost=cost,
                    original_amount=pricing.original_amount,
                    discount_percent=pricing.discount_percent,
                    affordable=user.points >= cost,
                )
            )
        return offers


@dataclass(frozen=True)
class ExchangePointsDto:
    plan_id: int
    days: int


@dataclass(frozen=True)
class PointsExchangeResultDto:
    payment_id: UUID
    spent: int
    remaining: int


class ExchangePoints(Interactor[ExchangePointsDto, PointsExchangeResultDto]):
    """Pay for a subscription with points: the offer is recalculated, recorded as a
    transaction that costs points instead of money, and completed through the regular
    payment pipeline, which takes the points in the same database transaction that
    completes the purchase and returns them if the subscription could not be issued."""

    required_permission = Permission.PUBLIC

    def __init__(
        self,
        uow: UnitOfWork,
        user_dao: UserDao,
        transaction_dao: TransactionDao,
        redis: Redis,
        get_points_exchange: GetPointsExchange,
        process_payment: ProcessPayment,
    ) -> None:
        self.uow = uow
        self.user_dao = user_dao
        self.transaction_dao = transaction_dao
        self.redis = redis
        self.get_points_exchange = get_points_exchange
        self.process_payment = process_payment

    async def _execute(self, actor: UserDto, data: ExchangePointsDto) -> PointsExchangeResultDto:
        if not await self.redis.set(
            f"points_exchange:{actor.id}", "1", ex=EXCHANGE_LOCK_SECONDS, nx=True
        ):
            raise PointsExchangeUnavailableError("Another exchange is in progress")

        exchange = await self.get_points_exchange(actor, data.plan_id)
        offer = exchange.get_offer(data.days)
        plan = exchange.plan

        if (
            exchange.status != PointsExchangeStatus.AVAILABLE
            or plan is None
            or plan.id != data.plan_id
            or offer is None
        ):
            raise PointsExchangeUnavailableError(
                f"Exchange is not available: status '{exchange.status}', plan '{data.plan_id}', "
                f"days '{data.days}'"
            )
        if not offer.affordable:
            raise InsufficientPointsError(required=offer.cost, available=exchange.points)

        transaction = TransactionDto(
            payment_id=uuid.uuid4(),
            user_id=actor.id,
            status=TransactionStatus.PENDING,
            purchase_type=exchange.purchase_type,
            gateway_type=PaymentGatewayType.POINTS,
            pricing=PriceDetailsDto(
                original_amount=offer.original_amount,
                discount_percent=offer.discount_percent,
                final_amount=Decimal(0),
                points_spent=offer.cost,
            ),
            currency=Currency.RUB,
            plan_snapshot=PlanSnapshotDto.from_plan(plan, offer.days),
        )

        async with self.uow:
            await self.transaction_dao.create(transaction)
            await self.uow.commit()

        logger.info(
            f"{actor.log} Exchanging '{offer.cost}' points: '{exchange.purchase_type}' "
            f"plan '{plan.id}' for '{offer.days}' days, transaction '{transaction.payment_id}'"
        )
        await self.process_payment.system(
            ProcessPaymentDto(
                payment_id=transaction.payment_id,
                new_transaction_status=TransactionStatus.COMPLETED,
                gateway_type=PaymentGatewayType.POINTS,
            )
        )

        user = await self.user_dao.get_by_id(actor.id)
        return PointsExchangeResultDto(
            payment_id=transaction.payment_id,
            spent=offer.cost,
            remaining=user.points if user else 0,
        )
