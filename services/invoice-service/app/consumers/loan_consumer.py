import json
import logging

import aio_pika

from app.config import RABBITMQ_URL
from app.database import SessionLocal
from app.services.invoice_service import InvoiceService

logger = logging.getLogger(__name__)


class LoanEventConsumer:
    """RabbitMQ consumer that listens for loan-lifecycle events and updates invoice statuses.

    Subscribed queues and routing keys:
        - invoice_repaid_updates  (routing key: loan.repaid)  -> sets status to REPAID
        - invoice_loan_updates    (routing key: loan.overdue)  -> sets status to DEFAULTED
    """

    def __init__(self):
        self.connection = None
        self.channel = None

    async def start(self):
        """Connect to RabbitMQ, declare queues, and begin consuming messages.

        Sets up two queues bound to an exchange with the appropriate routing keys.
        Each message is expected to contain a JSON body with an ``invoice_token`` field.
        """
        # TODO: implement
        # 1. Connect to RabbitMQ using aio_pika and RABBITMQ_URL
        # 2. Declare exchange (topic type)
        # 3. Declare and bind queue "invoice_repaid_updates" with routing key "loan.repaid"
        # 4. Declare and bind queue "invoice_loan_updates" with routing key "loan.overdue"
        # 5. Start consuming from both queues
        raise NotImplementedError

    async def _on_repaid(self, message: aio_pika.IncomingMessage):
        """Handle a loan.repaid event by setting the invoice status to REPAID.

        Args:
            message: The incoming RabbitMQ message containing invoice_token in its JSON body.
        """
        # TODO: implement
        # 1. Parse message body as JSON
        # 2. Extract invoice_token
        # 3. Open a DB session and call InvoiceService.update_status(token, "REPAID")
        # 4. Acknowledge the message
        raise NotImplementedError

    async def _on_overdue(self, message: aio_pika.IncomingMessage):
        """Handle a loan.overdue event by setting the invoice status to DEFAULTED.

        Args:
            message: The incoming RabbitMQ message containing invoice_token in its JSON body.
        """
        # TODO: implement
        # 1. Parse message body as JSON
        # 2. Extract invoice_token
        # 3. Open a DB session and call InvoiceService.update_status(token, "DEFAULTED")
        # 4. Acknowledge the message
        raise NotImplementedError

    async def stop(self):
        """Gracefully close the RabbitMQ connection."""
        if self.connection:
            await self.connection.close()
