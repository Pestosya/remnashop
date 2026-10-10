from typing import Final

from src.application.common import Interactor

from .commands.payments import RemindAbandonedPayments
from .commands.winback import SendWinbackSeries

RETENTION_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    RemindAbandonedPayments,
    SendWinbackSeries,
)
