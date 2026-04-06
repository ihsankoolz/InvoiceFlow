"""
Payment-related Temporal activities.
ALL Payment Service calls use gRPC exclusively — no HTTP fallback.
"""

from clients.grpc_client import PaymentGRPCClient
from temporalio import activity

grpc_client = PaymentGRPCClient()


@activity.defn
async def convert_escrow_to_loan(investor_id: int, invoice_token: str) -> dict:
    """Convert locked escrow to loan via gRPC ConvertEscrowToLoan RPC."""
    return await grpc_client.convert_escrow(
        investor_id=investor_id,
        invoice_token=invoice_token,
        idempotency_key=f"convert-{invoice_token}-{investor_id}",
    )


@activity.defn
async def create_loan(
    investor_id: int,
    seller_id: int,
    invoice_token: str,
    principal: float,
    bid_amount: float,
    due_date: str,
) -> dict:
    """Create a loan record via gRPC CreateLoan RPC. Returns loan dict with loan_id and due_date."""
    return await grpc_client.create_loan(
        investor_id=investor_id,
        seller_id=seller_id,
        invoice_token=invoice_token,
        principal=principal,
        bid_amount=bid_amount,
        due_date=due_date,
    )


@activity.defn
async def release_funds_to_seller(seller_id: int, amount: float, invoice_token: str) -> dict:
    """Release funds to seller's wallet via gRPC ReleaseFundsToSeller RPC."""
    return await grpc_client.release_funds(
        seller_id=seller_id,
        amount=amount,
        invoice_token=invoice_token,
    )


@activity.defn
async def get_loan_grpc(loan_id: str) -> dict:
    """Get loan details via gRPC GetLoan RPC. Used by LoanMaturityWorkflow."""
    return await grpc_client.get_loan(loan_id=loan_id)


@activity.defn
async def update_loan_status_grpc(loan_id: str, status: str) -> dict:
    """Update loan status via gRPC UpdateLoanStatus RPC. Used by LoanMaturityWorkflow."""
    return await grpc_client.update_loan_status(loan_id=loan_id, status=status)


@activity.defn
async def credit_wallet(user_id: int, amount: float) -> dict:
    """Credit investor wallet via gRPC CreditWallet RPC. Used by WalletTopUpWorkflow."""
    return await grpc_client.credit_wallet(user_id=user_id, amount=amount)


@activity.defn
async def release_escrow(investor_id: int, invoice_token: str, idempotency_key: str) -> dict:
    """Release locked escrow back to investor wallet via gRPC ReleaseEscrow RPC."""
    return await grpc_client.release_escrow(
        investor_id=investor_id,
        invoice_token=invoice_token,
        idempotency_key=idempotency_key,
    )
