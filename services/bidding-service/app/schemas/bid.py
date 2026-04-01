from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel


class BidCreate(BaseModel):
    invoice_token: str
    investor_id: int
    bid_amount: float


class BidResponse(BaseModel):
    id: int
    invoice_token: str
    investor_id: int
    bid_amount: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class BidCreateResponse(BaseModel):
    bid: BidResponse
    previous_highest: Optional[BidResponse] = None


class BidStatusUpdate(BaseModel):
    status: Literal["PENDING", "ACCEPTED", "REJECTED", "CANCELLED", "OUTBID"]
