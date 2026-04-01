# fixes1April — Session Changelog

## 1. Prometheus Metrics (GET /metrics returning 404)

**Bug:** All 12 services returned 404 on `GET /metrics`, causing Prometheus scrape failures.

**Fix:**
- Added `prometheus-fastapi-instrumentator==7.1.0` to `requirements.txt` for all 12 services
- Added `Instrumentator().instrument(app).expose(app)` after `app = FastAPI(...)` in all 12 `main.py` files

**Affected services:** bidding-service, invoice-service, marketplace-service, user-service, notification-service, stripe-wrapper, acra-wrapper, dlq-monitor, webhook-router, invoice-orchestrator, bidding-orchestrator, loan-orchestrator

---

## 2. Marketplace Service SQL Error (Missing DB Columns)

**Bug:** marketplace-service crashed on startup — Alembic tried to create the `listings` table but `init.sql` had already created it without the new columns (`face_value`, `debtor_name`, `current_bid`, `bid_count`).

**Fix:** Used `alembic stamp 0001` then `alembic upgrade head` to bring Alembic's migration history in sync with the existing table state. Same pattern applied to bidding-service.

---

## 3. Grafana / Vite Port 3000 Conflict

**Bug:** After a Stripe checkout, the success URL redirected to Grafana's login page instead of the frontend — both were running on port 3000.

**Fix:** Changed Grafana's host port in `docker-compose.yml` from `3000:3000` to `3001:3000`. Grafana is now at `http://localhost:3001`.

---

## 4. Tempo Crash (Permission Denied)

**Bug:** Tempo container crashed on startup with `permission denied` when trying to create `/tmp/tempo/blocks`.

**Fix:** Added `user: root` to the `tempo` service in `docker-compose.yml`.

---

## 5. Notification Service — Persistent Database

**New Feature:** Notification service previously stored notifications in-memory, so they disappeared on every container restart.

**Changes:**
- Added a new `notification-db` MySQL service in `docker-compose.yml` (port 3311)
- Created `databases/notification-db/init.sql` with a `notifications` table
- Added `services/notification-service/app/database.py` — SQLAlchemy engine + session
- Added `services/notification-service/app/models/notification.py` — Notification ORM model
- Updated `app/config.py` to include `DB_URL`
- Updated `app/main.py` to call `Base.metadata.create_all(bind=engine)` on startup
- Rewrote `notification_handler.py` to persist notifications to MySQL instead of in-memory list
- Rewrote `routers/notifications.py` to query MySQL (`GET /api/notifications`, `PATCH /api/notifications/{id}/read`)
- Added `cryptography==43.0.3` to requirements to support MySQL's `caching_sha2_password` auth

---

## 6. Wallet Error Message Improvement

**Bug:** When an investor with no wallet tried to place a bid, the error shown was `"Wallet not found for user 3"` — confusing to the end user.

**Fix:** Changed error messages in `services/payment-service/src/services/WalletService.js`:
- `debitWallet`: now throws `"You need to top up your wallet before placing a bid."`
- `getBalance`: same message

---

## 7. Escrow Not Released on Outbid

**Bug (Major):** When investor A was outbid by investor B:
- Investor A's funds stayed locked in escrow and were never returned to their wallet
- Investor A's bid status remained `PENDING` instead of changing to `OUTBID`
- No notification was sent to the seller about the new bid

**Root cause:** The bidding-orchestrator's outbid handling had no gRPC call to release the displaced investor's escrow, and there was no `OUTBID` bid status in the system.

**Changes:**

*Bidding Service:*
- Added `OUTBID` to the `bid_status` enum in `models/bid.py`
- Added `OUTBID` to `BidStatusUpdate` Literal in `schemas/bid.py`
- Added `outbid_bid(bid_id)` method to `services/bid_service.py`
- Added `PATCH /bids/{bid_id}/outbid` endpoint to `routers/bids.py`
- Created Alembic migration `0002_add_outbid_status.py`

*Bidding Orchestrator:*
- Added `release_escrow()` to `app/services/grpc_client.py`
- Updated Step 3 of `bid_orchestrator.py` to:
  1. Call `release_escrow` via gRPC for the displaced investor (best-effort)
  2. Call `PATCH /bids/{id}/outbid` to mark bid status as OUTBID (best-effort)
  3. Include `previous_bid_id` in `bid.outbid` event payload

*Temporal Worker:*
- Added `release_escrow` activity to `activities/payment_activities.py`
- Added `release_escrow` method to `clients/grpc_client.py`
- Updated `workflows/auction_close.py` to release escrow for all losing bidders at auction close (parallel `asyncio.gather`)

---

## 8. OUTBID Bids Disappearing from Active Bids Dashboard

**Bug:** After being outbid, the "Active Bids" card on the investor dashboard showed 0 bids because the filter only included `PENDING` and `ACTIVE` statuses.

**Fix:** Updated `frontend/src/pages/DashboardPage.jsx`:
- Filter now includes `OUTBID` status so the invoice still appears in the list
- Leading count only counts `PENDING`/`ACTIVE` bids
- Outbid count shows separately for `OUTBID` bids
- Bid row badge now correctly shows "Outbid" vs "Leading" based on status

---

## 9. Re-bid Escrow Leak (Post-Lock Failure)

**Bug:** If any step after escrow lock succeeded but before bid completion (e.g., fetching listing, publishing events) threw an exception, the escrow would remain locked and the bid orphaned — but no error was surfaced to rollback.

**Fix:** Wrapped Steps 3–5 of `bid_orchestrator.py` in a `try/except` block. On any failure after escrow lock:
1. Best-effort `release_escrow` to unlock the just-locked funds
2. Best-effort `DELETE /bids/{id}` to remove the orphaned bid
3. Returns HTTP 500 with a clear error message

---

## 10. Atomic Escrow Locking — Wallet Debit Without Escrow Record

**Bug (Critical):** When an investor re-bid on the same invoice after being outbid:
- Wallet balance was debited (money deducted)
- Escrow record was NOT created
- Bid was deleted via rollback
- Net result: money gone from wallet, no escrow, no bid

**Root Cause — Two sub-bugs:**

**Sub-bug A: Non-atomic transactions**
`EscrowService.lockEscrow` called `walletService.debitWallet()` inside an outer `sequelize.transaction()`, but `debitWallet` created its own **separate, independent** transaction. So the wallet debit committed even when the escrow INSERT later failed and the outer transaction rolled back.

**Sub-bug B: Unique constraint on (investor_id, invoice_token)**
The `escrows` table has `UNIQUE KEY unique_escrow (investor_id, invoice_token)`. Even after an escrow is RELEASED, the row still exists — so any re-bid attempt for the same invoice fails the INSERT with a unique constraint violation.

**Fixes in `services/payment-service`:**

`WalletService.js`:
- `debitWallet(userId, amount, outerTransaction = null)` — now accepts optional outer transaction; when provided, executes within it instead of creating a new one
- `creditWallet(userId, amount, outerTransaction = null)` — same change

`EscrowService.js`:
- `lockEscrow`: passes outer transaction `t` to `debitWallet(investorId, amount, t)` — wallet debit and escrow creation are now atomic
- `lockEscrow`: checks for existing escrow row first; if found (status RELEASED), does `UPDATE` instead of `INSERT` to avoid the unique constraint
- `releaseEscrow`: passes outer transaction `t` to `creditWallet(investorId, amount, t)` — credit and status update are now atomic

**Bidding Orchestrator Step 2 rollback (`bid_orchestrator.py`):**
- On escrow lock failure: now also attempts `release_escrow` (best-effort) before raising the error, to handle the case where the payment service deducted funds before gRPC errored
- Error message is now user-friendly: "Insufficient wallet balance" or "Could not place bid. Please try again."

**Data fix:** Investor 5's wallet was restored to the correct balance (150,000) after two orphaned debits (62,001 + 63,000) were identified and refunded via a `SYSTEM_CORRECTION` wallet transaction.
