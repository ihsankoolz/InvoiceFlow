from typing import List

from strawberry.dataloader import DataLoader
from sqlalchemy.orm import Session

from app.models.listing import Listing


async def load_listings_by_ids(keys: List[int]) -> List[Listing]:
    # TODO: Batch-load listings by a list of IDs to prevent N+1 queries
    pass


listing_loader = DataLoader(load_fn=load_listings_by_ids)
