"""
RabbitMQ publishing activity for Temporal workflows.
Publishes events to the invoiceflow_events topic exchange.

See BUILD_INSTRUCTIONS_V2.md Section 13 — publish_event
"""

import json

import aio_pika
from temporalio import activity

import config


@activity.defn
async def publish_event(routing_key: str, payload: dict):
    """
    Publish an event to RabbitMQ invoiceflow_events topic exchange.

    Used by all workflows to publish events like:
    - auction.closing.warning
    - auction.expired
    - auction.closed.winner
    - auction.closed.loser
    - loan.due
    - loan.overdue
    - wallet.credited

    See BUILD_INSTRUCTIONS_V2.md Section 13 — publish_event activity
    """
    # TODO: Implement
    pass
