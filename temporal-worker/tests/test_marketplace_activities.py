from unittest.mock import AsyncMock, patch

import pytest
from activities.marketplace_activities import bulk_delist, delist_listing


@pytest.mark.asyncio
async def test_delist_listing():
    with patch("activities.marketplace_activities.http_client") as mock_client:
        mock_client.delete = AsyncMock(return_value={"status": "DELISTED"})
        result = await delist_listing("tok-abc")

    assert result["status"] == "DELISTED"
    mock_client.delete.assert_called_once_with(
        "http://marketplace-service:5002/listings/by-token/tok-abc",
    )


@pytest.mark.asyncio
async def test_bulk_delist():
    with patch("activities.marketplace_activities.http_client") as mock_client:
        mock_client.delete = AsyncMock(return_value={})
        result = await bulk_delist(seller_id=42)

    assert result == {}
    mock_client.delete.assert_called_once_with(
        "http://marketplace-service:5002/listings/?seller_id=42",
    )
