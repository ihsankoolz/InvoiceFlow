import httpx


class UENValidator:
    """Validates Singapore UEN numbers against the data.gov.sg ACRA dataset."""

    ACRA_API_URL = "https://data.gov.sg/api/action/datastore_search"
    ACRA_RESOURCE_ID = "5ab68aac-91c3-4571-b484-e468b690a568"

    @staticmethod
    async def validate_uen(uen: str) -> bool:
        """Check whether the given UEN exists in the ACRA dataset on data.gov.sg.

        Args:
            uen: The Unique Entity Number string to validate.

        Returns:
            True if the UEN is found in the ACRA dataset, False otherwise.
        """
        params = {
            "resource_id": UENValidator.ACRA_RESOURCE_ID,
            "q": uen,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(UENValidator.ACRA_API_URL, params=params)
            response.raise_for_status()
            data = response.json()
        return data.get("result", {}).get("total", 0) > 0
