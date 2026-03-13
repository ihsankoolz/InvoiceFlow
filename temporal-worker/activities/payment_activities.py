"""
Payment-related Temporal activities.
ALL Payment Service calls use gRPC exclusively — no HTTP fallback.

See BUILD_INSTRUCTIONS_V2.md Section 13 — Activities
"""

from temporalio import activity

from clients.grpc_client import PaymentGRPCClient

grpc_client = PaymentGRPCClient()


@activity.defn
async def convert_escrow_to_loan(investor_id: int, invoice_token: str) -> dict:
    """
    Convert locked escrow to loan via gRPC ConvertEscrowToLoan RPC.

    See proto/payment.proto — ConvertEscrowToLoan
    """
    # TODO: Implement
    pass


@activity.defn
async def create_loan(investor_id: int, seller_id: int, invoice_token: str, principal: float, due_date: str) -> dict:
    """
    Create a loan record via gRPC CreateLoan RPC.

    Returns loan dict with loan_id and due_date.

    See proto/payment.proto — CreateLoan
    """
    # TODO: Implement
    pass


@activity.defn
async def release_funds_to_seller(seller_id: int, amount: float, invoice_token: str) -> dict:
    """
    Release funds to seller's wallet via gRPC ReleaseFundsToSeller RPC.

    See proto/payment.proto — ReleaseFundsToSeller
    """
    # TODO: Implement
    pass


@activity.defn
async def get_loan_grpc(loan_id: str) -> dict:
    """
    Get loan details via gRPC GetLoan RPC.
    Used by LoanMaturityWorkflow to check loan status after repayment window.

    See proto/payment.proto — GetLoan
    """
    # TODO: Implement
    pass


@activity.defn
async def update_loan_status_grpc(loan_id: str, status: str) -> dict:
    """
    Update loan status via gRPC UpdateLoanStatus RPC.
    Used by LoanMaturityWorkflow to mark loan DUE or OVERDUE.

    See proto/payment.proto — UpdateLoanStatus
    """
    # TODO: Implement
    pass


@activity.defn
async def credit_wallet(user_id: int, amount: float) -> dict:
    """
    Credit investor wallet via gRPC CreditWallet RPC.
    Used by WalletTopUpWorkflow after Stripe payment confirmation.

    See proto/payment.proto — CreditWallet
    """
    # TODO: Implement
    pass
