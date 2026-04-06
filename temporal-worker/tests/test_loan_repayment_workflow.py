"""
Workflow-level tests for LoanRepaymentWorkflow.

Four scenarios:
  1. Happy path     — all 5 steps execute in correct order, loan.repaid published
  2. Signal sent    — repayment_confirmed signal is sent to LoanMaturityWorkflow
  3. Signal skipped — if maturity workflow already completed, exception is swallowed
  4. Payload        — loan.repaid event contains correct fields
"""

import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

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

from workflows.loan_repayment import LoanRepaymentWorkflow  # noqa: E402

for _mod in _STUBBED_MODS:
    if _mod not in _previously_present:
        sys.modules.pop(_mod, None)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOAN_ID = "loan-repay-001"
STRIPE_SESSION = "cs_test_abc123"
SELLER_ID = 10
INVESTOR_ID = 5

_LOAN = {
    "loan_id": LOAN_ID,
    "status": "REPAID",
    "seller_id": SELLER_ID,
    "investor_id": INVESTOR_ID,
    "principal": "8000.00",
    "invoice_token": "INV-TOKEN-001",
}


# ---------------------------------------------------------------------------
# Mock builder
# ---------------------------------------------------------------------------


def _build_mock(signal_raises=False):
    activity_calls: list[tuple] = []
    signal_calls: list[str] = []

    async def fake_execute_activity(fn, *, args, **kwargs):
        name = getattr(fn, "_mock_name", None) or getattr(fn, "__name__", str(fn))
        activity_calls.append((name, list(args)))
        if name == "get_loan_grpc":
            return _LOAN
        if name == "get_user":
            return {"id": args[0], "email": f"user{args[0]}@test.com"}
        return {}

    mock_handle = MagicMock()
    if signal_raises:
        mock_handle.signal = AsyncMock(side_effect=Exception("workflow already completed"))
    else:
        mock_handle.signal = AsyncMock()

    def fake_get_external_handle(workflow_id):
        signal_calls.append(workflow_id)
        return mock_handle

    mock = MagicMock()
    mock.execute_activity = fake_execute_activity
    mock.get_external_workflow_handle = fake_get_external_handle

    return mock, activity_calls, signal_calls, mock_handle


# ---------------------------------------------------------------------------
# Test 1: Happy path — all 5 steps in correct order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_executes_all_steps_in_order():
    """All 5 workflow steps run: mark REPAID → signal → fetch loan → fetch users → publish."""
    mock_wf, activity_calls, _, _ = _build_mock()

    with patch("workflows.loan_repayment.workflow", mock_wf):
        wf = LoanRepaymentWorkflow()
        await wf.run(LOAN_ID, STRIPE_SESSION)

    names = [name for name, _ in activity_calls]

    assert "update_loan_status_grpc" in names
    assert "get_loan_grpc" in names
    assert "get_user" in names
    assert "publish_event" in names

    assert names.index("update_loan_status_grpc") < names.index("get_loan_grpc")
    assert names.index("get_loan_grpc") < names.index("publish_event")


# ---------------------------------------------------------------------------
# Test 2: Loan status set to REPAID
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_loan_marked_repaid():
    """update_loan_status_grpc is called with REPAID status."""
    mock_wf, activity_calls, _, _ = _build_mock()

    with patch("workflows.loan_repayment.workflow", mock_wf):
        wf = LoanRepaymentWorkflow()
        await wf.run(LOAN_ID, STRIPE_SESSION)

    repaid_calls = [
        (name, args) for name, args in activity_calls if name == "update_loan_status_grpc"
    ]
    assert len(repaid_calls) == 1
    assert repaid_calls[0][1] == [LOAN_ID, "REPAID"]


# ---------------------------------------------------------------------------
# Test 3: repayment_confirmed signal sent to LoanMaturityWorkflow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repayment_confirmed_signal_sent():
    """Signal is sent to the running LoanMaturityWorkflow via external handle."""
    mock_wf, _, signal_calls, mock_handle = _build_mock()

    with patch("workflows.loan_repayment.workflow", mock_wf):
        wf = LoanRepaymentWorkflow()
        await wf.run(LOAN_ID, STRIPE_SESSION)

    assert f"loan-{LOAN_ID}" in signal_calls
    mock_handle.signal.assert_awaited_once_with("repayment_confirmed")


# ---------------------------------------------------------------------------
# Test 4: Signal exception swallowed if maturity workflow already completed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_signal_exception_is_swallowed():
    """If LoanMaturityWorkflow already completed, signalling raises — workflow must not fail."""
    mock_wf, activity_calls, _, _ = _build_mock(signal_raises=True)

    with patch("workflows.loan_repayment.workflow", mock_wf):
        wf = LoanRepaymentWorkflow()
        await wf.run(LOAN_ID, STRIPE_SESSION)  # must not raise

    # Workflow still completes — loan.repaid is still published
    published = [args[0] for name, args in activity_calls if name == "publish_event"]
    assert "loan.repaid" in published


# ---------------------------------------------------------------------------
# Test 5: loan.repaid event payload contains correct fields
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_loan_repaid_event_payload():
    """loan.repaid event includes loan_id, seller_id, investor_id, principal, stripe_session_id."""
    mock_wf, activity_calls, _, _ = _build_mock()

    with patch("workflows.loan_repayment.workflow", mock_wf):
        wf = LoanRepaymentWorkflow()
        await wf.run(LOAN_ID, STRIPE_SESSION)

    publish_calls = [(name, args) for name, args in activity_calls if name == "publish_event"]
    assert len(publish_calls) == 1

    routing_key, payload = publish_calls[0][1]
    assert routing_key == "loan.repaid"
    assert payload["loan_id"] == LOAN_ID
    assert payload["seller_id"] == SELLER_ID
    assert payload["investor_id"] == INVESTOR_ID
    assert payload["principal"] == "8000.00"
    assert payload["stripe_session_id"] == STRIPE_SESSION
    assert payload["invoice_token"] == "INV-TOKEN-001"
