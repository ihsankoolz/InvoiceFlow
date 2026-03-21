from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.bid import BidCreate, BidResponse, BidCreateResponse
from app.services.bid_service import BidService

router = APIRouter(prefix="/bids", tags=["Bids"])


@router.post("", response_model=BidCreateResponse)
def create_bid(data: BidCreate, db: Session = Depends(get_db)):
    service = BidService(db)
    return service.create_bid(data)


@router.get("", response_model=List[BidResponse])
def get_bids_for_invoice(invoice_token: str, db: Session = Depends(get_db)):
    service = BidService(db)
    return service.get_bids_for_invoice(invoice_token)


@router.get("/{bid_id}", response_model=BidResponse)
def get_bid(bid_id: int, db: Session = Depends(get_db)):
    service = BidService(db)
    return service.get_bid(bid_id)


@router.patch("/{bid_id}/accept", response_model=BidResponse)
def accept_bid(bid_id: int, db: Session = Depends(get_db)):
    service = BidService(db)
    return service.accept_bid(bid_id)


@router.patch("/{bid_id}/reject", response_model=BidResponse)
def reject_bid(bid_id: int, db: Session = Depends(get_db)):
    service = BidService(db)
    return service.reject_bid(bid_id)


@router.delete("/{bid_id}", status_code=204)
def delete_bid(bid_id: int, db: Session = Depends(get_db)):
    service = BidService(db)
    service.delete_bid(bid_id)
