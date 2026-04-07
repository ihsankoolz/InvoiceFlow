from datetime import datetime, timedelta, timezone

import pytest
from app.schemas.listing import ListingCreate, ListingUpdate
from app.services.listing_service import ListingService


def _deadline(days=30):
    return datetime.now(timezone.utc) + timedelta(days=days)


def _make_listing_data(**overrides):
    defaults = dict(
        invoice_token="INV-TEST-001",
        seller_id=1,
        debtor_uen="200012345K",
        amount=5000.0,
        minimum_bid=100.0,
        urgency_level="MEDIUM",
        deadline=_deadline(),
        face_value=5000.0,
        debtor_name="Test Corp",
    )
    defaults.update(overrides)
    return ListingCreate(**defaults)


# ═══════════════════════════════════════════════════════════════
# CREATE
# ═══════════════════════════════════════════════════════════════


class TestCreateListing:
    def test_create_listing(self, db):
        service = ListingService(db)
        listing = service.create_listing(_make_listing_data())
        assert listing.id is not None
        assert listing.invoice_token == "INV-TEST-001"
        assert listing.status == "ACTIVE"
        assert listing.bid_count == 0

    def test_face_value_defaults_to_amount(self, db):
        service = ListingService(db)
        listing = service.create_listing(_make_listing_data(face_value=None))
        assert float(listing.face_value) == 5000.0

    def test_face_value_overrides_amount(self, db):
        service = ListingService(db)
        listing = service.create_listing(_make_listing_data(amount=5000.0, face_value=6000.0))
        assert float(listing.face_value) == 6000.0
        assert float(listing.amount) == 5000.0

    def test_create_stores_all_fields(self, db):
        service = ListingService(db)
        data = _make_listing_data(
            invoice_token="INV-FULL",
            seller_id=42,
            debtor_uen="199900001A",
            amount=10000.0,
            minimum_bid=500.0,
            urgency_level="CRITICAL",
            face_value=12000.0,
            debtor_name="Full Corp",
        )
        listing = service.create_listing(data)
        assert listing.seller_id == 42
        assert listing.debtor_uen == "199900001A"
        assert float(listing.amount) == 10000.0
        assert float(listing.minimum_bid) == 500.0
        assert listing.urgency_level == "CRITICAL"
        assert float(listing.face_value) == 12000.0
        assert listing.debtor_name == "Full Corp"

    def test_create_duplicate_invoice_token_fails(self, db):
        service = ListingService(db)
        service.create_listing(_make_listing_data(invoice_token="INV-DUP"))
        with pytest.raises(Exception):
            service.create_listing(_make_listing_data(invoice_token="INV-DUP"))

    def test_current_bid_starts_as_none(self, db):
        service = ListingService(db)
        listing = service.create_listing(_make_listing_data())
        assert listing.current_bid is None

    def test_create_with_all_urgency_levels(self, db):
        service = ListingService(db)
        for level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
            listing = service.create_listing(
                _make_listing_data(invoice_token=f"INV-{level}", urgency_level=level)
            )
            assert listing.urgency_level == level


# ═══════════════════════════════════════════════════════════════
# GET ALL LISTINGS (filtering & ordering)
# ═══════════════════════════════════════════════════════════════


class TestGetAllListings:
    def test_returns_active_only_by_default(self, db):
        service = ListingService(db)
        service.create_listing(_make_listing_data(invoice_token="INV-001"))
        service.create_listing(_make_listing_data(invoice_token="INV-002"))
        closed = service.create_listing(_make_listing_data(invoice_token="INV-003"))
        service.update_listing(closed.id, ListingUpdate(status="CLOSED"))

        listings = service.get_all_listings()
        assert len(listings) == 2
        assert all(item.status == "ACTIVE" for item in listings)

    def test_filter_by_urgency(self, db):
        service = ListingService(db)
        service.create_listing(_make_listing_data(invoice_token="INV-LOW", urgency_level="LOW"))
        service.create_listing(_make_listing_data(invoice_token="INV-HIGH", urgency_level="HIGH"))

        result = service.get_all_listings(urgency_level="HIGH")
        assert len(result) == 1
        assert result[0].urgency_level == "HIGH"

    def test_filter_by_status_closed(self, db):
        service = ListingService(db)
        listing = service.create_listing(_make_listing_data(invoice_token="INV-CL"))
        service.update_listing(listing.id, ListingUpdate(status="CLOSED"))
        service.create_listing(_make_listing_data(invoice_token="INV-AC"))

        result = service.get_all_listings(status="CLOSED")
        assert len(result) == 1
        assert result[0].invoice_token == "INV-CL"

    def test_filter_by_status_expired(self, db):
        service = ListingService(db)
        listing = service.create_listing(_make_listing_data(invoice_token="INV-EX"))
        service.update_listing(listing.id, ListingUpdate(status="EXPIRED"))

        result = service.get_all_listings(status="EXPIRED")
        # Listing still has a future deadline so it appears when filtering by EXPIRED status
        assert len(result) == 1
        assert result[0].status == "EXPIRED"

    def test_excludes_expired_deadlines(self, db):
        service = ListingService(db)
        service.create_listing(
            _make_listing_data(
                invoice_token="INV-PAST", deadline=datetime.now(timezone.utc) - timedelta(hours=1)
            )
        )
        service.create_listing(
            _make_listing_data(invoice_token="INV-FUTURE", deadline=_deadline(5))
        )

        listings = service.get_all_listings()
        assert len(listings) == 1
        assert listings[0].invoice_token == "INV-FUTURE"

    def test_ordered_by_deadline_asc(self, db):
        service = ListingService(db)
        service.create_listing(_make_listing_data(invoice_token="INV-FAR", deadline=_deadline(60)))
        service.create_listing(_make_listing_data(invoice_token="INV-NEAR", deadline=_deadline(5)))

        listings = service.get_all_listings()
        assert listings[0].invoice_token == "INV-NEAR"
        assert listings[1].invoice_token == "INV-FAR"

    def test_returns_empty_list_when_no_listings(self, db):
        service = ListingService(db)
        assert service.get_all_listings() == []

    def test_combined_urgency_and_status_filter(self, db):
        service = ListingService(db)
        l1 = service.create_listing(_make_listing_data(invoice_token="INV-1", urgency_level="HIGH"))
        service.update_listing(l1.id, ListingUpdate(status="CLOSED"))
        service.create_listing(_make_listing_data(invoice_token="INV-2", urgency_level="HIGH"))
        service.create_listing(_make_listing_data(invoice_token="INV-3", urgency_level="LOW"))

        result = service.get_all_listings(urgency_level="HIGH", status="ACTIVE")
        assert len(result) == 1
        assert result[0].invoice_token == "INV-2"

    def test_no_status_filter_returns_all_statuses_with_future_deadline(self, db):
        service = ListingService(db)
        service.create_listing(_make_listing_data(invoice_token="INV-A"))
        closed = service.create_listing(_make_listing_data(invoice_token="INV-B"))
        service.update_listing(closed.id, ListingUpdate(status="CLOSED"))

        result = service.get_all_listings(status=None)
        assert len(result) == 2


# ═══════════════════════════════════════════════════════════════
# GET SINGLE LISTING
# ═══════════════════════════════════════════════════════════════


class TestGetListing:
    def test_get_existing_listing(self, db):
        service = ListingService(db)
        created = service.create_listing(_make_listing_data())
        fetched = service.get_listing(created.id)
        assert fetched.id == created.id
        assert fetched.invoice_token == "INV-TEST-001"

    def test_get_nonexistent_listing_returns_none(self, db):
        service = ListingService(db)
        assert service.get_listing(9999) is None


# ═══════════════════════════════════════════════════════════════
# GET BY TOKEN
# ═══════════════════════════════════════════════════════════════


class TestGetListingByToken:
    def test_get_existing_token(self, db):
        service = ListingService(db)
        service.create_listing(_make_listing_data(invoice_token="INV-TOKEN-1"))
        result = service.get_listing_by_token("INV-TOKEN-1")
        assert result is not None
        assert result.invoice_token == "INV-TOKEN-1"

    def test_get_nonexistent_token_returns_none(self, db):
        service = ListingService(db)
        assert service.get_listing_by_token("DOES-NOT-EXIST") is None


# ═══════════════════════════════════════════════════════════════
# UPDATE
# ═══════════════════════════════════════════════════════════════


class TestUpdateListing:
    def test_update_current_bid_and_bid_count(self, db):
        service = ListingService(db)
        listing = service.create_listing(_make_listing_data())
        updated = service.update_listing(listing.id, ListingUpdate(current_bid=750.0, bid_count=3))
        assert float(updated.current_bid) == 750.0
        assert updated.bid_count == 3

    def test_update_status_to_closed(self, db):
        service = ListingService(db)
        listing = service.create_listing(_make_listing_data())
        updated = service.update_listing(listing.id, ListingUpdate(status="CLOSED"))
        assert updated.status == "CLOSED"

    def test_update_status_to_expired(self, db):
        service = ListingService(db)
        listing = service.create_listing(_make_listing_data())
        updated = service.update_listing(listing.id, ListingUpdate(status="EXPIRED"))
        assert updated.status == "EXPIRED"

    def test_update_deadline(self, db):
        service = ListingService(db)
        listing = service.create_listing(_make_listing_data())
        new_deadline = _deadline(90)
        updated = service.update_listing(listing.id, ListingUpdate(deadline=new_deadline))
        # Service strips tzinfo before storing, so both sides are naive
        assert updated.deadline == new_deadline.replace(tzinfo=None)

    def test_update_not_found_returns_none(self, db):
        service = ListingService(db)
        result = service.update_listing(9999, ListingUpdate(status="CLOSED"))
        assert result is None

    def test_partial_update_preserves_other_fields(self, db):
        service = ListingService(db)
        listing = service.create_listing(_make_listing_data())
        service.update_listing(listing.id, ListingUpdate(current_bid=500.0))
        refreshed = service.get_listing(listing.id)
        assert float(refreshed.current_bid) == 500.0
        assert refreshed.status == "ACTIVE"
        assert refreshed.invoice_token == "INV-TEST-001"

    def test_update_bid_count_only(self, db):
        service = ListingService(db)
        listing = service.create_listing(_make_listing_data())
        updated = service.update_listing(listing.id, ListingUpdate(bid_count=5))
        assert updated.bid_count == 5
        assert updated.current_bid is None

    def test_update_with_no_changes(self, db):
        service = ListingService(db)
        listing = service.create_listing(_make_listing_data())
        updated = service.update_listing(listing.id, ListingUpdate())
        assert updated.status == "ACTIVE"
        assert updated.bid_count == 0


# ═══════════════════════════════════════════════════════════════
# DELETE
# ═══════════════════════════════════════════════════════════════


class TestDeleteListing:
    def test_delete_existing_listing(self, db):
        service = ListingService(db)
        listing = service.create_listing(_make_listing_data())
        service.delete_listing(listing.id)
        assert service.get_listing(listing.id) is None

    def test_delete_nonexistent_listing_no_error(self, db):
        service = ListingService(db)
        service.delete_listing(9999)  # should not raise


# ═══════════════════════════════════════════════════════════════
# DELETE BY TOKEN
# ═══════════════════════════════════════════════════════════════


class TestDeleteListingByToken:
    def test_delete_by_token(self, db):
        service = ListingService(db)
        service.create_listing(_make_listing_data(invoice_token="INV-DEL"))
        service.delete_listing_by_token("INV-DEL")
        assert service.get_listing_by_token("INV-DEL") is None

    def test_delete_by_nonexistent_token_no_error(self, db):
        service = ListingService(db)
        service.delete_listing_by_token("NOPE")  # should not raise


# ═══════════════════════════════════════════════════════════════
# BULK DELETE BY SELLER
# ═══════════════════════════════════════════════════════════════


class TestBulkDeleteBySeller:
    def test_bulk_delete_removes_all_seller_listings(self, db):
        service = ListingService(db)
        service.create_listing(_make_listing_data(invoice_token="INV-S1-A", seller_id=10))
        service.create_listing(_make_listing_data(invoice_token="INV-S1-B", seller_id=10))
        service.create_listing(_make_listing_data(invoice_token="INV-S2-A", seller_id=20))

        result = service.bulk_delete_by_seller(10)
        assert result["deleted_count"] == 2
        assert set(result["invoice_tokens"]) == {"INV-S1-A", "INV-S1-B"}
        assert service.get_listing_by_token("INV-S1-A") is None
        assert service.get_listing_by_token("INV-S1-B") is None
        assert service.get_listing_by_token("INV-S2-A") is not None

    def test_bulk_delete_no_matches_returns_zero(self, db):
        service = ListingService(db)
        result = service.bulk_delete_by_seller(999)
        assert result["deleted_count"] == 0
        assert result["invoice_tokens"] == []


# ═══════════════════════════════════════════════════════════════
# ROUTER / API ENDPOINTS (internal CRUD)
# ═══════════════════════════════════════════════════════════════


class TestListingsRouter:
    def _create_via_api(self, client, **overrides):
        payload = dict(
            invoice_token="INV-API-001",
            seller_id=1,
            debtor_uen="200012345K",
            amount=5000.0,
            minimum_bid=100.0,
            urgency_level="MEDIUM",
            deadline=_deadline().isoformat(),
            face_value=5000.0,
            debtor_name="API Corp",
        )
        payload.update(overrides)
        return client.post("/listings/", json=payload)

    def test_create_listing_201(self, client):
        resp = self._create_via_api(client)
        assert resp.status_code == 201
        data = resp.json()
        assert data["invoice_token"] == "INV-API-001"
        assert data["status"] == "ACTIVE"

    def test_get_all_listings(self, client):
        self._create_via_api(client, invoice_token="INV-A1")
        self._create_via_api(client, invoice_token="INV-A2")
        resp = client.get("/listings/")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_get_listing_by_id(self, client):
        create_resp = self._create_via_api(client)
        listing_id = create_resp.json()["id"]
        resp = client.get(f"/listings/{listing_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == listing_id

    def test_get_listing_not_found(self, client):
        resp = client.get("/listings/9999")
        assert resp.status_code == 404

    def test_get_listing_by_token(self, client):
        self._create_via_api(client, invoice_token="INV-TK-1")
        resp = client.get("/listings/by-token/INV-TK-1")
        assert resp.status_code == 200
        assert resp.json()["invoice_token"] == "INV-TK-1"

    def test_get_listing_by_token_not_found(self, client):
        resp = client.get("/listings/by-token/NOPE")
        assert resp.status_code == 404

    def test_patch_listing(self, client):
        create_resp = self._create_via_api(client)
        listing_id = create_resp.json()["id"]
        resp = client.patch(f"/listings/{listing_id}", json={"status": "CLOSED"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "CLOSED"

    def test_patch_listing_not_found(self, client):
        resp = client.patch("/listings/9999", json={"status": "CLOSED"})
        assert resp.status_code == 404

    def test_delete_listing_204(self, client):
        create_resp = self._create_via_api(client)
        listing_id = create_resp.json()["id"]
        resp = client.delete(f"/listings/{listing_id}")
        assert resp.status_code == 204

    def test_delete_by_token_204(self, client):
        self._create_via_api(client, invoice_token="INV-DEL-TK")
        resp = client.delete("/listings/by-token/INV-DEL-TK")
        assert resp.status_code == 204

    def test_bulk_delete(self, client):
        self._create_via_api(client, invoice_token="INV-BD-1", seller_id=77)
        self._create_via_api(client, invoice_token="INV-BD-2", seller_id=77)
        resp = client.delete("/listings/?seller_id=77")
        assert resp.status_code == 200
        assert resp.json()["deleted_count"] == 2

    def test_filter_by_urgency_via_api(self, client):
        self._create_via_api(client, invoice_token="INV-L", urgency_level="LOW")
        self._create_via_api(client, invoice_token="INV-H", urgency_level="HIGH")
        resp = client.get("/listings/?urgency_level=HIGH")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["urgency_level"] == "HIGH"


# ═══════════════════════════════════════════════════════════════
# PUBLIC LISTINGS ROUTER (/api/listings — frontend-facing)
# ═══════════════════════════════════════════════════════════════


class TestPublicListingsRouter:
    def _seed_listing(self, client, **overrides):
        payload = dict(
            invoice_token="INV-PUB-001",
            seller_id=1,
            debtor_uen="200012345K",
            amount=5000.0,
            minimum_bid=100.0,
            urgency_level="MEDIUM",
            deadline=_deadline().isoformat(),
            face_value=5000.0,
            debtor_name="Public Corp",
        )
        payload.update(overrides)
        return client.post("/listings/", json=payload)

    def test_get_public_listings(self, client):
        self._seed_listing(client, invoice_token="INV-P1")
        self._seed_listing(client, invoice_token="INV-P2")
        resp = client.get("/api/listings")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_excludes_closed_listings(self, client):
        create_resp = self._seed_listing(client, invoice_token="INV-CL")
        listing_id = create_resp.json()["id"]
        client.patch(f"/listings/{listing_id}", json={"status": "CLOSED"})
        self._seed_listing(client, invoice_token="INV-AC")

        resp = client.get("/api/listings")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["invoice_token"] == "INV-AC"

    def test_excludes_expired_deadline_listings(self, client):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        self._seed_listing(client, invoice_token="INV-OLD", deadline=past)
        self._seed_listing(client, invoice_token="INV-NEW")

        resp = client.get("/api/listings")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["invoice_token"] == "INV-NEW"

    def test_filter_by_urgency(self, client):
        self._seed_listing(client, invoice_token="INV-PL", urgency_level="LOW")
        self._seed_listing(client, invoice_token="INV-PH", urgency_level="HIGH")

        resp = client.get("/api/listings?urgency_level=HIGH")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["urgency_level"] == "HIGH"

    def test_urgency_all_returns_everything(self, client):
        self._seed_listing(client, invoice_token="INV-A", urgency_level="LOW")
        self._seed_listing(client, invoice_token="INV-B", urgency_level="HIGH")

        resp = client.get("/api/listings?urgency_level=ALL")
        assert len(resp.json()) == 2

    def test_search_by_debtor_name(self, client):
        self._seed_listing(client, invoice_token="INV-S1", debtor_name="Alpha Holdings")
        self._seed_listing(client, invoice_token="INV-S2", debtor_name="Beta Corp")

        resp = client.get("/api/listings?search=alpha")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["debtor_name"] == "Alpha Holdings"

    def test_search_by_invoice_token(self, client):
        self._seed_listing(client, invoice_token="INV-UNIQUE-XYZ")
        self._seed_listing(client, invoice_token="INV-OTHER-ABC")

        resp = client.get("/api/listings?search=UNIQUE")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["invoice_token"] == "INV-UNIQUE-XYZ"

    def test_search_by_debtor_uen(self, client):
        self._seed_listing(client, invoice_token="INV-U1", debtor_uen="199900001A")
        self._seed_listing(client, invoice_token="INV-U2", debtor_uen="200012345K")

        resp = client.get("/api/listings?search=199900001A")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["debtor_uen"] == "199900001A"

    def test_search_case_insensitive(self, client):
        self._seed_listing(client, invoice_token="INV-CI", debtor_name="Acme Industries")

        resp = client.get("/api/listings?search=acme")
        assert len(resp.json()) == 1

    def test_search_no_match_returns_empty(self, client):
        self._seed_listing(client, invoice_token="INV-NM")

        resp = client.get("/api/listings?search=zzzzzzz")
        assert resp.json() == []

    def test_get_single_public_listing(self, client):
        create_resp = self._seed_listing(client, invoice_token="INV-SINGLE")
        listing_id = create_resp.json()["id"]

        resp = client.get(f"/api/listings/{listing_id}")
        assert resp.status_code == 200
        assert resp.json()["invoice_token"] == "INV-SINGLE"

    def test_get_single_public_listing_not_found(self, client):
        resp = client.get("/api/listings/9999")
        assert resp.status_code == 404

    def test_response_includes_read_model_fields(self, client):
        create_resp = self._seed_listing(
            client, invoice_token="INV-RM", face_value=10000.0, debtor_name="RM Corp"
        )
        listing_id = create_resp.json()["id"]
        client.patch(f"/listings/{listing_id}", json={"current_bid": 8000.0, "bid_count": 5})

        resp = client.get(f"/api/listings/{listing_id}")
        data = resp.json()
        assert data["face_value"] == 10000.0
        assert data["debtor_name"] == "RM Corp"
        assert data["current_bid"] == 8000.0
        assert data["bid_count"] == 5

    def test_deadline_returned_as_iso_string(self, client):
        self._seed_listing(client, invoice_token="INV-ISO")
        resp = client.get("/api/listings")
        data = resp.json()
        assert len(data) == 1
        # Should be a valid ISO format string
        datetime.fromisoformat(data[0]["deadline"])

    def test_empty_marketplace(self, client):
        resp = client.get("/api/listings")
        assert resp.status_code == 200
        assert resp.json() == []


# ═══════════════════════════════════════════════════════════════
# HEALTH ENDPOINT
# ═══════════════════════════════════════════════════════════════


class TestHealthEndpoint:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "marketplace-service"
