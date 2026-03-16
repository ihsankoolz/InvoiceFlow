from fastapi import APIRouter

from app.schemas.requests import BidResponse, PlaceBidRequest
from app.services.bid_orchestrator import BidOrchestrator

router = APIRouter()


@router.post(
    "/api/bids",
    response_model=BidResponse,
    tags=["Bidding"],
    summary="Place a bid on an invoice listing",
    description=(
        "Orchestrates bid placement: creates bid in Bidding Service, locks escrow "
        "via gRPC, publishes bid.outbid if someone is displaced, checks anti-snipe "
        "window (extends deadline if bid lands in final 5 min), and publishes bid.placed."
    ),
)
async def place_bid(data: PlaceBidRequest):
    orchestrator = BidOrchestrator()
    result = await orchestrator.place_bid(data)
    return result
