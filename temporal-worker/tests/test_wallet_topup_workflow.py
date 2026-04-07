"""
Workflow-level tests for WalletTopUpWorkflow.

Three scenarios:
  1. Happy path   — credit_wallet called, then get_user, then wallet.credited published
  2. Step order   — credit before publish (no event until wallet is actually credited)
  3. Payload      — wallet.credited event contains investor_id, investor_email, amount
"""

import sys
from unittest.mock import MagicMock, patch

import pytest

_STUBBED_MODS = [
    "grpc",
    "tenacity",
    "clients",
    "clients.grpc_client",
    "clients.http_client",
    "activities",
    "activities.payment_activities",
    "activities.invoice_activities",
    "activities.rabbitmq_activities",
]
_previously_present = {m for m in _STUBBED_MODS if m in sys.modules}
for _mod in _STUBBED_MODS:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from workflows.wallet_topup import WalletTopUpWorkflow  # noqa: E402

for _mod in _STUBBED_MODS:
    if _mod not in _previously_present:
        sys.modules.pop(_mod, None)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

USER_ID = 7
AMOUNT = 500.0


# ---------------------------------------------------------------------------
# Mock builder
# ---------------------------------------------------------------------------


def _build_mock():
    activity_calls: list[tuple] = []

    async def fake_execute_activity(fn, *, args, **kwargs):
        name = getattr(fn, "_mock_name", None) or getattr(fn, "__name__", str(fn))
        activity_calls.append((name, list(args)))
        if name == "get_user":
            return {"id": args[0], "email": f"user{args[0]}@test.com"}
        return {}

    mock = MagicMock()
    mock.execute_activity = fake_execute_activity
    return mock, activity_calls


# ---------------------------------------------------------------------------
# Test 1: Happy path — all three steps execute
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_executes_all_steps():
    """credit_wallet, get_user, and publish_event all called."""
    mock_wf, activity_calls = _build_mock()

    with patch("workflows.wallet_topup.workflow", mock_wf):
        wf = WalletTopUpWorkflow()
        await wf.run(USER_ID, AMOUNT)

    names = [name for name, _ in activity_calls]
    assert "credit_wallet" in names
    assert "get_user" in names
    assert "publish_event" in names


# ---------------------------------------------------------------------------
# Test 2: credit_wallet called before publish_event
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_credit_before_publish():
    """Wallet is credited before event is published."""
    mock_wf, activity_calls = _build_mock()

    with patch("workflows.wallet_topup.workflow", mock_wf):
        wf = WalletTopUpWorkflow()
        await wf.run(USER_ID, AMOUNT)

    names = [name for name, _ in activity_calls]
    assert names.index("credit_wallet") < names.index("publish_event")


# ---------------------------------------------------------------------------
# Test 3: wallet.credited event payload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wallet_credited_event_payload():
    """wallet.credited event contains investor_id, investor_email, and amount."""
    mock_wf, activity_calls = _build_mock()

    with patch("workflows.wallet_topup.workflow", mock_wf):
        wf = WalletTopUpWorkflow()
        await wf.run(USER_ID, AMOUNT)

    publish_calls = [(name, args) for name, args in activity_calls if name == "publish_event"]
    assert len(publish_calls) == 1

    routing_key, payload = publish_calls[0][1]
    assert routing_key == "wallet.credited"
    assert payload["investor_id"] == USER_ID
    assert payload["investor_email"] == f"user{USER_ID}@test.com"
    assert payload["amount"] == AMOUNT
