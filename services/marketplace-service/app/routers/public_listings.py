"""
Public listings router — /api/listings

Returns the marketplace read model in a single DB query.
No N+1 HTTP calls to other services: face_value, debtor_name,
current_bid, and bid_count are pre-materialised columns on the
listings table, kept up-to-date by MarketplaceEventConsumer.
"""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.listing import Listing

router = APIRouter(tags=["Public Listings"])


def _listing_to_dict(listing: Listing) -> dict:
    return {
        "id": listing.id,
        "invoice_token": listing.invoice_token,
        "seller_id": listing.seller_id,
        "debtor_uen": listing.debtor_uen,
        "face_value": float(listing.face_value)
        if listing.face_value is not None
        else float(listing.amount),
        "minimum_bid": float(listing.minimum_bid),
        "current_bid": float(listing.current_bid) if listing.current_bid is not None else None,
        "bid_count": listing.bid_count or 0,
        "urgency_level": listing.urgency_level,
        "deadline": listing.deadline.isoformat() if listing.deadline else None,
        "debtor_name": listing.debtor_name,
        "status": listing.status,
        "created_at": listing.created_at.isoformat() if listing.created_at else None,
    }


@router.get("/api/listings", summary="Get marketplace listings")
def get_listings(
    urgency_level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    seller_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Returns active auction listings from the read model for the frontend marketplace page.

    Single DB query — no calls to invoice-service or bidding-service.
    Filters: urgency_level, search (invoice_token / debtor_name / debtor_uen), seller_id.
    Only returns listings with status=ACTIVE and deadline in the future.
    """
    now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
    query = db.query(Listing).filter(Listing.status == "ACTIVE", Listing.deadline > now_utc)

    if seller_id:
        query = query.filter(Listing.seller_id == seller_id)

    if urgency_level and urgency_level != "ALL":
        query = query.filter(Listing.urgency_level == urgency_level)

    if search:
        s = f"%{search.lower()}%"
        query = query.filter(
            Listing.invoice_token.ilike(s)
            | Listing.debtor_name.ilike(s)
            | Listing.debtor_uen.ilike(s)
        )

    listings = query.order_by(Listing.deadline.asc()).all()
    return [_listing_to_dict(listing) for listing in listings]


@router.get("/api/listings/{listing_id}", summary="Get a single listing")
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    """
    Returns a single active listing by ID.

    Called by Bidding Orchestrator at step B11 to check the anti-snipe window.
    Returns 404 if not found.
    """
    listing = db.query(Listing).filter(Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return _listing_to_dict(listing)
