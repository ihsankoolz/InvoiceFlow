from typing import Optional

from fastapi import APIRouter, Query

from app import config
from app.services.http_client import HTTPClient

router = APIRouter()

_http = HTTPClient()


@router.get("/api/listings", tags=["Listings"], summary="Get marketplace listings with full details")
async def get_listings(
    urgency_level: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """
    Aggregates listing data from:
    - Marketplace Service (listing details, minimum_bid)
    - Invoice Service (face_value, debtor_name, invoice_id)
    - Bidding Service (current_bid, bid_count)
    """
    # Fetch active listings from marketplace service
    params = {"status": "ACTIVE"}
    if urgency_level and urgency_level != "ALL":
        params["urgency_level"] = urgency_level

    listings = await _http.get(f"{config.MARKETPLACE_SERVICE_URL}/listings/", params=params)
    if not isinstance(listings, list):
        listings = []

    results = []
    for listing in listings:
        invoice_token = listing.get("invoice_token")

        # Fetch invoice data (face_value, debtor_name, invoice_id)
        try:
            invoice = await _http.get(f"{config.INVOICE_SERVICE_URL}/invoices/{invoice_token}")
            face_value = float(invoice.get("amount", 0))
            debtor_name = invoice.get("debtor_name")
            invoice_id = invoice.get("id")
        except Exception:
            face_value = float(listing.get("amount", 0))
            debtor_name = None
            invoice_id = None

        # Fetch bids (current_bid, bid_count)
        try:
            bids = await _http.get(
                f"{config.BIDDING_SERVICE_URL}/bids",
                params={"invoice_token": invoice_token},
            )
            if not isinstance(bids, list):
                bids = []
            pending_bids = [b for b in bids if b.get("status") == "PENDING"]
            bid_count = len(bids)
            current_bid = max((float(b["bid_amount"]) for b in pending_bids), default=None)
        except Exception:
            bid_count = 0
            current_bid = None

        # Apply search filter client-side (by token or debtor name)
        if search:
            s = search.lower()
            token_match = s in (invoice_token or "").lower()
            name_match = s in (debtor_name or "").lower()
            uen_match = s in (listing.get("debtor_uen") or "").lower()
            if not (token_match or name_match or uen_match):
                continue

        results.append({
            "id": listing.get("id"),
            "invoice_token": invoice_token,
            "invoice_id": invoice_id,
            "seller_id": listing.get("seller_id"),
            "face_value": face_value,
            "minimum_bid": float(listing.get("minimum_bid", 0)),
            "current_bid": current_bid,
            "bid_count": bid_count,
            "urgency_level": listing.get("urgency_level"),
            "deadline": listing.get("deadline"),
            "debtor_name": debtor_name,
            "debtor_uen": listing.get("debtor_uen"),
            "status": listing.get("status"),
            "created_at": listing.get("created_at"),
        })

    return results


@router.get("/api/listings/{listing_id}", tags=["Listings"], summary="Get a single listing with full details")
async def get_listing(listing_id: int):
    """
    Aggregates single listing data from:
    - Marketplace Service (listing details, minimum_bid)
    - Invoice Service (face_value, debtor_name)
    - Bidding Service (current_bid, bid_count)
    """
    listing = await _http.get(f"{config.MARKETPLACE_SERVICE_URL}/listings/{listing_id}")
    if not listing or listing.get("detail") == "Listing not found":
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Listing not found")

    invoice_token = listing.get("invoice_token")

    try:
        invoice = await _http.get(f"{config.INVOICE_SERVICE_URL}/invoices/{invoice_token}")
        face_value = float(invoice.get("amount", 0))
        debtor_name = invoice.get("debtor_name")
        invoice_id = invoice.get("id")
    except Exception:
        face_value = float(listing.get("amount", 0))
        debtor_name = None
        invoice_id = None

    try:
        bids = await _http.get(
            f"{config.BIDDING_SERVICE_URL}/bids",
            params={"invoice_token": invoice_token},
        )
        if not isinstance(bids, list):
            bids = []
        pending_bids = [b for b in bids if b.get("status") == "PENDING"]
        bid_count = len(bids)
        current_bid = max((float(b["bid_amount"]) for b in pending_bids), default=None)
    except Exception:
        bid_count = 0
        current_bid = None

    return {
        "id": listing.get("id"),
        "invoice_token": invoice_token,
        "invoice_id": invoice_id,
        "seller_id": listing.get("seller_id"),
        "face_value": face_value,
        "minimum_bid": float(listing.get("minimum_bid", 0)),
        "current_bid": current_bid,
        "bid_count": bid_count,
        "urgency_level": listing.get("urgency_level"),
        "deadline": listing.get("deadline"),
        "debtor_name": debtor_name,
        "debtor_uen": listing.get("debtor_uen"),
        "status": listing.get("status"),
        "created_at": listing.get("created_at"),
    }
