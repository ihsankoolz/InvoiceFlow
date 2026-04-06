"""
WalletTopUpWorkflow — credits investor wallet after Stripe payment confirmation.
Started by Bidding Orchestrator's Stripe webhook handler.
"""

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities.invoice_activities import get_user
    from activities.payment_activities import credit_wallet
    from activities.rabbitmq_activities import publish_event


@workflow.defn
class WalletTopUpWorkflow:
    """Credits wallet and publishes wallet.credited event."""

    @workflow.run
    async def run(self, user_id: int, amount: float):
        act_opts = {"schedule_to_close_timeout": timedelta(seconds=30)}

        await workflow.execute_activity(credit_wallet, args=[user_id, amount], **act_opts)
        investor = await workflow.execute_activity(get_user, args=[user_id], **act_opts)
        await workflow.execute_activity(
            publish_event,
            args=[
                "wallet.credited",
                {
                    "investor_id": user_id,
                    "investor_email": investor["email"],
                    "amount": amount,
                },
            ],
            **act_opts,
        )
