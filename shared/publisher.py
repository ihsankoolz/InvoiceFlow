"""Shared RabbitMQ event publisher using aio-pika."""

import json
import logging

import aio_pika

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "invoiceflow_events"


class EventPublisher:
    """Publishes events to the invoiceflow_events topic exchange."""

    def __init__(self, rabbitmq_url: str, exchange_name: str = EXCHANGE_NAME):
        self.rabbitmq_url = rabbitmq_url
        self.exchange_name = exchange_name
        self._connection: aio_pika.RobustConnection | None = None
        self._channel = None
        self._exchange = None

    async def _ensure_connected(self) -> None:
        if self._exchange is None:
            self._connection = await aio_pika.connect_robust(self.rabbitmq_url)
            self._channel = await self._connection.channel()
            self._exchange = await self._channel.declare_exchange(
                self.exchange_name, aio_pika.ExchangeType.TOPIC, durable=True
            )

    async def publish(self, routing_key: str, payload: dict) -> None:
        await self._ensure_connected()
        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            content_type="application/json",
        )
        await self._exchange.publish(message, routing_key=routing_key)
        logger.debug("Published event %s", routing_key)

    async def close(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
