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
        Full Scenario 1 orchestration.

        Steps:
        1. GET User Service /users/{seller_id} — check account_status is ACTIVE
           → If DEFAULTED, raise 403
        2. POST Invoice Service /invoices — create invoice + upload PDF (multipart)
           → Returns invoice with invoice_token and extracted_data
        3. POST ACRA Wrapper /validate-uen — validate debtor UEN
           → If invalid, PATCH invoice status to REJECTED, publish invoice.rejected, raise 400
        4. POST Marketplace Service /listings — create listing with urgency + deadline
        5. PATCH Invoice Service /invoices/{token}/status — set to LISTED
        6. Start AuctionCloseWorkflow via Temporal (workflow_id: auction-{invoice_token})
        7. Publish invoice.listed to RabbitMQ

        See BUILD_INSTRUCTIONS_V2.md Section 8 — Orchestration Flow
        """
        # TODO: Implement the 8-step orchestration
        pass
