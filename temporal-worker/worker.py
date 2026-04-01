"""
Temporal Worker — main entry point.
Registers all workflows and activities, starts polling the invoiceflow-queue.
"""

import asyncio
import sys

import config
from workflows.auction_close import AuctionCloseWorkflow
from workflows.loan_maturity import LoanMaturityWorkflow
from workflows.loan_repayment import LoanRepaymentWorkflow
from workflows.wallet_topup import WalletTopUpWorkflow
from activities.invoice_activities import verify_invoice, update_invoice_status, get_user
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
    from temporalio.client import Client
    from temporalio.worker import Worker

    client = await Client.connect(config.TEMPORAL_HOST)
    worker = Worker(
        client,
        task_queue="invoiceflow-queue",
        workflows=[
            AuctionCloseWorkflow,
            LoanMaturityWorkflow,
            LoanRepaymentWorkflow,
            WalletTopUpWorkflow,
        ],
        activities=[
            verify_invoice, update_invoice_status, get_user,
            get_offers, accept_offer, reject_offer,
            convert_escrow_to_loan, create_loan, release_funds_to_seller,
            get_loan_grpc, update_loan_status_grpc, credit_wallet,
            delist_listing, bulk_delist,
            publish_event,
        ],
    )
    print("Worker started, polling invoiceflow-queue", flush=True)
    await worker.run()


if __name__ == "__main__":
    sys.stdout.reconfigure(line_buffering=True)
    asyncio.run(main())
