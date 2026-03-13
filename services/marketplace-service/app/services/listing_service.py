from sqlalchemy.orm import Session

from app.models.listing import Listing
from app.schemas.listing import ListingCreate, ListingUpdate


class ListingService:
    def __init__(self, db: Session):
        self.db = db

    def create_listing(self, data: ListingCreate) -> Listing:
        # TODO: Create a new listing record from data and persist to DB
        pass

    def get_listing(self, listing_id: int) -> Listing:
        # TODO: Retrieve a listing by its primary key
        pass

    def update_listing(self, listing_id: int, data: ListingUpdate) -> Listing:
        # TODO: Partially update listing fields (deadline, status) by ID
        pass

    def delete_listing(self, listing_id: int) -> None:
        # TODO: Delete a single listing by ID
        pass

    def bulk_delete_by_seller(self, seller_id: int) -> int:
        # TODO: Delete all listings for a given seller_id, return count deleted
        pass
