from sqlalchemy import Column, DateTime, Enum, Integer, String, func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    role = Column(Enum("SELLER", "INVESTOR", name="user_role"), nullable=False)
    uen = Column(String(20), nullable=True)
    account_status = Column(
        Enum("ACTIVE", "DEFAULTED", name="account_status"),
        nullable=False,
        default="ACTIVE",
        server_default="ACTIVE",
    )
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
