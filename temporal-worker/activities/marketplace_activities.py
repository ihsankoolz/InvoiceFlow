"""
Marketplace-related Temporal activities.
Each activity makes HTTP calls to Marketplace Service.
"""

from temporalio import activity

from clients.http_client import HTTPClient
import config

http_client = HTTPClient()


@activity.defn
async def delist_listing(invoice_token: str) -> dict:
    """Delist a single listing after auction close."""
    return await http_client.patch(
        f"{config.MARKETPLACE_SERVICE_URL}/listings/{invoice_token}",
        json={"status": "DELISTED"},
    )


@activity.defn
async def bulk_delist(seller_id: int) -> dict:
    """Bulk delist all listings for a defaulting seller. Called by LoanMaturityWorkflow on OVERDUE."""
    return await http_client.delete(
        f"{config.MARKETPLACE_SERVICE_URL}/listings/bulk?seller_id={seller_id}",
    )
