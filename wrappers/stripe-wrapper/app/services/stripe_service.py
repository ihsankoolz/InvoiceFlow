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
        import stripe

        stripe.api_key = config.STRIPE_SECRET_KEY

        product_name = "Wallet Top-Up" if data.type == "wallet_topup" else "Loan Repayment"

        metadata = {
            "user_id": str(data.user_id),
            "type": data.type,
        }
        if data.loan_id:
            metadata["loan_id"] = data.loan_id

        # Append ?type= so the success/cancel pages know which flow completed
        sep = "&" if "?" in config.STRIPE_SUCCESS_URL else "?"
        success_url = f"{config.STRIPE_SUCCESS_URL}{sep}type={data.type}"
        cancel_sep = "&" if "?" in config.STRIPE_CANCEL_URL else "?"
        cancel_url = f"{config.STRIPE_CANCEL_URL}{cancel_sep}type={data.type}"

        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "sgd",
                        "unit_amount": int(data.amount * 100),
                        "product_data": {"name": product_name},
                    },
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata=metadata,
        )

        return CheckoutResponse(url=session.url, session_id=session.id)
