# Updates — 3 April 2026

This document records all changes made on 3 April 2026, why they were made, and how each issue would have affected the live deployment and architecture if left unfixed. Intended as a reference for updating the README and final architecture documentation.

---

## Overview

All changes fall into two categories:

1. **Demo mode** — a new env-var-driven feature that speeds up all long-running Temporal workflow timers for live presentations, without touching production behaviour.
2. **Bug fixes** — four concrete bugs discovered during demo preparation that would have caused failures in the deployed system.

---

## 1. Demo Mode Feature

### What was added

A `DEMO_MODE` flag (and associated timing env vars) that, when enabled, overrides all long-running Temporal timers with short fixed durations. This allows the full three-scenario user journey to be demonstrated live in under 5 minutes instead of days.

### Files changed

| File | Change |
|------|--------|
| `temporal-worker/config.py` | Added `DEMO_MODE`, `DEMO_AUCTION_SECONDS`, `DEMO_LOAN_MATURITY_SECONDS`, `DEMO_REPAYMENT_WINDOW_SECONDS` |
| `temporal-worker/workflows/auction_close.py` | In demo mode: skips T-12h and T-1h closing warning events; sleeps `DEMO_AUCTION_SECONDS` instead of `bid_period_hours` |
| `temporal-worker/workflows/loan_maturity.py` | In demo mode: sleeps `DEMO_LOAN_MATURITY_SECONDS` instead of waiting until the actual loan due date; uses `DEMO_REPAYMENT_WINDOW_SECONDS` as the repayment window |
| `orchestrators/invoice-orchestrator/app/config.py` | Added `DEMO_MODE`, `DEMO_AUCTION_SECONDS` |
| `orchestrators/invoice-orchestrator/app/services/orchestrator.py` | `calculate_deadline()` now sets the marketplace listing deadline to `now + DEMO_AUCTION_SECONDS` in demo mode |
| `orchestrators/bidding-orchestrator/app/config.py` | Added `ANTI_SNIPE_WINDOW_SECONDS` (default 300) |
| `orchestrators/bidding-orchestrator/app/services/bid_orchestrator.py` | `ANTI_SNIPE_WINDOW` now reads from `ANTI_SNIPE_WINDOW_SECONDS` instead of being hardcoded to 5 minutes |
| `.env.example` | Documented all new env vars with descriptions |

### Env vars to set for demo (add to `.env` on EC2)

```
DEMO_MODE=true
DEMO_AUCTION_SECONDS=90
DEMO_LOAN_MATURITY_SECONDS=90
DEMO_REPAYMENT_WINDOW_SECONDS=60
ANTI_SNIPE_SECONDS=15
ANTI_SNIPE_WINDOW_SECONDS=15
```

### Architectural impact

The demo mode feature intentionally touches three layers of the architecture:

- **Temporal worker** (`temporal-worker/`) — controls the actual workflow sleep durations. This is the source of truth for how long things take.
- **Invoice orchestrator** (`orchestrators/invoice-orchestrator/`) — controls the deadline stored in the Marketplace database when a listing is created. This is what the frontend countdown reads from.
- **Bidding orchestrator** (`orchestrators/bidding-orchestrator/`) — controls when the anti-snipe signal is sent to the Temporal workflow.

All three layers must be in sync. If only the Temporal worker is changed without changing the other two, the system is internally inconsistent (see Bug 1 and Bug 2 below).

In production, all three default to their original values (`DEMO_MODE=false`, etc.) so there is zero impact on the production deployment path.

---

## 2. Bug: Frontend Countdown Mismatch with Temporal Timer

### What was wrong

`calculate_deadline()` in `invoice-orchestrator/app/services/orchestrator.py` always computed the marketplace listing deadline as `now + timedelta(hours=bid_period_hours)`. This deadline is written to the Marketplace database and read by the frontend countdown timer.

In demo mode, the Temporal `AuctionCloseWorkflow` overrides `bid_period_hours` and closes the auction in 90 seconds. However, the marketplace deadline was still set to hours in the future. The result:

- Frontend countdown shows "0h 59m 30s remaining"
- Temporal closes the auction 90 seconds after listing
- The UI shows an active auction with time remaining while the backend has already settled it

### How this would affect deployment

This is not just a demo problem. It reveals that the marketplace listing deadline and the Temporal workflow timer were **not derived from the same source** — they were independently computed from the same input (`bid_period_hours`) at two different points in time. In production, the two values would be almost identical due to the same `timedelta(hours=...)` calculation, but any clock drift between service restarts or timezone handling issues could cause a discrepancy.

More critically: the anti-snipe logic in the bidding orchestrator reads the marketplace deadline (not the Temporal timer) to decide whether to extend. If these two values diverge for any reason, the anti-snipe logic fires at the wrong time.

### Fix

`calculate_deadline()` now uses `timedelta(seconds=config.DEMO_AUCTION_SECONDS)` when `DEMO_MODE=True`, keeping the marketplace deadline in sync with what Temporal will actually do.

---

## 3. Bug: Anti-Snipe Never Triggered in Demo Mode

### What was wrong

`ANTI_SNIPE_WINDOW = timedelta(minutes=5)` was hardcoded in `bid_orchestrator.py`. The anti-snipe check is:

```python
if deadline - now <= ANTI_SNIPE_WINDOW:
    # extend auction
```

Because the marketplace deadline was set hours in the future (Bug 1), `deadline - now` was always well above 5 minutes. The condition never evaluated to true, meaning no bid ever triggered the anti-snipe extension during a demo. The Temporal signal `extend_deadline` was never sent, so the anti-snipe loop in `AuctionCloseWorkflow` was never exercised.

### How this would affect deployment

The hardcoded value is a broader architectural issue: the anti-snipe window was defined in two places — `ANTI_SNIPE_SECONDS` in the Temporal worker (how long the workflow extends by) and the hardcoded 5 minutes in the bidding orchestrator (when to trigger the extension). These two values are conceptually the same thing but were maintained separately, making them easy to drift out of sync.

### Fix

`ANTI_SNIPE_WINDOW` now reads from `config.ANTI_SNIPE_WINDOW_SECONDS` (env var, default 300). The orchestrator and the Temporal worker now both use the same env var (`ANTI_SNIPE_SECONDS` / `ANTI_SNIPE_WINDOW_SECONDS` — both should be set to the same value). For demo: set both to 15.

---

## 4. Bug: Temporal Workflow Duplicate ID Crashes the API

### What was wrong

`TemporalClient.start_workflow()` in `invoice-orchestrator/app/temporal/client.py` called `client.start_workflow()` with no error handling. The Temporal SDK raises `WorkflowAlreadyStartedError` if a workflow with the same ID is already running.

The workflow ID is `auction-{invoice_token}`. If the same invoice is submitted twice (double-click on the form, demo rerun, network retry), the second call raises an unhandled exception that propagates as an HTTP 500 to the frontend.

### How this would affect deployment

In production, this is a real risk. A user with a slow connection may double-submit the invoice listing form. The first submission creates the invoice, listing, and starts the workflow successfully. The second submission creates a duplicate invoice record, fails at the Temporal step with a 500, and leaves an orphaned invoice and marketplace listing in the database with no workflow attached to them. Those listings would sit in the marketplace forever with no auction ever closing.

### Fix

`WorkflowAlreadyStartedError` is now caught and silently ignored in `TemporalClient.start_workflow()`. If the workflow is already running, there is nothing to do — the auction is proceeding correctly from the first submission.

---

## 5. Bug: Activity-Log-Bridge Hangs on Startup

### What was wrong

`services/activity-log-bridge/bridge.py` opened a `pika.BlockingConnection` at module level with no retry logic:

```python
connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
```

RabbitMQ can take 15–30 seconds to become available after `docker compose up`, even with `depends_on: condition: service_healthy` on other services. The activity-log-bridge does not have a `depends_on` healthcheck dependency on RabbitMQ, so it starts immediately. If RabbitMQ is not yet accepting connections, the blocking call hangs indefinitely. The container appears to be running (process is alive) but is frozen and will never consume any events.

### How this would affect deployment

This is a silent failure. Docker reports the container as running. Logs show no error. All events are published to RabbitMQ normally, and all other consumers (notification-service, etc.) work correctly. But every event that should be forwarded to the OutSystems activity log is silently dropped for the entire lifetime of that container instance. The DLQ and Grafana alert would not catch this because the queue is never even declared.

On EC2, a fresh `docker compose up --build` after a reboot is the most likely scenario to trigger this, since all containers start nearly simultaneously.

### Fix

The connection is now wrapped in a retry loop: up to 15 attempts with a 5-second delay between each. If RabbitMQ is not ready within 75 seconds, the bridge exits with an error (which Docker will log and can be configured to restart). This matches the retry behaviour already present in other services.

---

## 6. Test Suite: Demo Mode Coverage

### What was added

`temporal-worker/tests/test_demo_mode.py` — 9 new tests covering demo mode behaviour for both `AuctionCloseWorkflow` and `LoanMaturityWorkflow`.

Existing test files (`test_auction_close_workflow.py`, `test_loan_maturity_workflow.py`) were also updated to add the new demo config attributes (`DEMO_MODE=False`, etc.) to their module-level config stubs, ensuring they continue to pass alongside the new tests.

### Tests added

| Test | Proves |
|------|--------|
| `test_auction_demo_sleeps_configured_seconds_not_hours` | Temporal sleeps 90s, not `bid_period_hours` |
| `test_auction_demo_skips_closing_warnings` | No T-12h/T-1h `auction.closing.warning` events published |
| `test_auction_demo_settlement_executes_correctly` | Full 10-step settlement (winner, loser, loan) still runs after short sleep |
| `test_auction_demo_anti_snipe_still_works` | Anti-snipe signal still extends auction in demo mode |
| `test_auction_demo_zero_bids_expires` | Zero-bid expiry path still publishes `auction.expired` |
| `test_loan_demo_sleeps_configured_seconds_not_due_date` | Loan maturity ignores real due date, sleeps 90s |
| `test_loan_demo_uses_short_repayment_window` | `wait_condition` timeout is 60s, not 86400s |
| `test_loan_demo_overdue_path_fires` | OVERDUE + bulk delist fires correctly in demo mode |
| `test_loan_demo_early_exit_on_repayment_signal` | `repayment_confirmed` signal still causes early exit |

All 16 tests (7 existing + 9 new) pass.

---

## Services Affected — Summary

| Service | Changed | Reason |
|---------|---------|--------|
| `temporal-worker` | Yes | Demo mode timers, test suite |
| `orchestrators/invoice-orchestrator` | Yes | Marketplace deadline sync, Temporal error handling |
| `orchestrators/bidding-orchestrator` | Yes | Anti-snipe window made configurable |
| `services/activity-log-bridge` | Yes | RabbitMQ connection retry |
| `.env.example` | Yes | Documented all new env vars |

Services not changed: `user-service`, `invoice-service`, `marketplace-service`, `bidding-service`, `payment-service`, `notification-service`, `loan-orchestrator`, `acra-wrapper`, `stripe-wrapper`, `webhook-router`, `dlq-monitor`, `frontend`.

---

## Deployment Notes

- **Containers to rebuild after these changes:** `temporal-worker`, `invoice-orchestrator`, `bidding-orchestrator`, `activity-log-bridge`. All others are unaffected.
- **Demo deploy command:** add the demo env vars to `.env` on EC2, then `docker compose up --build`.
- **Reverting after demo:** set `DEMO_MODE=false` (or remove the demo vars) and `docker compose up --build`.
- **No database migrations required** — no schema changes were made.
- **No frontend changes required** — the frontend countdown already reads `listing.deadline` from the API; fixing the deadline at the source is sufficient.
