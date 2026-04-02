"""
Marketplace-related Temporal activities.
Each activity makes HTTP calls to Marketplace Service.
"""

from clients.http_client import HTTPClient
from temporalio import activity

import config

http_client = HTTPClient()


@activity.defn
async def delist_listing(invoice_token: str) -> dict:
    """Delist a single listing after auction close (by invoice_token)."""
    return await http_client.delete(
        f"{config.MARKETPLACE_SERVICE_URL}/listings/by-token/{invoice_token}",
    )


@activity.defn
async def bulk_delist(seller_id: int) -> dict:
    """Bulk delist all listings for a defaulting seller. Called by LoanMaturityWorkflow on OVERDUE."""
    return await http_client.delete(
        f"{config.MARKETPLACE_SERVICE_URL}/listings/?seller_id={seller_id}",
    )
