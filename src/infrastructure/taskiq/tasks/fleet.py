from dishka.integrations.taskiq import FromDishka, inject

from src.application.use_cases.fleet.commands.check import CheckFleet
from src.application.use_cases.fleet.commands.compensation import (
    CompensateOutage,
    CompensateOutageDto,
)
from src.infrastructure.taskiq.broker import broker


# no retries: a failed check simply waits for the next run
@broker.task(schedule=[{"cron": "*/15 * * * *"}], retry_on_error=False)
@inject(patch_module=True)
async def check_fleet_task(check_fleet: FromDishka[CheckFleet]) -> None:
    await check_fleet.system(False)


# started by an admin from the dashboard: runs even when the monitoring is switched off
@broker.task(retry_on_error=False)
@inject(patch_module=True)
async def check_fleet_now_task(check_fleet: FromDishka[CheckFleet]) -> None:
    await check_fleet.system(True)


# no retries either: the run reports its own per-user failures
@broker.task(retry_on_error=False)
@inject(patch_module=True)
async def compensate_outage_task(
    run_id: str,
    days: int,
    notify: bool,
    compensate_outage: FromDishka[CompensateOutage],
) -> None:
    await compensate_outage.system(CompensateOutageDto(run_id=run_id, days=days, notify=notify))
