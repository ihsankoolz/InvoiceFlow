import re
from datetime import date
from unittest.mock import MagicMock

import pytest
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate
from app.services.invoice_service import InvoiceService, _generate_invoice_token
from fastapi import HTTPException

# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _make_service(db):
    """InvoiceService with mocked MinIO + PDF extractor."""
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


# ═══════════════════════════════════════════════════════════════
# TOKEN GENERATION
# ═══════════════════════════════════════════════════════════════

class TestTokenGeneration:
    def test_format_with_seller_name(self):
        token = _generate_invoice_token(seller_id=1, seller_name="Acme Corp")
        assert re.match(r"INV-ACMECORP-\d{8}-[A-Z0-9]{6}", token)

    def test_format_without_seller_name(self):
        token = _generate_invoice_token(seller_id=42)
        assert re.match(r"INV-42-\d{8}-[A-Z0-9]{6}", token)

    def test_seller_name_truncated_to_8_chars(self):
        token = _generate_invoice_token(seller_id=1, seller_name="VeryLongCompanyName")
        assert re.match(r"INV-VERYLONG-\d{8}-[A-Z0-9]{6}", token)

    def test_uniqueness_across_50_tokens(self):
        tokens = {_generate_invoice_token(seller_id=1, seller_name="Acme") for _ in range(50)}
        assert len(tokens) == 50

    def test_special_characters_stripped_from_name(self):
        token = _generate_invoice_token(seller_id=1, seller_name="O'Brien & Co.")
        # Only alphanumeric chars should remain
        slug = token.split("-")[1]
        assert slug.isalnum()

    def test_empty_seller_name_uses_id(self):
        token = _generate_invoice_token(seller_id=7, seller_name="")
        # Empty string → slug becomes empty → falls back to seller_id
        assert re.match(r"INV-.*-\d{8}-[A-Z0-9]{6}", token)

    def test_numeric_seller_name(self):
        token = _generate_invoice_token(seller_id=1, seller_name="12345")
        assert re.match(r"INV-12345-\d{8}-[A-Z0-9]{6}", token)

    def test_none_seller_name_uses_id(self):
        token = _generate_invoice_token(seller_id=99, seller_name=None)
        assert re.match(r"INV-99-\d{8}-[A-Z0-9]{6}", token)


# ═══════════════════════════════════════════════════════════════
# CREATE INVOICE
# ═══════════════════════════════════════════════════════════════

class TestCreateInvoice:
    def test_persists_record(self, db):
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"%PDF-test")
        assert invoice.id is not None
        assert invoice.status == "DRAFT"
        assert invoice.pdf_url == "http://minio/invoices/test.pdf"

    def test_generates_unique_token(self, db):
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"")
        assert invoice.invoice_token.startswith("INV-")

    def test_seller_debtor_name_takes_precedence(self, db):
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(debtor_name="Seller Provided"), pdf_bytes=b"")
        assert invoice.debtor_name == "Seller Provided"

    def test_falls_back_to_extracted_debtor_name(self, db):
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(debtor_name=None), pdf_bytes=b"")
        assert invoice.debtor_name == "Extracted Corp"

    def test_stores_all_fields(self, db):
        service = _make_service(db)
        data = _make_invoice_data(
            seller_id=42,
            debtor_uen="199900001A",
            amount=50000.0,
            due_date=date(2027, 6, 15),
        )
        invoice = service.create_invoice(data, pdf_bytes=b"")
        assert invoice.seller_id == 42
        assert invoice.debtor_uen == "199900001A"
        assert float(invoice.amount) == 50000.0
        assert invoice.due_date == date(2027, 6, 15)
        assert invoice.currency == "SGD"

    def test_stores_extracted_data_as_json(self, db):
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"")
        assert invoice.extracted_data is not None
        assert invoice.extracted_data.get("debtor_name") == "Extracted Corp"

    def test_calls_storage_upload(self, db):
        service = _make_service(db)
        service.create_invoice(_make_invoice_data(), pdf_bytes=b"pdf-content")
        service.storage_service.upload_pdf.assert_called_once()
        args = service.storage_service.upload_pdf.call_args
        assert args[0][1] == b"pdf-content"

    def test_calls_pdf_extractor(self, db):
        service = _make_service(db)
        service.create_invoice(_make_invoice_data(), pdf_bytes=b"pdf-content")
        service.pdf_extractor.extract_fields.assert_called_once_with(b"pdf-content")

    def test_initial_status_is_draft(self, db):
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"")
        assert invoice.status == "DRAFT"

    def test_created_at_is_set(self, db):
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"")
        assert invoice.created_at is not None


# ═══════════════════════════════════════════════════════════════
# GET INVOICE BY TOKEN
# ═══════════════════════════════════════════════════════════════

class TestGetInvoice:
    def test_get_existing_invoice(self, db):
        service = _make_service(db)
        created = service.create_invoice(_make_invoice_data(), pdf_bytes=b"")
        fetched = service.get_invoice(created.invoice_token)
        assert fetched.id == created.id
        assert fetched.invoice_token == created.invoice_token

    def test_get_nonexistent_raises_404(self, db):
        service = _make_service(db)
        with pytest.raises(HTTPException) as exc_info:
            service.get_invoice("INV-DOESNOTEXIST-20260101-ZZZZ")
        assert exc_info.value.status_code == 404

    def test_get_returns_all_fields(self, db):
        service = _make_service(db)
        created = service.create_invoice(
            _make_invoice_data(debtor_name="Full Corp", debtor_uen="999999999Z", amount=7777.0),
            pdf_bytes=b"",
        )
        fetched = service.get_invoice(created.invoice_token)
        assert fetched.debtor_name == "Full Corp"
        assert fetched.debtor_uen == "999999999Z"
        assert float(fetched.amount) == 7777.0


# ═══════════════════════════════════════════════════════════════
# GET INVOICES BY SELLER
# ═══════════════════════════════════════════════════════════════

class TestGetInvoicesBySeller:
    def test_returns_only_seller_invoices(self, db):
        service = _make_service(db)
        service.create_invoice(_make_invoice_data(seller_id=10), pdf_bytes=b"")
        service.create_invoice(_make_invoice_data(seller_id=10), pdf_bytes=b"")
        service.create_invoice(_make_invoice_data(seller_id=99), pdf_bytes=b"")

        result = service.get_invoices_by_seller(10)
        assert len(result) == 2
        assert all(inv.seller_id == 10 for inv in result)

    def test_returns_empty_for_unknown_seller(self, db):
        service = _make_service(db)
        result = service.get_invoices_by_seller(999)
        assert result == []

    def test_returns_invoices_of_all_statuses(self, db):
        service = _make_service(db)
        inv1 = service.create_invoice(_make_invoice_data(seller_id=5), pdf_bytes=b"")
        inv2 = service.create_invoice(_make_invoice_data(seller_id=5), pdf_bytes=b"")
        service.update_status(inv1.invoice_token, "LISTED")
        service.update_status(inv2.invoice_token, "FINANCED")

        result = service.get_invoices_by_seller(5)
        assert len(result) == 2
        statuses = {inv.status for inv in result}
        assert statuses == {"LISTED", "FINANCED"}


# ═══════════════════════════════════════════════════════════════
# STATUS UPDATES (lifecycle transitions)
# ═══════════════════════════════════════════════════════════════

class TestUpdateStatus:
    def test_draft_to_listed(self, db):
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"")
        updated = service.update_status(invoice.invoice_token, "LISTED")
        assert updated.status == "LISTED"

    def test_listed_to_financed(self, db):
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"")
        service.update_status(invoice.invoice_token, "LISTED")
        updated = service.update_status(invoice.invoice_token, "FINANCED")
        assert updated.status == "FINANCED"

    def test_financed_to_repaid(self, db):
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"")
        service.update_status(invoice.invoice_token, "LISTED")
        service.update_status(invoice.invoice_token, "FINANCED")
        updated = service.update_status(invoice.invoice_token, "REPAID")
        assert updated.status == "REPAID"

    def test_financed_to_defaulted(self, db):
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"")
        service.update_status(invoice.invoice_token, "LISTED")
        service.update_status(invoice.invoice_token, "FINANCED")
        updated = service.update_status(invoice.invoice_token, "DEFAULTED")
        assert updated.status == "DEFAULTED"

    def test_draft_to_rejected(self, db):
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"")
        updated = service.update_status(invoice.invoice_token, "REJECTED")
        assert updated.status == "REJECTED"

    def test_update_nonexistent_raises_404(self, db):
        service = _make_service(db)
        with pytest.raises(HTTPException) as exc_info:
            service.update_status("INV-NOPE-20260101-ZZZZ", "LISTED")
        assert exc_info.value.status_code == 404

    def test_status_persists_after_refetch(self, db):
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"")
        service.update_status(invoice.invoice_token, "FINANCED")
        refetched = service.get_invoice(invoice.invoice_token)
        assert refetched.status == "FINANCED"

    def test_multiple_status_transitions(self, db):
        """Full lifecycle: DRAFT → LISTED → FINANCED → REPAID"""
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"")
        assert invoice.status == "DRAFT"

        service.update_status(invoice.invoice_token, "LISTED")
        service.update_status(invoice.invoice_token, "FINANCED")
        service.update_status(invoice.invoice_token, "REPAID")

        final = service.get_invoice(invoice.invoice_token)
        assert final.status == "REPAID"

    def test_defaulted_lifecycle(self, db):
        """Full lifecycle: DRAFT → LISTED → FINANCED → DEFAULTED"""
        service = _make_service(db)
        invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"")
        service.update_status(invoice.invoice_token, "LISTED")
        service.update_status(invoice.invoice_token, "FINANCED")
        service.update_status(invoice.invoice_token, "DEFAULTED")

        final = service.get_invoice(invoice.invoice_token)
        assert final.status == "DEFAULTED"

    def test_all_valid_statuses(self, db):
        """Each valid status can be set."""
        valid_statuses = ["DRAFT", "LISTED", "FINANCED", "REPAID", "DEFAULTED", "REJECTED"]
        service = _make_service(db)
        for status in valid_statuses:
            invoice = service.create_invoice(_make_invoice_data(), pdf_bytes=b"")
            updated = service.update_status(invoice.invoice_token, status)
            assert updated.status == status


# ═══════════════════════════════════════════════════════════════
# ROUTER / API ENDPOINTS
# ═══════════════════════════════════════════════════════════════

class TestInvoiceRouter:
    def _create_via_db(self, db):
        """Directly insert an invoice into the DB for API tests (bypasses MinIO)."""
        invoice = Invoice(
            invoice_token="INV-API-20260405-T001",
            seller_id=1,
            debtor_name="API Debtor",
            debtor_uen="200012345K",
            amount=5000.0,
            due_date=date(2026, 12, 31),
            currency="SGD",
            pdf_url="http://minio/test.pdf",
            status="DRAFT",
            extracted_data={"debtor_name": "API Debtor"},
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)
        return invoice

    def test_get_invoice_by_token(self, client, db):
        inv = self._create_via_db(db)
        resp = client.get(f"/invoices/{inv.invoice_token}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["invoice_token"] == inv.invoice_token
        assert data["debtor_name"] == "API Debtor"

    def test_get_invoice_not_found(self, client):
        resp = client.get("/invoices/INV-NOPE-20260101-ZZZZ")
        assert resp.status_code == 404

    def test_list_invoices_by_seller(self, client, db):
        self._create_via_db(db)
        # Create a second with different token
        inv2 = Invoice(
            invoice_token="INV-API-20260405-T002",
            seller_id=1,
            debtor_name="Another",
            debtor_uen="200012345K",
            amount=3000.0,
            due_date=date(2026, 12, 31),
            currency="SGD",
            pdf_url="http://minio/test2.pdf",
            status="DRAFT",
        )
        db.add(inv2)
        db.commit()

        resp = client.get("/invoices?seller_id=1")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2

    def test_list_invoices_empty_for_unknown_seller(self, client):
        resp = client.get("/invoices?seller_id=9999")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_update_status_via_api(self, client, db):
        inv = self._create_via_db(db)
        resp = client.patch(
            f"/invoices/{inv.invoice_token}/status",
            json={"status": "LISTED"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "LISTED"

    def test_update_status_not_found(self, client):
        resp = client.patch(
            "/invoices/INV-NOPE-20260101-ZZZZ/status",
            json={"status": "LISTED"},
        )
        assert resp.status_code == 404

    def test_update_status_invalid_value(self, client, db):
        inv = self._create_via_db(db)
        resp = client.patch(
            f"/invoices/{inv.invoice_token}/status",
            json={"status": "INVALID_STATUS"},
        )
        assert resp.status_code == 422

    def test_response_includes_all_fields(self, client, db):
        inv = self._create_via_db(db)
        resp = client.get(f"/invoices/{inv.invoice_token}")
        data = resp.json()
        assert "id" in data
        assert "invoice_token" in data
        assert "seller_id" in data
        assert "debtor_name" in data
        assert "debtor_uen" in data
        assert "amount" in data
        assert "due_date" in data
        assert "currency" in data
        assert "pdf_url" in data
        assert "status" in data
        assert "extracted_data" in data
        assert "created_at" in data

    def test_status_transition_via_api_full_lifecycle(self, client, db):
        inv = self._create_via_db(db)
        for status in ["LISTED", "FINANCED", "REPAID"]:
            resp = client.patch(
                f"/invoices/{inv.invoice_token}/status",
                json={"status": status},
            )
            assert resp.status_code == 200
            assert resp.json()["status"] == status

    def test_list_returns_all_statuses(self, client, db):
        """Seller's My Invoices page should see invoices of all statuses."""
        for i, status in enumerate(["DRAFT", "LISTED", "FINANCED", "REPAID", "DEFAULTED"]):
            inv = Invoice(
                invoice_token=f"INV-MIX-{i}",
                seller_id=50,
                debtor_name=f"Debtor {i}",
                debtor_uen="200012345K",
                amount=1000.0 * (i + 1),
                due_date=date(2026, 12, 31),
                currency="SGD",
                pdf_url="http://minio/test.pdf",
                status=status,
            )
            db.add(inv)
        db.commit()

        resp = client.get("/invoices?seller_id=50")
        data = resp.json()
        assert len(data) == 5
        returned_statuses = {inv["status"] for inv in data}
        assert returned_statuses == {"DRAFT", "LISTED", "FINANCED", "REPAID", "DEFAULTED"}

    def test_different_sellers_isolated(self, client, db):
        """Invoices from different sellers don't leak across."""
        for seller_id in [10, 20]:
            inv = Invoice(
                invoice_token=f"INV-SELLER-{seller_id}",
                seller_id=seller_id,
                debtor_name="Debtor",
                debtor_uen="200012345K",
                amount=1000.0,
                due_date=date(2026, 12, 31),
                currency="SGD",
                pdf_url="http://minio/test.pdf",
                status="DRAFT",
            )
            db.add(inv)
        db.commit()

        resp = client.get("/invoices?seller_id=10")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["seller_id"] == 10


# ═══════════════════════════════════════════════════════════════
# HEALTH ENDPOINT
# ═══════════════════════════════════════════════════════════════

class TestHealthEndpoint:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "invoice-service"
