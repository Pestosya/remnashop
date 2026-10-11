from typing import Final

from src.application.common import Interactor

from .exchange import ExchangePoints, GetPointsExchange

POINTS_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    GetPointsExchange,
    ExchangePoints,
)
