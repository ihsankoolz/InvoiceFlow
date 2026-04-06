from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import TokenResponse, UserCreate, UserLogin, UserResponse
from app.services.user_service import UserService

router = APIRouter(tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user (BUSINESS or INVESTOR role).

    UEN validation for SELLER accounts is handled separately by the user-orchestrator.
    Returns 409 if email already exists.
    """
    service = UserService(db)
    return service.create_user(data)


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user and return a signed JWT access token.

    The JWT is validated by KONG on all subsequent API requests.
    Returns 401 if credentials are invalid.
    """
    service = UserService(db)
    return service.authenticate(data.email, data.password)
