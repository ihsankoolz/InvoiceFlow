from fastapi import APIRouter

from app.schemas.checkout import CheckoutRequest, CheckoutResponse
from app.services.stripe_service import StripeService

router = APIRouter()


@router.post(
    "/create-checkout-session",
    response_model=CheckoutResponse,
    tags=["Stripe"],
    summary="Create Stripe Checkout Session",
)
async def create_checkout_session(data: CheckoutRequest):
    """
    Create a Stripe Checkout Session for wallet top-up or loan repayment.

    - type=wallet_topup: called by Bidding Orchestrator at step A4 (Scenario 2A)
    - type=loan_repayment: called by Loan Orchestrator at step B5 (Scenario 3 repayment)

    Returns a checkout_url the frontend redirects the user to.
    The session expires after 30 minutes.
    """
    service = StripeService()
    return service.create_checkout_session(data)
