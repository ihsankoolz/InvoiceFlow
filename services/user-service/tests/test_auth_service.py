import pytest
from fastapi import HTTPException
from jose import jwt as jose_jwt
from passlib.context import CryptContext

from app.config import JWT_SECRET, JWT_ALGORITHM
from app.models.user import User
from app.services.user_service import UserService

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _seed_user(db, email="test@example.com", password="secret123", role="INVESTOR"):
    user = User(
        email=email,
        password_hash=pwd_context.hash(password),
        full_name="Test User",
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_authenticate_success(db):
    _seed_user(db, email="inv@test.com", password="pass1234")
    service = UserService(db)
    result = service.authenticate("inv@test.com", "pass1234")
    assert result.access_token
    assert result.token_type == "bearer"


def test_authenticate_wrong_email_raises_401(db):
    service = UserService(db)
    with pytest.raises(HTTPException) as exc_info:
        service.authenticate("nobody@nowhere.com", "pass")
    assert exc_info.value.status_code == 401


def test_authenticate_wrong_password_raises_401(db):
    _seed_user(db, email="user@test.com", password="correct")
    service = UserService(db)
    with pytest.raises(HTTPException) as exc_info:
        service.authenticate("user@test.com", "wrong")
    assert exc_info.value.status_code == 401


def test_authenticate_returns_jwt_with_correct_claims(db):
    user = _seed_user(db, email="seller@test.com", password="mypassword", role="INVESTOR")
    service = UserService(db)
    result = service.authenticate("seller@test.com", "mypassword")

    payload = jose_jwt.decode(result.access_token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    assert payload["sub"] == str(user.id)
    assert payload["role"] == "INVESTOR"
    assert "exp" in payload


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_login_endpoint_invalid_credentials(client):
    response = client.post(
        "/login",
        json={"email": "ghost@test.com", "password": "nope"},
    )
    assert response.status_code == 401
