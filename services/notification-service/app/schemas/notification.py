from datetime import datetime
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    user_id: int
    event_type: str
    message: str
    payload: dict
    is_read: bool
    created_at: datetime
