from typing import Final

from src.application.common import Interactor

from .commands.check import CheckFleet
from .commands.compensation import CompensateOutage
from .commands.settings import ToggleFleetOption
from .queries.state import GetFleetState

FLEET_USE_CASES: Final[tuple[type[Interactor], ...]] = (
    CheckFleet,
    CompensateOutage,
    ToggleFleetOption,
    GetFleetState,
)
