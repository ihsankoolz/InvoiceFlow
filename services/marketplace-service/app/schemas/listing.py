from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ListingCreate(BaseModel):
    invoice_token: str
    seller_id: int
    debtor_uen: str
    amount: float
    minimum_bid: float
    urgency_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    deadline: datetime
    # Read-model fields — optional at creation, populated from invoice data
    face_value: Optional[float] = None
    debtor_name: Optional[str] = None


class ListingResponse(BaseModel):
    id: int
    invoice_token: str
    seller_id: int
    debtor_uen: str
    amount: float
    minimum_bid: float
    urgency_level: str
    deadline: datetime
    status: str
    face_value: Optional[float] = None
    debtor_name: Optional[str] = None
    current_bid: Optional[float] = None
    bid_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class ListingUpdate(BaseModel):
    deadline: Optional[datetime] = None
    status: Optional[Literal["ACTIVE", "CLOSED", "EXPIRED"]] = None
    current_bid: Optional[float] = None
    bid_count: Optional[int] = None
