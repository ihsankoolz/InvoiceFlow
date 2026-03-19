"""
InvoiceOrchestrator — main orchestration logic for Scenario 1.

See BUILD_INSTRUCTIONS_V2.md Section 8 — Orchestration Flow
"""

from datetime import datetime, timedelta

from app.services.http_client import HTTPClient
from app.services.rabbitmq_publisher import RabbitMQPublisher
from app.temporal.client import TemporalClient
from app import config


def calculate_urgency(due_date_str: str) -> str:
    """
    Calculate urgency level based on days until invoice due date.
    - CRITICAL: <= 7 days
    - HIGH: <= 14 days
    - MEDIUM: <= 30 days
    - LOW: > 30 days
    """
    due_date = datetime.fromisoformat(due_date_str).date() if isinstance(due_date_str, str) else due_date_str
    days_until_due = (due_date - datetime.utcnow().date()).days
    if days_until_due <= 7:
        return "CRITICAL"
    elif days_until_due <= 14:
        return "HIGH"
    elif days_until_due <= 30:
        return "MEDIUM"
    return "LOW"


def calculate_deadline(bid_period_hours: int) -> str:
    """Calculate auction deadline as ISO 8601 string."""
    return (datetime.utcnow() + timedelta(hours=bid_period_hours)).isoformat()


class InvoiceOrchestrator:
    """
    Orchestrates Scenario 1: invoice creation → UEN validation →
    marketplace listing → Temporal workflow start.
    """

    def __init__(
        self,
        http_client: HTTPClient,
        publisher: RabbitMQPublisher,
        temporal_client: TemporalClient,
    ):
        self.http_client = http_client
        self.publisher = publisher
        self.temporal_client = temporal_client

    async def list_invoice(self, seller_id: int, debtor_uen: str, amount: float,
                           due_date: str, bid_period_hours: int, pdf_file) -> dict:
        """
        Full Scenario 1 orchestration:
        1. Account Check (User Service)
        2. Invoice Creation (Invoice Service)
        3. UEN Validation (ACRA Wrapper)
        4. Rejection Path (on invalid UEN)
        5. Marketplace Listing (Marketplace Service)
        6. Activation (Invoice Service)
        7. Workflow Start (Temporal)
        8. Event Notification (RabbitMQ)
        """
        # 1. Check seller account is ACTIVE
        user_url = f"{config.USER_SERVICE_URL}/users/{seller_id}"
        user_data = await self.http_client.get(user_url)
        if user_data.get("account_status") != "ACTIVE":
            from fastapi import HTTPException
            raise HTTPException(403, f"Seller account {seller_id} is {user_data.get('account_status')}")

        # 2. Create invoice + upload PDF
        invoice_url = f"{config.INVOICE_SERVICE_URL}/invoices"
        pdf_bytes = await pdf_file.read()
        
        # Multipart form data
        files = {"pdf_file": (pdf_file.filename, pdf_bytes, "application/pdf")}
        data = {
            "seller_id": str(seller_id),
            "debtor_uen": debtor_uen,
            "amount": str(amount),
            "due_date": due_date,
        }
        
        invoice = await self.http_client.post(invoice_url, data=data, files=files)
        invoice_token = invoice["invoice_token"]

        # 3. Validate debtor UEN
        acra_url = f"{config.ACRA_WRAPPER_URL}/validate-uen"
        acra_payload = {"uen": debtor_uen}
        acra_result = await self.http_client.post(acra_url, json=acra_payload)

        # 4. Handle UEN validation failure
        if not acra_result.get("is_valid"):
            # Update status to REJECTED
            status_url = f"{config.INVOICE_SERVICE_URL}/invoices/{invoice_token}/status"
            await self.http_client.patch(status_url, json={"status": "REJECTED"})
            
            # Publish invoice.rejected
            await self.publisher.publish("invoice.rejected", {"invoice_token": invoice_token, "reason": "Invalid debtor UEN"})
            
            from fastapi import HTTPException
            raise HTTPException(400, "Debtor UEN validation failed")

        # 5. Create marketplace listing
        urgency = calculate_urgency(due_date)
        deadline = calculate_deadline(bid_period_hours)
        marketplace_url = f"{config.MARKETPLACE_SERVICE_URL}/listings/"
        listing_payload = {
            "invoice_token": invoice_token,
            "seller_id": seller_id,
            "debtor_uen": debtor_uen,
            "amount": amount,
            "urgency_level": urgency,
            "deadline": deadline,
        }
        listing = await self.http_client.post(marketplace_url, json=listing_payload)

        # 6. Update invoice status to LISTED
        status_url = f"{config.INVOICE_SERVICE_URL}/invoices/{invoice_token}/status"
        await self.http_client.patch(status_url, json={"status": "LISTED"})

        # 7. Start AuctionCloseWorkflow via Temporal
        workflow_id = f"auction-{invoice_token}"
        workflow_args = {
            "invoice_token": invoice_token,
            "bid_period_hours": bid_period_hours,
            "deadline": deadline
        }
        await self.temporal_client.start_workflow(
            "AuctionCloseWorkflow",
            workflow_id=workflow_id,
            args=workflow_args
        )

        # 8. Publish invoice.listed to RabbitMQ
        event_payload = {
            "invoice_token": invoice_token,
            "listing_id": listing["id"],
            "seller_id": seller_id,
            "urgency": urgency,
            "deadline": deadline
        }
        await self.publisher.publish("invoice.listed", event_payload)

        return {
            "status": "LISTED",
            "invoice_token": invoice_token,
            "listing_id": listing["id"],
            "urgency": urgency,
            "deadline": deadline
        }
