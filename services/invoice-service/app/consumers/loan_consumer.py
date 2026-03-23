import json
import logging

import aio_pika

from app.config import RABBITMQ_URL
from app.database import SessionLocal
from app.services.invoice_service import InvoiceService

logger = logging.getLogger(__name__)


class LoanEventConsumer:
    """RabbitMQ consumer that listens for loan-lifecycle events and updates invoice statuses."""

    def __init__(self):
        self.connection = None
        self.channel = None

    async def start(self):
        """Connect to RabbitMQ, declare queues, and begin consuming messages."""
        self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
        self.channel = await self.connection.channel()

        # Topic exchange for system-wide events
        exchange = await self.channel.declare_exchange(
            "invoiceflow_events", aio_pika.ExchangeType.TOPIC, durable=True
        )

        # 1. Repaid Queue
        repaid_queue = await self.channel.declare_queue("invoice_repaid_updates", durable=True)
        await repaid_queue.bind(exchange, routing_key="loan.repaid")
        await repaid_queue.consume(self._on_repaid)

        # 2. Overdue Queue
        loan_queue = await self.channel.declare_queue("invoice_loan_updates", durable=True)
        await loan_queue.bind(exchange, routing_key="loan.overdue")
        await loan_queue.consume(self._on_overdue)

        logger.info("LoanEventConsumer started and connected to RabbitMQ.")

    async def _on_repaid(self, message: aio_pika.IncomingMessage):
        """Handle a loan.repaid event by setting the invoice status to REPAID."""
        async with message.process():
            try:
                data = json.loads(message.body.decode())
                invoice_token = data.get("invoice_token")
                if not invoice_token:
                    logger.error("Message missing invoice_token")
                    return

                with SessionLocal() as db:
                    service = InvoiceService(db)
                    service.update_status(invoice_token, "REPAID")
                    logger.info(f"Invoice {invoice_token} status updated to REPAID via choreography.")
            except Exception as e:
                logger.error(f"Error processing loan.repaid: {e}")

    async def _on_overdue(self, message: aio_pika.IncomingMessage):
        """Handle a loan.overdue event by setting the invoice status to DEFAULTED."""
        async with message.process():
            try:
                data = json.loads(message.body.decode())
                invoice_token = data.get("invoice_token")
                if not invoice_token:
                    logger.error("Message missing invoice_token")
                    return

                with SessionLocal() as db:
                    service = InvoiceService(db)
                    service.update_status(invoice_token, "DEFAULTED")
                    logger.info(f"Invoice {invoice_token} status updated to DEFAULTED via choreography.")
            except Exception as e:
                logger.error(f"Error processing loan.overdue: {e}")

    async def stop(self):
        """Gracefully close the RabbitMQ connection."""
        if self.connection:
            await self.connection.close()
