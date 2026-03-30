"""
GraphQL schema for the Bidding Orchestrator.

Exposes fully enriched listing data by aggregating:
  - Marketplace Service  → listing metadata, minimum_bid, deadline
  - Invoice Service      → face_value, debtor_name
  - Bidding Service      → current_bid, bid_count

This lives in the orchestrator (not the marketplace atomic service) so that
Kong never needs to directly reach an atomic service — consistent with the
rest of the routing architecture.
"""

from typing import List, Optional

import strawberry

from app import config
from app.services.http_client import HTTPClient

_http = HTTPClient()


@strawberry.type
class ListingType:
    id: int
    invoice_token: str
    seller_id: int
    face_value: float
    minimum_bid: float
    current_bid: Optional[float]
    bid_count: int
    urgency_level: str
    deadline: Optional[str]
    debtor_name: Optional[str]
    debtor_uen: Optional[str]
    status: str
    created_at: Optional[str]


async def _enrich(listing: dict) -> ListingType:
    invoice_token = listing.get("invoice_token")

    try:
        invoice = await _http.get(f"{config.INVOICE_SERVICE_URL}/invoices/{invoice_token}")
        face_value = float(invoice.get("amount", 0))
        debtor_name = invoice.get("debtor_name")
    except Exception:
        face_value = float(listing.get("amount", 0))
        debtor_name = None

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

    return ListingType(
        id=listing.get("id"),
        invoice_token=invoice_token,
        seller_id=listing.get("seller_id"),
        face_value=face_value,
        minimum_bid=float(listing.get("minimum_bid", 0)),
        current_bid=current_bid,
        bid_count=bid_count,
        urgency_level=listing.get("urgency_level", ""),
        deadline=listing.get("deadline"),
        debtor_name=debtor_name,
        debtor_uen=listing.get("debtor_uen"),
        status=listing.get("status", ""),
        created_at=listing.get("created_at"),
    )


@strawberry.type
class Query:
    @strawberry.field
    async def listings(
        self,
        urgency_level: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[ListingType]:
        params = {"status": "ACTIVE"}
        if urgency_level and urgency_level != "ALL":
            params["urgency_level"] = urgency_level

        raw = await _http.get(
            f"{config.MARKETPLACE_SERVICE_URL}/listings/",
            params=params,
        )
        if not isinstance(raw, list):
            raw = []

        results = []
        for listing in raw:
            enriched = await _enrich(listing)
            if search:
                s = search.lower()
                if not (
                    s in (enriched.invoice_token or "").lower()
                    or s in (enriched.debtor_name or "").lower()
                    or s in (enriched.debtor_uen or "").lower()
                ):
                    continue
            results.append(enriched)

        return results

    @strawberry.field
    async def listing(self, id: int) -> Optional[ListingType]:
        try:
            raw = await _http.get(f"{config.MARKETPLACE_SERVICE_URL}/listings/{id}")
        except Exception:
            return None
        if not raw:
            return None
        return await _enrich(raw)


schema = strawberry.Schema(query=Query)
