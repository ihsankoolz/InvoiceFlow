"""Base RabbitMQ consumer with Dead Letter Queue support."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import aio_pika

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "invoiceflow_events"
DLQ_EXCHANGE_NAME = "invoiceflow_dlq"


class BaseConsumer(ABC):
    """Base class for topic-exchange consumers with automatic DLQ routing.

    Subclasses implement ``handle(routing_key, body)`` and pass the queue
    name plus routing keys to bind on construction.  Failed messages are
    nack'd (not requeued) so aio-pika routes them to the DLQ exchange.
    """

    def __init__(
        self,
        rabbitmq_url: str,
        queue_name: str,
        routing_keys: list[str],
        exchange_name: str = EXCHANGE_NAME,
    ):
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.routing_keys = routing_keys
        self.exchange_name = exchange_name
        self._connection: aio_pika.RobustConnection | None = None
        self._channel = None

    async def start(self) -> None:
        self._connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self._channel = await self._connection.channel()

        # DLQ exchange + queue
        dlq_exchange = await self._channel.declare_exchange(
            DLQ_EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )
        dlq_queue = await self._channel.declare_queue(
            f"{self.queue_name}.dlq", durable=True
        )
        for key in self.routing_keys:
            await dlq_queue.bind(dlq_exchange, routing_key=key)

        # Main exchange + queue (DLX configured)
        exchange = await self._channel.declare_exchange(
            self.exchange_name, aio_pika.ExchangeType.TOPIC, durable=True
        )
        queue = await self._channel.declare_queue(
            self.queue_name,
            durable=True,
            arguments={"x-dead-letter-exchange": DLQ_EXCHANGE_NAME},
        )
        for key in self.routing_keys:
            await queue.bind(exchange, routing_key=key)

        await queue.consume(self._process_message)
        logger.info(
            "Consumer started on queue '%s' for keys %s",
            self.queue_name,
            self.routing_keys,
        )

    async def _process_message(self, message: aio_pika.IncomingMessage) -> None:
        async with message.process(requeue=False):
            try:
                body = json.loads(message.body.decode())
                await self.handle(message.routing_key, body)
            except Exception as e:
                logger.error(
                    "Failed to process message on key '%s': %s",
                    message.routing_key,
                    e,
                    exc_info=True,
                )
                raise  # nack → DLQ

    @abstractmethod
    async def handle(self, routing_key: str, body: dict[str, Any]) -> None:
        """Process a single event. Raise on unrecoverable errors to DLQ."""

    async def stop(self) -> None:
        if self._connection and not self._connection.is_closed:
            await self._connection.close()
            logger.info("Consumer '%s' stopped.", self.queue_name)
