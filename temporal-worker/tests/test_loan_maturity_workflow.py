"""
Workflow-level tests for LoanMaturityWorkflow.

These tests avoid the Temporal server entirely (no start_time_skipping, no
start_local) so they run instantly on any platform including Windows CI.

The approach: mock every `workflow.*` call and `execute_activity` call that
the workflow makes, then call workflow.run() directly as a coroutine.

Three scenarios:
  1. Signal handler — repayment_confirmed() sets the internal flag to True
  2. Default path   — window expires, loan still DUE → OVERDUE + bulk_delist
  3. Missed signal  — window expires, loan already REPAID → exits cleanly
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
]
_previously_present = {m for m in _STUBBED_MODS if m in sys.modules}
for _mod in _STUBBED_MODS:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

_config_orig = sys.modules.get("config")
_config = types.ModuleType("config")
_config.REPAYMENT_WINDOW_SECONDS = 30
_config.DEMO_MODE = False
_config.DEMO_LOAN_MATURITY_SECONDS = 90
_config.DEMO_REPAYMENT_WINDOW_SECONDS = 60
sys.modules["config"] = _config

from workflows.loan_maturity import LoanMaturityWorkflow  # noqa: E402

# Restore everything so later test modules see the real packages.
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

DUE_DATE_PAST = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
LOAN_ID = "loan-test-123"
SELLER_ID = 42
INVESTOR_ID = 7


def _base_loan(status: str = "DUE") -> dict:
    return {
        "loan_id": LOAN_ID,
        "status": status,
        "seller_id": SELLER_ID,
        "investor_id": INVESTOR_ID,
        "principal": "5000.00",
        "invoice_token": "inv-tok-abc",
    }


# ---------------------------------------------------------------------------
# Test 1: signal handler unit test (pure Python, no server)
# ---------------------------------------------------------------------------


def test_repayment_confirmed_signal_sets_flag():
    """repayment_confirmed() sets _repayment_confirmed = True.

    The wait_condition lambda reads this flag, so verifying the flag proves
    the early-exit path is reachable when a signal is delivered.
    """
    wf = LoanMaturityWorkflow()
    assert wf._repayment_confirmed is False
    wf.repayment_confirmed()
    assert wf._repayment_confirmed is True


# ---------------------------------------------------------------------------
# Shared mock context for workflow.run() tests
# ---------------------------------------------------------------------------


def _workflow_mock(loan_status: str, signal_before_wait: bool = False):
    """
    Returns a patch context that replaces `workflow.now`, `workflow.sleep`,
    `workflow.wait_condition`, and `workflow.execute_activity` so that
    workflow.run() can be called directly as a coroutine without a server.
    """
    now_dt = datetime.now(timezone.utc)

    activity_calls: list[tuple] = []

    async def fake_execute_activity(fn, *, args, **kwargs):
        # fn is the activity stub from the workflow's imports_passed_through block.
        # These are MagicMocks whose ._mock_name matches the import name.
        # Fall back to __name__ for any non-mock callables.
        name = getattr(fn, "_mock_name", None) or getattr(fn, "__name__", str(fn))
        activity_calls.append((name, args))
        if name == "get_loan_grpc":
            return _base_loan(loan_status)
        if name == "get_user":
            return {"id": args[0], "email": f"user{args[0]}@test.com"}
        return {}

    async def fake_wait_condition(condition, *, timeout):
        # If signal was pre-delivered, condition is already True — return immediately.
        # Otherwise simulate timeout (condition stays False).
        pass

    mock = MagicMock()
    mock.now.return_value = now_dt
    mock.sleep = AsyncMock()
    mock.execute_activity = fake_execute_activity
    mock.wait_condition = AsyncMock(side_effect=fake_wait_condition)

    return mock, activity_calls


# ---------------------------------------------------------------------------
# Test 2: no signal, window expires, loan still DUE → OVERDUE + bulk_delist
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_default_path_marks_overdue_and_delists():
    """No signal → wait_condition times out → loan checked → OVERDUE + bulk_delist."""
    mock_wf, activity_calls = _workflow_mock(loan_status="DUE")

    with patch("workflows.loan_maturity.workflow", mock_wf):
        wf = LoanMaturityWorkflow()
        await wf.run(LOAN_ID, DUE_DATE_PAST)

    names_and_args = [(name, args) for name, args in activity_calls]

    update_statuses = [
        args[1] for name, args in names_and_args if name == "update_loan_status_grpc"
    ]
    assert "DUE" in update_statuses
    assert "OVERDUE" in update_statuses

    published = [args[0] for name, args in names_and_args if name == "publish_event"]
    assert "loan.overdue" in published

    bulk_delist_calls = [args for name, args in names_and_args if name == "bulk_delist"]
    assert len(bulk_delist_calls) == 1


# ---------------------------------------------------------------------------
# Test 3: no signal, window expires, loan already REPAID → exits cleanly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missed_signal_repaid_in_db_exits_cleanly():
    """wait_condition times out but get_loan returns REPAID → OVERDUE never set."""
    mock_wf, activity_calls = _workflow_mock(loan_status="REPAID")

    with patch("workflows.loan_maturity.workflow", mock_wf):
        wf = LoanMaturityWorkflow()
        await wf.run(LOAN_ID, DUE_DATE_PAST)

    update_statuses = [
        args[1] for name, args in activity_calls if name == "update_loan_status_grpc"
    ]
    assert "OVERDUE" not in update_statuses

    published = [args[0] for name, args in activity_calls if name == "publish_event"]
    assert "loan.overdue" not in published

    bulk_delist_calls = [args for name, args in activity_calls if name == "bulk_delist"]
    assert len(bulk_delist_calls) == 0
