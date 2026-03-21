"""
Invoice-related Temporal activities.
Each activity makes HTTP calls to Invoice Service.
"""

from temporalio import activity
from temporalio.exceptions import ApplicationError

from clients.http_client import HTTPClient
import config

http_client = HTTPClient()


@activity.defn
async def verify_invoice(invoice_token: str) -> dict:
    """Verify invoice exists and is in LISTED status."""
    response = await http_client.get(f"{config.INVOICE_SERVICE_URL}/invoices/{invoice_token}")
    if response["status"] != "LISTED":
        raise ApplicationError(f"Invoice {invoice_token} is not available (status: {response['status']})")
    return response


@activity.defn
async def update_invoice_status(invoice_token: str, status: str) -> dict:
    """Update invoice status (e.g., FINANCED after auction close)."""
    return await http_client.patch(
        f"{config.INVOICE_SERVICE_URL}/invoices/{invoice_token}/status",
        json={"status": status},
    )
