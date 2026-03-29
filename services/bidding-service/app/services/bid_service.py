from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.bid import Bid
from app.schemas.bid import BidCreate


class BidService:

    def __init__(self, db: Session):
        self.db = db

    def create_bid(self, data: BidCreate) -> dict:
        """Insert bid, check highest, return {"bid": Bid, "previous_highest": Bid|None}.

        Steps:
            1. Reject if investor already has a bid for this invoice (409).
            2. Find the current highest PENDING bid before inserting.
            3. Insert the new bid.
            4. If the new bid is the highest, the current highest becomes previous_highest.
        """
        existing = (
            self.db.query(Bid)
            .filter(
                Bid.invoice_token == data.invoice_token,
                Bid.investor_id == data.investor_id,
            )
            .first()
        )
        if existing:
            if existing.status == "PENDING":
                raise HTTPException(status_code=409, detail="Investor already has a bid for this invoice")
            # Stale CANCELLED record (from a previous failed escrow) — remove it
            # so the unique constraint doesn't block the retry.
            self.db.delete(existing)
            self.db.flush()

        current_highest: Optional[Bid] = (
            self.db.query(Bid)
            .filter(
                Bid.invoice_token == data.invoice_token,
                Bid.status == "PENDING",
            )
            .order_by(Bid.bid_amount.desc())
            .first()
        )

        bid = Bid(
            invoice_token=data.invoice_token,
            investor_id=data.investor_id,
            bid_amount=data.bid_amount,
            status="PENDING",
        )
        self.db.add(bid)
        self.db.commit()
        self.db.refresh(bid)

        # Return previous_highest only when new bid actually outbids someone else
        previous_highest = None
        if current_highest and float(data.bid_amount) > float(current_highest.bid_amount):
            previous_highest = current_highest

        return {"bid": bid, "previous_highest": previous_highest}

    def get_bids_for_invoice(self, invoice_token: str) -> List[Bid]:
        """Return all bids for an invoice, ordered by bid_amount DESC."""
        return (
            self.db.query(Bid)
            .filter(Bid.invoice_token == invoice_token)
            .order_by(Bid.bid_amount.desc())
            .all()
        )

    def get_bids_for_investor(self, investor_id: int) -> List[Bid]:
        """Return all bids placed by a specific investor, newest first."""
        return (
            self.db.query(Bid)
            .filter(Bid.investor_id == investor_id)
            .order_by(Bid.id.desc())
            .all()
        )

    def get_bid(self, bid_id: int) -> Bid:
        """Return a single bid by ID."""
        bid = self.db.query(Bid).filter(Bid.id == bid_id).first()
        if not bid:
            raise HTTPException(status_code=404, detail="Bid not found")
        return bid

    def accept_bid(self, bid_id: int) -> Bid:
        """Mark a bid as ACCEPTED."""
        bid = self.db.query(Bid).filter(Bid.id == bid_id).first()
        if not bid:
            raise HTTPException(status_code=404, detail="Bid not found")
        bid.status = "ACCEPTED"
        self.db.commit()
        self.db.refresh(bid)
        return bid

    def reject_bid(self, bid_id: int) -> Bid:
        """Mark a bid as REJECTED."""
        bid = self.db.query(Bid).filter(Bid.id == bid_id).first()
        if not bid:
            raise HTTPException(status_code=404, detail="Bid not found")
        bid.status = "REJECTED"
        self.db.commit()
        self.db.refresh(bid)
        return bid

    def delete_bid(self, bid_id: int) -> None:
        """Hard-delete a bid row (rollback after escrow failure).

        Must be a hard delete — the unique constraint on (invoice_token, investor_id)
        means a soft-delete (CANCELLED) would block the investor from retrying.
        """
        bid = self.db.query(Bid).filter(Bid.id == bid_id).first()
        if not bid:
            raise HTTPException(status_code=404, detail="Bid not found")
        self.db.delete(bid)
        self.db.commit()
