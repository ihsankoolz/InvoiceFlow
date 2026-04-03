"""
Tests for previously untested activities: get_user and release_escrow.
"""

from unittest.mock import AsyncMock, patch

import pytest
from activities.invoice_activities import get_user
from activities.payment_activities import release_escrow

# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_user_returns_user_dict():
    """get_user calls User Service and returns the user dict."""
    with patch("activities.invoice_activities.http_client") as mock_client:
        mock_client.get = AsyncMock(return_value={
            "id": 42, "email": "investor@test.com", "full_name": "Test User", "role": "INVESTOR",
        })
        result = await get_user(42)

    assert result["id"] == 42
    assert result["email"] == "investor@test.com"
    mock_client.get.assert_called_once_with("http://user-service:5000/users/42")


@pytest.mark.asyncio
async def test_get_user_passes_correct_url_for_different_id():
    """get_user constructs the correct URL from the user_id argument."""
    with patch("activities.invoice_activities.http_client") as mock_client:
        mock_client.get = AsyncMock(return_value={"id": 99, "email": "seller@test.com"})
        await get_user(99)

    mock_client.get.assert_called_once_with("http://user-service:5000/users/99")


# ---------------------------------------------------------------------------
# release_escrow
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_release_escrow_calls_grpc_with_correct_args():
    """release_escrow forwards all three arguments to grpc_client.release_escrow."""
    with patch("activities.payment_activities.grpc_client") as mock_client:
        mock_client.release_escrow = AsyncMock(return_value={"status": "RELEASED"})
        result = await release_escrow(
            investor_id=3,
            invoice_token="INV-TOK-XYZ",
            idempotency_key="release-loser-7",
        )

    assert result["status"] == "RELEASED"
    mock_client.release_escrow.assert_called_once_with(
        investor_id=3,
        invoice_token="INV-TOK-XYZ",
        idempotency_key="release-loser-7",
    )


@pytest.mark.asyncio
async def test_release_escrow_idempotency_key_passed_through():
    """Idempotency key is forwarded unchanged — prevents double-release on Temporal retry."""
    key = "release-loser-42"
    with patch("activities.payment_activities.grpc_client") as mock_client:
        mock_client.release_escrow = AsyncMock(return_value={})
        await release_escrow(investor_id=1, invoice_token="tok-abc", idempotency_key=key)

    call_kwargs = mock_client.release_escrow.call_args.kwargs
    assert call_kwargs["idempotency_key"] == key
