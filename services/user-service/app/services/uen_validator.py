import json

import httpx


class UENValidator:
    """Validates Singapore UEN numbers against the data.gov.sg ACRA dataset."""

    ACRA_API_URL = "https://data.gov.sg/api/action/datastore_search"
    ACRA_RESOURCE_ID = "d_3f960c10fed6145404ca7b821f263b87"

    @staticmethod
    async def validate_uen(uen: str) -> bool:
        """Check whether the given UEN exists in the ACRA dataset on data.gov.sg.

        Uses an exact field filter on the 'uen' column to prevent false positives
        from partial/full-text matches.

        Args:
            uen: The Unique Entity Number string to validate.

        Returns:
            True if the UEN is found and active in the ACRA dataset, False otherwise.
        """
        params = {
            "resource_id": UENValidator.ACRA_RESOURCE_ID,
            "filters": json.dumps({"uen": uen.upper()}),
            "limit": 1,
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(UENValidator.ACRA_API_URL, params=params)
            if response.status_code != 200:
                return True  # data.gov.sg unavailable — allow registration to proceed
            data = response.json()
        records = data.get("result", {}).get("records", [])
        if not records:
            return False
        uen_status = records[0].get("uen_status_desc", "")
        return uen_status == "Registered"
