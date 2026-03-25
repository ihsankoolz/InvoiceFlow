from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app import config
from app.schemas.requests import (
    RepayLoanRequest,
    ConfirmRepaymentRequest,
    RepaymentResponse,
    CheckoutUrlResponse,
)
from app.services.http_client import HTTPClient
from app.services.loan_orchestrator import LoanOrchestrator

router = APIRouter()

_http = HTTPClient()


@router.get(
    "/api/loans",
    tags=["Loans"],
    summary="List loans by investor or seller",
    description="Returns loans filtered by investor_id or seller_id.",
)
async def list_loans(
    investor_id: Optional[int] = Query(None),
    seller_id: Optional[int] = Query(None),
):
    if investor_id is None and seller_id is None:
        raise HTTPException(status_code=400, detail="Provide investor_id or seller_id")
    params = {}
    if seller_id is not None:
        params["seller_id"] = seller_id
    else:
        params["investor_id"] = investor_id
    return await _http.get(f"{config.PAYMENT_SERVICE_URL}/loans", params=params)


@router.post(
    "/api/loans/{loan_id}/repay",
    response_model=CheckoutUrlResponse,
    tags=["Repayment"],
    summary="Initiate loan repayment via Stripe",
    description="Gets loan details via gRPC, creates Stripe checkout session via Stripe Wrapper.",
)
async def repay_loan(loan_id: str, data: RepayLoanRequest):
    orchestrator = LoanOrchestrator()
    return await orchestrator.initiate_repayment(loan_id, data)


@router.post(
    "/api/loans/{loan_id}/confirm-repayment",
    response_model=RepaymentResponse,
    tags=["Repayment"],
    summary="Confirm loan repayment after Stripe payment",
    description="Updates loan status to REPAID via gRPC, publishes loan.repaid event.",
)
async def confirm_repayment(loan_id: str, data: ConfirmRepaymentRequest):
    orchestrator = LoanOrchestrator()
    return await orchestrator.confirm_repayment(loan_id, data.stripe_session_id)
