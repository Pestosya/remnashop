from uuid import UUID

from dishka.integrations.taskiq import FromDishka, inject
from loguru import logger

from src.application.use_cases.gateways.commands.payment import ProcessPayment, ProcessPaymentDto
from src.application.use_cases.misc.commands.maintenance import CancelOldTransactions
from src.application.use_cases.retention.commands.payments import RemindAbandonedPayments
from src.core.enums import PaymentGatewayType, TransactionStatus
from src.infrastructure.taskiq.broker import broker


@broker.task()
@inject(patch_module=True)
async def handle_payment_transaction_task(
    payment_id: UUID,
    payment_status: TransactionStatus,
    gateway_type: PaymentGatewayType,
    process_payment: FromDishka[ProcessPayment],
) -> None:
    await process_payment.system(
        ProcessPaymentDto(
            payment_id=payment_id,
            new_transaction_status=payment_status,
            gateway_type=gateway_type,
        )
    )


@broker.task(schedule=[{"cron": "*/30 * * * *"}])
@inject(patch_module=True)
async def cancel_old_transactions_task(
    cancel_old_transactions: FromDishka[CancelOldTransactions],
    remind_abandoned_payments: FromDishka[RemindAbandonedPayments],
) -> None:
    await cancel_old_transactions.system()

    try:
        await remind_abandoned_payments.system()
    except Exception:
        # reminders are best-effort and must not fail (and retry) the cleanup itself
        logger.exception("Failed to send abandoned payment reminders")
