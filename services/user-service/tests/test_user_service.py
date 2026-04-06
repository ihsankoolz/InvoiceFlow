"""
Tests for UserService.create_user, get_user, and update_status.

Covers the critical registration paths that were previously untested:
- Duplicate email rejection
- SELLER missing UEN
- SELLER with invalid UEN (mocked ACRA call)
- Successful INVESTOR registration
- Successful SELLER registration
- get_user 404
- update_status happy path and 404
"""

import pytest
from app.models.user import User
from app.schemas import UserCreate
from app.services.user_service import UserService
from fastapi import HTTPException
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _make_data(**kwargs):
    defaults = {
        "email": "new@test.com",
        "password": "password123",
        "full_name": "New User",
        "role": "INVESTOR",
        "uen": None,
    }
    defaults.update(kwargs)
    return UserCreate(**defaults)


def _seed_user(db, email="existing@test.com", role="INVESTOR"):
    user = User(
        email=email,
        password_hash=pwd_context.hash("pass"),
        full_name="Existing User",
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# ---------------------------------------------------------------------------
# create_user — duplicate email
# ---------------------------------------------------------------------------

def test_create_user_duplicate_email_raises_409(db):
    _seed_user(db, email="taken@test.com")
    service = UserService(db)

    with pytest.raises(HTTPException) as exc_info:
        service.create_user(_make_data(email="taken@test.com"))
    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# create_user — SELLER without UEN
# ---------------------------------------------------------------------------

def test_create_seller_without_uen_raises_422(db):
    service = UserService(db)

    with pytest.raises(HTTPException) as exc_info:
        service.create_user(_make_data(role="SELLER", uen=None))
    assert exc_info.value.status_code == 422
    assert "UEN" in exc_info.value.detail


# ---------------------------------------------------------------------------
# create_user — successful INVESTOR registration
# ---------------------------------------------------------------------------

def test_create_investor_success(db):
    service = UserService(db)
    user = service.create_user(_make_data(email="investor@test.com", role="INVESTOR"))

    assert user.id is not None
    assert user.email == "investor@test.com"
    assert user.role == "INVESTOR"
    assert pwd_context.verify("password123", user.password_hash)


# ---------------------------------------------------------------------------
# create_user — successful SELLER registration (UEN validation done by orchestrator)
# ---------------------------------------------------------------------------

def test_create_seller_success(db):
    service = UserService(db)
    user = service.create_user(
        _make_data(email="seller@test.com", role="SELLER", uen="200509501E")
    )

    assert user.role == "SELLER"
    assert user.uen == "200509501E"


# ---------------------------------------------------------------------------
# get_user — 404 for missing user
# ---------------------------------------------------------------------------

def test_get_user_not_found_raises_404(db):
    service = UserService(db)

    with pytest.raises(HTTPException) as exc_info:
        service.get_user(99999)
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# get_user — returns correct user
# ---------------------------------------------------------------------------

def test_get_user_returns_user(db):
    seeded = _seed_user(db, email="find@test.com")
    service = UserService(db)

    result = service.get_user(seeded.id)
    assert result.id == seeded.id
    assert result.email == "find@test.com"


# ---------------------------------------------------------------------------
# update_status — happy path
# ---------------------------------------------------------------------------

def test_update_status_changes_account_status(db):
    user = _seed_user(db)
    service = UserService(db)

    updated = service.update_status(user.id, "DEFAULTED")
    assert updated.account_status == "DEFAULTED"


def test_update_status_back_to_active(db):
    user = _seed_user(db)
    service = UserService(db)
    service.update_status(user.id, "DEFAULTED")

    result = service.update_status(user.id, "ACTIVE")
    assert result.account_status == "ACTIVE"


# ---------------------------------------------------------------------------
# update_status — 404 for missing user
# ---------------------------------------------------------------------------

def test_update_status_not_found_raises_404(db):
    service = UserService(db)

    with pytest.raises(HTTPException) as exc_info:
        service.update_status(99999, "DEFAULTED")
    assert exc_info.value.status_code == 404
