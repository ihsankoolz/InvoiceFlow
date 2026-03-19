from fastapi import APIRouter, File, Form, UploadFile, HTTPException

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
    1. Check seller status
    2. Create invoice + upload PDF
    3. Validate debtor UEN
    4. Create listing
    5. Update status
    6. Start Temporal workflow
    7. Publish RabbitMQ event
    """
    orchestrator = InvoiceOrchestrator(http_client, publisher, temporal_client)
    
    try:
        result = await orchestrator.list_invoice(
            seller_id=seller_id,
            debtor_uen=debtor_uen,
            amount=amount,
            due_date=due_date,
            bid_period_hours=bid_period_hours,
            pdf_file=pdf
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
