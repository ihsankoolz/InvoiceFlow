import random
import re
import string
from datetime import datetime
from typing import List

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate
from app.services.pdf_extractor import PDFExtractor
from app.services.storage_service import StorageService


def _generate_invoice_token(seller_id: int, seller_name: str = None) -> str:
    """Generate a human-readable invoice token: INV-{SELLER_SLUG}-{YYYYMMDD}-{4-char-random}
    e.g. INV-ACMECORP-20260331-K8X2
    """
    date_str = datetime.utcnow().strftime("%Y%m%d")
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    if seller_name:
        slug = re.sub(r'[^A-Z0-9]', '', seller_name.upper())[:8]
    else:
        slug = str(seller_id)
    return f"INV-{slug}-{date_str}-{suffix}"


class InvoiceService:
    """Core business-logic layer for invoice operations."""

    def __init__(self, db: Session):
        self.db = db
        self.pdf_extractor = PDFExtractor()
        self.storage_service = StorageService()

    def create_invoice(self, data: InvoiceCreate, pdf_bytes: bytes) -> Invoice:
        """Create a new invoice record, upload the PDF to MinIO, and extract text fields."""
        invoice_token = _generate_invoice_token(data.seller_id, data.seller_name)

        # 1. Upload to MinIO
        pdf_url = self.storage_service.upload_pdf(invoice_token, pdf_bytes)

        # 2. Extract fields from PDF
        extracted_data = self.pdf_extractor.extract_fields(pdf_bytes)

        # 3. Create DB record — seller-provided debtor_name takes precedence over PDF extraction
        invoice = Invoice(
            invoice_token=invoice_token,
            seller_id=data.seller_id,
            debtor_name=data.debtor_name or extracted_data.get("debtor_name"),
            debtor_uen=data.debtor_uen,
            amount=data.amount,
            due_date=data.due_date,
            pdf_url=pdf_url,
            status="DRAFT",  # Initial status per architecture
            extracted_data=extracted_data
        )

        self.db.add(invoice)
        self.db.commit()
        self.db.refresh(invoice)
        return invoice

    def get_invoice(self, invoice_token: str) -> Invoice:
        """Retrieve a single invoice by its unique token."""
        invoice = self.db.query(Invoice).filter(Invoice.invoice_token == invoice_token).first()
        if not invoice:
            raise HTTPException(404, f"Invoice {invoice_token} not found")
        return invoice

    def get_invoices_by_seller(self, seller_id: int) -> List[Invoice]:
        """Return all invoices belonging to the given seller."""
        return self.db.query(Invoice).filter(Invoice.seller_id == seller_id).all()

    def update_status(self, invoice_token: str, status: str) -> Invoice:
        """Transition an invoice to a new status."""
        invoice = self.get_invoice(invoice_token)
        invoice.status = status
        self.db.commit()
        self.db.refresh(invoice)
        return invoice
