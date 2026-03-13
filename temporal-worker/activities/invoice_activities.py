"""
Invoice-related Temporal activities.
Each activity makes HTTP calls to Invoice Service.

See BUILD_INSTRUCTIONS_V2.md Section 13 — Activities
"""

from temporalio import activity

from clients.http_client import HTTPClient
import config

http_client = HTTPClient()


@activity.defn
async def verify_invoice(invoice_token: str) -> dict:
    """
    Verify invoice exists and is in LISTED status.

    Calls: GET {INVOICE_SERVICE_URL}/invoices/{invoice_token}
    Raises ApplicationError if invoice status != LISTED.

    See BUILD_INSTRUCTIONS_V2.md Section 13 — verify_invoice
    """
    # TODO: Implement
    pass


@activity.defn
async def update_invoice_status(invoice_token: str, status: str) -> dict:
    """
    Update invoice status (e.g., to FINANCED after auction close).

    Calls: PATCH {INVOICE_SERVICE_URL}/invoices/{invoice_token}
           Body: {"status": status}

    See BUILD_INSTRUCTIONS_V2.md Section 13 — update_invoice_status
    """
    # TODO: Implement
    pass
