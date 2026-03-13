"""
StripeService — wraps Stripe API for creating checkout sessions.

See BUILD_INSTRUCTIONS_V2.md Section 12 — Key Classes
"""

from app import config
from app.schemas.checkout import CheckoutRequest, CheckoutResponse


class StripeService:
    """Creates Stripe Checkout Sessions for wallet top-up and loan repayment."""

    def create_checkout_session(self, data: CheckoutRequest) -> CheckoutResponse:
        """
        Create a Stripe Checkout Session.

        Steps:
        1. Import stripe, set stripe.api_key = config.STRIPE_SECRET_KEY
        2. Build line_items from data.amount (convert to cents)
        3. Set metadata: { user_id, type, loan_id (if applicable) }
        4. Call stripe.checkout.Session.create(
               mode="payment",
               line_items=[...],
               success_url=config.STRIPE_SUCCESS_URL,
               cancel_url=config.STRIPE_CANCEL_URL,
               metadata={...},
           )
        5. Return CheckoutResponse(url=session.url, session_id=session.id)

        See BUILD_INSTRUCTIONS_V2.md Section 12 — StripeService
        """
        # TODO: Implement
        pass
