"""
InvoiceOrchestrator — main orchestration logic for Scenario 1.

See BUILD_INSTRUCTIONS_V2.md Section 8 — Orchestration Flow
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app import config
from app.services.http_client import HTTPClient
from app.services.rabbitmq_publisher import RabbitMQPublisher
from app.temporal.client import TemporalClient


def calculate_urgency(due_date_str: str) -> str:
    """
    Calculate urgency level based on days until invoice due date.
    - CRITICAL: <= 7 days
    - HIGH: <= 14 days
    - MEDIUM: <= 30 days
    - LOW: > 30 days
    """
    due_date = (
        datetime.fromisoformat(due_date_str).date()
        if isinstance(due_date_str, str)
        else due_date_str
    )
    days_until_due = (due_date - datetime.utcnow().date()).days
    if days_until_due <= 7:
        return "CRITICAL"
    elif days_until_due <= 14:
        return "HIGH"
    elif days_until_due <= 30:
        return "MEDIUM"
    return "LOW"


def calculate_deadline(bid_period_hours: float) -> str:
    """Calculate auction deadline as ISO 8601 string."""
    return (datetime.now(timezone.utc) + timedelta(hours=bid_period_hours)).isoformat()


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

    async def list_invoice(
        self,
        seller_id: int,
        debtor_uen: str,
        face_value: float,
        minimum_bid: float,
        due_date: str,
        bid_period_hours: float,
        pdf_file,
        debtor_name: str = None,
        urgency_level: str = "MEDIUM",
    ) -> dict:
        """Full Scenario 1 orchestration — 8-step flow."""

        # Step 1: Check seller account is ACTIVE
        user = await self.http_client.get(f"{config.USER_SERVICE_URL}/users/{seller_id}")
        if user["account_status"] != "ACTIVE":
            raise HTTPException(status_code=403, detail="Seller account is defaulted")

        # Step 2: Create invoice + upload PDF
        invoice = await self.http_client.post(
            f"{config.INVOICE_SERVICE_URL}/invoices",
            files={"pdf_file": (pdf_file.filename, await pdf_file.read(), pdf_file.content_type)},
            data={
                "seller_id": str(seller_id),
                "seller_name": user.get("full_name", ""),
                "debtor_name": debtor_name or "",
                "debtor_uen": debtor_uen,
                "amount": str(face_value),
                "due_date": due_date,
            },
        )

        # Step 3: Validate debtor UEN via ACRA Wrapper
        uen_result = await self.http_client.post(
            f"{config.ACRA_WRAPPER_URL}/validate-uen",
            json={"uen": debtor_uen},
        )

        # Step 4: If UEN invalid → reject invoice, publish event, raise 400
        if not uen_result["valid"]:
            await self.http_client.patch(
                f"{config.INVOICE_SERVICE_URL}/invoices/{invoice['invoice_token']}/status",
                json={"status": "REJECTED"},
            )
            await self.publisher.publish(
                "invoice.rejected",
                {
                    "invoice_token": invoice["invoice_token"],
                    "seller_id": seller_id,
                    "seller_email": user["email"],
                    "reason": "Invalid debtor UEN",
                },
            )
            raise HTTPException(status_code=400, detail="Invalid debtor UEN")

        # Step 5: Create marketplace listing (include read-model fields at creation time)
        listing = await self.http_client.post(
            f"{config.MARKETPLACE_SERVICE_URL}/listings/",
            json={
                "invoice_token": invoice["invoice_token"],
                "seller_id": seller_id,
                "debtor_uen": debtor_uen,
                "amount": face_value,
                "minimum_bid": minimum_bid,
                "urgency_level": urgency_level,
                "deadline": calculate_deadline(bid_period_hours),
                "face_value": face_value,
                "debtor_name": debtor_name,
            },
        )

        # Step 6: Update invoice status to LISTED
        await self.http_client.patch(
            f"{config.INVOICE_SERVICE_URL}/invoices/{invoice['invoice_token']}/status",
            json={"status": "LISTED"},
        )

        # Step 7: Start AuctionCloseWorkflow via Temporal
        await self.temporal_client.start_workflow(
            "AuctionCloseWorkflow",
            workflow_id=f"auction-{invoice['invoice_token']}",
            args={"invoice_token": invoice["invoice_token"], "bid_period_hours": bid_period_hours},
            task_queue="invoiceflow-queue",
        )

        # Step 8: Publish invoice.listed event
        await self.publisher.publish(
            "invoice.listed",
            {
                "invoice_token": invoice["invoice_token"],
                "seller_id": seller_id,
                "seller_email": user["email"],
                "amount": face_value,
                "deadline": listing["deadline"],
            },
        )

        return {
            "invoice_token": invoice["invoice_token"],
            "listing_id": listing["id"],
            "status": "LISTED",
            "message": "Invoice listed successfully",
        }
