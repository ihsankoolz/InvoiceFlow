from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.listing import ListingCreate, ListingResponse, ListingUpdate
from app.services.listing_service import ListingService

router = APIRouter(prefix="/listings", tags=["Listings"])


@router.get("/", response_model=List[ListingResponse])
def get_all_listings(
    urgency_level: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    """Get all listings, optionally filtered by urgency_level or status."""
    service = ListingService(db)
    return service.get_all_listings(urgency_level=urgency_level, status=status_filter or "ACTIVE")


@router.post("/", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
def create_listing(data: ListingCreate, db: Session = Depends(get_db)):
    """
    Create a new auction listing.

    Called by Invoice Orchestrator at step 10 of Scenario 1.
    """
    service = ListingService(db)
    listing = service.create_listing(data)
    return listing


@router.delete("/")
def bulk_delete_listings(seller_id: int = Query(...), db: Session = Depends(get_db)):
    """
    Bulk delete all active listings for a seller.

    Called by Temporal Worker at step B8 of Scenario 3 (business default).
    """
    service = ListingService(db)
    deleted_count = service.bulk_delete_by_seller(seller_id)
    return {"deleted_count": deleted_count}


@router.get("/by-token/{invoice_token}", response_model=ListingResponse)
def get_listing_by_token(invoice_token: str, db: Session = Depends(get_db)):
    """Look up a listing by invoice token. Returns 404 if not found."""
    service = ListingService(db)
    listing = service.get_listing_by_token(invoice_token)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.delete("/by-token/{invoice_token}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing_by_token(invoice_token: str, db: Session = Depends(get_db)):
    """
    Delete a listing by invoice token.

    Called by Temporal Worker at step C10 of Scenario 2C (auction close).
    """
    service = ListingService(db)
    service.delete_listing_by_token(invoice_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    """Get a listing by its numeric ID. Returns 404 if not found."""
    service = ListingService(db)
    listing = service.get_listing(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.patch("/{listing_id}", response_model=ListingResponse)
def update_listing(listing_id: int, data: ListingUpdate, db: Session = Depends(get_db)):
    """
    Update listing fields (e.g. deadline extension).

    Called by Bidding Orchestrator at step B12b (anti-snipe +300s extension).
    """
    service = ListingService(db)
    listing = service.update_listing(listing_id, data)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(listing_id: int, db: Session = Depends(get_db)):
    """Delete a listing by ID."""
    service = ListingService(db)
    service.delete_listing(listing_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
