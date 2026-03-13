from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.bid import Bid
from app.schemas.bid import BidCreate


class BidService:

    def __init__(self, db: Session):
        self.db = db

    def create_bid(self, data: BidCreate) -> dict:
        """Insert bid, check highest, return {"bid": Bid, "previous_highest": Bid|None}."""
        # TODO: implement
        pass

    def get_bids_for_invoice(self, invoice_token: str) -> List[Bid]:
        """Return all bids for an invoice, ordered by bid_amount DESC."""
        # TODO: implement
        pass

    def get_bid(self, bid_id: int) -> Bid:
        """Return a single bid by ID."""
        # TODO: implement
        pass

    def accept_bid(self, bid_id: int) -> Bid:
        """Mark a bid as ACCEPTED."""
        # TODO: implement
        pass

    def reject_bid(self, bid_id: int) -> Bid:
        """Mark a bid as REJECTED."""
        # TODO: implement
        pass

    def delete_bid(self, bid_id: int) -> None:
        """Cancel/rollback a bid (for escrow failure)."""
        # TODO: implement
        pass
