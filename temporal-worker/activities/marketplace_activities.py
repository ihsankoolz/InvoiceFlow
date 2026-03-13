"""
Marketplace-related Temporal activities.
Each activity makes HTTP calls to Marketplace Service.

See BUILD_INSTRUCTIONS_V2.md Section 13 — Activities
"""

from temporalio import activity

from clients.http_client import HTTPClient
import config

http_client = HTTPClient()


@activity.defn
async def delist_listing(invoice_token: str) -> dict:
    """
    Delist a single listing after auction close.

    Calls: PATCH {MARKETPLACE_SERVICE_URL}/listings/{invoice_token}
           Body: {"status": "DELISTED"}

    See BUILD_INSTRUCTIONS_V2.md Section 13 — delist_listing
    """
    # TODO: Implement
    pass


@activity.defn
async def bulk_delist(seller_id: int) -> dict:
    """
    Bulk delist all listings for a defaulting seller.
    Called by LoanMaturityWorkflow when loan becomes OVERDUE.

    Calls: DELETE {MARKETPLACE_SERVICE_URL}/listings/bulk?seller_id={seller_id}

    See BUILD_INSTRUCTIONS_V2.md Section 13 — bulk_delist
    """
    # TODO: Implement
    pass
