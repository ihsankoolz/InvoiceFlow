"""
BidOrchestrator — orchestrates bid placement with escrow locking.

Flow (5 steps):
  1. Create bid in Bidding Service → get bid + previous_highest
  2. Lock escrow via gRPC — rollback bid if this fails
  3. If someone was outbid → publish bid.outbid (choreography releases their escrow)
  4. Check anti-snipe — if auction within final 5 min, signal Temporal + extend deadline
  5. Publish bid.placed
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from app import config
from app.schemas.requests import PlaceBidRequest
from app.services.grpc_client import PaymentGRPCClient
from app.services.http_client import HTTPClient
from app.services.rabbitmq_publisher import RabbitMQPublisher
from app.temporal.client import TemporalClient

ANTI_SNIPE_WINDOW = timedelta(minutes=5)


class BidOrchestrator:
    """Orchestrates Scenario 2: bid placement with escrow locking, outbid handling, anti-snipe."""

    def __init__(self):
        self.http_client = HTTPClient()
        self.grpc_client = PaymentGRPCClient()
        self.publisher = RabbitMQPublisher(config.RABBITMQ_URL)
        self.temporal_client = TemporalClient()

    async def place_bid(self, data: PlaceBidRequest) -> dict:
        """Orchestrate bid placement end-to-end."""

        # ── Step 1: Create bid in Bidding Service ──────────────────────────
        result = await self.http_client.post(
            f"{config.BIDDING_SERVICE_URL}/bids",
            json={
                "invoice_token": data.invoice_token,
                "investor_id": data.investor_id,
                "bid_amount": data.bid_amount,
            },
        )
        bid = result["bid"]
        previous_highest = result.get("previous_highest")

        # ── Step 2: Lock escrow via gRPC ───────────────────────────────────
        try:
            await self.grpc_client.lock_escrow(
                investor_id=data.investor_id,
                invoice_token=data.invoice_token,
                amount=data.bid_amount,
                idempotency_key=f"escrow-{bid['id']}",
            )
        except Exception as e:
            # Rollback: remove the orphaned bid so Bidding Service stays consistent
            try:
                await self.http_client.delete(
                    f"{config.BIDDING_SERVICE_URL}/bids/{bid['id']}"
                )
            except Exception:
                pass  # best-effort rollback; log in production
            raise HTTPException(
                status_code=400,
                detail=f"Escrow lock failed (insufficient balance?): {str(e)}",
            )

        # ── Step 3: Outbid choreography ────────────────────────────────────
        if previous_highest:
            await self.publisher.publish(
                "bid.outbid",
                {
                    "invoice_token": data.invoice_token,
                    "outbid_investor_id": previous_highest["investor_id"],
                    "outbid_amount": str(previous_highest["bid_amount"]),
                    "new_highest_investor_id": data.investor_id,
                    "new_highest_amount": str(data.bid_amount),
                },
            )

        # ── Step 4: Anti-snipe check ───────────────────────────────────────
        listing = await self.http_client.get(
            f"{config.MARKETPLACE_SERVICE_URL}/listings/{data.listing_id}"
        )
        # Marketplace returns deadline as ISO string; parse it
        deadline_str: str = listing["deadline"]
        deadline = datetime.fromisoformat(deadline_str.replace("Z", "+00:00"))
        now = datetime.now(tz=timezone.utc)

        if deadline - now <= ANTI_SNIPE_WINDOW:
            new_deadline = now + ANTI_SNIPE_WINDOW
            new_deadline_iso = new_deadline.isoformat()

            # Signal AuctionCloseWorkflow to reset its 5-min timer
            try:
                await self.temporal_client.signal_workflow(
                    workflow_id=f"auction-{data.invoice_token}",
                    signal_name="extend_deadline",
                )
            except Exception:
                pass  # Temporal may not be up in dev; don't fail the bid

            # Update the displayed deadline in Marketplace
            await self.http_client.patch(
                f"{config.MARKETPLACE_SERVICE_URL}/listings/{data.listing_id}",
                json={"deadline": new_deadline_iso},
            )

            await self.publisher.publish(
                "auction.extended",
                {
                    "invoice_token": data.invoice_token,
                    "new_deadline": new_deadline_iso,
                },
            )

        # ── Step 5: Publish bid.placed ─────────────────────────────────────
        await self.publisher.publish(
            "bid.placed",
            {
                "invoice_token": data.invoice_token,
                "investor_id": data.investor_id,
                "bid_amount": str(data.bid_amount),
            },
        )

        return bid
