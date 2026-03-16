"""
AuctionCloseWorkflow — handles auction timer, anti-snipe extension, and 10-step financial settlement.

CRITICAL: The anti-snipe loop MUST check the flag BEFORE resetting it.
CRITICAL: LoanMaturityWorkflow MUST be started with start_child_workflow (fire-and-forget).
"""

import asyncio
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities.invoice_activities import verify_invoice, update_invoice_status
    from activities.bidding_activities import get_offers, accept_offer, reject_offer
    from activities.payment_activities import (
        convert_escrow_to_loan,
        create_loan,
        release_funds_to_seller,
    )
    from activities.marketplace_activities import delist_listing
    from activities.rabbitmq_activities import publish_event
    from workflows.loan_maturity import LoanMaturityWorkflow


@workflow.defn
class AuctionCloseWorkflow:
    """
    Manages the full auction lifecycle: timer → anti-snipe → settlement.
    Signal: extend_deadline — received from Bidding Orchestrator when bid arrives in final 5 minutes.
    """

    def __init__(self):
        self.extend_requested = False

    @workflow.signal
    async def extend_deadline(self):
        """Signal received from Bidding Orchestrator when a bid arrives in the final 5 minutes."""
        self.extend_requested = True

    @workflow.run
    async def run(self, invoice_token: str, bid_period_hours: int):
        act_opts = {"schedule_to_close_timeout": timedelta(seconds=30)}
        deadline = workflow.now() + timedelta(hours=bid_period_hours)

        # T-12h warning
        t12h = deadline - timedelta(hours=12)
        if t12h > workflow.now():
            await workflow.sleep_until(t12h)
            await workflow.execute_activity(
                publish_event,
                args=["auction.closing.warning", {"invoice_token": invoice_token, "hours_remaining": 12}],
                **act_opts,
            )

        # T-1h warning
        t1h = deadline - timedelta(hours=1)
        if t1h > workflow.now():
            await workflow.sleep_until(t1h)
            await workflow.execute_activity(
                publish_event,
                args=["auction.closing.warning", {"invoice_token": invoice_token, "hours_remaining": 1}],
                **act_opts,
            )

        # Wait until deadline
        await workflow.sleep_until(deadline)

        # Anti-snipe loop: keep extending while signals arrive
        # CRITICAL: Check flag BEFORE resetting — a signal may have arrived during sleep_until
        while True:
            if not self.extend_requested:
                try:
                    await workflow.wait_condition(
                        lambda: self.extend_requested,
                        timeout=timedelta(minutes=5),
                    )
                except asyncio.TimeoutError:
                    # No signal in 5 minutes → auction closes
                    break
            # Signal was received — reset flag and loop for another 5-min window
            self.extend_requested = False

        # Fetch all bids
        offers = await workflow.execute_activity(get_offers, args=[invoice_token], **act_opts)
        if not offers:
            await workflow.execute_activity(
                publish_event,
                args=["auction.expired", {"invoice_token": invoice_token}],
                **act_opts,
            )
            return

        winner = max(offers, key=lambda o: o["bid_amount"])
        losers = [o for o in offers if o["id"] != winner["id"]]

        # 10-step financial settlement
        invoice = await workflow.execute_activity(verify_invoice, args=[invoice_token], **act_opts)
        await workflow.execute_activity(
            convert_escrow_to_loan, args=[winner["investor_id"], invoice_token], **act_opts
        )
        loan = await workflow.execute_activity(
            create_loan,
            args=[winner["investor_id"], invoice["seller_id"], invoice_token,
                  winner["bid_amount"], invoice["due_date"]],
            **act_opts,
        )

        # Fire-and-forget: LoanMaturityWorkflow runs for days/weeks — do NOT await result
        child_handle = await workflow.start_child_workflow(
            LoanMaturityWorkflow.run,
            args=[loan["loan_id"], loan["due_date"]],
            id=f"loan-{loan['loan_id']}",
        )
        # Intentionally not awaiting child_handle.result()

        await workflow.execute_activity(
            release_funds_to_seller,
            args=[invoice["seller_id"], winner["bid_amount"], invoice_token],
            **act_opts,
        )
        await workflow.execute_activity(update_invoice_status, args=[invoice_token, "FINANCED"], **act_opts)
        await workflow.execute_activity(delist_listing, args=[invoice_token], **act_opts)
        await workflow.execute_activity(accept_offer, args=[winner["id"]], **act_opts)

        # Reject all losers in parallel
        await asyncio.gather(*[
            workflow.execute_activity(reject_offer, args=[o["id"]], **act_opts)
            for o in losers
        ])

        # Publish outcome events
        await workflow.execute_activity(
            publish_event,
            args=["auction.closed.winner", {
                "invoice_token": invoice_token,
                "investor_id": winner["investor_id"],
                "loan_id": loan["loan_id"],
            }],
            **act_opts,
        )
        for loser in losers:
            await workflow.execute_activity(
                publish_event,
                args=["auction.closed.loser", {
                    "invoice_token": invoice_token,
                    "investor_id": loser["investor_id"],
                }],
                **act_opts,
            )
