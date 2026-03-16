"""
Stripe webhook handler.

Verifies the Stripe-Signature header (HMAC-SHA256), then starts
WalletTopUpWorkflow via Temporal for checkout.session.completed events.
No Stripe SDK needed — signature verification is done manually per Stripe docs.
"""

import hashlib
import hmac
import json
import time

from fastapi import APIRouter, HTTPException, Request

from app import config
from app.schemas.requests import WebhookResponse
from app.temporal.client import TemporalClient

router = APIRouter()

_temporal = TemporalClient()


def _verify_stripe_signature(payload: bytes, sig_header: str, secret: str) -> None:
    """
    Verify Stripe-Signature header.

    Raises HTTPException 400 if signature is invalid or timestamp is >5 min old.
    Stripe signature format: t=<timestamp>,v1=<hex_digest>
    Signed payload:          <timestamp>.<raw_body>
    """
    try:
        parts = dict(item.split("=", 1) for item in sig_header.split(","))
        timestamp = parts["t"]
        expected_sig = parts["v1"]
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid Stripe-Signature header")

    # Replay attack protection: reject webhooks older than 5 minutes
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


@router.post(
    "/api/webhooks/stripe",
    response_model=WebhookResponse,
    tags=["Webhook"],
    summary="Handle Stripe webhook events",
    description=(
        "Verifies the Stripe-Signature header, then handles checkout.session.completed "
        "events. For wallet_topup sessions, starts WalletTopUpWorkflow via Temporal "
        "(idempotent — same session ID prevents duplicate processing)."
    ),
)
async def handle_stripe_webhook(request: Request):
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

        if metadata.get("type") == "wallet_topup":
            session_id = session["id"]
            workflow_id = f"wallet-topup-{session_id}"

            await _temporal.start_workflow(
                workflow_name="WalletTopUpWorkflow",
                workflow_id=workflow_id,
                args={
                    "user_id": int(metadata["user_id"]),
                    "amount": session["amount_total"],  # in cents from Stripe
                },
                task_queue="invoiceflow-queue",
            )

    return {"status": "ok"}
