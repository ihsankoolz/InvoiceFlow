"""
WalletOrchestrator — orchestrates wallet top-up via Stripe.

See BUILD_INSTRUCTIONS_V2.md Section 9 — WalletOrchestrator
"""

from app import config
from app.schemas.requests import TopUpRequest
from app.services.http_client import HTTPClient


class WalletOrchestrator:
    """Creates Stripe checkout sessions for wallet top-up."""

    def __init__(self):
        self.http_client = HTTPClient()

    async def create_topup(self, data: TopUpRequest) -> dict:
        """
        Create Stripe checkout session for wallet top-up.

        Steps:
        1. Call Stripe Wrapper POST /create-checkout-session with amount, user_id, type=wallet_topup
        2. Return { checkout_url: session.url }

        See BUILD_INSTRUCTIONS_V2.md Section 9 — WalletOrchestrator.create_topup()
        """
        # TODO: Implement
        pass
