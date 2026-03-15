from typing import List, Optional

from strawberry.dataloader import DataLoader

from app.database import SessionLocal
from app.models.listing import Listing


async def load_listings_by_ids(keys: List[int]) -> List[Optional[Listing]]:
    db = SessionLocal()
    try:
        listings = db.query(Listing).filter(Listing.id.in_(keys)).all()
        listing_map = {listing.id: listing for listing in listings}
        return [listing_map.get(key) for key in keys]
    finally:
        db.close()


listing_loader = DataLoader(load_fn=load_listings_by_ids)
