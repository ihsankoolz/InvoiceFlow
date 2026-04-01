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


def test_create_listing(db):
    service = ListingService(db)
    listing = service.create_listing(_make_listing_data())
    assert listing.id is not None
    assert listing.invoice_token == "INV-TEST-001"
    assert listing.status == "ACTIVE"
    assert listing.bid_count == 0


def test_create_listing_face_value_defaults_to_amount(db):
    service = ListingService(db)
    listing = service.create_listing(_make_listing_data(face_value=None))
    assert float(listing.face_value) == 5000.0


def test_get_all_listings_returns_active_only_by_default(db):
    service = ListingService(db)
    service.create_listing(_make_listing_data(invoice_token="INV-001"))
    service.create_listing(_make_listing_data(invoice_token="INV-002"))
    closed = service.create_listing(_make_listing_data(invoice_token="INV-003"))
    service.update_listing(closed.id, ListingUpdate(status="CLOSED"))

    listings = service.get_all_listings()
    assert len(listings) == 2
    assert all(l.status == "ACTIVE" for l in listings)


def test_get_all_listings_filter_by_urgency(db):
    service = ListingService(db)
    service.create_listing(_make_listing_data(invoice_token="INV-LOW", urgency_level="LOW"))
    service.create_listing(_make_listing_data(invoice_token="INV-HIGH", urgency_level="HIGH"))

    result = service.get_all_listings(urgency_level="HIGH")
    assert len(result) == 1
    assert result[0].urgency_level == "HIGH"


def test_update_listing_current_bid_and_bid_count(db):
    service = ListingService(db)
    listing = service.create_listing(_make_listing_data())
    updated = service.update_listing(listing.id, ListingUpdate(current_bid=750.0, bid_count=3))
    assert float(updated.current_bid) == 750.0
    assert updated.bid_count == 3


def test_update_listing_status_to_closed(db):
    service = ListingService(db)
    listing = service.create_listing(_make_listing_data())
    updated = service.update_listing(listing.id, ListingUpdate(status="CLOSED"))
    assert updated.status == "CLOSED"


def test_update_listing_not_found_returns_none(db):
    service = ListingService(db)
    result = service.update_listing(9999, ListingUpdate(status="CLOSED"))
    assert result is None


def test_delete_listing(db):
    service = ListingService(db)
    listing = service.create_listing(_make_listing_data())
    service.delete_listing(listing.id)
    assert service.get_listing(listing.id) is None


def test_listings_ordered_by_deadline_asc(db):
    service = ListingService(db)
    service.create_listing(_make_listing_data(invoice_token="INV-FAR", deadline=_deadline(60)))
    service.create_listing(_make_listing_data(invoice_token="INV-NEAR", deadline=_deadline(5)))

    listings = service.get_all_listings()
    assert listings[0].invoice_token == "INV-NEAR"
    assert listings[1].invoice_token == "INV-FAR"


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
