from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import TokenResponse, UserCreate, UserLogin, UserResponse
from app.services.user_service import UserService

router = APIRouter(tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user. UEN validation for SELLER accounts is handled by the user-orchestrator."""
    service = UserService(db)
    return service.create_user(data)


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """Verify credentials and return a JWT access token."""
    service = UserService(db)
    return service.authenticate(data.email, data.password)
