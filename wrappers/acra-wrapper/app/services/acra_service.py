"""
ACRAService — calls data.gov.sg ACRA dataset API to validate UENs.

See BUILD_INSTRUCTIONS_V2.md Section 11 — Key Classes
"""

import time
import httpx

from app import config
from app.schemas.uen import UENValidateResponse

_cache: dict[str, tuple[UENValidateResponse, float]] = {}
CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours


class ACRAService:
    """Wraps the data.gov.sg ACRA UEN registry API."""

    async def validate_uen(self, uen: str) -> UENValidateResponse:
        if config.MOCK_UEN_VALIDATION:
            return UENValidateResponse(
                valid=True,
                uen=uen,
                entity_name="Mock Entity (dev mode)",
                uen_status="Registered",
                message="UEN is valid and registered",
            )

        key = uen.upper()
        cached, expiry = _cache.get(key, (None, 0))
        if cached and time.monotonic() < expiry:
            return cached

        url = (
            f"{config.DATA_GOV_API_URL}"
            f"?resource_id={config.ACRA_DATASET_RESOURCE_ID}"
            f"&q={uen}"
            f"&limit=10"
        )

        headers = {"User-Agent": "InvoiceFlow/1.0"}
        if config.DATA_GOV_API_KEY:
            headers["Authorization"] = config.DATA_GOV_API_KEY
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0, headers=headers)
            response.raise_for_status()
            data = response.json()

        records = data.get("result", {}).get("records", [])

        # Find exact UEN match
        match = next((r for r in records if r.get("uen", "").upper() == uen.upper()), None)

        if not match:
            result = UENValidateResponse(
                valid=False,
                uen=uen,
                message="UEN not found in ACRA registry",
            )
        else:
            entity_name = match.get("entity_name")
            uen_status = match.get("uen_status_desc")
            is_active = uen_status == "Registered"
            result = UENValidateResponse(
                valid=is_active,
                uen=uen,
                entity_name=entity_name,
                uen_status=uen_status,
                message="UEN is valid and registered" if is_active else "UEN is not active",
            )

        _cache[key] = (result, time.monotonic() + CACHE_TTL_SECONDS)
        return result
