"""
Webhook Router — receives raw Stripe webhook events, verifies the signature,
and publishes a normalised stripe.checkout.completed event to RabbitMQ.

This decouples Stripe from business logic: the bidding-orchestrator and
loan-orchestrator consumers pick up the event and act on it independently.

Kong routes /api/webhooks/stripe → this service (no JWT — uses Stripe signature).
"""

import hashlib
import hmac
import json
import logging
import time
from contextlib import asynccontextmanager

import aio_pika
from fastapi import FastAPI, HTTPException, Request
from prometheus_fastapi_instrumentator import Instrumentator

from app import config

logger = logging.getLogger(__name__)

_publisher = None


async def _get_publisher():
    global _publisher
    if _publisher is None:
        connection = await aio_pika.connect_robust(config.RABBITMQ_URL)
        channel = await connection.channel()
        _publisher = await channel.declare_exchange(
            "invoiceflow_events", aio_pika.ExchangeType.TOPIC, durable=True
        )
    return _publisher


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Eagerly connect to RabbitMQ on startup
    try:
        await _get_publisher()
        logger.info("webhook-router connected to RabbitMQ.")
    except Exception as e:
        logger.warning("Could not pre-connect to RabbitMQ: %s", e)
    yield


app = FastAPI(title="Webhook Router", version="1.0.0", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> None:
    """Verify Stripe-Signature header (HMAC-SHA256, replay-protected)."""
    try:
        parts = dict(item.split("=", 1) for item in sig_header.split(","))
        timestamp = parts["t"]
        expected_sig = parts["v1"]
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid Stripe-Signature header")

    if abs(time.time() - int(timestamp)) > 300:
        raise HTTPException(status_code=400, detail="Webhook timestamp too old")

    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
    computed = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(computed, expected_sig):
        raise HTTPException(status_code=400, detail="Invalid Stripe signature")


@app.post("/api/webhooks/stripe", tags=["Webhooks"])
async def handle_stripe_webhook(request: Request):
    """
    Verify and route incoming Stripe webhook events to RabbitMQ.

    Supported events:
      checkout.session.completed (type=wallet_topup)  → stripe.checkout.completed
      checkout.session.completed (type=loan_repayment) → stripe.checkout.completed
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    _verify_stripe_signature(payload, sig_header, config.STRIPE_WEBHOOK_SECRET)

    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    if event.get("type") == "checkout.session.completed":
        session = event["data"]["object"]
        metadata = session.get("metadata", {})
        event_type = metadata.get("type")

        if event_type in ("wallet_topup", "loan_repayment"):
            normalised = {
                "session_id": session["id"],
                "type": event_type,
                "user_id": metadata.get("user_id"),
                "amount": session.get("amount_total", 0) / 100,
                "loan_id": metadata.get("loan_id"),
            }
            try:
                exchange = await _get_publisher()
                await exchange.publish(
                    aio_pika.Message(
                        body=json.dumps(normalised).encode(),
                        content_type="application/json",
                    ),
                    routing_key="stripe.checkout.completed",
                )
                logger.info("Published stripe.checkout.completed type=%s", event_type)
            except Exception as e:
                logger.error("Failed to publish stripe event: %s", e)
                raise HTTPException(status_code=500, detail="Event routing failed")
        else:
            logger.debug("Ignoring stripe event with unhandled type=%s", event_type)

    return {"received": True}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "service": "webhook-router"}
