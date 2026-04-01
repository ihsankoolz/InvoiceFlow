"""
Async HTTP client for Temporal activities with tenacity retry.
Retries on: timeouts, connection errors, 5xx responses (up to 3 attempts).
Never retries 4xx — those are application errors and Temporal should not retry them.
Raises ApplicationError so Temporal workflows can inspect the failure reason.
"""

import httpx
from temporalio.exceptions import ApplicationError
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


_RETRY = dict(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=0.5, max=4.0),
    retry=retry_if_exception(_is_transient),
    reraise=True,
)


class HTTPClient:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def get(self, url: str) -> dict:
        try:
            async for attempt in AsyncRetrying(**_RETRY):
                with attempt:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.get(url)
                        response.raise_for_status()
                        return response.json()
        except httpx.TimeoutException as e:
            raise ApplicationError(f"Timeout calling {url}") from e
        except httpx.HTTPStatusError as e:
            raise ApplicationError(f"HTTP {e.response.status_code}: {e.response.text}") from e

    async def post(self, url: str, **kwargs) -> dict:
        try:
            async for attempt in AsyncRetrying(**_RETRY):
                with attempt:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(url, **kwargs)
                        response.raise_for_status()
                        return response.json()
        except httpx.TimeoutException as e:
            raise ApplicationError(f"Timeout calling {url}") from e
        except httpx.HTTPStatusError as e:
            raise ApplicationError(f"HTTP {e.response.status_code}: {e.response.text}") from e

    async def patch(self, url: str, **kwargs) -> dict:
        try:
            async for attempt in AsyncRetrying(**_RETRY):
                with attempt:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.patch(url, **kwargs)
                        response.raise_for_status()
                        return response.json()
        except httpx.TimeoutException as e:
            raise ApplicationError(f"Timeout calling {url}") from e
        except httpx.HTTPStatusError as e:
            raise ApplicationError(f"HTTP {e.response.status_code}: {e.response.text}") from e

    async def delete(self, url: str) -> dict:
        try:
            async for attempt in AsyncRetrying(**_RETRY):
                with attempt:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.delete(url)
                        response.raise_for_status()
                        return response.json() if response.content else {}
        except httpx.TimeoutException as e:
            raise ApplicationError(f"Timeout calling {url}") from e
        except httpx.HTTPStatusError as e:
            raise ApplicationError(f"HTTP {e.response.status_code}: {e.response.text}") from e
