"""
PaymentGRPCClient — gRPC client for Payment Service.
Used by payment_activities to call all 8 Payment Service RPCs.

ALL Payment Service calls from Temporal Worker use gRPC exclusively — no HTTP fallback.

See BUILD_INSTRUCTIONS_V2.md Section 13 — gRPC Client
See proto/payment.proto for service definition.
"""

import config


class PaymentGRPCClient:
    """gRPC client for Payment Service at payment-service:50051."""

    def __init__(self):
        self.channel = None
        self.stub = None

    async def connect(self):
        """
        Connect to Payment Service gRPC server.

        Steps:
        1. Import grpc and load payment.proto using grpc.protos_and_services
        2. Create insecure channel to config.PAYMENT_SERVICE_GRPC
        3. Create PaymentServiceStub

        See proto/payment.proto
        """
        # TODO: Implement
        pass

    async def convert_escrow(self, investor_id: int, invoice_token: str, idempotency_key: str) -> dict:
        """Call ConvertEscrowToLoan RPC."""
        # TODO: Implement
        pass

    async def create_loan(self, investor_id: int, seller_id: int, invoice_token: str, principal: float, due_date: str) -> dict:
        """Call CreateLoan RPC."""
        # TODO: Implement
        pass

    async def release_funds(self, seller_id: int, amount: float, invoice_token: str) -> dict:
        """Call ReleaseFundsToSeller RPC."""
        # TODO: Implement
        pass

    async def get_loan(self, loan_id: str) -> dict:
        """Call GetLoan RPC."""
        # TODO: Implement
        pass

    async def update_loan_status(self, loan_id: str, status: str) -> dict:
        """Call UpdateLoanStatus RPC."""
        # TODO: Implement
        pass

    async def credit_wallet(self, user_id: int, amount: float) -> dict:
        """Call CreditWallet RPC."""
        # TODO: Implement
        pass
