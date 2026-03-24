"""
Bidding-related Temporal activities.
Each activity makes HTTP calls to Bidding Service.
"""

from temporalio import activity

from clients.http_client import HTTPClient
import config

http_client = HTTPClient()


@activity.defn
async def get_offers(invoice_token: str) -> list:
    """Get all bids for an invoice."""
    return await http_client.get(f"{config.BIDDING_SERVICE_URL}/bids?invoice_token={invoice_token}")


@activity.defn
async def accept_offer(bid_id: int) -> dict:
    """Accept a winning bid."""
    return await http_client.patch(
        f"{config.BIDDING_SERVICE_URL}/bids/{bid_id}/accept",
    )


@activity.defn
async def reject_offer(bid_id: int) -> dict:
    """Reject a losing bid."""
    return await http_client.patch(
        f"{config.BIDDING_SERVICE_URL}/bids/{bid_id}/reject",
    )
