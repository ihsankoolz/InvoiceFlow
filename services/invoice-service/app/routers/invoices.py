from datetime import datetime as datetime_type
from datetime import timezone
from typing import List

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.invoice import InvoiceCreate, InvoiceResponse, InvoiceStatusUpdate
from app.services.invoice_service import InvoiceService
from app.services.pdf_extractor import PDFExtractor

router = APIRouter()


@router.post("/invoices/extract", tags=["Invoices"])
async def extract_invoice_fields(pdf_file: UploadFile = File(...)):
    """Extract fields from an invoice PDF without creating an invoice."""
    pdf_bytes = await pdf_file.read()
    extractor = PDFExtractor()
    extracted = extractor.extract_fields(pdf_bytes)
    return {
        "debtor_name": extracted.get("debtor_name"),
        "debtor_uen": extracted.get("debtor_uen"),
        "amount": extracted.get("amount"),
        "due_date": extracted.get("due_date"),
    }


@router.post("/invoices", response_model=InvoiceResponse, tags=["Invoices"])
async def create_invoice(
    seller_id: int = Form(...),
    seller_name: str = Form(None),
    debtor_name: str = Form(None),
    debtor_uen: str = Form(...),
    amount: float = Form(...),
    due_date: str = Form(...),
    pdf_file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Create a new invoice with an uploaded PDF file."""
    service = InvoiceService(db)
    pdf_bytes = await pdf_file.read()
    # Parse ISO datetime string (date-only "YYYY-MM-DD" or full "YYYY-MM-DDTHH:MM:SS[±TZ]").
    # Timezone-aware strings are converted to UTC; naive strings are treated as UTC.
    # Stored as UTC-naive in MySQL DATETIME.
    _dt = datetime_type.fromisoformat(due_date)
    if _dt.tzinfo is not None:
        _dt = _dt.astimezone(timezone.utc).replace(tzinfo=None)

    data = InvoiceCreate(
        seller_id=seller_id,
        seller_name=seller_name or None,
        debtor_name=debtor_name or None,
        debtor_uen=debtor_uen,
        amount=amount,
        due_date=_dt,
    )
    invoice = service.create_invoice(data, pdf_bytes)
    return invoice


@router.get("/invoices/{invoice_token}", response_model=InvoiceResponse, tags=["Invoices"])
def get_invoice(invoice_token: str, db: Session = Depends(get_db)):
    """Retrieve a single invoice by its token."""
    service = InvoiceService(db)
    return service.get_invoice(invoice_token)


@router.get("/invoices", response_model=List[InvoiceResponse], tags=["Invoices"])
def list_invoices_by_seller(seller_id: int, db: Session = Depends(get_db)):
    """List all invoices belonging to a specific seller."""
    service = InvoiceService(db)
    return service.get_invoices_by_seller(seller_id)


@router.patch("/invoices/{invoice_token}/status", response_model=InvoiceResponse, tags=["Status"])
def update_invoice_status(
    invoice_token: str,
    body: InvoiceStatusUpdate,
    db: Session = Depends(get_db),
):
    """Update the status of an invoice."""
    service = InvoiceService(db)
    return service.update_status(invoice_token, body.status)
