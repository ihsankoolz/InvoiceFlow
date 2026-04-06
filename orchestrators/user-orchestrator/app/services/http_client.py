"""
Async HTTP client with tenacity retry for transient errors.
Retries on: timeouts, connection errors, 5xx responses (up to 3 attempts).
Never retries 4xx — those are caller errors and must propagate immediately.
"""

import httpx
from fastapi import HTTPException
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, (httpx.TimeoutException, httpx.ConnectError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code >= 500:
        return True
    return False


def _extract_detail(e: httpx.HTTPStatusError) -> str:
    try:
        return e.response.json().get("detail", e.response.text)
    except Exception:
        return e.response.text


_RETRY = dict(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=4.0),
    retry=retry_if_exception(_is_transient),
    reraise=True,
)


class HTTPClient:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def get(self, url: str, params: dict = None) -> dict:
        try:
            async for attempt in AsyncRetrying(**_RETRY):
                with attempt:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.get(url, params=params)
                        response.raise_for_status()
                        return response.json()
        except httpx.TimeoutException:
            raise HTTPException(504, f"Timeout calling {url}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, _extract_detail(e))

    async def post(self, url: str, **kwargs) -> dict:
        try:
            async for attempt in AsyncRetrying(**_RETRY):
                with attempt:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(url, **kwargs)
                        response.raise_for_status()
                        return response.json()
        except httpx.TimeoutException:
            raise HTTPException(504, f"Timeout calling {url}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, _extract_detail(e))
