from fastapi import APIRouter, HTTPException

from app.schemas.uen import UENValidateRequest, UENValidateResponse

router = APIRouter()


@router.post(
    "/validate-uen",
    response_model=UENValidateResponse,
    tags=["UEN Validation"],
    summary="Validate a UEN against ACRA registry",
)
async def validate_uen(data: UENValidateRequest):
    """
    Validate a debtor UEN against the data.gov.sg ACRA dataset.

    See BUILD_INSTRUCTIONS_V2.md Section 11 — ACRAService
    """
    # TODO: Implement — instantiate ACRAService and call validate_uen()
    raise HTTPException(501, "Not implemented yet")
