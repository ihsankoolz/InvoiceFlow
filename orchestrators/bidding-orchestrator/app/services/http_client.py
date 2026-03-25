"""
Reusable async HTTP client with error handling.
Used by all orchestrators for service-to-service calls.
"""

import httpx
from fastapi import HTTPException


class HTTPClient:
    def __init__(self, timeout: float = 5.0):
        self.client = httpx.AsyncClient(timeout=timeout)

    async def get(self, url: str, params: dict = None) -> dict:
        try:
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(504, f"Timeout calling {url}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)

    async def post(self, url: str, **kwargs) -> dict:
        try:
            response = await self.client.post(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(504, f"Timeout calling {url}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)

    async def patch(self, url: str, **kwargs) -> dict:
        try:
            response = await self.client.patch(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(504, f"Timeout calling {url}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)

    async def delete(self, url: str) -> dict:
        try:
            response = await self.client.delete(url)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.TimeoutException:
            raise HTTPException(504, f"Timeout calling {url}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)
