import pytest
from app.models.bid import Bid
from app.schemas.bid import BidCreate
from app.services.bid_service import BidService
from fastapi import HTTPException


def _make_bid_data(invoice_token="INV-001", investor_id=1, bid_amount=500.0):
    return BidCreate(invoice_token=invoice_token, investor_id=investor_id, bid_amount=bid_amount)


def test_create_bid_success(db):
    service = BidService(db)
    result = service.create_bid(_make_bid_data())
    assert result["bid"].id is not None
    assert result["bid"].status == "PENDING"
    assert result["previous_highest"] is None


def test_create_bid_duplicate_pending_raises_409(db):
    service = BidService(db)
    service.create_bid(_make_bid_data())
    with pytest.raises(HTTPException) as exc_info:
        service.create_bid(_make_bid_data())
    assert exc_info.value.status_code == 409


def test_create_bid_replaces_cancelled_record(db):
    service = BidService(db)
    result = service.create_bid(_make_bid_data())
    bid = result["bid"]
    # Manually cancel the bid to simulate a failed escrow rollback
    bid.status = "CANCELLED"
    db.commit()
    # Investor should be allowed to bid again
    result2 = service.create_bid(_make_bid_data())
    assert result2["bid"].status == "PENDING"


def test_create_bid_returns_previous_highest_when_outbid(db):
    service = BidService(db)
    # First investor bids 300
    service.create_bid(_make_bid_data(investor_id=1, bid_amount=300.0))
    # Second investor bids 500 (higher) — previous_highest should be investor 1's bid
    result = service.create_bid(_make_bid_data(investor_id=2, bid_amount=500.0))
    assert result["previous_highest"] is not None
    assert float(result["previous_highest"].bid_amount) == 300.0


def test_create_bid_no_previous_highest_when_not_outbid(db):
    service = BidService(db)
    # First investor bids 500
    service.create_bid(_make_bid_data(investor_id=1, bid_amount=500.0))
    # Second investor bids 300 (lower) — not outbidding anyone, no previous_highest
    result = service.create_bid(_make_bid_data(investor_id=2, bid_amount=300.0))
    assert result["previous_highest"] is None


def test_get_bid_not_found_raises_404(db):
    service = BidService(db)
    with pytest.raises(HTTPException) as exc_info:
        service.get_bid(999)
    assert exc_info.value.status_code == 404


def test_accept_bid(db):
    service = BidService(db)
    bid = service.create_bid(_make_bid_data())["bid"]
    accepted = service.accept_bid(bid.id)
    assert accepted.status == "ACCEPTED"


def test_reject_bid(db):
    service = BidService(db)
    bid = service.create_bid(_make_bid_data())["bid"]
    rejected = service.reject_bid(bid.id)
    assert rejected.status == "REJECTED"


def test_delete_bid(db):
    service = BidService(db)
    bid = service.create_bid(_make_bid_data())["bid"]
    service.delete_bid(bid.id)
    assert db.query(Bid).filter(Bid.id == bid.id).first() is None


def test_get_bids_for_investor(db):
    service = BidService(db)
    service.create_bid(_make_bid_data(invoice_token="INV-001", investor_id=7))
    service.create_bid(_make_bid_data(invoice_token="INV-002", investor_id=7))
    service.create_bid(_make_bid_data(invoice_token="INV-003", investor_id=99))
    bids = service.get_bids_for_investor(7)
    assert len(bids) == 2
    assert all(b.investor_id == 7 for b in bids)


def test_get_bids_for_invoice(db):
    service = BidService(db)
    service.create_bid(_make_bid_data(invoice_token="INV-XYZ", investor_id=1, bid_amount=100))
    service.create_bid(_make_bid_data(invoice_token="INV-XYZ", investor_id=2, bid_amount=200))
    service.create_bid(_make_bid_data(invoice_token="INV-OTHER", investor_id=3))
    bids = service.get_bids_for_invoice("INV-XYZ")
    assert len(bids) == 2
    # Ordered by bid_amount DESC
    assert float(bids[0].bid_amount) == 200.0


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_list_bids_requires_filter(client):
    response = client.get("/bids")
    assert response.status_code == 400
