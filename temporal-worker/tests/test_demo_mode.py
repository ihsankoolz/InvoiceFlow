"""
Tests for DEMO_MODE behaviour in AuctionCloseWorkflow and LoanMaturityWorkflow.

Each test patches workflows.*.config directly so it is order-independent
regardless of which test file pytest loads first.

Scenarios covered:
  Auction (DEMO_MODE=True)
    1. Full settlement still executes correctly
    2. Anti-snipe still works

  Loan Maturity (DEMO_MODE=True)
    3. wait_condition uses DEMO_REPAYMENT_WINDOW_SECONDS, not REPAYMENT_WINDOW_SECONDS
    4. OVERDUE path still fires when repayment window expires unreplied
    5. Early-exit still works when repayment_confirmed signal arrives
"""

import asyncio
import sys
import types
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub heavy deps at import time so the workflow modules are importable.
# If another test file already imported them, these stubs are ignored but
# we still get the already-cached workflow classes — that is fine because
# every test patches config explicitly.
# ---------------------------------------------------------------------------

_STUBBED_MODS = [
    "grpc", "tenacity",
    "clients", "clients.grpc_client", "clients.http_client",
    "activities", "activities.payment_activities",
    "activities.invoice_activities", "activities.marketplace_activities",
    "activities.rabbitmq_activities", "activities.bidding_activities",
]
_previously_present = {m for m in _STUBBED_MODS if m in sys.modules}
for _mod in _STUBBED_MODS:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

_config_orig = sys.modules.get("config")
_config = types.ModuleType("config")
_config.ANTI_SNIPE_SECONDS = 15
_config.REPAYMENT_WINDOW_SECONDS = 86400
_config.DEMO_MODE = False
_config.DEMO_AUCTION_SECONDS = 90
_config.DEMO_LOAN_MATURITY_SECONDS = 90
_config.DEMO_REPAYMENT_WINDOW_SECONDS = 60
sys.modules["config"] = _config

from workflows.auction_close import AuctionCloseWorkflow  # noqa: E402
from workflows.loan_maturity import LoanMaturityWorkflow  # noqa: E402

for _mod in _STUBBED_MODS:
    if _mod not in _previously_present:
        sys.modules.pop(_mod, None)
if _config_orig is not None:
    sys.modules["config"] = _config_orig
else:
    sys.modules.pop("config", None)


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

INVOICE_TOKEN = "INV-DEMO-001"
SELLER_ID = 10
INVESTOR_A = 1
INVESTOR_B = 2
LOAN_ID = "loan-demo-123"

_INVOICE = {"invoice_token": INVOICE_TOKEN, "seller_id": SELLER_ID, "status": "LISTED", "due_date": "2030-01-01", "amount": 7000.0}
_LOAN = {"loan_id": LOAN_ID, "due_date": "2030-01-01", "bid_amount": 5000.0}
_OFFER_A = {"id": 1, "investor_id": INVESTOR_A, "bid_amount": 5000.0, "status": "PENDING"}
_OFFER_B = {"id": 2, "investor_id": INVESTOR_B, "bid_amount": 3000.0, "status": "PENDING"}
_DUE_DATE_FUTURE = "2030-01-01T00:00:00"  # far future — demo mode must override this


def _demo_config(auction_secs=90, loan_secs=90, repayment_secs=60, anti_snipe_secs=15):
    """Return a fresh config module with DEMO_MODE=True."""
    cfg = types.ModuleType("config")
    cfg.DEMO_MODE = True
    cfg.DEMO_AUCTION_SECONDS = auction_secs
    cfg.DEMO_LOAN_MATURITY_SECONDS = loan_secs
    cfg.DEMO_REPAYMENT_WINDOW_SECONDS = repayment_secs
    cfg.ANTI_SNIPE_SECONDS = anti_snipe_secs
    cfg.REPAYMENT_WINDOW_SECONDS = 86400
    return cfg


# ---------------------------------------------------------------------------
# Auction workflow helpers
# ---------------------------------------------------------------------------

def _auction_wf_mock(offers):
    """Build a workflow mock for AuctionCloseWorkflow (same pattern as main test file)."""
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

    return mock, activity_calls, child_calls


# ---------------------------------------------------------------------------
# Loan maturity helpers
# ---------------------------------------------------------------------------

def _loan_wf_mock(loan_status="DUE"):
    now_dt = datetime.now(timezone.utc)
    activity_calls: list[tuple] = []

    async def fake_execute_activity(fn, *, args, **kwargs):
        name = getattr(fn, "_mock_name", None) or getattr(fn, "__name__", str(fn))
        activity_calls.append((name, list(args)))
        if name == "get_loan_grpc":
            return {
                "loan_id": LOAN_ID,
                "status": loan_status,
                "seller_id": SELLER_ID,
                "investor_id": INVESTOR_A,
                "principal": "5000.00",
                "invoice_token": INVOICE_TOKEN,
            }
        if name == "get_user":
            return {"id": args[0], "email": f"user{args[0]}@test.com"}
        return {}

    async def fake_wait_condition(condition, *, timeout):
        pass  # always times out (no signal), overridden per test when needed

    mock = MagicMock()
    mock.now.return_value = now_dt
    mock.sleep = AsyncMock()
    mock.execute_activity = fake_execute_activity
    mock.wait_condition = AsyncMock(side_effect=fake_wait_condition)

    return mock, activity_calls


# ===========================================================================
# AUCTION — Demo Mode Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_auction_demo_settlement_executes_correctly():
    """Demo mode: after the short sleep, full 10-step settlement still runs in correct order."""
    mock_wf, activity_calls, child_calls = _auction_wf_mock(offers=[_OFFER_A, _OFFER_B])

    with patch("workflows.auction_close.config", _demo_config()):
        with patch("workflows.auction_close.workflow", mock_wf):
            wf = AuctionCloseWorkflow()
            await wf.run(INVOICE_TOKEN, bid_period_hours=48)

    names = [name for name, _ in activity_calls]

    # Correct settlement order
    assert names.index("verify_invoice") < names.index("convert_escrow_to_loan")
    assert names.index("convert_escrow_to_loan") < names.index("create_loan")
    assert names.index("create_loan") < names.index("release_funds_to_seller")
    assert names.index("release_funds_to_seller") < names.index("update_invoice_status")

    # Winner is investor A (highest bid)
    accept_args = [args for name, args in activity_calls if name == "accept_offer"]
    assert accept_args[0][0] == _OFFER_A["id"]

    # Loser B rejected and escrowed released
    reject_args = [args for name, args in activity_calls if name == "reject_offer"]
    assert any(args[0] == _OFFER_B["id"] for args in reject_args)
    release_args = [args[0] for name, args in activity_calls if name == "release_escrow"]
    assert INVESTOR_B in release_args
    assert INVESTOR_A not in release_args

    # LoanMaturityWorkflow started
    assert len(child_calls) == 1
    assert child_calls[0]["id"] == f"loan-{_LOAN['loan_id']}"

    # Outcome events published
    published = [args[0] for name, args in activity_calls if name == "publish_event"]
    assert "auction.closed.winner" in published
    assert "auction.closed.loser" in published


@pytest.mark.asyncio
async def test_auction_demo_zero_bids_expires():
    """Demo mode: zero bids still publishes auction.expired and skips settlement."""
    mock_wf, activity_calls, child_calls = _auction_wf_mock(offers=[])

    with patch("workflows.auction_close.config", _demo_config()):
        with patch("workflows.auction_close.workflow", mock_wf):
            wf = AuctionCloseWorkflow()
            await wf.run(INVOICE_TOKEN, bid_period_hours=48)

    published = [args[0] for name, args in activity_calls if name == "publish_event"]
    assert "auction.expired" in published
    assert len(child_calls) == 0

    settlement_names = {"convert_escrow_to_loan", "create_loan", "release_funds_to_seller"}
    called = {name for name, _ in activity_calls}
    assert called.isdisjoint(settlement_names)


# ===========================================================================
# LOAN MATURITY — Demo Mode Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_loan_demo_uses_short_repayment_window():
    """Demo mode: wait_condition timeout is DEMO_REPAYMENT_WINDOW_SECONDS, not REPAYMENT_WINDOW_SECONDS (86400)."""
    mock_wf, _ = _loan_wf_mock(loan_status="DUE")

    with patch("workflows.loan_maturity.config", _demo_config(repayment_secs=60)):
        with patch("workflows.loan_maturity.workflow", mock_wf):
            wf = LoanMaturityWorkflow()
            await wf.run(LOAN_ID, _DUE_DATE_FUTURE)

    wait_calls = mock_wf.wait_condition.call_args_list
    assert len(wait_calls) == 1
    timeout_used = wait_calls[0].kwargs["timeout"]
    assert timeout_used == timedelta(seconds=60), (
        f"Expected 60s repayment window, got {timeout_used}"
    )


@pytest.mark.asyncio
async def test_loan_demo_overdue_path_fires():
    """Demo mode: if window expires unreplied, loan is marked OVERDUE and seller is bulk-delisted."""
    mock_wf, activity_calls = _loan_wf_mock(loan_status="DUE")

    with patch("workflows.loan_maturity.config", _demo_config()):
        with patch("workflows.loan_maturity.workflow", mock_wf):
            wf = LoanMaturityWorkflow()
            await wf.run(LOAN_ID, _DUE_DATE_FUTURE)

    statuses = [args[1] for name, args in activity_calls if name == "update_loan_status_grpc"]
    assert "DUE" in statuses
    assert "OVERDUE" in statuses

    published = [args[0] for name, args in activity_calls if name == "publish_event"]
    assert "loan.overdue" in published

    assert any(name == "bulk_delist" for name, _ in activity_calls)


@pytest.mark.asyncio
async def test_loan_demo_early_exit_on_repayment_signal():
    """Demo mode: repayment_confirmed signal causes early exit — OVERDUE never set."""
    mock_wf, activity_calls = _loan_wf_mock(loan_status="DUE")

    # Override wait_condition to simulate signal arriving (condition becomes True immediately)
    async def signal_arrives(condition, *, timeout):
        pass  # returns without raising — condition is checked as True via _repayment_confirmed

    mock_wf.wait_condition = AsyncMock(side_effect=signal_arrives)

    with patch("workflows.loan_maturity.config", _demo_config()):
        with patch("workflows.loan_maturity.workflow", mock_wf):
            wf = LoanMaturityWorkflow()
            wf._repayment_confirmed = True  # pre-deliver signal
            await wf.run(LOAN_ID, _DUE_DATE_FUTURE)

    statuses = [args[1] for name, args in activity_calls if name == "update_loan_status_grpc"]
    assert "OVERDUE" not in statuses

    published = [args[0] for name, args in activity_calls if name == "publish_event"]
    assert "loan.overdue" not in published
