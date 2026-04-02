import uuid
from datetime import datetime, timezone

from app.database import Base
from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, nullable=False, index=True)
    event_type = Column(String(100), nullable=False)
    message = Column(String(500), nullable=False)
    payload = Column(JSON, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
