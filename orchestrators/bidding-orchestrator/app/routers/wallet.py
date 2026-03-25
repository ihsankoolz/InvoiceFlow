from fastapi import APIRouter, Query

from app import config
from app.schemas.requests import TopUpRequest, TopUpResponse
from app.services.http_client import HTTPClient
from app.services.wallet_orchestrator import WalletOrchestrator

router = APIRouter()

_http = HTTPClient()


@router.get(
    "/api/wallet/balance",
    tags=["Wallet"],
    summary="Get wallet balance for a user",
    description="Returns the current wallet balance for the given user_id.",
)
async def get_wallet_balance(user_id: int = Query(..., description="User ID")):
    return await _http.get(f"{config.PAYMENT_SERVICE_URL}/wallets/{user_id}")


@router.get(
    "/api/wallet/transactions",
    tags=["Wallet"],
    summary="Get wallet transaction history for a user",
    description="Returns all wallet credit/debit transactions for the given user_id.",
)
async def get_wallet_transactions(user_id: int = Query(..., description="User ID")):
    return await _http.get(
        f"{config.PAYMENT_SERVICE_URL}/transactions",
        params={"user_id": user_id},
    )


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
