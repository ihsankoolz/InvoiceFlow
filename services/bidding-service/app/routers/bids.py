from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.bid import BidCreate, BidCreateResponse, BidResponse
from app.services.bid_service import BidService

router = APIRouter(prefix="/bids", tags=["Bids"])


@router.post("", response_model=BidCreateResponse)
def create_bid(data: BidCreate, db: Session = Depends(get_db)):
    """
    Create a new bid record.

    Called by Bidding Orchestrator at step B8. Also returns the previous
    highest bidder's info if one exists, so the orchestrator can publish bid.outbid.
    """
    service = BidService(db)
    return service.create_bid(data)


@router.get("", response_model=List[BidResponse])
def get_bids(
    invoice_token: Optional[str] = None,
    investor_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """
    Get bids filtered by invoice_token or investor_id.

    Called by Temporal Worker at step C2 to fetch all bids before auction close.
    Must provide exactly one of invoice_token or investor_id.
    """
    service = BidService(db)
    if investor_id is not None:
        return service.get_bids_for_investor(investor_id)
    if invoice_token is not None:
        return service.get_bids_for_invoice(invoice_token)
    raise HTTPException(status_code=400, detail="Provide invoice_token or investor_id")


@router.get("/{bid_id}", response_model=BidResponse)
def get_bid(bid_id: int, db: Session = Depends(get_db)):
    """Get a single bid by its ID."""
    service = BidService(db)
    return service.get_bid(bid_id)


@router.patch("/{bid_id}/accept", response_model=BidResponse)
def accept_bid(bid_id: int, db: Session = Depends(get_db)):
    """
    Mark a bid as ACCEPTED (winner).

    Called by Temporal Worker at step C11 after auction closes.
    """
    service = BidService(db)
    return service.accept_bid(bid_id)


@router.patch("/{bid_id}/reject", response_model=BidResponse)
def reject_bid(bid_id: int, db: Session = Depends(get_db)):
    """
    Mark a bid as REJECTED (loser).

    Called by Temporal Worker at step C12 for all losing bids after auction closes.
    """
    service = BidService(db)
    return service.reject_bid(bid_id)


@router.patch("/{bid_id}/outbid", response_model=BidResponse)
def outbid_bid(bid_id: int, db: Session = Depends(get_db)):
    """
    Mark a bid as OUTBID when a higher bid is placed.

    Called by the RabbitMQ consumer processing bid.outbid events (step B10b).
    """
    service = BidService(db)
    return service.outbid_bid(bid_id)


@router.delete("/{bid_id}", status_code=204)
def delete_bid(bid_id: int, db: Session = Depends(get_db)):
    """Delete a bid record by ID."""
    service = BidService(db)
    service.delete_bid(bid_id)
