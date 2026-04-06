from sqlalchemy import DECIMAL, JSON, Column, DateTime, Enum, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_token = Column(String(36), unique=True, nullable=False)
    seller_id = Column(Integer, nullable=False)
    debtor_name = Column(String(255), nullable=True)
    debtor_uen = Column(String(20), nullable=False)
    amount = Column(DECIMAL(12, 2), nullable=False)
    due_date = Column(DateTime, nullable=False)
    currency = Column(String(3), default="SGD")
    pdf_url = Column(String(500), nullable=True)
    status = Column(
        Enum(
            "DRAFT",
            "LISTED",
            "FINANCED",
            "REPAID",
            "DEFAULTED",
            "REJECTED",
            "EXPIRED",
            "DELISTED",
            name="invoice_status",
        ),
        default="DRAFT",
    )
    extracted_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
