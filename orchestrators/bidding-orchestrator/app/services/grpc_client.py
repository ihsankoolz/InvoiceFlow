"""
PaymentGRPCClient — wraps gRPC calls to Payment Service.

See BUILD_INSTRUCTIONS_V2.md Section 9 — PaymentGRPCClient
"""

from app import config


class PaymentGRPCClient:
    """gRPC client for Payment Service at payment-service:50051."""

    def __init__(self):
        self.channel = None
        self.stub = None

    async def connect(self):
        """
        Connect to Payment Service gRPC server.

        Steps:
        1. Import grpc and payment_pb2, payment_pb2_grpc
        2. Create insecure channel to config.PAYMENT_SERVICE_GRPC
        3. Create PaymentServiceStub

        See BUILD_INSTRUCTIONS_V2.md Section 9 — PaymentGRPCClient
        """
        # TODO: Implement
        pass

    async def lock_escrow(self, investor_id: int, invoice_token: str, amount: float, idempotency_key: str) -> dict:
        """
        Lock escrow for a bid via gRPC LockEscrow RPC.

        Args:
            investor_id: Investor placing the bid
            invoice_token: Invoice being bid on
            amount: Bid amount to lock
            idempotency_key: Unique key for idempotent escrow creation (e.g., "escrow-{bid_id}")

        See proto/payment.proto — LockEscrow RPC
        """
        # TODO: Implement
        pass
