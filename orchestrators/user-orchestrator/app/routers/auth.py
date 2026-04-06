from fastapi import APIRouter

from app.schemas.requests import RegisterRequest, RegisterResponse
from app.services.http_client import HTTPClient
from app.services.orchestrator import UserOrchestrator

router = APIRouter()


@router.post(
    "/api/auth/register",
    response_model=RegisterResponse,
    status_code=201,
    tags=["Auth"],
    summary="Register a new user",
    description=(
        "Orchestrates user registration:\n"
        "1. SELLER only — validate company UEN against the ACRA registry (ACRA Wrapper)\n"
        "2. Create the user account (User Service)\n\n"
        "INVESTOR registrations skip UEN validation and go directly to step 2."
    ),
)
async def register(data: RegisterRequest):
    orchestrator = UserOrchestrator(http_client=HTTPClient())
    result = await orchestrator.register(data.model_dump())
    return RegisterResponse(**result)
