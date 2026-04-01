from typing import Optional

from pydantic import BaseModel


class PlaceBidRequest(BaseModel):
    invoice_token: str
    investor_id: int
    bid_amount: float
    listing_id: int


class BidResponse(BaseModel):
    id: int
    invoice_token: str
    investor_id: int
    bid_amount: float
    status: str

    model_config = {"from_attributes": True}


class TopUpRequest(BaseModel):
    investor_id: int
    amount: float


class TopUpResponse(BaseModel):
    checkout_url: str


class WebhookResponse(BaseModel):
    status: str
