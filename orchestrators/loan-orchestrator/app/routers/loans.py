from fastapi import APIRouter

from app.schemas.requests import (
    RepayLoanRequest,
    ConfirmRepaymentRequest,
    RepaymentResponse,
    CheckoutUrlResponse,
)
from app.services.loan_orchestrator import LoanOrchestrator

router = APIRouter()


@router.post(
    "/api/loans/{loan_id}/repay",
    response_model=CheckoutUrlResponse,
    tags=["Repayment"],
    summary="Initiate loan repayment via Stripe",
    description="Gets loan details via gRPC, creates Stripe checkout session via Stripe Wrapper.",
)
async def repay_loan(loan_id: int, data: RepayLoanRequest):
    orchestrator = LoanOrchestrator()
    return await orchestrator.initiate_repayment(loan_id, data)


@router.post(
    "/api/loans/{loan_id}/confirm-repayment",
    response_model=RepaymentResponse,
    tags=["Repayment"],
    summary="Confirm loan repayment after Stripe payment",
    description="Updates loan status to REPAID via gRPC, publishes loan.repaid event.",
)
async def confirm_repayment(loan_id: int, data: ConfirmRepaymentRequest):
    orchestrator = LoanOrchestrator()
    return await orchestrator.confirm_repayment(loan_id, data.stripe_session_id)
