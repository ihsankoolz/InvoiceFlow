from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationResponse

router = APIRouter(tags=["Notifications"])


@router.get("/api/notifications", response_model=List[NotificationResponse])
def get_notifications(
    user_id: int = Query(..., description="User ID to fetch notifications for"),
    db: Session = Depends(get_db),
):
    """
    Fetch the 50 most recent notifications for a user, newest first.

    Called by the frontend after login to populate the notification panel.
    """
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )


@router.patch("/api/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str, db: Session = Depends(get_db)):
    """
    Mark a notification as read (is_read = True).

    Returns 404 if the notification ID does not exist.
    """
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    return {"status": "ok"}
