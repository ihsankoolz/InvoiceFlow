from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.listing import ListingCreate, ListingResponse, ListingUpdate
from app.services.listing_service import ListingService

router = APIRouter(prefix="/listings", tags=["Listings"])


@router.post("/", response_model=ListingResponse, status_code=status.HTTP_201_CREATED)
def create_listing(data: ListingCreate, db: Session = Depends(get_db)):
    service = ListingService(db)
    listing = service.create_listing(data)
    return listing


@router.delete("/")
def bulk_delete_listings(seller_id: int = Query(...), db: Session = Depends(get_db)):
    service = ListingService(db)
    deleted_count = service.bulk_delete_by_seller(seller_id)
    return {"deleted_count": deleted_count}


@router.get("/{listing_id}", response_model=ListingResponse)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    service = ListingService(db)
    listing = service.get_listing(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.patch("/{listing_id}", response_model=ListingResponse)
def update_listing(listing_id: int, data: ListingUpdate, db: Session = Depends(get_db)):
    service = ListingService(db)
    listing = service.update_listing(listing_id, data)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return listing


@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(listing_id: int, db: Session = Depends(get_db)):
    service = ListingService(db)
    service.delete_listing(listing_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
