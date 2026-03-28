"""
Invoice Orchestrator — API routes.

See BUILD_INSTRUCTIONS_V2.md Section 8 — API Endpoint
"""

from typing import List

from fastapi import APIRouter, File, Form, Query, UploadFile

from app.schemas.requests import ListInvoiceResponse
from app.services.orchestrator import InvoiceOrchestrator
from app.services.http_client import HTTPClient
from app.services.rabbitmq_publisher import RabbitMQPublisher
from app.temporal.client import TemporalClient
from app import config

router = APIRouter()

# Instantiate dependencies (Global or per-request)
http_client = HTTPClient()
publisher = RabbitMQPublisher(config.RABBITMQ_URL)
temporal_client = TemporalClient()


@router.get(
    "/api/invoices",
    tags=["Invoice Workflow"],
    summary="List invoices for a seller",
    description="Returns all invoices belonging to the given seller_id.",
)
async def list_invoices(seller_id: int = Query(..., description="Seller user ID")):
    result = await http_client.get(
        f"{config.INVOICE_SERVICE_URL}/invoices",
        params={"seller_id": seller_id},
    )
    return result


@router.post(
    "/api/invoices/extract",
    tags=["Invoice Workflow"],
    summary="Extract fields from an invoice PDF",
    description="Upload a PDF and get extracted debtor_name and amount back to prepopulate the form.",
)
async def extract_invoice(pdf: UploadFile = File(...)):
    pdf_bytes = await pdf.read()
    result = await http_client.post(
        f"{config.INVOICE_SERVICE_URL}/invoices/extract",
        files={"pdf_file": (pdf.filename, pdf_bytes, pdf.content_type)},
    )
    return result


@router.post(
    "/api/invoices",
    response_model=ListInvoiceResponse,
    tags=["Invoice Workflow"],
    summary="List an invoice for auction (full Scenario 1 orchestration)",
    description="""
Full Scenario 1 orchestration:
1. Check seller account is ACTIVE (User Service)
2. Create invoice + upload PDF (Invoice Service)
3. Validate debtor UEN (ACRA Wrapper)
4. If invalid → PATCH status to REJECTED + publish invoice.rejected
5. Create marketplace listing (Marketplace Service)
6. Update invoice status to LISTED (Invoice Service)
7. Start AuctionCloseWorkflow (Temporal)
8. Publish invoice.listed event (RabbitMQ)
    """,
)
async def list_invoice(
    seller_id: int = Form(...),
    debtor_name: str = Form(None),
    debtor_uen: str = Form(...),
    face_value: float = Form(...),
    minimum_bid: float = Form(...),
    due_date: str = Form(...),
    bid_period_hours: int = Form(48),
    pdf: UploadFile = File(...),
):
    orchestrator = InvoiceOrchestrator(
        http_client=HTTPClient(),
        publisher=RabbitMQPublisher(config.RABBITMQ_URL),
        temporal_client=TemporalClient(),
    )
    result = await orchestrator.list_invoice(
        seller_id=seller_id,
        debtor_name=debtor_name,
        debtor_uen=debtor_uen,
        face_value=face_value,
        minimum_bid=minimum_bid,
        due_date=due_date,
        bid_period_hours=bid_period_hours,
        pdf_file=pdf,
    )
    return ListInvoiceResponse(**result)
