"""
AuctionCloseWorkflow — handles auction timer, anti-snipe extension, and 10-step financial settlement.

CRITICAL: The anti-snipe loop MUST check the flag BEFORE resetting it.
CRITICAL: LoanMaturityWorkflow MUST be started with start_child_workflow (fire-and-forget).
"""

import asyncio
from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities.bidding_activities import accept_offer, get_offers, reject_offer
    from activities.invoice_activities import get_user, update_invoice_status, verify_invoice
    from activities.marketplace_activities import delist_listing
    from activities.payment_activities import (
        convert_escrow_to_loan,
        create_loan,
        release_escrow,
        release_funds_to_seller,
    )
    from activities.rabbitmq_activities import publish_event

    import config
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
            await workflow.sleep(t12h - workflow.now())
            offers_12h = await workflow.execute_activity(get_offers, args=[invoice_token], **act_opts)
            bidders_12h = []
            for o in offers_12h:
                u = await workflow.execute_activity(get_user, args=[o["investor_id"]], **act_opts)
                bidders_12h.append({"user_id": o["investor_id"], "email": u["email"]})
            await workflow.execute_activity(
                publish_event,
                args=["auction.closing.warning", {
                    "invoice_token": invoice_token,
                    "hours_remaining": 12,
                    "bidders": bidders_12h,
                }],
                **act_opts,
            )

        # T-1h warning
        t1h = deadline - timedelta(hours=1)
        if t1h > workflow.now():
            await workflow.sleep(t1h - workflow.now())
            offers_1h = await workflow.execute_activity(get_offers, args=[invoice_token], **act_opts)
            bidders_1h = []
            for o in offers_1h:
                u = await workflow.execute_activity(get_user, args=[o["investor_id"]], **act_opts)
                bidders_1h.append({"user_id": o["investor_id"], "email": u["email"]})
            await workflow.execute_activity(
                publish_event,
                args=["auction.closing.warning", {
                    "invoice_token": invoice_token,
                    "hours_remaining": 1,
                    "bidders": bidders_1h,
                }],
                **act_opts,
            )

        # Wait until deadline
        await workflow.sleep(deadline - workflow.now())

        # Anti-snipe loop: keep extending while signals arrive
        # CRITICAL: Check flag BEFORE resetting — a signal may have arrived during sleep_until
        while True:
            if not self.extend_requested:
                try:
                    await workflow.wait_condition(
                        lambda: self.extend_requested,
                        timeout=timedelta(seconds=config.ANTI_SNIPE_SECONDS),
                    )
                except asyncio.TimeoutError:
                    # No signal in 5 minutes → auction closes
                    break
            # Signal was received — reset flag and loop for another 5-min window
            self.extend_requested = False

        # Fetch all bids
        offers = await workflow.execute_activity(get_offers, args=[invoice_token], **act_opts)
        if not offers:
            invoice_exp = await workflow.execute_activity(verify_invoice, args=[invoice_token], **act_opts)
            seller_exp = await workflow.execute_activity(get_user, args=[invoice_exp["seller_id"]], **act_opts)
            await workflow.execute_activity(
                publish_event,
                args=["auction.expired", {
                    "invoice_token": invoice_token,
                    "seller_id": invoice_exp["seller_id"],
                    "seller_email": seller_exp["email"],
                }],
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
        await workflow.start_child_workflow(
            LoanMaturityWorkflow.run,
            args=[loan["loan_id"], loan["due_date"]],
            id=f"loan-{loan['loan_id']}",
            parent_close_policy=workflow.ParentClosePolicy.ABANDON,
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

        # Reject all losers and release their escrow in parallel
        await asyncio.gather(*[
            workflow.execute_activity(reject_offer, args=[o["id"]], **act_opts)
            for o in losers
        ])
        await asyncio.gather(*[
            workflow.execute_activity(
                release_escrow,
                args=[o["investor_id"], invoice_token, f"release-loser-{o['id']}"],
                **act_opts,
            )
            for o in losers
        ])

        # Fetch emails for outcome events
        winner_user = await workflow.execute_activity(get_user, args=[winner["investor_id"]], **act_opts)
        seller_user = await workflow.execute_activity(get_user, args=[invoice["seller_id"]], **act_opts)

        # Publish outcome events
        await workflow.execute_activity(
            publish_event,
            args=["auction.closed.winner", {
                "invoice_token": invoice_token,
                "winner_id": winner["investor_id"],
                "winner_email": winner_user["email"],
                "seller_id": invoice["seller_id"],
                "seller_email": seller_user["email"],
                "loan_id": loan["loan_id"],
            }],
            **act_opts,
        )
        for loser in losers:
            loser_user = await workflow.execute_activity(get_user, args=[loser["investor_id"]], **act_opts)
            await workflow.execute_activity(
                publish_event,
                args=["auction.closed.loser", {
                    "invoice_token": invoice_token,
                    "loser_id": loser["investor_id"],
                    "loser_email": loser_user["email"],
                }],
                **act_opts,
            )
