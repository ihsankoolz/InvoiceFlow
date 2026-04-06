from unittest.mock import AsyncMock, MagicMock, patch

import activities.rabbitmq_activities  # ensure module is in sys.modules before patch resolves it
import pytest
from activities.rabbitmq_activities import publish_event


def _make_aio_pika_mock():
    """Build a mock aio_pika that satisfies the async-with connection pattern."""
    exchange = MagicMock()
    exchange.publish = AsyncMock()

    channel = MagicMock()
    channel.declare_exchange = AsyncMock(return_value=exchange)

    connection = AsyncMock()
    connection.channel = AsyncMock(return_value=channel)
    # Support `async with connection:`
    connection.__aenter__ = AsyncMock(return_value=connection)
    connection.__aexit__ = AsyncMock(return_value=False)

    mock_aio_pika = MagicMock()
    mock_aio_pika.connect_robust = AsyncMock(return_value=connection)
    mock_aio_pika.ExchangeType = MagicMock(TOPIC="topic")
    mock_aio_pika.Message = MagicMock(side_effect=lambda body, **kw: MagicMock(body=body))

    return mock_aio_pika, exchange


@pytest.mark.asyncio
async def test_publish_event_calls_exchange():
    mock_aio_pika, exchange = _make_aio_pika_mock()

    with patch("activities.rabbitmq_activities.aio_pika", mock_aio_pika):
        await publish_event("loan.due", {"loan_id": "loan-123"})

    exchange.publish.assert_called_once()
    _, kwargs = exchange.publish.call_args
    assert kwargs["routing_key"] == "loan.due"


@pytest.mark.asyncio
async def test_publish_event_serializes_payload():
    import json

    mock_aio_pika, exchange = _make_aio_pika_mock()

    captured = {}

    def capture_message(body, **kw):
        captured["body"] = body
        return MagicMock(body=body)

    mock_aio_pika.Message = MagicMock(side_effect=capture_message)

    with patch("activities.rabbitmq_activities.aio_pika", mock_aio_pika):
        await publish_event("loan.overdue", {"loan_id": "loan-456", "investor_id": 1})

    assert json.loads(captured["body"]) == {"loan_id": "loan-456", "investor_id": 1}
