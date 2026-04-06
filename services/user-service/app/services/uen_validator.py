import httpx

from app.config import ACRA_WRAPPER_URL


class UENValidator:
    """Validates Singapore UEN numbers via the acra-wrapper service."""

    @staticmethod
    async def validate_uen(uen: str) -> bool:
        """Check whether the given UEN is registered via the ACRA wrapper.

        Returns:
            True if the UEN is valid and registered, False otherwise.
            Raises HTTPException-compatible errors on service failure (caller handles).
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{ACRA_WRAPPER_URL}/validate-uen",
                json={"uen": uen.upper()},
            )
            response.raise_for_status()
            data = response.json()
        return data.get("valid", False)
