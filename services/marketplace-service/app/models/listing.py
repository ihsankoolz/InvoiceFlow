from sqlalchemy import Column, Integer, String, DateTime, Enum, DECIMAL, func
from app.database import Base


class Listing(Base):
    __tablename__ = "listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_token = Column(String(36), unique=True, nullable=False)
    seller_id = Column(Integer, nullable=False)
    debtor_uen = Column(String(20), nullable=False)
    amount = Column(DECIMAL(12, 2), nullable=False)
    minimum_bid = Column(DECIMAL(12, 2), nullable=False)
    urgency_level = Column(
        Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="urgency_level_enum"),
        nullable=False,
    )
    deadline = Column(DateTime, nullable=False)
    status = Column(
        Enum("ACTIVE", "CLOSED", "EXPIRED", name="status_enum"),
        server_default="ACTIVE",
    )
    # Read-model columns — populated on listing creation and updated by event consumer
    face_value = Column(DECIMAL(12, 2), nullable=True)
    debtor_name = Column(String(255), nullable=True)
    current_bid = Column(DECIMAL(12, 2), nullable=True)
    bid_count = Column(Integer, nullable=False, server_default="0")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
