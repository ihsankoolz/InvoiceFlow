"""
Tests for anti-snipe deadline extension in AuctionCloseWorkflow.

Covers the extend_deadline signal path — the signal carries a new deadline ISO
string and the workflow must re-sleep until that deadline before settling.

Three scenarios:
  1. Single extension   — one signal delays settlement; auction.closed.winner published after
  2. Multiple extensions — two back-to-back signals each further extend the deadline
  3. Zero bids + extend  — signal received but no bids → auction.expired, not settled
"""

import sys
import types
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub heavy dependencies before importing the workflow module.
# ---------------------------------------------------------------------------

_STUBBED_MODS = [
    "grpc",
    "tenacity",
    "clients",
    "clients.grpc_client",
    "clients.http_client",
    "activities",
    "activities.payment_activities",
    "activities.invoice_activities",
    "activities.marketplace_activities",
    "activities.rabbitmq_activities",
    "activities.bidding_activities",
]
_previously_present = {m for m in _STUBBED_MODS if m in sys.modules}
for _mod in _STUBBED_MODS:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

_config_orig = sys.modules.get("config")
_config = types.ModuleType("config")
_config.ANTI_SNIPE_SECONDS = 300
_config.REPAYMENT_WINDOW_SECONDS = 30
_config.DEMO_MODE = False
_config.DEMO_LOAN_MATURITY_SECONDS = 90
_config.DEMO_REPAYMENT_WINDOW_SECONDS = 60
sys.modules["config"] = _config

from workflows.auction_close import AuctionCloseWorkflow  # noqa: E402

for _mod in _STUBBED_MODS:
    if _mod not in _previously_present:
        sys.modules.pop(_mod, None)
if _config_orig is not None:
    sys.modules["config"] = _config_orig
else:
    sys.modules.pop("config", None)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

INVOICE_TOKEN = "INV-SNIPE-001"
SELLER_ID = 10
INVESTOR_A = 1
INVESTOR_B = 2

_INVOICE = {
    "invoice_token": INVOICE_TOKEN,
    "seller_id": SELLER_ID,
    "status": "LISTED",
    "due_date": "2026-12-31T00:00:00",
    "amount": 7000.0,
}
_LOAN = {"loan_id": "loan-snipe-123", "due_date": "2026-12-31T00:00:00", "bid_amount": 5000.0}
_OFFER_A = {"id": 1, "investor_id": INVESTOR_A, "bid_amount": 5000.0, "status": "PENDING"}
_OFFER_B = {"id": 2, "investor_id": INVESTOR_B, "bid_amount": 3000.0, "status": "PENDING"}


# ---------------------------------------------------------------------------
# Mock builder
# ---------------------------------------------------------------------------


def _build_mock(offers: list):
    now_dt = datetime.now(timezone.utc)
    activity_calls: list[tuple] = []
    child_calls: list[dict] = []

    async def fake_execute_activity(fn, *, args, **kwargs):
        name = getattr(fn, "_mock_name", None) or getattr(fn, "__name__", str(fn))
        activity_calls.append((name, list(args)))
        if name == "get_offers":
            return offers
        if name == "verify_invoice":
            return _INVOICE
        if name == "get_user":
            return {"id": args[0], "email": f"user{args[0]}@test.com"}
        if name == "create_loan":
            return _LOAN
        if name == "convert_escrow_to_loan":
            return {"status": "CONVERTED"}
        if name == "release_funds_to_seller":
            return {"success": True}
        if name == "release_escrow":
            return {"status": "RELEASED"}
        return {}

    async def fake_start_child_workflow(fn, args, *, id, parent_close_policy):
        child_calls.append({"id": id, "args": list(args)})
        return MagicMock()

    mock = MagicMock()
    mock.now.return_value = now_dt
    mock.sleep = AsyncMock()
    mock.execute_activity = fake_execute_activity
    mock.start_child_workflow = fake_start_child_workflow
    mock.ParentClosePolicy = MagicMock()
    mock.ParentClosePolicy.ABANDON = "ABANDON"

    return mock, activity_calls, child_calls, now_dt


# ===========================================================================
# Test 1: Single extension — settlement fires after the extended deadline
# ===========================================================================


@pytest.mark.asyncio
async def test_single_extend_signal_delays_settlement():
    """
    One extend_deadline signal during the final sleep must cause the workflow
    to re-sleep and only then settle — auction.closed.winner published after both sleeps.
    """
    mock_wf, activity_calls, child_calls, now_dt = _build_mock(offers=[_OFFER_A, _OFFER_B])

    extended_deadline = now_dt + timedelta(seconds=30)
    sleep_count = 0

    async def fake_sleep(duration):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count == 1:
            # Simulate signal arriving during the original deadline sleep
            wf.new_deadline = extended_deadline

    mock_wf.sleep = AsyncMock(side_effect=fake_sleep)

    with patch("workflows.auction_close.workflow", mock_wf):
        wf = AuctionCloseWorkflow()
        await wf.run(INVOICE_TOKEN, bid_period_hours=0.5)

    # Workflow must have slept twice: once for original deadline, once for extended
    assert sleep_count == 2

    published = [args[0] for name, args in activity_calls if name == "publish_event"]
    assert "auction.closed.winner" in published
    assert "auction.closed.loser" in published

    # Settlement still runs correctly after the extension
    names = [name for name, _ in activity_calls]
    assert "convert_escrow_to_loan" in names
    assert "create_loan" in names
    assert "release_funds_to_seller" in names
    assert len(child_calls) == 1


# ===========================================================================
# Test 2: Multiple extensions — each signal further extends the deadline
# ===========================================================================


@pytest.mark.asyncio
async def test_multiple_extend_signals_each_extend_deadline():
    """
    Two back-to-back extend_deadline signals must each push the deadline further —
    the workflow sleeps a third time and only settles after the last extension expires.
    """
    mock_wf, activity_calls, child_calls, now_dt = _build_mock(offers=[_OFFER_A, _OFFER_B])

    first_extension = now_dt + timedelta(seconds=30)
    second_extension = now_dt + timedelta(seconds=60)
    sleep_count = 0

    async def fake_sleep(duration):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count == 1:
            wf.new_deadline = first_extension
        elif sleep_count == 2:
            wf.new_deadline = second_extension
        # Third sleep: no signal — workflow breaks and settles

    mock_wf.sleep = AsyncMock(side_effect=fake_sleep)

    with patch("workflows.auction_close.workflow", mock_wf):
        wf = AuctionCloseWorkflow()
        await wf.run(INVOICE_TOKEN, bid_period_hours=0.5)

    assert sleep_count == 3

    published = [args[0] for name, args in activity_calls if name == "publish_event"]
    assert "auction.closed.winner" in published
    assert len(child_calls) == 1


# ===========================================================================
# Test 3: Zero bids + extension — still expires, no settlement
# ===========================================================================


@pytest.mark.asyncio
async def test_extend_signal_with_zero_bids_still_expires():
    """
    extend_deadline signal received but no bids placed — after the extended sleep
    the workflow must still publish auction.expired and skip financial settlement.
    """
    mock_wf, activity_calls, child_calls, now_dt = _build_mock(offers=[])

    extended_deadline = now_dt + timedelta(seconds=30)
    sleep_count = 0

    async def fake_sleep(duration):
        nonlocal sleep_count
        sleep_count += 1
        if sleep_count == 1:
            wf.new_deadline = extended_deadline

    mock_wf.sleep = AsyncMock(side_effect=fake_sleep)

    with patch("workflows.auction_close.workflow", mock_wf):
        wf = AuctionCloseWorkflow()
        await wf.run(INVOICE_TOKEN, bid_period_hours=0.5)

    assert sleep_count == 2

    published = [args[0] for name, args in activity_calls if name == "publish_event"]
    assert "auction.expired" in published
    assert "auction.closed.winner" not in published

    settlement_names = {"convert_escrow_to_loan", "create_loan", "release_funds_to_seller"}
    called = {name for name, _ in activity_calls}
    assert called.isdisjoint(settlement_names)
    assert len(child_calls) == 0
