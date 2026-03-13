"""
Bidding-related Temporal activities.
Each activity makes HTTP calls to Bidding Service.

See BUILD_INSTRUCTIONS_V2.md Section 13 — Activities
"""

from temporalio import activity

from clients.http_client import HTTPClient
import config

http_client = HTTPClient()


@activity.defn
async def get_offers(invoice_token: str) -> list:
    """
    Get all bids for an invoice.

    Calls: GET {BIDDING_SERVICE_URL}/bids?invoice_token={invoice_token}
    Returns list of bid dicts.

    See BUILD_INSTRUCTIONS_V2.md Section 13 — get_offers
    """
    # TODO: Implement
    pass


@activity.defn
async def accept_offer(bid_id: int) -> dict:
    """
    Accept a winning bid.

    Calls: PATCH {BIDDING_SERVICE_URL}/bids/{bid_id}
           Body: {"status": "ACCEPTED"}

    See BUILD_INSTRUCTIONS_V2.md Section 13 — accept_offer
    """
    # TODO: Implement
    pass


@activity.defn
async def reject_offer(bid_id: int) -> dict:
    """
    Reject a losing bid.

    Calls: PATCH {BIDDING_SERVICE_URL}/bids/{bid_id}
           Body: {"status": "REJECTED"}

    See BUILD_INSTRUCTIONS_V2.md Section 13 — reject_offer
    """
    # TODO: Implement
    pass
