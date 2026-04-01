"""
RabbitMQ publisher for event publishing to invoiceflow_events topic exchange.
"""

import json

import aio_pika


class RabbitMQPublisher:
    def __init__(self, rabbitmq_url: str, exchange_name: str = "invoiceflow_events"):
        self.rabbitmq_url = rabbitmq_url
        self.exchange_name = exchange_name
        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            self.exchange_name, aio_pika.ExchangeType.TOPIC, durable=True
        )

    async def publish(self, routing_key: str, payload: dict):
        if not self.exchange:
            await self.connect()
        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            content_type="application/json",
        )
        await self.exchange.publish(message, routing_key=routing_key)

    async def close(self):
        if self.connection:
            await self.connection.close()
