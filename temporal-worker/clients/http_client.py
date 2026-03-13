"""
Reusable async HTTP client for Temporal activities.
Activities use this to call atomic services (Invoice, Bidding, Marketplace).
"""

import httpx
from temporalio.exceptions import ApplicationError


class HTTPClient:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def get(self, url: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            if response.status_code >= 400:
                raise ApplicationError(f"HTTP {response.status_code}: {response.text}")
            return response.json()

    async def post(self, url: str, **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, **kwargs)
            if response.status_code >= 400:
                raise ApplicationError(f"HTTP {response.status_code}: {response.text}")
            return response.json()

    async def patch(self, url: str, **kwargs) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.patch(url, **kwargs)
            if response.status_code >= 400:
                raise ApplicationError(f"HTTP {response.status_code}: {response.text}")
            return response.json()

    async def delete(self, url: str) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.delete(url)
            if response.status_code >= 400:
                raise ApplicationError(f"HTTP {response.status_code}: {response.text}")
            return response.json() if response.content else {}
