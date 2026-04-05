"""
Workflow-level tests for AuctionCloseWorkflow.

Tests run instantly — workflow.sleep and workflow.now are all mocked
so no real timers fire. start_child_workflow is also mocked so
LoanMaturityWorkflow is never actually started (it has its own test file).

Three scenarios:
  1. Zero bids        — auction expires with no bids → auction.expired published, no settlement
  2. Winner + losers  — 10-step settlement executes in correct order
  3. Loser escrow     — losing bidder's escrow released, winner's escrow not touched
"""

import asyncio
import sys
import types
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Stub heavy dependencies before importing the workflow module.
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
_config.ANTI_SNIPE_SECONDS = 300
_config.REPAYMENT_WINDOW_SECONDS = 30
_config.DEMO_MODE = False
_config.DEMO_AUCTION_SECONDS = 90
_config.DEMO_LOAN_MATURITY_SECONDS = 90
_config.DEMO_REPAYMENT_WINDOW_SECONDS = 60
sys.modules["config"] = _config

from workflows.auction_close import AuctionCloseWorkflow  # noqa: E402
from workflows.loan_maturity import LoanMaturityWorkflow  # noqa: E402 (needed for child ref)

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

INVOICE_TOKEN = "INV-TEST-001"
SELLER_ID = 10
INVESTOR_A = 1   # winner (highest bid)
INVESTOR_B = 2   # loser

_INVOICE = {
    "invoice_token": INVOICE_TOKEN,
    "seller_id": SELLER_ID,
    "status": "LISTED",
    "due_date": "2026-12-31",
    "amount": 7000.0,
}
_LOAN = {"loan_id": "loan-abc-123", "due_date": "2026-12-31", "bid_amount": 5000.0}
_OFFER_A = {"id": 1, "investor_id": INVESTOR_A, "bid_amount": 5000.0, "status": "PENDING"}
_OFFER_B = {"id": 2, "investor_id": INVESTOR_B, "bid_amount": 3000.0, "status": "PENDING"}


# ---------------------------------------------------------------------------
# Mock builder
# ---------------------------------------------------------------------------

def _build_mock(offers: list):
    """
    Build a patched workflow module and tracking lists.

    offers — what get_offers returns during settlement (empty = no bids)
    """
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

    return mock, activity_calls, child_calls


# ---------------------------------------------------------------------------
# Test 1: Zero bids — auction.expired, no settlement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_zero_bids_publishes_auction_expired():
    """No bids → invoice set to EXPIRED, auction.expired published, financial settlement never runs."""
    mock_wf, activity_calls, child_calls = _build_mock(offers=[])

    with patch("workflows.auction_close.workflow", mock_wf):
        wf = AuctionCloseWorkflow()
        await wf.run(INVOICE_TOKEN, bid_period_hours=1)

    published = [args[0] for name, args in activity_calls if name == "publish_event"]
    assert "auction.expired" in published

    # Invoice status must be set to EXPIRED before delist
    names = [name for name, _ in activity_calls]
    assert "update_invoice_status" in names
    status_args = [args for name, args in activity_calls if name == "update_invoice_status"]
    assert status_args[0] == [INVOICE_TOKEN, "EXPIRED"]
    assert names.index("update_invoice_status") < names.index("delist_listing")

    # Financial settlement must not run
    settlement_names = {
        "convert_escrow_to_loan", "create_loan", "release_funds_to_seller",
        "accept_offer",
    }
    called_names = {name for name, _ in activity_calls}
    assert called_names.isdisjoint(settlement_names)
    assert len(child_calls) == 0


# ---------------------------------------------------------------------------
# Test 2: Winner + loser — 10-step settlement in correct order
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_settlement_executes_in_correct_order():
    """Two bidders: winner is highest bid, 10-step settlement runs in order."""
    mock_wf, activity_calls, child_calls = _build_mock(offers=[_OFFER_A, _OFFER_B])

    with patch("workflows.auction_close.workflow", mock_wf):
        wf = AuctionCloseWorkflow()
        await wf.run(INVOICE_TOKEN, bid_period_hours=1)

    names = [name for name, _ in activity_calls]

    # Correct step ordering
    assert names.index("verify_invoice") < names.index("convert_escrow_to_loan")
    assert names.index("convert_escrow_to_loan") < names.index("create_loan")
    assert names.index("create_loan") < names.index("release_funds_to_seller")
    assert names.index("release_funds_to_seller") < names.index("update_invoice_status")
    assert names.index("update_invoice_status") < names.index("delist_listing")
    assert names.index("delist_listing") < names.index("accept_offer")

    # Winner is investor A (bid 5000 > 3000)
    accept_args = [args for name, args in activity_calls if name == "accept_offer"]
    assert accept_args[0][0] == _OFFER_A["id"]

    # Loser B rejected
    reject_args = [args for name, args in activity_calls if name == "reject_offer"]
    assert any(args[0] == _OFFER_B["id"] for args in reject_args)

    # LoanMaturityWorkflow started with correct loan_id
    assert len(child_calls) == 1
    assert child_calls[0]["id"] == f"loan-{_LOAN['loan_id']}"

    # Outcome events published
    published = [args[0] for name, args in activity_calls if name == "publish_event"]
    assert "auction.closed.winner" in published
    assert "auction.closed.loser" in published


# ---------------------------------------------------------------------------
# Test 3: Loser escrow released, winner escrow not released
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_loser_escrow_released_winner_escrow_not_released():
    """Loser's escrow is released after rejection. Winner's escrow is converted, not released."""
    mock_wf, activity_calls, _ = _build_mock(offers=[_OFFER_A, _OFFER_B])

    with patch("workflows.auction_close.workflow", mock_wf):
        wf = AuctionCloseWorkflow()
        await wf.run(INVOICE_TOKEN, bid_period_hours=1)

    release_calls = [args for name, args in activity_calls if name == "release_escrow"]
    released_investors = [args[0] for args in release_calls]

    # Loser B's escrow released
    assert INVESTOR_B in released_investors
    # Winner A's escrow was converted to loan, not released
    assert INVESTOR_A not in released_investors
