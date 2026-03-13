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
        # TODO: implement
        logger.info("LoanEventConsumer.start not yet implemented")

    async def _on_repaid(self, message: aio_pika.IncomingMessage):
        """Handle a loan.repaid event — set seller status to ACTIVE.

        Expected message body (JSON):
            {"seller_id": int, ...}
        """
        # TODO: implement
        # Parse message body, open DB session, call UserService.update_status(seller_id, "ACTIVE")
        async with message.process():
            logger.info("_on_repaid handler not yet implemented")

    async def _on_overdue(self, message: aio_pika.IncomingMessage):
        """Handle a loan.overdue event — set seller status to DEFAULTED.

        Expected message body (JSON):
            {"seller_id": int, ...}
        """
        # TODO: implement
        # Parse message body, open DB session, call UserService.update_status(seller_id, "DEFAULTED")
        async with message.process():
            logger.info("_on_overdue handler not yet implemented")
