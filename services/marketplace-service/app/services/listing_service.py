from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.schemas.listing import ListingCreate, ListingUpdate


class ListingService:
    def __init__(self, db: Session):
        self.db = db

    def create_listing(self, data: ListingCreate) -> Listing:
        listing = Listing(
            invoice_token=data.invoice_token,
            seller_id=data.seller_id,
            debtor_uen=data.debtor_uen,
            amount=data.amount,
            urgency_level=data.urgency_level,
            deadline=data.deadline,
        )
        self.db.add(listing)
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def get_listing(self, listing_id: int) -> Listing:
        return self.db.query(Listing).filter(Listing.id == listing_id).first()

    def update_listing(self, listing_id: int, data: ListingUpdate) -> Listing:
        listing = self.db.query(Listing).filter(Listing.id == listing_id).first()
        if not listing:
            return None
        if data.deadline is not None:
            listing.deadline = data.deadline
        if data.status is not None:
            listing.status = data.status
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def delete_listing(self, listing_id: int) -> None:
        listing = self.db.query(Listing).filter(Listing.id == listing_id).first()
        if listing:
            self.db.delete(listing)
            self.db.commit()

    def bulk_delete_by_seller(self, seller_id: int) -> int:
        count = (
            self.db.query(Listing)
            .filter(Listing.seller_id == seller_id)
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return count
