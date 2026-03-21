import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_get_offers():
    with patch("activities.bidding_activities.http_client") as mock_client:
        mock_client.get = AsyncMock(return_value=[{"bid_id": 1, "amount": 5000}])
        from activities.bidding_activities import get_offers
        result = await get_offers("tok-abc")

    assert len(result) == 1
    assert result[0]["bid_id"] == 1
    mock_client.get.assert_called_once_with(
        "http://bidding-service:5003/bids?invoice_token=tok-abc"
    )


@pytest.mark.asyncio
async def test_accept_offer():
    with patch("activities.bidding_activities.http_client") as mock_client:
        mock_client.patch = AsyncMock(return_value={"bid_id": 1, "status": "ACCEPTED"})
        from activities.bidding_activities import accept_offer
        result = await accept_offer(bid_id=1)

    assert result["status"] == "ACCEPTED"
    mock_client.patch.assert_called_once_with(
        "http://bidding-service:5003/bids/1",
        json={"status": "ACCEPTED"},
    )


@pytest.mark.asyncio
async def test_reject_offer():
    with patch("activities.bidding_activities.http_client") as mock_client:
        mock_client.patch = AsyncMock(return_value={"bid_id": 2, "status": "REJECTED"})
        from activities.bidding_activities import reject_offer
        result = await reject_offer(bid_id=2)

    assert result["status"] == "REJECTED"
    mock_client.patch.assert_called_once_with(
        "http://bidding-service:5003/bids/2",
        json={"status": "REJECTED"},
    )
