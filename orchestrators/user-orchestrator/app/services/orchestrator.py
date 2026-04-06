from fastapi import HTTPException

from app import config
from app.services.http_client import HTTPClient


class UserOrchestrator:
    """
    Orchestrates user registration:
    - SELLER: validate UEN via ACRA Wrapper, then create user via User Service
    - INVESTOR: create user via User Service directly (no UEN validation needed)
    """

    def __init__(self, http_client: HTTPClient):
        self.http_client = http_client

    async def register(self, data: dict) -> dict:
        # Step 1: If SELLER, validate UEN via ACRA Wrapper before creating the account
        if data.get("role") == "SELLER":
            if not data.get("uen"):
                raise HTTPException(status_code=422, detail="UEN is required for SELLER role")

            uen_result = await self.http_client.post(
                f"{config.ACRA_WRAPPER_URL}/validate-uen",
                json={"uen": data["uen"].upper()},
            )

            if not uen_result.get("valid"):
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid UEN: {uen_result.get('message', 'not found in ACRA registry')}",
                )

        # Step 2: Create the user via User Service
        user = await self.http_client.post(
            f"{config.USER_SERVICE_URL}/register",
            json=data,
        )
        return user
