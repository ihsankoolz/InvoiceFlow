"""
Invoice Orchestrator — API routes.

See BUILD_INSTRUCTIONS_V2.md Section 8 — API Endpoint
"""

from fastapi import APIRouter, File, Form, UploadFile, HTTPException

from app.schemas.requests import ListInvoiceResponse

router = APIRouter()


@router.post(
    "/api/invoices",
    response_model=ListInvoiceResponse,
    tags=["Invoice Workflow"],
    summary="List an invoice for auction (full Scenario 1 orchestration)",
)
async def list_invoice(
    seller_id: int = Form(...),
    debtor_uen: str = Form(...),
    amount: float = Form(...),
    due_date: str = Form(...),
    bid_period_hours: int = Form(48),
    pdf: UploadFile = File(...),
):
    """
    Full Scenario 1 orchestration:
    1. Check seller account is ACTIVE (User Service)
    2. Create invoice + upload PDF (Invoice Service)
    3. Validate debtor UEN (ACRA Wrapper)
    4. If invalid → reject + publish invoice.rejected
    5. Create marketplace listing (Marketplace Service)
    6. Update invoice status to LISTED (Invoice Service)
    7. Start AuctionCloseWorkflow (Temporal)
    8. Publish invoice.listed event (RabbitMQ)

    See BUILD_INSTRUCTIONS_V2.md Section 8 — Orchestration Flow
    """
    # TODO: Implement — instantiate InvoiceOrchestrator and call list_invoice()
    raise HTTPException(501, "Not implemented yet")
