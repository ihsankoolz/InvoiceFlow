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
        url = (
            f"{config.DATA_GOV_API_URL}"
            f"?resource_id={config.ACRA_DATASET_RESOURCE_ID}"
            f"&q={uen}"
            f"&limit=10"
        )

        headers = {"User-Agent": "InvoiceFlow/1.0"}
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0, headers=headers)
            response.raise_for_status()
            data = response.json()

        records = data.get("result", {}).get("records", [])

        # Find exact UEN match
        match = next((r for r in records if r.get("uen", "").upper() == uen.upper()), None)

        if not match:
            return UENValidateResponse(
                valid=False,
                uen=uen,
                message="UEN not found in ACRA registry",
            )

        entity_name = match.get("entity_name")
        uen_status = match.get("uen_status_desc")

        is_active = uen_status == "Registered"

        return UENValidateResponse(
            valid=is_active,
            uen=uen,
            entity_name=entity_name,
            uen_status=uen_status,
            message="UEN is valid and registered" if is_active else "UEN is not active",
        )
