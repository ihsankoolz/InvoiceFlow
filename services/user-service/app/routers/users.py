from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import StatusUpdate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    """
    Fetch a single user by ID.

    Called by Invoice Orchestrator (step 4) to verify account_status is ACTIVE.
    Returns 404 if user does not exist.
    """
    service = UserService(db)
    return service.get_user(user_id)


@router.patch("/{user_id}/status", response_model=UserResponse)
def update_user_status(user_id: int, body: StatusUpdate, db: Session = Depends(get_db)):
    """
    Update a user's account_status to ACTIVE or DEFAULTED.

    Called by RabbitMQ consumer (loan.overdue) to mark business as DEFAULTED,
    and by loan.repaid consumer to reset back to ACTIVE.
    """
    service = UserService(db)
    return service.update_status(user_id, body.account_status)