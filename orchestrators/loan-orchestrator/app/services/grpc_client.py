"""
PaymentGRPCClient — wraps gRPC calls to Payment Service.

Uses grpc.aio (async gRPC) so it fits naturally in FastAPI's async request handlers.
Proto stubs are generated at Docker build time into app/proto/.
"""

import grpc
import grpc.aio

from app import config


class PaymentGRPCClient:
    """Async gRPC client for Payment Service at payment-service:50051."""

    def __init__(self):
        self._channel: grpc.aio.Channel | None = None
        self._stub = None

    async def _get_stub(self):
        """Lazily connect and return the gRPC stub."""
        if self._stub is None:
            from app.proto import payment_pb2_grpc  # noqa: PLC0415

            self._channel = grpc.aio.insecure_channel(config.PAYMENT_SERVICE_GRPC)
            self._stub = payment_pb2_grpc.PaymentServiceStub(self._channel)
        return self._stub

    async def get_loan(self, loan_id: str) -> dict:
        """Get loan details via gRPC GetLoan RPC."""
        from app.proto import payment_pb2  # noqa: PLC0415

        stub = await self._get_stub()
        request = payment_pb2.GetLoanRequest(loan_id=str(loan_id))
        response = await stub.GetLoan(request)
        return {
            "loan_id": response.loan_id,
            "status": response.status,
            "principal": response.principal,
            "due_date": response.due_date,
            "investor_id": response.investor_id,
            "seller_id": response.seller_id,
            "invoice_token": response.invoice_token,
        }

    async def update_loan_status(self, loan_id: str, status: str) -> dict:
        """Update loan status via gRPC UpdateLoanStatus RPC."""
        from app.proto import payment_pb2  # noqa: PLC0415

        stub = await self._get_stub()
        request = payment_pb2.UpdateLoanStatusRequest(
            loan_id=str(loan_id),
            status=status,
        )
        response = await stub.UpdateLoanStatus(request)
        return {
            "loan_id": response.loan_id,
            "status": response.status,
            "principal": response.principal,
            "due_date": response.due_date,
            "investor_id": response.investor_id,
            "seller_id": response.seller_id,
        }

    async def close(self):
        if self._channel:
            await self._channel.close()
