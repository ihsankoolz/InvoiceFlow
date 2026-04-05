"""
PaymentGRPCClient — gRPC client for Payment Service.
Used by payment_activities to call all Payment Service RPCs.

ALL Payment Service calls from Temporal Worker use gRPC exclusively — no HTTP fallback.

See proto/payment.proto for service definition.
"""

import grpc
import grpc.aio

import config


class PaymentGRPCClient:
    """Async gRPC client for Payment Service at payment-service:50051."""

    def __init__(self):
        self._channel: grpc.aio.Channel | None = None
        self._stub = None

    async def _get_stub(self):
        """Lazily connect and return the gRPC stub."""
        if self._stub is None:
            from proto import payment_pb2_grpc  # generated at Docker build time
            self._channel = grpc.aio.insecure_channel(config.PAYMENT_SERVICE_GRPC)
            self._stub = payment_pb2_grpc.PaymentServiceStub(self._channel)
        return self._stub

    async def convert_escrow(self, investor_id: int, invoice_token: str, idempotency_key: str) -> dict:
        """Call ConvertEscrowToLoan RPC."""
        from proto import payment_pb2
        stub = await self._get_stub()
        response = await stub.ConvertEscrowToLoan(payment_pb2.ConvertEscrowRequest(
            investor_id=investor_id,
            invoice_token=invoice_token,
            idempotency_key=idempotency_key,
        ))
        return {"id": response.id, "status": response.status, "amount": response.amount}

    async def create_loan(self, investor_id: int, seller_id: int, invoice_token: str,
                          principal: float, due_date: str) -> dict:
        """Call CreateLoan RPC."""
        from proto import payment_pb2
        stub = await self._get_stub()
        response = await stub.CreateLoan(payment_pb2.CreateLoanRequest(
            invoice_token=invoice_token,
            investor_id=investor_id,
            seller_id=seller_id,
            principal=str(principal),
            due_date=due_date,
            idempotency_key=f"loan-{invoice_token}",
        ))
        return {
            "loan_id": response.loan_id,
            "status": response.status,
            "principal": response.principal,
            "due_date": response.due_date,
            "investor_id": response.investor_id,
            "seller_id": response.seller_id,
        }

    async def release_funds(self, seller_id: int, amount: float, invoice_token: str) -> dict:
        """Call ReleaseFundsToSeller RPC."""
        from proto import payment_pb2
        stub = await self._get_stub()
        response = await stub.ReleaseFundsToSeller(payment_pb2.ReleaseFundsRequest(
            seller_id=seller_id,
            amount=str(amount),
            invoice_token=invoice_token,
            idempotency_key=f"release-{invoice_token}",
        ))
        return {"success": response.success, "message": response.message}

    async def get_loan(self, loan_id: str) -> dict:
        """Call GetLoan RPC."""
        from proto import payment_pb2
        stub = await self._get_stub()
        response = await stub.GetLoan(payment_pb2.GetLoanRequest(loan_id=loan_id))
        return {
            "loan_id": response.loan_id,
            "status": response.status,
            "principal": response.principal,
            "due_date": response.due_date,
            "investor_id": response.investor_id,
            "seller_id": response.seller_id,
        }

    async def update_loan_status(self, loan_id: str, status: str) -> dict:
        """Call UpdateLoanStatus RPC."""
        from proto import payment_pb2
        stub = await self._get_stub()
        response = await stub.UpdateLoanStatus(payment_pb2.UpdateLoanStatusRequest(
            loan_id=loan_id,
            status=status,
        ))
        return {"loan_id": response.loan_id, "status": response.status}

    async def credit_wallet(self, user_id: int, amount: float) -> dict:
        """Call CreditWallet RPC."""
        from proto import payment_pb2
        stub = await self._get_stub()
        response = await stub.CreditWallet(payment_pb2.CreditWalletRequest(
            user_id=user_id,
            amount=str(amount),
            idempotency_key=f"topup-{user_id}-{amount}",
        ))
        return {"user_id": response.user_id, "balance": response.balance}

    async def release_escrow(self, investor_id: int, invoice_token: str, idempotency_key: str) -> dict:
        """Call ReleaseEscrow RPC — returns funds from escrow to investor wallet."""
        from proto import payment_pb2
        stub = await self._get_stub()
        response = await stub.ReleaseEscrow(payment_pb2.ReleaseEscrowRequest(
            investor_id=investor_id,
            invoice_token=invoice_token,
            idempotency_key=idempotency_key,
        ))
        return {"id": response.id, "status": response.status, "amount": response.amount}
