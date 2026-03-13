from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import UserCreate, UserResponse, UserLogin, TokenResponse
from app.services.user_service import UserService

router = APIRouter(tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user. If the role is SELLER, the UEN is validated via data.gov.sg."""
    # TODO: Instantiate UserService and call create_user
    service = UserService(db)
    return service.create_user(data)


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Verify credentials and return a JWT access token."""
    # TODO: Instantiate UserService and call authenticate
    service = UserService(db)
    return service.authenticate(data.email, data.password)
