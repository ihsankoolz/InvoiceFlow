"""
Marketplace event consumer.

Listens for domain events on RabbitMQ and keeps the marketplace listings
read model up-to-date without N+1 HTTP calls.

Events handled:
  invoice.listed    — listing already created via REST; acknowledged, no action needed
  bid.placed        — updates current_bid and bid_count (columns added in Section 5 migration;
                       assignments are silently ignored by SQLAlchemy until columns exist)
  auction.closed.*  — sets listing status to CLOSED
  auction.extended  — updates listing deadline to the new extended deadline
"""

import logging
from datetime import datetime
from typing import Any

from app import config
from app.database import SessionLocal
from app.models.listing import Listing

logger = logging.getLogger(__name__)

from shared.consumer import BaseConsumer  # noqa: E402

QUEUE_NAME = "marketplace_events"
ROUTING_KEYS = [
    "invoice.listed",
    "bid.placed",
    "auction.closed.*",
    "auction.extended",
]


class MarketplaceEventConsumer(BaseConsumer):
    def __init__(self):
        super().__init__(
            rabbitmq_url=config.RABBITMQ_URL,
            queue_name=QUEUE_NAME,
            routing_keys=ROUTING_KEYS,
        )

    async def handle(self, routing_key: str, body: dict[str, Any]) -> None:
        if routing_key == "invoice.listed":
            # Listing is created synchronously via REST in InvoiceOrchestrator.
            # Nothing to do here — just acknowledge.
            logger.debug("invoice.listed acknowledged for %s", body.get("invoice_token"))

        elif routing_key == "bid.placed":
            await self._on_bid_placed(body)

        elif routing_key.startswith("auction.closed"):
            await self._on_auction_closed(body)

        elif routing_key == "auction.extended":
            await self._on_auction_extended(body)

    async def _on_bid_placed(self, body: dict[str, Any]) -> None:
        invoice_token = body.get("invoice_token")
        bid_amount = body.get("bid_amount")
        if not invoice_token:
            return

        with SessionLocal() as db:
            listing = db.query(Listing).filter(Listing.invoice_token == invoice_token).first()
            if not listing:
                logger.warning("bid.placed: listing not found for token %s", invoice_token)
                return

            # current_bid and bid_count are read-model columns added in Section 5.
            # SQLAlchemy silently ignores assignments to unmapped attributes, so
            # this code is safe to commit before the migration runs.
            if bid_amount is not None:
                listing.current_bid = float(bid_amount)
            existing_count = getattr(listing, "bid_count", None) or 0
            listing.bid_count = existing_count + 1
            db.commit()
            logger.debug(
                "bid.placed: updated listing %s bid_count=%s current_bid=%s",
                invoice_token,
                listing.bid_count,
                bid_amount,
            )

    async def _on_auction_closed(self, body: dict[str, Any]) -> None:
        invoice_token = body.get("invoice_token")
        if not invoice_token:
            return

        with SessionLocal() as db:
            listing = db.query(Listing).filter(Listing.invoice_token == invoice_token).first()
            if not listing:
                logger.warning("auction.closed: listing not found for token %s", invoice_token)
                return
            listing.status = "CLOSED"
            db.commit()
            logger.info("auction.closed: listing %s marked CLOSED", invoice_token)

    async def _on_auction_extended(self, body: dict[str, Any]) -> None:
        invoice_token = body.get("invoice_token")
        new_deadline_str = body.get("new_deadline")
        if not invoice_token or not new_deadline_str:
            return

        try:
            new_deadline = datetime.fromisoformat(new_deadline_str.replace("Z", "+00:00"))
        except ValueError:
            logger.error("auction.extended: invalid deadline format '%s'", new_deadline_str)
            return

        with SessionLocal() as db:
            listing = db.query(Listing).filter(Listing.invoice_token == invoice_token).first()
            if not listing:
                logger.warning("auction.extended: listing not found for token %s", invoice_token)
                return
            listing.deadline = new_deadline
            db.commit()
            logger.info(
                "auction.extended: listing %s deadline updated to %s", invoice_token, new_deadline
            )
