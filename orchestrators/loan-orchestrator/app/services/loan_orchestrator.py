"""
LoanOrchestrator — orchestrates Scenario 3 loan repayment flow.
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

    async def initiate_repayment(self, loan_id: str, data: RepayLoanRequest) -> dict:
        """
        Initiate loan repayment via Stripe.

        Steps:
        1. Get loan details via gRPC
        2. Verify loan status is DUE
        3. Create Stripe checkout session via Stripe Wrapper
        4. Return checkout_url
        """
        # ── Step 1: Get loan details ───────────────────────────────────────
        loan = await self.grpc_client.get_loan(loan_id)

        # ── Step 2: Verify loan is repayable ──────────────────────────────
        if loan["status"] not in ("DUE", "OVERDUE"):
            raise HTTPException(
                status_code=400,
                detail=f"Loan {loan_id} is not due for repayment (status: {loan['status']})",
            )

        # ── Step 3: Create Stripe checkout session ─────────────────────────
        session = await self.http_client.post(
            f"{config.STRIPE_WRAPPER_URL}/create-checkout-session",
            json={
                "amount": float(loan["principal"]),
                "user_id": data.seller_id,
                "type": "loan_repayment",
                "loan_id": str(loan_id),
            },
        )

        # ── Step 4: Return checkout URL ────────────────────────────────────
        return {"checkout_url": session["url"]}

    async def confirm_repayment(self, loan_id: str, stripe_session_id: str) -> RepaymentResponse:
        """
        Confirm repayment after Stripe payment succeeds.

        Steps:
        1. Update loan status to REPAID via gRPC
        2. Get full loan details via gRPC
        3. Publish loan.repaid event
        4. Return RepaymentResponse
        """
        # ── Step 1: Update loan status to REPAID ──────────────────────────
        await self.grpc_client.update_loan_status(loan_id, "REPAID")

        # ── Step 2: Get full loan details ──────────────────────────────────
        loan = await self.grpc_client.get_loan(loan_id)

        # ── Step 3: Publish loan.repaid event ─────────────────────────────
        # Consumers: Invoice Service, Payment Service, User Service, Notification Service
        seller = await self.http_client.get(f"{config.USER_SERVICE_URL}/users/{loan['seller_id']}")
        investor = await self.http_client.get(f"{config.USER_SERVICE_URL}/users/{loan['investor_id']}")
        await self.publisher.publish(
            "loan.repaid",
            {
                "loan_id": str(loan_id),
                "invoice_token": loan["invoice_token"],
                "seller_id": loan["seller_id"],
                "seller_email": seller["email"],
                "investor_id": loan["investor_id"],
                "investor_email": investor["email"],
                "principal": loan["principal"],
                "stripe_session_id": stripe_session_id,
            },
        )

        # ── Step 4: Return response ────────────────────────────────────────
        return RepaymentResponse(status="REPAID", loan_id=loan_id)
