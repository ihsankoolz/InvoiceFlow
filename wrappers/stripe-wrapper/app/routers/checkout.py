from fastapi import APIRouter, HTTPException

from app.schemas.checkout import CheckoutRequest, CheckoutResponse

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
    # TODO: Implement — instantiate StripeService and call create_checkout_session()
    raise HTTPException(501, "Not implemented yet")
