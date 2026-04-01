"""
Stripe event consumer for loan-orchestrator.

Listens for stripe.checkout.completed events on RabbitMQ and confirms
loan repayments for loan_repayment sessions.

This is the event-driven path — the webhook-router publishes a normalised
stripe.checkout.completed event, and this consumer processes it without
requiring the user to manually call /confirm-repayment.
"""

import logging
from typing import Any

from app import config
from app.services.loan_orchestrator import LoanOrchestrator

logger = logging.getLogger(__name__)

from shared.consumer import BaseConsumer  # noqa: E402

QUEUE_NAME = "loan_stripe_events"
ROUTING_KEYS = ["stripe.checkout.completed"]


class LoanStripeConsumer(BaseConsumer):
    """Processes stripe.checkout.completed events for loan repayments."""

    def __init__(self):
        super().__init__(
            rabbitmq_url=config.RABBITMQ_URL,
            queue_name=QUEUE_NAME,
            routing_keys=ROUTING_KEYS,
        )

    async def handle(self, routing_key: str, body: dict[str, Any]) -> None:
        event_type = body.get("type")

        if event_type != "loan_repayment":
            logger.debug("Skipping stripe event with type=%s", event_type)
            return

        loan_id = body.get("loan_id")
        session_id = body.get("session_id")

        if not loan_id or not session_id:
            logger.error("Malformed loan_repayment event — missing fields: %s", body)
            return

        logger.info("Confirming repayment for loan %s session %s", loan_id, session_id)
        orchestrator = LoanOrchestrator()
        await orchestrator.confirm_repayment(loan_id, session_id)
        logger.info("Loan %s repayment confirmed via event consumer", loan_id)
