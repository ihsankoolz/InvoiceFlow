"""
LoanOrchestrator — orchestrates Scenario 3 loan repayment flow.

See BUILD_INSTRUCTIONS_V2.md Section 10 — LoanOrchestrator
"""

from fastapi import HTTPException

from app import config
from app.schemas.requests import RepayLoanRequest, RepaymentResponse
from app.services.grpc_client import PaymentGRPCClient
from app.services.http_client import HTTPClient
from app.services.rabbitmq_publisher import RabbitMQPublisher


class LoanOrchestrator:
    """Orchestrates loan repayment: Stripe checkout → confirm → publish loan.repaid."""

    def __init__(self):
        self.grpc_client = PaymentGRPCClient()
        self.http_client = HTTPClient()
        self.publisher = RabbitMQPublisher(config.RABBITMQ_URL)

    async def initiate_repayment(self, loan_id: int, data: RepayLoanRequest) -> dict:
        """
        Initiate loan repayment via Stripe.

        Steps:
        1. Get loan details via gRPC get_loan(loan_id)
        2. Verify loan status is DUE — reject if not
        3. Create Stripe checkout session via Stripe Wrapper with type=loan_repayment
        4. Return { checkout_url: session.url }

        See BUILD_INSTRUCTIONS_V2.md Section 10 — LoanOrchestrator.initiate_repayment()
        """
        # TODO: Implement
        pass

    async def confirm_repayment(self, loan_id: int, stripe_session_id: str) -> RepaymentResponse:
        """
        Confirm repayment after Stripe payment succeeds.

        Steps:
        1. Update loan status to REPAID via gRPC update_loan_status(loan_id, "REPAID")
        2. Get full loan details via gRPC get_loan(loan_id)
        3. Publish loan.repaid event → four consumers react via choreography:
           - Invoice Service: update invoice status
           - Payment Service: release escrow / update records
           - User Service: set account_status back to ACTIVE
           - Notification Service: send repayment confirmation
        4. Return RepaymentResponse(status="REPAID", loan_id=loan_id)

        See BUILD_INSTRUCTIONS_V2.md Section 10 — LoanOrchestrator.confirm_repayment()
        """
        # TODO: Implement
        pass
