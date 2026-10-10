from dishka.integrations.taskiq import FromDishka, inject

from src.application.use_cases.retention.commands.winback import SendWinbackSeries
from src.infrastructure.taskiq.broker import broker


# 10:00 UTC = 13:00 Moscow time
@broker.task(schedule=[{"cron": "0 10 * * *"}], retry_on_error=False)
@inject(patch_module=True)
async def send_winback_series_task(
    send_winback_series: FromDishka[SendWinbackSeries],
) -> None:
    await send_winback_series.system()
