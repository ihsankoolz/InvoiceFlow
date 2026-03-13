import json
import asyncio
import logging

import aio_pika

from app.config import RABBITMQ_URL
from app.services.notification_handler import notification_handler

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "invoiceflow_events"
QUEUE_NAME = "notification_all_events"
ROUTING_KEY = "#"  # Wildcard — subscribe to ALL events


class EventConsumer:
    """RabbitMQ consumer that listens for all events on the invoiceflow_events
    topic exchange and delegates processing to the NotificationHandler."""

    def __init__(self):
        self.connection = None
        self.channel = None

    async def start(self) -> None:
        """Connect to RabbitMQ, declare exchange/queue, bind with # routing key,
        and begin consuming messages.
        """
        # TODO: Implement RabbitMQ connection and consumption
        # 1. Connect to RabbitMQ using aio_pika
        # 2. Declare topic exchange 'invoiceflow_events'
        # 3. Declare queue 'notification_all_events'
        # 4. Bind queue with routing_key '#'
        # 5. Start consuming and call _process_message for each message
        try:
            self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
            self.channel = await self.connection.channel()

            exchange = await self.channel.declare_exchange(
                EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
            )

            queue = await self.channel.declare_queue(QUEUE_NAME, durable=True)
            await queue.bind(exchange, routing_key=ROUTING_KEY)

            await queue.consume(self._process_message)
            logger.info("EventConsumer started — listening on queue '%s'", QUEUE_NAME)
        except Exception as e:
            logger.error("Failed to start EventConsumer: %s", e)
            raise

    async def _process_message(self, message: aio_pika.IncomingMessage) -> None:
        """Process a single incoming RabbitMQ message.

        Args:
            message: The incoming aio-pika message.
        """
        # TODO: Parse message body, extract event_type from routing_key,
        # and delegate to notification_handler.handle_event
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                event_type = message.routing_key
                logger.info("Received event: %s", event_type)
                await notification_handler.handle_event(event_type, body)
            except Exception as e:
                logger.error("Error processing message: %s", e)

    async def stop(self) -> None:
        """Gracefully close the RabbitMQ connection."""
        # TODO: Close connection if open
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("EventConsumer stopped.")


# Singleton instance
event_consumer = EventConsumer()
