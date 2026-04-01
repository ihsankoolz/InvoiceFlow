import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.notification_handler import notification_store


@pytest.fixture(autouse=True)
def clear_store():
    notification_store.clear()
    yield
    notification_store.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _add_notification(user_id: int, event_type: str = "invoice.listed", message: str = "test"):
    entry = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "event_type": event_type,
        "message": message,
        "payload": {},
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
    }
    notification_store.append(entry)
    return entry


def test_get_notifications_empty(client):
    response = client.get("/api/notifications", params={"user_id": 1})
    assert response.status_code == 200
    assert response.json() == []


def test_get_notifications_filters_by_user_id(client):
    _add_notification(user_id=1)
    _add_notification(user_id=2)
    _add_notification(user_id=1)

    response = client.get("/api/notifications", params={"user_id": 1})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert all(n["user_id"] == 1 for n in data)


def test_get_notifications_capped_at_50(client):
    for _ in range(60):
        _add_notification(user_id=5)

    response = client.get("/api/notifications", params={"user_id": 5})
    assert response.status_code == 200
    assert len(response.json()) == 50


def test_mark_notification_read(client):
    entry = _add_notification(user_id=1)
    nid = entry["id"]

    response = client.patch(f"/api/notifications/{nid}/read")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verify in-store update
    stored = next(n for n in notification_store if n["id"] == nid)
    assert stored["is_read"] is True


def test_mark_notification_read_not_found(client):
    response = client.patch(f"/api/notifications/{uuid.uuid4()}/read")
    assert response.status_code == 404


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
