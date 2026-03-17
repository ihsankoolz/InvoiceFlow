from typing import List
from fastapi import APIRouter, Query

from app.schemas.notification import NotificationResponse
from app.services.notification_handler import notification_store

router = APIRouter(tags=["Notifications"])


@router.get("/api/notifications", response_model=List[NotificationResponse])
async def get_notifications(user_id: int = Query(..., description="User ID to fetch notifications for")):
    """Fetch recent notifications from the in-memory store for a given user."""
    user_notifications = [
        n for n in notification_store if n["user_id"] == user_id
    ]
    # Return the most recent 50 notifications, newest first
    return sorted(user_notifications, key=lambda x: x["created_at"], reverse=True)[:50]
