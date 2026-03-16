"""
WalletOrchestrator — orchestrates wallet top-up via Stripe.

Creates a Stripe checkout session through the Stripe Wrapper.
Actual wallet crediting happens after Stripe webhook fires (webhooks.py).
"""

from app import config
from app.schemas.requests import TopUpRequest
from app.services.http_client import HTTPClient


class WalletOrchestrator:
    """Creates Stripe checkout sessions for investor wallet top-up."""

    def __init__(self):
        self.http_client = HTTPClient()

    async def create_topup(self, data: TopUpRequest) -> dict:
        """
        Create a Stripe checkout session for wallet top-up.

        Calls Stripe Wrapper POST /create-checkout-session.
        Returns { checkout_url } for the frontend to redirect to.
        """
        session = await self.http_client.post(
            f"{config.STRIPE_WRAPPER_URL}/create-checkout-session",
            json={
                "amount": data.amount,
                "user_id": data.investor_id,
                "type": "wallet_topup",
            },
        )
        return {"checkout_url": session["url"]}
