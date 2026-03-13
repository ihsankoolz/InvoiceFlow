"""
PaymentGRPCClient — wraps gRPC calls to Payment Service.

See BUILD_INSTRUCTIONS_V2.md Section 10 — PaymentGRPCClient
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
        """
        # TODO: Implement
        pass

    async def get_loan(self, loan_id: int) -> dict:
        """
        Get loan details via gRPC GetLoan RPC.

        See proto/payment.proto — GetLoan RPC
        """
        # TODO: Implement
        pass

    async def update_loan_status(self, loan_id: int, status: str) -> dict:
        """
        Update loan status via gRPC UpdateLoanStatus RPC.

        See proto/payment.proto — UpdateLoanStatus RPC
        """
        # TODO: Implement
        pass
