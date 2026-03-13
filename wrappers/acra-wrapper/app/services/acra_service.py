"""
ACRAService — calls data.gov.sg ACRA dataset API to validate UENs.

See BUILD_INSTRUCTIONS_V2.md Section 11 — Key Classes
"""

import httpx

from app import config
from app.schemas.uen import UENValidateResponse


class ACRAService:
    """Wraps the data.gov.sg ACRA UEN registry API."""

    async def validate_uen(self, uen: str) -> UENValidateResponse:
        """
        Validate a UEN against the ACRA registry.

        Steps:
        1. Call data.gov.sg API: GET {DATA_GOV_API_URL}?resource_id={ACRA_DATASET_RESOURCE_ID}&q={uen}
        2. Parse response — check if UEN exists in results
        3. If found, extract entity_name and uen_status
        4. Return UENValidateResponse with valid=True/False

        See BUILD_INSTRUCTIONS_V2.md Section 11 — ACRAService
        """
        # TODO: Implement
        pass
