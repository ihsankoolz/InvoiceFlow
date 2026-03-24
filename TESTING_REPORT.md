# InvoiceFlow Backend — End-to-End Testing Report

**Date:** 24 March 2026
**Scope:** Full backend integration test across all microservices, orchestrators, Temporal workflows, and RabbitMQ choreography.

---

## Test Environment

- All 11 services running via Docker Compose (6 atomic, 3 orchestrators, 2 wrappers)
- Infrastructure: Temporal, RabbitMQ, MinIO, Kong, 5 MySQL databases, 1 PostgreSQL (Temporal)
- Temporal workflows tested with reduced timer values (`REPAYMENT_WINDOW_SECONDS=15`, `ANTI_SNIPE_SECONDS=10`) to avoid waiting hours/days

## Scenarios Tested

### Scenario 1 — Invoice Upload & Listing
**Flow:** Seller registers → uploads invoice (PDF + metadata) → ACRA UEN validation → marketplace listing created → invoice status set to LISTED

**Result:** Passed. Invoice created with PDF extraction (via pdfplumber), stored in MinIO, listed on marketplace.

### Scenario 2 — Auction Settlement & Loan Default (Overdue Path)
**Flow:** Multiple investors bid on listed invoice → AuctionCloseWorkflow runs (anti-snipe timer → 10-step settlement) → LoanMaturityWorkflow fires as child → repayment window expires → loan marked OVERDUE → seller DEFAULTED → bulk delist

**Verified:**
- Invoice status: `FINANCED` → `DEFAULTED`
- Winning bid: `ACCEPTED`, losing bids: `REJECTED`
- Marketplace listing: deleted
- Loan status: `ACTIVE` → `DUE` → `OVERDUE`
- Seller account: `ACTIVE` → `DEFAULTED`
- RabbitMQ `loan.overdue` event triggered 4 choreography consumers (invoice status update, 5% penalty calculation, seller default, notification)

### Scenario 3 — Auction Settlement & Loan Repayment (Happy Path)
**Flow:** Same auction settlement → LoanMaturityWorkflow fires → seller repays within window → loan marked REPAID → seller stays ACTIVE

**Verified:**
- Loan status: `REPAID`
- Seller account: remains `ACTIVE`
- Invoice status: remains `FINANCED`
- LoanMaturityWorkflow exited cleanly without triggering overdue path

---

## Bugs Found & Fixed

| # | Bug | Service | Root Cause | Fix |
|---|-----|---------|------------|-----|
| 1 | `ModuleNotFoundError: dotenv` | Invoice Orchestrator | Missing `python-dotenv` in requirements.txt | Added `python-dotenv==1.0.1` |
| 2 | Invoice PDF upload 422 error | Invoice Orchestrator | Sent file as `"pdf"` but Invoice Service expects `"pdf_file"` | Fixed field name in `orchestrator.py` |
| 3 | POST /listings 307 redirect drops body | Invoice Orchestrator | Missing trailing slash on `/listings` URL | Changed to `/listings/` |
| 4 | Delist activity calls wrong URL | Temporal Worker | Called `PATCH /listings/{token}` but no such endpoint exists | Added `DELETE /by-token/{token}` endpoint to Marketplace Service, updated activity |
| 5 | gRPC proto import failure | Bidding & Loan Orchestrators | Generated stubs use bare `import payment_pb2` but live in `app/proto/` subpackage | Added `sys.path.insert` in `__init__.py` |
| 6 | Anti-snipe timezone error | Bidding Orchestrator | `TypeError: can't subtract offset-naive and offset-aware datetimes` | Ensured deadline is timezone-aware UTC |
| 7 | `loan_id` type mismatch | Loan Orchestrator | Expected `int` but Payment Service uses UUID strings | Changed all `loan_id: int` to `str` |
| 8 | Missing `invoice_token` in events | Payment Service + gRPC clients | `loan.repaid`/`loan.overdue` events didn't include `invoice_token`, breaking Invoice Service choreography | Added `invoice_token` field to `LoanResponse` proto, updated all gRPC handlers and clients |
| 9 | Wrong accept/reject bid URLs | Temporal Worker | Called `PATCH /bids/{id}` with JSON body but Bidding Service expects `PATCH /bids/{id}/accept` and `/reject` (no body) | Fixed URLs |
| 10 | Child workflow terminated on parent close | Temporal Worker | `start_child_workflow` defaults to `TERMINATE` parent close policy; LoanMaturityWorkflow killed when AuctionCloseWorkflow finishes | Added `parent_close_policy=ParentClosePolicy.ABANDON` |

## Files Changed (22 files)

**Orchestrators:**
- `orchestrators/invoice-orchestrator/app/services/orchestrator.py` — PDF field name + trailing slash fix
- `orchestrators/bidding-orchestrator/app/proto/__init__.py` — sys.path fix for proto imports
- `orchestrators/bidding-orchestrator/app/services/bid_orchestrator.py` — timezone-aware anti-snipe
- `orchestrators/bidding-orchestrator/proto/payment.proto` — added `invoice_token` to LoanResponse
- `orchestrators/loan-orchestrator/app/proto/__init__.py` — sys.path fix for proto imports
- `orchestrators/loan-orchestrator/app/config.py` — added PAYMENT_SERVICE_URL
- `orchestrators/loan-orchestrator/app/routers/loans.py` — loan_id int→str
- `orchestrators/loan-orchestrator/app/schemas/requests.py` — loan_id int→str
- `orchestrators/loan-orchestrator/app/services/grpc_client.py` — loan_id int→str + invoice_token
- `orchestrators/loan-orchestrator/app/services/loan_orchestrator.py` — loan_id int→str + invoice_token in events
- `orchestrators/loan-orchestrator/proto/payment.proto` — added `invoice_token` to LoanResponse

**Atomic Services:**
- `services/marketplace-service/app/routers/listings.py` — added by-token GET/DELETE endpoints
- `services/marketplace-service/app/services/listing_service.py` — added by-token query/delete methods
- `services/payment-service/proto/payment.proto` — added `invoice_token` to LoanResponse
- `services/payment-service/src/grpc/handlers.js` — return `invoice_token` in gRPC responses

**Temporal Worker:**
- `temporal-worker/activities/bidding_activities.py` — fixed accept/reject offer URLs
- `temporal-worker/activities/marketplace_activities.py` — fixed delist/bulk_delist URLs
- `temporal-worker/clients/grpc_client.py` — added `invoice_token` to get_loan response
- `temporal-worker/config.py` — added ANTI_SNIPE_SECONDS config
- `temporal-worker/proto/payment.proto` — added `invoice_token` to LoanResponse
- `temporal-worker/workflows/auction_close.py` — configurable anti-snipe timer + ParentClosePolicy.ABANDON

**Infrastructure:**
- `docker-compose.yml` — added ANTI_SNIPE_SECONDS env var to temporal-worker
