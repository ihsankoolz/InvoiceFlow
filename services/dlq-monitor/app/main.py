"""
DLQ Monitor — exposes dead-letter queue depths via the RabbitMQ Management API.

GET /health         — liveness check
GET /dlq/status     — list DLQ queues with message counts
GET /dlq/queues     — alias for /dlq/status

The monitor does NOT consume messages — it only reads queue metadata via the
RabbitMQ HTTP management API so that dead messages are preserved for inspection.
"""

import logging

import httpx
from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator

from app import config

logger = logging.getLogger(__name__)

app = FastAPI(title="DLQ Monitor", version="1.0.0")
Instrumentator().instrument(app).expose(app)

DLQ_SUFFIX = ".dlq"


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "dlq-monitor"}


@app.get("/api/dlq/status", tags=["DLQ"])
@app.get("/api/dlq/queues", tags=["DLQ"])
async def dlq_status():
    """
    Returns all DLQ queues and their message counts.
    Queries the RabbitMQ Management API — no messages are consumed.
    """
    url = f"{config.RABBITMQ_MGMT_URL}/api/queues"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                url,
                auth=(config.RABBITMQ_USER, config.RABBITMQ_PASS),
            )
            response.raise_for_status()
            all_queues = response.json()
    except httpx.HTTPError as e:
        logger.error("Failed to query RabbitMQ management API: %s", e)
        raise HTTPException(status_code=503, detail="RabbitMQ management API unavailable")

    dlq_queues = [
        {
            "name": q["name"],
            "messages": q.get("messages", 0),
            "messages_ready": q.get("messages_ready", 0),
            "messages_unacknowledged": q.get("messages_unacknowledged", 0),
            "consumers": q.get("consumers", 0),
        }
        for q in all_queues
        if q["name"].endswith(DLQ_SUFFIX)
    ]

    total = sum(q["messages"] for q in dlq_queues)

    if total > 0:
        logger.warning("DLQ has %d unprocessed messages across %d queues", total, len(dlq_queues))

    return {
        "total_dlq_messages": total,
        "queues": dlq_queues,
    }
