from typing import Literal, Optional

from pydantic import BaseModel


class CheckoutRequest(BaseModel):
    amount: float  # in SGD
    user_id: int
    type: Literal["wallet_topup", "loan_repayment"]
    loan_id: Optional[str] = None  # only for loan_repayment


class CheckoutResponse(BaseModel):
    url: str  # Stripe hosted checkout URL
    session_id: str
