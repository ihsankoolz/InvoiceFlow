from typing import Optional

import asyncio
import httpx
from fastapi import APIRouter, HTTPException, Query

from app import config
from app.schemas.requests import BidResponse, PlaceBidRequest
from app.services.bid_orchestrator import BidOrchestrator
from app.services.http_client import HTTPClient

router = APIRouter()

_http = HTTPClient()


async def _fetch_listing_by_token(token: str) -> dict | None:
    """Fetch a marketplace listing by invoice_token; returns None on any error."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{config.MARKETPLACE_SERVICE_URL}/listings/by-token/{token}"
            )
            if r.status_code == 200:
                return r.json()
    except Exception:
        pass
    return None


@router.get(
    "/api/bids",
    tags=["Bidding"],
    summary="List bids by investor or invoice",
    description="Returns bids filtered by investor_id or invoice_token, enriched with listing data.",
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

    raw = await _http.get(f"{config.BIDDING_SERVICE_URL}/bids", params=params)
    bids: list = raw if isinstance(raw, list) else raw.get("bids", [])

    # Deduplicate tokens and fetch all listings concurrently
    tokens = list({b["invoice_token"] for b in bids if b.get("invoice_token")})
    listings_list = await asyncio.gather(*[_fetch_listing_by_token(t) for t in tokens])
    listing_map: dict = {t: l for t, l in zip(tokens, listings_list) if l}

    enriched = []
    for bid in bids:
        listing = listing_map.get(bid.get("invoice_token"))
        enriched.append({
            **bid,
            "amount": bid.get("bid_amount"),          # frontend reads bid.amount
            "face_value": listing["amount"] if listing else None,
            "deadline": listing["deadline"] if listing else None,
            "listing_id": listing["id"] if listing else None,
        })

    return enriched


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
