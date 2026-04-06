"""
Stripe event consumer for bidding-orchestrator.

Listens for stripe.checkout.completed events on RabbitMQ and starts
WalletTopUpWorkflow via Temporal for wallet_topup sessions.

This is the event-driven path (RabbitMQ ← webhook-router).  The existing
REST webhook endpoint at /api/webhooks/stripe remains as the primary path;
this consumer handles the same event when routed via the message bus.
"""

import logging
from typing import Any

from app import config
from app.temporal.client import TemporalClient

logger = logging.getLogger(__name__)

# Import BaseConsumer from the shared volume mount
from shared.consumer import BaseConsumer  # noqa: E402

QUEUE_NAME = "bidding_stripe_events"
ROUTING_KEYS = ["stripe.checkout.completed"]


class StripeWebhookConsumer(BaseConsumer):
    """Processes stripe.checkout.completed events published by the webhook-router."""

    def __init__(self):
        super().__init__(
            rabbitmq_url=config.RABBITMQ_URL,
            queue_name=QUEUE_NAME,
            routing_keys=ROUTING_KEYS,
        )
        self._temporal = TemporalClient()

    async def handle(self, routing_key: str, body: dict[str, Any]) -> None:
        event_type = body.get("type")

        if event_type != "wallet_topup":
            logger.debug("Skipping stripe event with type=%s", event_type)
            return

        session_id = body.get("session_id")
        user_id = body.get("user_id")
        amount = body.get("amount")

        if not all([session_id, user_id, amount]):
            logger.error("Malformed wallet_topup event — missing fields: %s", body)
            return

        workflow_id = f"wallet-topup-{session_id}"
        logger.info(
            "Starting WalletTopUpWorkflow %s for user %s amount %s", workflow_id, user_id, amount
        )

        await self._temporal.start_workflow(
            workflow_name="WalletTopUpWorkflow",
            workflow_id=workflow_id,
            args={"user_id": int(user_id), "amount": float(amount)},
            task_queue="invoiceflow-queue",
        )
