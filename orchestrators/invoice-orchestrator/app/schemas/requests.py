from datetime import date

from pydantic import BaseModel


class ListInvoiceRequest(BaseModel):
    seller_id: int
    debtor_uen: str
    amount: float
    due_date: date
    bid_period_hours: float = 48


class ListInvoiceResponse(BaseModel):
    invoice_token: str
    listing_id: int
    status: str
    message: str
