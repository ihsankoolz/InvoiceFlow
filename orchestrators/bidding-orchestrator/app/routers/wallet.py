from fastapi import APIRouter

from app.schemas.requests import TopUpRequest, TopUpResponse
from app.services.wallet_orchestrator import WalletOrchestrator

router = APIRouter()


@router.post(
    "/api/wallet/topup",
    response_model=TopUpResponse,
    tags=["Wallet"],
    summary="Create Stripe checkout session for wallet top-up",
    description=(
        "Calls Stripe Wrapper to create a hosted checkout session. "
        "Returns a checkout_url the frontend redirects the investor to. "
        "Wallet is credited after Stripe fires the webhook to /api/webhooks/stripe."
    ),
)
async def topup_wallet(data: TopUpRequest):
    orchestrator = WalletOrchestrator()
    result = await orchestrator.create_topup(data)
    return result
