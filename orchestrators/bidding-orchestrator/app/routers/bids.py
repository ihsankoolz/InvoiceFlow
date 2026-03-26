from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app import config
from app.schemas.requests import BidResponse, PlaceBidRequest
from app.services.bid_orchestrator import BidOrchestrator
from app.services.http_client import HTTPClient

router = APIRouter()

_http = HTTPClient()


@router.get(
    "/api/bids",
    tags=["Bidding"],
    summary="List bids by investor or invoice",
    description="Returns bids filtered by investor_id or invoice_token.",
)
async def list_bids(
    investor_id: Optional[int] = Query(None),
    invoice_token: Optional[str] = Query(None),
):
    if investor_id is None and invoice_token is None:
        raise HTTPException(status_code=400, detail="Provide investor_id or invoice_token")
    params = {}
    if investor_id is not None:
        params["investor_id"] = investor_id
    else:
        params["invoice_token"] = invoice_token
    return await _http.get(f"{config.BIDDING_SERVICE_URL}/bids", params=params)


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
