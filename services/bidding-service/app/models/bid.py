from sqlalchemy import DECIMAL, Column, DateTime, Enum, Integer, String, UniqueConstraint
from sqlalchemy.sql import func

from app.database import Base


class Bid(Base):
    __tablename__ = "bids"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_token = Column(String(36), nullable=False)
    investor_id = Column(Integer, nullable=False)
    bid_amount = Column(DECIMAL(12, 2), nullable=False)
    status = Column(
        Enum("PENDING", "ACCEPTED", "REJECTED", "CANCELLED", "OUTBID", name="bid_status"),
        default="PENDING",
    )
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("invoice_token", "investor_id", name="unique_bid"),
    )
