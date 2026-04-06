"""
BidOrchestrator — orchestrates bid placement with escrow locking.

Flow (5 steps):
  1. Create bid in Bidding Service → get bid + previous_highest
  2. Lock escrow via gRPC — rollback bid if this fails
  3. If someone was outbid → release their escrow via gRPC, mark bid OUTBID, publish bid.outbid
  4. Check anti-snipe — if auction within ANTI_SNIPE_WINDOW, signal Temporal + extend deadline
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

ANTI_SNIPE_WINDOW = timedelta(seconds=config.ANTI_SNIPE_WINDOW_SECONDS)


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
            # Rollback: delete the orphaned bid
            try:
                await self.http_client.delete(
                    f"{config.BIDDING_SERVICE_URL}/bids/{bid['id']}"
                )
            except Exception:
                pass
            # Also release escrow in case payment service deducted funds before erroring
            try:
                await self.grpc_client.release_escrow(
                    investor_id=data.investor_id,
                    invoice_token=data.invoice_token,
                    idempotency_key=f"release-lockfail-{bid['id']}",
                )
            except Exception:
                pass
            error_msg = str(e)
            if "insufficient" in error_msg.lower() or "balance" in error_msg.lower():
                raise HTTPException(
                    status_code=400,
                    detail="Insufficient wallet balance. Please top up your wallet before placing a bid.",
                )
            raise HTTPException(
                status_code=400,
                detail="Could not place bid. Please try again.",
            )

        # ── Steps 3-5: wrapped so any failure releases the just-locked escrow ──
        try:
            # ── Step 3: Outbid handling ────────────────────────────────────────
            if previous_highest:
                outbid_user = await self.http_client.get(
                    f"{config.USER_SERVICE_URL}/users/{previous_highest['investor_id']}"
                )

                # Release the outbid investor's escrow back to their wallet
                try:
                    await self.grpc_client.release_escrow(
                        investor_id=previous_highest["investor_id"],
                        invoice_token=data.invoice_token,
                        idempotency_key=f"release-outbid-{previous_highest['id']}",
                    )
                except Exception:
                    pass  # best-effort; escrow will be released at auction close if this fails

                # Mark the displaced bid as OUTBID
                try:
                    await self.http_client.patch(
                        f"{config.BIDDING_SERVICE_URL}/bids/{previous_highest['id']}/outbid"
                    )
                except Exception:
                    pass  # best-effort

                await self.publisher.publish(
                    "bid.outbid",
                    {
                        "invoice_token": data.invoice_token,
                        "previous_bid_id": previous_highest["id"],
                        "previous_bidder_id": previous_highest["investor_id"],
                        "previous_bidder_email": outbid_user["email"],
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
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
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

                current_offers = await self.http_client.get(
                    f"{config.BIDDING_SERVICE_URL}/bids?invoice_token={data.invoice_token}"
                )
                bidders = []
                for o in current_offers:
                    u = await self.http_client.get(f"{config.USER_SERVICE_URL}/users/{o['investor_id']}")
                    bidders.append({"user_id": o["investor_id"], "email": u["email"]})
                seller_info = await self.http_client.get(
                    f"{config.USER_SERVICE_URL}/users/{listing['seller_id']}"
                )
                await self.publisher.publish(
                    "auction.extended",
                    {
                        "invoice_token": data.invoice_token,
                        "new_deadline": new_deadline_iso,
                        "bidders": bidders,
                        "seller_id": listing["seller_id"],
                        "seller_email": seller_info["email"],
                    },
                )

            # ── Step 5: Publish bid.placed + bid.confirmed ────────────────────
            seller_user = await self.http_client.get(
                f"{config.USER_SERVICE_URL}/users/{listing['seller_id']}"
            )
            investor_user = await self.http_client.get(
                f"{config.USER_SERVICE_URL}/users/{data.investor_id}"
            )
            await self.publisher.publish(
                "bid.placed",
                {
                    "invoice_token": data.invoice_token,
                    "investor_id": data.investor_id,
                    "bid_amount": str(data.bid_amount),
                    "seller_id": listing["seller_id"],
                    "seller_email": seller_user["email"],
                },
            )
            await self.publisher.publish(
                "bid.confirmed",
                {
                    "invoice_token": data.invoice_token,
                    "investor_id": data.investor_id,
                    "investor_email": investor_user["email"],
                    "bid_amount": str(data.bid_amount),
                },
            )

        except Exception as e:
            # Something failed after escrow was locked — release it so funds aren't stranded
            try:
                await self.grpc_client.release_escrow(
                    investor_id=data.investor_id,
                    invoice_token=data.invoice_token,
                    idempotency_key=f"release-failed-{bid['id']}",
                )
            except Exception:
                pass
            # Delete the orphaned bid record
            try:
                await self.http_client.delete(
                    f"{config.BIDDING_SERVICE_URL}/bids/{bid['id']}"
                )
            except Exception:
                pass
            raise HTTPException(status_code=500, detail=f"Bid placement failed: {str(e)}")

        return bid
