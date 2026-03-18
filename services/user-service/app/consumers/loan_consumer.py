import asyncio
import json
import logging

import aio_pika

from app.config import RABBITMQ_URL
from app.database import SessionLocal
from app.services.user_service import UserService

logger = logging.getLogger(__name__)


class LoanEventConsumer:
    """RabbitMQ consumer that listens for loan lifecycle events and updates user status.

    Queues:
        - user_repaid_updates (routing key: loan.repaid)
            On message -> UserService.update_status(seller_id, "ACTIVE")
        - user_loan_updates (routing key: loan.overdue)
            On message -> UserService.update_status(seller_id, "DEFAULTED")
    """

    EXCHANGE_NAME = "loan_events"

    async def start(self):
        """Connect to RabbitMQ, declare exchange and queues, and begin consuming.

        Steps:
            1. Connect to RabbitMQ using RABBITMQ_URL.
            2. Declare a topic exchange named 'loan_events'.
            3. Declare queue 'user_repaid_updates' bound with routing key 'loan.repaid'.
            4. Declare queue 'user_loan_updates' bound with routing key 'loan.overdue'.
            5. Start consuming from both queues.
        """
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        channel = await connection.channel()

        exchange = await channel.declare_exchange(
            self.EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )

        repaid_queue = await channel.declare_queue("user_repaid_updates", durable=True)
        await repaid_queue.bind(exchange, routing_key="loan.repaid")

        overdue_queue = await channel.declare_queue("user_loan_updates", durable=True)
        await overdue_queue.bind(exchange, routing_key="loan.overdue")

        await repaid_queue.consume(self._on_repaid)
        await overdue_queue.consume(self._on_overdue)

        logger.info("LoanEventConsumer started, consuming from user_repaid_updates and user_loan_updates")

        try:
            await asyncio.Future()  # run forever until cancelled
        finally:
            await connection.close()

    async def _on_repaid(self, message: aio_pika.IncomingMessage):
        """Handle a loan.repaid event — set seller status to ACTIVE.

        Expected message body (JSON):
            {"seller_id": int, ...}
        """
        async with message.process():
            try:
                body = json.loads(message.body)
                seller_id = body["seller_id"]
                db = SessionLocal()
                try:
                    UserService(db).update_status(seller_id, "ACTIVE")
                finally:
                    db.close()
                logger.info("Set user %s status to ACTIVE (loan.repaid)", seller_id)
            except Exception as e:
                logger.error("Error handling loan.repaid: %s", e)

    async def _on_overdue(self, message: aio_pika.IncomingMessage):
        """Handle a loan.overdue event — set seller status to DEFAULTED.

        Expected message body (JSON):
            {"seller_id": int, ...}
        """
        async with message.process():
            try:
                body = json.loads(message.body)
                seller_id = body["seller_id"]
                db = SessionLocal()
                try:
                    UserService(db).update_status(seller_id, "DEFAULTED")
                finally:
                    db.close()
                logger.info("Set user %s status to DEFAULTED (loan.overdue)", seller_id)
            except Exception as e:
                logger.error("Error handling loan.overdue: %s", e)
