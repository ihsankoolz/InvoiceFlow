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


async def _fetch_all_bids_for_invoice(token: str) -> list:
    """Fetch all PENDING bids for an invoice to determine highest bidder."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(
                f"{config.BIDDING_SERVICE_URL}/bids",
                params={"invoice_token": token},
            )
            if r.status_code == 200:
                data = r.json()
                return data if isinstance(data, list) else data.get("bids", [])
    except Exception:
        pass
    return []


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

    # Deduplicate tokens and fetch listings + all bids per invoice concurrently
    tokens = list({b["invoice_token"] for b in bids if b.get("invoice_token")})
    listings_list, all_bids_list = await asyncio.gather(
        asyncio.gather(*[_fetch_listing_by_token(t) for t in tokens]),
        asyncio.gather(*[_fetch_all_bids_for_invoice(t) for t in tokens]),
    )
    listing_map: dict = {t: l for t, l in zip(tokens, listings_list) if l}

    # Build a map of invoice_token → highest bid_amount among all PENDING bids
    highest_map: dict = {}
    for token, invoice_bids in zip(tokens, all_bids_list):
        pending = [b for b in invoice_bids if b.get("status") == "PENDING"]
        if pending:
            highest_map[token] = max(float(b.get("bid_amount", 0)) for b in pending)

    enriched = []
    for bid in bids:
        token = bid.get("invoice_token")
        listing = listing_map.get(token)
        my_amount = float(bid.get("bid_amount") or 0)
        highest = highest_map.get(token, my_amount)
        is_leading = bid.get("status") == "PENDING" and my_amount >= highest
        enriched.append({
            **bid,
            "amount": bid.get("bid_amount"),
            "face_value": listing["amount"] if listing else None,
            "deadline": listing["deadline"] if listing else None,
            "listing_id": listing["id"] if listing else None,
            "is_leading": is_leading,
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
