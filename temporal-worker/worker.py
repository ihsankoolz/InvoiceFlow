"""
Temporal Worker — main entry point.
Registers all workflows and activities, starts polling the invoiceflow-queue.

See BUILD_INSTRUCTIONS_V2.md Section 13 — Worker Entry Point
"""

import asyncio

import config
from workflows.auction_close import AuctionCloseWorkflow
from workflows.loan_maturity import LoanMaturityWorkflow
from workflows.wallet_topup import WalletTopUpWorkflow
from activities.invoice_activities import verify_invoice, update_invoice_status
from activities.bidding_activities import get_offers, accept_offer, reject_offer
from activities.payment_activities import (
    convert_escrow_to_loan,
    create_loan,
    release_funds_to_seller,
    get_loan_grpc,
    update_loan_status_grpc,
    credit_wallet,
)
from activities.marketplace_activities import delist_listing, bulk_delist
from activities.rabbitmq_activities import publish_event


async def main():
    """
    Connect to Temporal Server and start the worker.

    Steps:
    1. Import temporalio.client.Client and temporalio.worker.Worker
    2. Connect to config.TEMPORAL_HOST
    3. Create Worker with:
       - task_queue="invoiceflow-queue"
       - workflows=[AuctionCloseWorkflow, LoanMaturityWorkflow, WalletTopUpWorkflow]
       - activities=[all activity functions]
    4. Run the worker (blocks until shutdown)

    See BUILD_INSTRUCTIONS_V2.md Section 13 — Worker Entry Point
    """
    # TODO: Implement
    pass


if __name__ == "__main__":
    asyncio.run(main())
