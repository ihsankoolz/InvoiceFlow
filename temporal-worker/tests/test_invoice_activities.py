import pytest
from unittest.mock import AsyncMock, patch
from temporalio.exceptions import ApplicationError

from activities.invoice_activities import verify_invoice, update_invoice_status


@pytest.mark.asyncio
async def test_verify_invoice_listed():
    with patch("activities.invoice_activities.http_client") as mock_client:
        mock_client.get = AsyncMock(return_value={"invoice_token": "tok-abc", "status": "LISTED"})
        result = await verify_invoice("tok-abc")

    assert result["status"] == "LISTED"


@pytest.mark.asyncio
async def test_verify_invoice_not_listed_raises():
    with patch("activities.invoice_activities.http_client") as mock_client:
        mock_client.get = AsyncMock(return_value={"invoice_token": "tok-abc", "status": "FINANCED"})

        with pytest.raises(ApplicationError, match="not available"):
            await verify_invoice("tok-abc")


@pytest.mark.asyncio
async def test_update_invoice_status():
    with patch("activities.invoice_activities.http_client") as mock_client:
        mock_client.patch = AsyncMock(return_value={"invoice_token": "tok-abc", "status": "FINANCED"})
        result = await update_invoice_status("tok-abc", "FINANCED")

    assert result["status"] == "FINANCED"
    mock_client.patch.assert_called_once_with(
        "http://invoice-service:5001/invoices/tok-abc/status",
        json={"status": "FINANCED"},
    )
