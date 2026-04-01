"""FastAPI middleware for X-Correlation-ID propagation.

Kong's correlation-id plugin already stamps the header on inbound requests.
This middleware reads it (or generates a new UUID) and echoes it on every
response so clients can trace calls end-to-end.
"""

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

HEADER = "X-Correlation-ID"


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        correlation_id = request.headers.get(HEADER) or str(uuid.uuid4())
        request.state.correlation_id = correlation_id
        response = await call_next(request)
        response.headers[HEADER] = correlation_id
        return response
