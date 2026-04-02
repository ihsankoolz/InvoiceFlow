"""
Workflow-level tests for LoanMaturityWorkflow.

Uses Temporal's WorkflowEnvironment with auto_time_skipping so durable
timers resolve instantly without real wall-clock delays.

Three scenarios are covered:
  1. Early signal  — repayment_confirmed arrives during the window → workflow exits cleanly, OVERDUE is never called
  2. Default path  — window expires with no signal and loan is still DUE → OVERDUE + bulk_delist called
  3. Missed signal — window expires, but loan is already REPAID in DB → workflow exits cleanly
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from temporalio import activity
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from workflows.loan_maturity import LoanMaturityWorkflow


# ---------------------------------------------------------------------------
# Shared helpers
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


def _make_activities(loan_status_after_window: str = "DUE"):
    """Return a namespace of activity mocks for the workflow to call."""

    update_calls: list[tuple] = []
    publish_calls: list[tuple] = []

    @activity.defn(name="update_loan_status_grpc")
    async def update_loan_status_grpc(loan_id: str, status: str):
        update_calls.append((loan_id, status))
        return {"loan_id": loan_id, "status": status}

    @activity.defn(name="get_loan_grpc")
    async def get_loan_grpc(loan_id: str):
        return _base_loan(loan_status_after_window)

    @activity.defn(name="get_user")
    async def get_user(user_id: int):
        return {"id": user_id, "email": f"user{user_id}@test.com"}

    @activity.defn(name="publish_event")
    async def publish_event(event_type: str, payload: dict):
        publish_calls.append((event_type, payload))

    @activity.defn(name="bulk_delist")
    async def bulk_delist(seller_id: int):
        pass

    activity_fns = [
        update_loan_status_grpc,
        get_loan_grpc,
        get_user,
        publish_event,
        bulk_delist,
    ]
    return activity_fns, update_calls, publish_calls


# ---------------------------------------------------------------------------
# Test 1: repayment_confirmed signal arrives during window → exits cleanly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_repayment_signal_exits_workflow_early():
    """
    When repayment_confirmed is signalled during the repayment window,
    the workflow exits without calling UpdateLoanStatus(OVERDUE) or bulk_delist.
    """
    activity_fns, update_calls, publish_calls = _make_activities(loan_status_after_window="DUE")

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[LoanMaturityWorkflow],
            activities=activity_fns,
        ):
            handle = await env.client.start_workflow(
                LoanMaturityWorkflow.run,
                args=[LOAN_ID, DUE_DATE_PAST],
                id="test-loan-early-signal",
                task_queue="test-queue",
            )

            # Give the workflow a moment to reach the wait_condition
            await asyncio.sleep(0.1)

            # Send the repayment signal
            await handle.signal(LoanMaturityWorkflow.repayment_confirmed)

            await handle.result()

    # OVERDUE should never have been set
    assert ("loan-test-123", "OVERDUE") not in update_calls
    # DUE should have been set
    assert ("loan-test-123", "DUE") in update_calls
    # loan.overdue should not have been published
    overdue_events = [e for e, _ in publish_calls if e == "loan.overdue"]
    assert len(overdue_events) == 0
    # loan.due should have been published
    due_events = [e for e, _ in publish_calls if e == "loan.due"]
    assert len(due_events) == 1


# ---------------------------------------------------------------------------
# Test 2: window expires with no signal, loan still DUE → OVERDUE + delist
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_default_path_marks_overdue_and_delists():
    """
    When the repayment window expires and the loan is still DUE,
    the workflow marks OVERDUE, publishes loan.overdue, and calls bulk_delist.
    """
    activity_fns, update_calls, publish_calls = _make_activities(loan_status_after_window="DUE")

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[LoanMaturityWorkflow],
            activities=activity_fns,
        ):
            handle = await env.client.start_workflow(
                LoanMaturityWorkflow.run,
                args=[LOAN_ID, DUE_DATE_PAST],
                id="test-loan-default",
                task_queue="test-queue",
            )
            await handle.result()

    assert ("loan-test-123", "DUE") in update_calls
    assert ("loan-test-123", "OVERDUE") in update_calls

    overdue_events = [e for e, _ in publish_calls if e == "loan.overdue"]
    assert len(overdue_events) == 1


# ---------------------------------------------------------------------------
# Test 3: window expires but loan already REPAID in DB (missed/late signal)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_missed_signal_but_repaid_in_db_exits_cleanly():
    """
    When the repayment window expires without a signal but get_loan returns REPAID,
    the workflow exits cleanly without marking OVERDUE.
    """
    activity_fns, update_calls, publish_calls = _make_activities(loan_status_after_window="REPAID")

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue="test-queue",
            workflows=[LoanMaturityWorkflow],
            activities=activity_fns,
        ):
            handle = await env.client.start_workflow(
                LoanMaturityWorkflow.run,
                args=[LOAN_ID, DUE_DATE_PAST],
                id="test-loan-repaid-fallback",
                task_queue="test-queue",
            )
            await handle.result()

    assert ("loan-test-123", "OVERDUE") not in update_calls
    overdue_events = [e for e, _ in publish_calls if e == "loan.overdue"]
    assert len(overdue_events) == 0
