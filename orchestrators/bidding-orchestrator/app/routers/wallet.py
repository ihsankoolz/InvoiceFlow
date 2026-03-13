from fastapi import APIRouter, HTTPException

from app.schemas.requests import TopUpRequest, TopUpResponse

router = APIRouter()


@router.post(
    "/api/wallet/topup",
    response_model=TopUpResponse,
    tags=["Wallet"],
    summary="Create Stripe checkout session for wallet top-up",
    description="Creates a Stripe checkout session via Stripe Wrapper for investor wallet top-up.",
)
async def topup_wallet(data: TopUpRequest):
    """
    Create Stripe checkout session for wallet top-up.

    See BUILD_INSTRUCTIONS_V2.md Section 9 — WalletOrchestrator.create_topup()
    """
    # TODO: Implement — instantiate WalletOrchestrator and call create_topup()
    raise HTTPException(501, "Not implemented yet")
