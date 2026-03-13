import uuid
from typing import List

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate
from app.services.pdf_extractor import PDFExtractor
from app.services.storage_service import StorageService


class InvoiceService:
    """Core business-logic layer for invoice operations."""

    def __init__(self, db: Session):
        self.db = db
        self.pdf_extractor = PDFExtractor()
        self.storage_service = StorageService()

    def create_invoice(self, data: InvoiceCreate, pdf_bytes: bytes) -> Invoice:
        """Create a new invoice record, upload the PDF to MinIO, and extract text fields.

        Steps:
            1. Generate a unique invoice_token (UUID4).
            2. Upload the PDF to object storage via StorageService.
            3. Extract structured fields from the PDF via PDFExtractor.
            4. Persist the invoice row in the database.
            5. Return the created Invoice ORM object.

        Args:
            data: Validated invoice creation payload.
            pdf_bytes: Raw bytes of the uploaded PDF file.

        Returns:
            The newly created Invoice instance.
        """
        # TODO: implement
        raise NotImplementedError

    def get_invoice(self, invoice_token: str) -> Invoice:
        """Retrieve a single invoice by its unique token.

        Args:
            invoice_token: The UUID token identifying the invoice.

        Returns:
            The matching Invoice instance.

        Raises:
            HTTPException 404 if the invoice is not found.
        """
        # TODO: implement
        raise NotImplementedError

    def get_invoices_by_seller(self, seller_id: int) -> List[Invoice]:
        """Return all invoices belonging to the given seller.

        Args:
            seller_id: The ID of the seller whose invoices to retrieve.

        Returns:
            A list of Invoice instances (may be empty).
        """
        # TODO: implement
        raise NotImplementedError

    def update_status(self, invoice_token: str, status: str) -> Invoice:
        """Transition an invoice to a new status.

        Args:
            invoice_token: The UUID token identifying the invoice.
            status: The target status string (must be a valid ENUM value).

        Returns:
            The updated Invoice instance.

        Raises:
            HTTPException 404 if the invoice is not found.
        """
        # TODO: implement
        raise NotImplementedError
