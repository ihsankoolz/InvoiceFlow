"""
RabbitMQ publishing activity for Temporal workflows.
Publishes events to the invoiceflow_events topic exchange.
"""

import json

import aio_pika
from temporalio import activity

import config


@activity.defn
async def publish_event(routing_key: str, payload: dict):
    """Publish an event to RabbitMQ invoiceflow_events topic exchange."""
    connection = await aio_pika.connect_robust(config.RABBITMQ_URL)
    async with connection:
        channel = await connection.channel()
        exchange = await channel.declare_exchange(
            "invoiceflow_events", aio_pika.ExchangeType.TOPIC, durable=True
        )
        await exchange.publish(
            aio_pika.Message(
                body=json.dumps(payload).encode(),
                content_type="application/json",
            ),
            routing_key=routing_key,
        )
