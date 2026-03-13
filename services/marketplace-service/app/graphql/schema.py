from datetime import datetime
from typing import List, Optional

import strawberry
from strawberry.types import Info

from app.database import SessionLocal
from app.models.listing import Listing as ListingModel


@strawberry.type
class ListingType:
    id: int
    invoice_token: str
    seller_id: int
    debtor_uen: str
    amount: float
    urgency_level: str
    deadline: datetime
    status: str
    created_at: datetime


def _model_to_type(listing: ListingModel) -> ListingType:
    return ListingType(
        id=listing.id,
        invoice_token=listing.invoice_token,
        seller_id=listing.seller_id,
        debtor_uen=listing.debtor_uen,
        amount=float(listing.amount),
        urgency_level=listing.urgency_level,
        deadline=listing.deadline,
        status=listing.status,
        created_at=listing.created_at,
    )


@strawberry.type
class Query:
    @strawberry.field
    def listings(
        self,
        urgency_level: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        status: Optional[str] = "ACTIVE",
    ) -> List[ListingType]:
        db = SessionLocal()
        try:
            query = db.query(ListingModel)
            if status is not None:
                query = query.filter(ListingModel.status == status)
            if urgency_level is not None:
                query = query.filter(ListingModel.urgency_level == urgency_level)
            if min_amount is not None:
                query = query.filter(ListingModel.amount >= min_amount)
            if max_amount is not None:
                query = query.filter(ListingModel.amount <= max_amount)
            results = query.all()
            return [_model_to_type(r) for r in results]
        finally:
            db.close()

    @strawberry.field
    def listing(self, id: int) -> Optional[ListingType]:
        db = SessionLocal()
        try:
            result = db.query(ListingModel).filter(ListingModel.id == id).first()
            if result is None:
                return None
            return _model_to_type(result)
        finally:
            db.close()


schema = strawberry.Schema(query=Query)
