"""
LoanMaturityWorkflow — waits until loan due date, then checks for repayment.

Started as a CHILD workflow from AuctionCloseWorkflow via start_child_workflow (fire-and-forget).
This workflow runs for days/weeks — it sleeps until the loan's due date.
"""

from datetime import datetime, timedelta, timezone

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities.payment_activities import get_loan_grpc, update_loan_status_grpc
    from activities.marketplace_activities import bulk_delist
    from activities.rabbitmq_activities import publish_event
    import config


@workflow.defn
class LoanMaturityWorkflow:
    """Monitors loan maturity: waits until due date → checks repayment → marks OVERDUE if not repaid."""

    @workflow.run
    async def run(self, loan_id: str, due_date: str):
        act_opts = {"schedule_to_close_timeout": timedelta(seconds=30)}

        # Step 1: Sleep until due date
        due_dt = datetime.fromisoformat(due_date).replace(tzinfo=timezone.utc)
        delay = due_dt - workflow.now()
        if delay.total_seconds() > 0:
            await workflow.sleep(delay)

        # Step 2: Mark loan DUE
        await workflow.execute_activity(update_loan_status_grpc, args=[loan_id, "DUE"], **act_opts)
        await workflow.execute_activity(
            publish_event,
            args=["loan.due", {"loan_id": loan_id}],
            **act_opts,
        )

        # Step 3: Wait for repayment window
        repayment_window = timedelta(seconds=config.REPAYMENT_WINDOW_SECONDS)
        await workflow.sleep(repayment_window)

        # Step 4: Check if repaid
        loan = await workflow.execute_activity(get_loan_grpc, args=[loan_id], **act_opts)
        if loan["status"] == "REPAID":
            return  # Seller repaid in time — done

        # Step 5: Mark OVERDUE + publish event + bulk delist
        await workflow.execute_activity(update_loan_status_grpc, args=[loan_id, "OVERDUE"], **act_opts)
        await workflow.execute_activity(
            publish_event,
            args=["loan.overdue", {
                "loan_id": loan_id,
                "invoice_token": loan.get("invoice_token", ""),
                "investor_id": loan["investor_id"],
                "seller_id": loan["seller_id"],
            }],
            **act_opts,
        )
        await workflow.execute_activity(bulk_delist, args=[loan["seller_id"]], **act_opts)
