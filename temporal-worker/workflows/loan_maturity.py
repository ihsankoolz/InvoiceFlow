"""
LoanMaturityWorkflow — waits until loan due date, then checks for repayment.

Started as a CHILD workflow from AuctionCloseWorkflow via start_child_workflow (fire-and-forget).
This workflow runs for days/weeks — it sleeps until the loan's due date.

See BUILD_INSTRUCTIONS_V2.md Section 13 — LoanMaturityWorkflow
"""

from datetime import datetime, timedelta

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
        """
        Run the loan maturity workflow.

        Steps:
        1. Sleep until due_date (datetime ISO string)
        2. Mark loan DUE via gRPC update_loan_status_grpc(loan_id, "DUE")
        3. Publish loan.due event
        4. Sleep for repayment window (REPAYMENT_WINDOW_SECONDS — 120s demo / 86400s production)
        5. Check loan status via gRPC get_loan_grpc(loan_id)
        6. If status == "REPAID" → return (business repaid in time)
        7. If not repaid → mark OVERDUE via gRPC update_loan_status_grpc(loan_id, "OVERDUE")
        8. Publish loan.overdue event (triggers 4-consumer choreography)
        9. Bulk delist defaulting seller's listings

        See BUILD_INSTRUCTIONS_V2.md Section 13 — LoanMaturityWorkflow
        """
        # TODO: Implement
        pass
