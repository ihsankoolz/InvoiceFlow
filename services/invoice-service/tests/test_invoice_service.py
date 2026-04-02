import re
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate
from app.services.invoice_service import InvoiceService, _generate_invoice_token

# ── Token generation ─────────────────────────────────────────────────────────

def test_token_format_with_seller_name():
    token = _generate_invoice_token(seller_id=1, seller_name="Acme Corp")
    # Expected: INV-ACMECORP-YYYYMMDD-XXXX
    assert re.match(r"INV-ACMECORP-\d{8}-[A-Z0-9]{4}", token), f"Unexpected token: {token}"


def test_token_format_without_seller_name():
    token = _generate_invoice_token(seller_id=42)
    assert re.match(r"INV-42-\d{8}-[A-Z0-9]{4}", token), f"Unexpected token: {token}"


def test_token_seller_name_truncated_to_8_chars():
    token = _generate_invoice_token(seller_id=1, seller_name="VeryLongCompanyName")
    # Slug is stripped of non-alphanumeric chars then capped at 8
    assert re.match(r"INV-VERYLONG-\d{8}-[A-Z0-9]{4}", token), f"Unexpected token: {token}"


def test_token_uniqueness():
    tokens = {_generate_invoice_token(seller_id=1, seller_name="Acme") for _ in range(50)}
    # All 50 should be unique (4-char random suffix makes collision astronomically unlikely)
    assert len(tokens) == 50


# ── InvoiceService with mocked dependencies ──────────────────────────────────

def _make_service(db):
    service = InvoiceService(db)
    service.storage_service = MagicMock()
    service.storage_service.upload_pdf.return_value = "http://minio/invoices/test.pdf"
    service.pdf_extractor = MagicMock()
    service.pdf_extractor.extract_fields.return_value = {
        "debtor_name": "Extracted Corp",
        "debtor_uen": "123456789A",
        "amount": "1000.00",
        "due_date": "2026-12-31",
    }
    return service


def _make_invoice_data(**overrides):
    defaults = dict(
        seller_id=1,
        seller_name="Acme",
        debtor_name="Test Debtor",
        debtor_uen="200012345K",
        amount=1000.0,
        due_date=date(2026, 12, 31),
    )
    defaults.update(overrides)
    return InvoiceCreate(**defaults)


def test_create_invoice_persists_record(db):
    service = _make_service(db)
    invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"%PDF-test")
    assert invoice.id is not None
    assert invoice.status == "DRAFT"
    assert invoice.pdf_url == "http://minio/invoices/test.pdf"


def test_create_invoice_seller_debtor_name_takes_precedence(db):
    service = _make_service(db)
    invoice = service.create_invoice(_make_invoice_data(debtor_name="Seller Provided"), pdf_bytes=b"")
    # Seller-provided debtor_name wins over PDF extraction
    assert invoice.debtor_name == "Seller Provided"


def test_create_invoice_falls_back_to_extracted_debtor_name(db):
    service = _make_service(db)
    invoice = service.create_invoice(_make_invoice_data(debtor_name=None), pdf_bytes=b"")
    assert invoice.debtor_name == "Extracted Corp"


def test_get_invoices_for_seller(db):
    service = _make_service(db)
    service.create_invoice(_make_invoice_data(seller_id=10), pdf_bytes=b"")
    service.create_invoice(_make_invoice_data(seller_id=10), pdf_bytes=b"")
    service.create_invoice(_make_invoice_data(seller_id=99), pdf_bytes=b"")

    seller_invoices = db.query(Invoice).filter(Invoice.seller_id == 10).all()
    assert len(seller_invoices) == 2


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
