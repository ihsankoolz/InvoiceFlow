from pydantic import BaseModel


class RepayLoanRequest(BaseModel):
    seller_id: int


class ConfirmRepaymentRequest(BaseModel):
    stripe_session_id: str


class RepaymentResponse(BaseModel):
    status: str
    loan_id: str


class CheckoutUrlResponse(BaseModel):
    checkout_url: str
