"""
LoanRepaymentWorkflow — confirms loan repayment after Stripe payment.

Started by the loan-orchestrator's Stripe event consumer (or directly via
the /confirm-repayment REST endpoint in future iterations).

Steps:
  1. Update loan status to REPAID via gRPC
  2. Signal the running LoanMaturityWorkflow so it exits the repayment window early
  3. Fetch full loan details
  4. Fetch seller and investor emails
  5. Publish loan.repaid event for downstream consumers
     (invoice-service sets invoice → REPAID, notification-service emails both parties)
"""

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities.invoice_activities import get_user
    from activities.payment_activities import get_loan_grpc, update_loan_status_grpc
    from activities.rabbitmq_activities import publish_event


@workflow.defn
class LoanRepaymentWorkflow:
    """Confirms loan repayment: marks REPAID via gRPC and publishes loan.repaid."""

    @workflow.run
    async def run(self, loan_id: str, stripe_session_id: str):
        act_opts = {"schedule_to_close_timeout": timedelta(seconds=30)}

        # Step 1: Mark loan REPAID via gRPC
        await workflow.execute_activity(
            update_loan_status_grpc, args=[loan_id, "REPAID"], **act_opts
        )

        # Step 2: Signal LoanMaturityWorkflow so it exits the repayment window early
        # instead of sleeping the full window and then polling for status.
        try:
            maturity_handle = workflow.get_external_workflow_handle(f"loan-{loan_id}")
            await maturity_handle.signal("repayment_confirmed")
        except Exception:
            # Maturity workflow may have already completed (e.g. window expired simultaneously).
            # Not a fatal error — the status is already REPAID in the database.
            pass

        # Step 3: Fetch full loan details (investor_id, seller_id, principal, invoice_token)
        loan = await workflow.execute_activity(get_loan_grpc, args=[loan_id], **act_opts)

        # Step 4: Fetch user details for notification events
        seller = await workflow.execute_activity(
            get_user, args=[loan["seller_id"]], **act_opts
        )
        investor = await workflow.execute_activity(
            get_user, args=[loan["investor_id"]], **act_opts
        )

        # Step 5: Publish loan.repaid — consumed by invoice-service, notification-service
        await workflow.execute_activity(
            publish_event,
            args=[
                "loan.repaid",
                {
                    "loan_id": loan_id,
                    "invoice_token": loan.get("invoice_token", ""),
                    "seller_id": loan["seller_id"],
                    "seller_email": seller["email"],
                    "investor_id": loan["investor_id"],
                    "investor_email": investor["email"],
                    "principal": loan["principal"],
                    "stripe_session_id": stripe_session_id,
                },
            ],
            **act_opts,
        )
