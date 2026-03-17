import json
import logging

import aio_pika

from app.config import RABBITMQ_URL

logger = logging.getLogger(__name__)

EXCHANGE_NAME = "invoiceflow_events"
QUEUE_NAME = "notification_all_events"
ROUTING_KEY = "#"  # Wildcard — subscribe to ALL events


class EventConsumer:
    """RabbitMQ consumer that listens for all events on the invoiceflow_events
    topic exchange and delegates processing to the NotificationHandler."""

    def __init__(self, rabbitmq_url: str = RABBITMQ_URL, websocket_manager=None):
        self.rabbitmq_url = rabbitmq_url
        self.websocket_manager = websocket_manager
        self.connection = None
        self.channel = None
        # Import here to allow ws_manager injection before handler is used
        from app.services.notification_handler import NotificationHandler
        self._handler = NotificationHandler(websocket_manager=websocket_manager)

    async def start(self) -> None:
        """Connect to RabbitMQ, declare exchange/queue, bind with # routing key,
        and begin consuming messages.
        """
        try:
            self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
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
        """Process a single incoming RabbitMQ message."""
        async with message.process():
            try:
                body = json.loads(message.body.decode())
                event_type = message.routing_key
                logger.info("Received event: %s", event_type)
                await self._handler.handle_event(event_type, body)
            except Exception as e:
                logger.error("Error processing message: %s", e)

    async def stop(self) -> None:
        """Gracefully close the RabbitMQ connection."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("EventConsumer stopped.")
