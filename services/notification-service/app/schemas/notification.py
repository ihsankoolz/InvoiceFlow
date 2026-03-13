from datetime import datetime
from pydantic import BaseModel


class NotificationResponse(BaseModel):
    id: str
    user_id: int
    event_type: str
    message: str
    payload: dict
    created_at: datetime
