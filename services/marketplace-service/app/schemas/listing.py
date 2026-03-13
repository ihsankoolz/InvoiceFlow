from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class ListingCreate(BaseModel):
    invoice_token: str
    seller_id: int
    debtor_uen: str
    amount: float
    urgency_level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    deadline: datetime


class ListingResponse(BaseModel):
    id: int
    invoice_token: str
    seller_id: int
    debtor_uen: str
    amount: float
    urgency_level: str
    deadline: datetime
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ListingUpdate(BaseModel):
    deadline: Optional[datetime] = None
    status: Optional[Literal["ACTIVE", "CLOSED", "EXPIRED"]] = None
