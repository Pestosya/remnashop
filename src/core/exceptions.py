from datetime import datetime
from typing import Union


class MenuRenderError(Exception): ...


class PermissionDeniedError(Exception): ...


class UserNotFoundError(Exception):
    def __init__(self, user_id: Union[int, str, None] = None) -> None:
        self.user_id = user_id
        super().__init__(f"User with id '{user_id}' not found" if user_id else "User not found")


class SubscriptionNotLinkedError(Exception):
    """A subscription still carries a pre-3.0 panel UUID instead of a panel id.

    Panel 3.x identifies users by a numeric id and no longer exposes the UUID
    these rows were created with, so they must be re-linked (see the backfill
    in `SyncRemnaUser`) before any panel call can target them.
    """

    def __init__(self, subscription_id: Union[int, None] = None) -> None:
        self.subscription_id = subscription_id
        super().__init__(
            f"Subscription '{subscription_id}' is not linked to a Remnawave panel user id"
        )


class FileNotFoundError(Exception): ...


class LogsToFileDisabledError(Exception):
    def __init__(self) -> None:
        super().__init__("Logging to file is disabled in configuration")


class PlanError(Exception): ...


class SquadsEmptyError(PlanError): ...


class TrialDurationError(PlanError): ...


class PlanNameAlreadyExistsError(PlanError): ...


class UserAlreadyAllowedError(PlanError): ...


class DurationAlreadyExistsError(PlanError): ...


class PriceNotFoundError(PlanError): ...


class GatewayNotConfiguredError(Exception): ...


class PurchaseError(Exception): ...


class InsufficientPointsError(Exception):
    def __init__(self, required: int, available: int) -> None:
        self.required = required
        self.available = available
        super().__init__(f"Not enough points: '{required}' required, '{available}' available")


class PointsExchangeUnavailableError(Exception): ...


class TrialNotAvailableError(Exception): ...


class MenuEditorInvalidPayloadError(Exception): ...


class BlacklistSourceAlreadyExistsError(Exception): ...


class CooldownError(Exception):
    def __init__(self, available_at: datetime) -> None:
        self.available_at = available_at
        super().__init__(f"Cooldown active until {available_at}")


class PromocodeError(Exception): ...


class PromocodeNotFoundError(PromocodeError): ...


class PromocodeNotAvailableError(PromocodeError): ...


class PromocodeExpiredError(PromocodeNotAvailableError): ...


class PromocodeAlreadyActivatedError(PromocodeError): ...


class EmailDeliveryError(Exception): ...


class EmailDeliveryDisabledError(Exception): ...
