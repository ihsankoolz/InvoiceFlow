import uuid
from datetime import datetime, timezone

import pytest
from app.models.notification import Notification
from fastapi.testclient import TestClient


def _add_notification(db, user_id: int, event_type: str = "invoice.listed", message: str = "test"):
    entry = Notification(
        id=str(uuid.uuid4()),
        user_id=user_id,
        event_type=event_type,
        message=message,
        payload={},
        is_read=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def test_get_notifications_empty(client):
    response = client.get("/api/notifications", params={"user_id": 1})
    assert response.status_code == 200
    assert response.json() == []


def test_get_notifications_filters_by_user_id(client, db):
    _add_notification(db, user_id=1)
    _add_notification(db, user_id=2)
    _add_notification(db, user_id=1)

    response = client.get("/api/notifications", params={"user_id": 1})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(n["user_id"] == 1 for n in data)


def test_get_notifications_capped_at_50(client, db):
    for _ in range(60):
        _add_notification(db, user_id=5)

    response = client.get("/api/notifications", params={"user_id": 5})
    assert response.status_code == 200
    assert len(response.json()) == 50


def test_mark_notification_read(client, db):
    entry = _add_notification(db, user_id=1)
    nid = entry.id

    response = client.patch(f"/api/notifications/{nid}/read")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    db.refresh(entry)
    assert entry.is_read is True


def test_mark_notification_read_not_found(client):
    response = client.patch(f"/api/notifications/{uuid.uuid4()}/read")
    assert response.status_code == 404


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
