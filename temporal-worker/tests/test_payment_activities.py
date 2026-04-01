from unittest.mock import AsyncMock, patch

import pytest
from activities.payment_activities import (
    convert_escrow_to_loan,
    create_loan,
    credit_wallet,
    get_loan_grpc,
    release_funds_to_seller,
    update_loan_status_grpc,
)


@pytest.mark.asyncio
async def test_get_loan_grpc():
    with patch("activities.payment_activities.grpc_client") as mock_client:
        mock_client.get_loan = AsyncMock(return_value={
            "loan_id": "loan-123", "status": "ACTIVE", "principal": "5000.0",
            "due_date": "2026-04-01", "investor_id": 1, "seller_id": 2,
        })
        result = await get_loan_grpc("loan-123")

    assert result["loan_id"] == "loan-123"
    assert result["status"] == "ACTIVE"
    mock_client.get_loan.assert_called_once_with(loan_id="loan-123")


@pytest.mark.asyncio
async def test_update_loan_status_grpc():
    with patch("activities.payment_activities.grpc_client") as mock_client:
        mock_client.update_loan_status = AsyncMock(return_value={"loan_id": "loan-123", "status": "OVERDUE"})
        result = await update_loan_status_grpc("loan-123", "OVERDUE")

    assert result["status"] == "OVERDUE"
    mock_client.update_loan_status.assert_called_once_with(loan_id="loan-123", status="OVERDUE")


@pytest.mark.asyncio
async def test_create_loan():
    with patch("activities.payment_activities.grpc_client") as mock_client:
        mock_client.create_loan = AsyncMock(return_value={
            "loan_id": "loan-456", "status": "ACTIVE", "principal": "10000.0",
            "due_date": "2026-05-01", "investor_id": 3, "seller_id": 4,
        })
        result = await create_loan(
            investor_id=3, seller_id=4, invoice_token="tok-abc",
            principal=10000.0, due_date="2026-05-01",
        )

    assert result["loan_id"] == "loan-456"
    mock_client.create_loan.assert_called_once_with(
        investor_id=3, seller_id=4, invoice_token="tok-abc",
        principal=10000.0, due_date="2026-05-01",
    )


@pytest.mark.asyncio
async def test_convert_escrow_to_loan():
    with patch("activities.payment_activities.grpc_client") as mock_client:
        mock_client.convert_escrow = AsyncMock(return_value={"id": "escrow-1", "status": "CONVERTED", "amount": "5000.0"})
        result = await convert_escrow_to_loan(investor_id=1, invoice_token="tok-xyz")

    assert result["status"] == "CONVERTED"
    mock_client.convert_escrow.assert_called_once_with(
        investor_id=1,
        invoice_token="tok-xyz",
        idempotency_key="convert-tok-xyz-1",
    )


@pytest.mark.asyncio
async def test_release_funds_to_seller():
    with patch("activities.payment_activities.grpc_client") as mock_client:
        mock_client.release_funds = AsyncMock(return_value={"success": True, "message": "ok"})
        result = await release_funds_to_seller(seller_id=2, amount=5000.0, invoice_token="tok-abc")

    assert result["success"] is True
    mock_client.release_funds.assert_called_once_with(seller_id=2, amount=5000.0, invoice_token="tok-abc")


@pytest.mark.asyncio
async def test_credit_wallet():
    with patch("activities.payment_activities.grpc_client") as mock_client:
        mock_client.credit_wallet = AsyncMock(return_value={"user_id": 5, "balance": "15000.0"})
        result = await credit_wallet(user_id=5, amount=5000.0)

    assert result["user_id"] == 5
    mock_client.credit_wallet.assert_called_once_with(user_id=5, amount=5000.0)
