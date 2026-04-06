from datetime import datetime

from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.schemas.listing import ListingCreate, ListingUpdate


class ListingService:
    def __init__(self, db: Session):
        self.db = db

    def get_all_listings(self, urgency_level: str = None, status: str = "ACTIVE") -> list:
        query = self.db.query(Listing)
        if status:
            query = query.filter(Listing.status == status)
        if urgency_level:
            query = query.filter(Listing.urgency_level == urgency_level)
        query = query.filter(Listing.deadline > datetime.utcnow())
        return query.order_by(Listing.deadline.asc()).all()

    def create_listing(self, data: ListingCreate) -> Listing:
        listing = Listing(
            invoice_token=data.invoice_token,
            seller_id=data.seller_id,
            debtor_uen=data.debtor_uen,
            amount=data.amount,
            minimum_bid=data.minimum_bid,
            urgency_level=data.urgency_level,
            deadline=data.deadline,
            face_value=data.face_value if data.face_value is not None else data.amount,
            debtor_name=data.debtor_name,
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
            dl = data.deadline
            listing.deadline = dl.replace(tzinfo=None) if dl.tzinfo else dl
        if data.status is not None:
            listing.status = data.status
        if data.current_bid is not None:
            listing.current_bid = data.current_bid
        if data.bid_count is not None:
            listing.bid_count = data.bid_count
        self.db.commit()
        self.db.refresh(listing)
        return listing

    def delete_listing(self, listing_id: int) -> None:
        listing = self.db.query(Listing).filter(Listing.id == listing_id).first()
        if listing:
            self.db.delete(listing)
            self.db.commit()

    def get_listing_by_token(self, invoice_token: str) -> Listing:
        return self.db.query(Listing).filter(Listing.invoice_token == invoice_token).first()

    def delete_listing_by_token(self, invoice_token: str) -> None:
        listing = self.db.query(Listing).filter(Listing.invoice_token == invoice_token).first()
        if listing:
            self.db.delete(listing)
            self.db.commit()

    def bulk_delete_by_seller(self, seller_id: int) -> dict:
        listings = self.db.query(Listing).filter(Listing.seller_id == seller_id).all()
        invoice_tokens = [l.invoice_token for l in listings]
        for listing in listings:
            self.db.delete(listing)
        self.db.commit()
        return {"deleted_count": len(invoice_tokens), "invoice_tokens": invoice_tokens}
