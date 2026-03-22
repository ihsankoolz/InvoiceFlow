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

    See BUILD_INSTRUCTIONS_V2.md Section 12 — StripeService
    """
    service = StripeService()
    return service.create_checkout_session(data)
