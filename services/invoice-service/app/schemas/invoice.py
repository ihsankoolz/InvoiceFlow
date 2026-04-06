from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel


class InvoiceCreate(BaseModel):
    seller_id: int
    seller_name: Optional[str] = None
    debtor_name: Optional[str] = None
    debtor_uen: str
    amount: float
    due_date: datetime


class InvoiceResponse(BaseModel):
    id: int
    invoice_token: str
    seller_id: int
    debtor_name: Optional[str]
    debtor_uen: str
    amount: float
    due_date: datetime
    currency: str
    pdf_url: Optional[str]
    status: str
    extracted_data: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceStatusUpdate(BaseModel):
    status: Literal["DRAFT", "LISTED", "FINANCED", "REPAID", "DEFAULTED", "REJECTED", "EXPIRED", "DELISTED"]
