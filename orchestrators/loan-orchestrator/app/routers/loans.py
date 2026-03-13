from fastapi import APIRouter, HTTPException

from app.schemas.requests import (
    RepayLoanRequest,
    ConfirmRepaymentRequest,
    RepaymentResponse,
    CheckoutUrlResponse,
)

router = APIRouter()


@router.post(
    "/api/loans/{loan_id}/repay",
    response_model=CheckoutUrlResponse,
    tags=["Repayment"],
    summary="Initiate loan repayment via Stripe",
    description="Gets loan details via gRPC, creates Stripe checkout session via Stripe Wrapper.",
)
async def repay_loan(loan_id: int, data: RepayLoanRequest):
    """
    Initiate loan repayment — create Stripe checkout session.

    See BUILD_INSTRUCTIONS_V2.md Section 10 — LoanOrchestrator.initiate_repayment()
    """
    # TODO: Implement — instantiate LoanOrchestrator and call initiate_repayment()
    raise HTTPException(501, "Not implemented yet")


@router.post(
    "/api/loans/{loan_id}/confirm-repayment",
    response_model=RepaymentResponse,
    tags=["Repayment"],
    summary="Confirm loan repayment after Stripe payment",
    description="Updates loan status to REPAID via gRPC, publishes loan.repaid event.",
)
async def confirm_repayment(loan_id: int, data: ConfirmRepaymentRequest):
    """
    Confirm repayment — update loan status and publish loan.repaid.

    See BUILD_INSTRUCTIONS_V2.md Section 10 — LoanOrchestrator.confirm_repayment()
    """
    # TODO: Implement — instantiate LoanOrchestrator and call confirm_repayment()
    raise HTTPException(501, "Not implemented yet")
