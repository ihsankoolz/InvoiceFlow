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
            # Import generated stubs (created at Docker build time)
            from app.proto import payment_pb2_grpc  # noqa: PLC0415

            self._channel = grpc.aio.insecure_channel(config.PAYMENT_SERVICE_GRPC)
            self._stub = payment_pb2_grpc.PaymentServiceStub(self._channel)
        return self._stub

    async def lock_escrow(
        self,
        investor_id: int,
        invoice_token: str,
        amount: float,
        idempotency_key: str,
    ) -> dict:
        """
        Lock escrow for a bid via gRPC LockEscrow RPC.

        Raises grpc.aio.AioRpcError on failure (e.g., insufficient balance).
        The BidOrchestrator catches this and rolls back the bid.
        """
        from app.proto import payment_pb2  # noqa: PLC0415

        stub = await self._get_stub()
        request = payment_pb2.LockEscrowRequest(
            investor_id=investor_id,
            invoice_token=invoice_token,
            amount=str(amount),
            idempotency_key=idempotency_key,
        )
        response = await stub.LockEscrow(request)
        return {
            "id": response.id,
            "status": response.status,
            "amount": response.amount,
        }

    async def close(self):
        if self._channel:
            await self._channel.close()
