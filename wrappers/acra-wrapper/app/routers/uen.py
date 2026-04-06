from fastapi import APIRouter, HTTPException

from app.schemas.uen import UENValidateRequest, UENValidateResponse
from app.services.acra_service import ACRAService

router = APIRouter()


@router.post(
    "/validate-uen",
    response_model=UENValidateResponse,
    tags=["UEN Validation"],
    summary="Validate a UEN against ACRA registry",
)
async def validate_uen(data: UENValidateRequest):
    """
    Validate a Singapore UEN against the data.gov.sg ACRA public dataset.

    Called by Invoice Orchestrator at step 7 of Scenario 1.
    Returns valid=True with entity details if UEN exists.
    Returns valid=False if UEN is not found in registry.
    Returns 502 if data.gov.sg is unreachable.
    """
    service = ACRAService()
    try:
        return await service.validate_uen(data.uen)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ACRA registry unreachable: {str(e)}")
