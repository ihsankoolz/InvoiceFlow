# InvoiceFlow — Detailed Scenario Flows

Steps labelled Xa/Xb/Xc occur **concurrently**.

---

## Scenario 1: Business Lists Invoice for Auction

**Trigger:** Business clicks "List Invoice" in the React frontend.

| Step | From | To | Action | Tech | Notes |
|------|------|----|--------|------|-------|
| 1 | Business | React Frontend | Upload PDF + fill form | Browser | |
| 2 | React Frontend | KONG | `POST /api/invoices` (JWT + PDF multipart) | HTTPS | |
| 3 | KONG | Invoice Orchestrator :5010 | Route | REST/JSON | JWT validated |
| 4 | Invoice Orchestrator | User Service | `GET /users/{id}` — check account_status ACTIVE | HTTP | Rejects if DEFAULTED |
| 5 | Invoice Orchestrator | Invoice Service | `POST /invoices` — create record, pdfplumber extract, upload to MinIO | HTTP | |
| 6 | Invoice Service | MinIO | Store PDF | S3 :9000 | Internal to Invoice Service |
| 7 | Invoice Orchestrator | ACRA Wrapper :5007 | `POST /validate-uen` — validate debtor UEN | REST/JSON | |
| 8 | ACRA Wrapper | data.gov.sg | UEN registry lookup | HTTPS (external) | |
| 9a | *(UEN invalid)* Invoice Orchestrator | Invoice Service | `PATCH /invoices/{token}` → REJECTED | HTTP | Concurrent with 9b |
| 9b | *(UEN invalid)* Invoice Orchestrator | RabbitMQ | Publish `invoice.rejected` → **flow ends** | AMQP | Concurrent with 9a |
| 10 | Invoice Orchestrator | Marketplace Service | `POST /listings` — create listing with urgency + deadline | HTTP | |
| 11 | Invoice Orchestrator | Invoice Service | `PATCH /invoices/{token}` → LISTED | HTTP | |
| 12 | Invoice Orchestrator | Temporal Server | Start `AuctionCloseWorkflow` (ID: `auction-{invoice_token}`) | Temporal SDK | Durable timer begins |
| 13 | Invoice Orchestrator | RabbitMQ | Publish `invoice.listed` | AMQP | |
| 14a | RabbitMQ | Notification Service | Consume `invoice.listed` | AMQP | Concurrent with 14b |
| 14b | RabbitMQ | Activity Log Bridge | Consume `invoice.listed` → relay to OutSystems | AMQP → HTTPS | Concurrent with 14a |
| 15a | Notification Service | Resend | Send invoice listed confirmation email to business | HTTPS (external) | Concurrent with 15b |
| 15b | Notification Service | React Frontend | WebSocket push — invoice listed notification | WebSocket | Concurrent with 15a |

**AuctionCloseWorkflow (background, durable):**

| Step | Action |
|------|--------|
| T1 | Temporal Worker polls `invoiceflow-queue` |
| T2 | Durable timer runs for `bid_period_hours` |
| T3a | At T-12h: publish `auction.closing.warning` to RabbitMQ |
| T3b | At T-1h: publish `auction.closing.warning` to RabbitMQ |

---

## Scenario 2: Investor Bids on Invoice (with Anti-Snipe) and Wins Auction

### Phase A: Wallet Top-Up via Stripe

| Step | From | To | Action | Tech | Notes |
|------|------|----|--------|------|-------|
| A1 | Investor | React Frontend | Click "Top Up Wallet" | Browser | |
| A2 | React Frontend | KONG | `POST /api/wallet/topup` | HTTPS | |
| A3 | KONG | Bidding Orchestrator :5011 | Route | REST/JSON | |
| A4 | Bidding Orchestrator | Stripe Wrapper :5008 | `POST /create-checkout-session` (type=wallet_topup) | REST/JSON | |
| A5 | Stripe Wrapper | Stripe | Create Checkout Session | HTTPS (external) | |
| A6 | Stripe | Stripe Wrapper | Return checkout URL | HTTPS response | |
| A7 | Stripe Wrapper | Bidding Orchestrator | Return checkout URL | REST response | |
| A8 | Bidding Orchestrator | KONG | Return checkout URL | REST response | |
| A9 | KONG | React Frontend | Forward checkout URL → redirect investor | REST response | |
| A10 | Investor | Stripe | Complete payment on hosted checkout | Browser | |
| A11 | Stripe | KONG | Webhook `checkout.session.completed` (Stripe-Signature header) | HTTPS | |
| A12 | KONG | Webhook Router :5013 | Route | REST/JSON | |
| A13 | Webhook Router | — | Verify Stripe-Signature HMAC; reject mismatches/replays >5 min | Internal | |
| A14 | Webhook Router | RabbitMQ | Publish `stripe.checkout.completed` (type=wallet_topup) | AMQP | |
| A15 | RabbitMQ | Bidding Orchestrator | Consume `stripe.checkout.completed` (type=wallet_topup) | AMQP | |
| A16 | Bidding Orchestrator | Temporal Server | Start `WalletTopUpWorkflow` (ID: `wallet-topup-{session_id}`) | Temporal SDK | Idempotent |
| A17 | Temporal Worker | Payment Service | `CreditWallet` — credit investor wallet | gRPC :50051 | |
| A18 | Temporal Worker | User Service | `GET /users/{id}` — fetch investor email | HTTP | |
| A19 | Temporal Worker | RabbitMQ | Publish `wallet.credited` | AMQP | |
| A20a | RabbitMQ | Notification Service | Consume `wallet.credited` | AMQP | Concurrent with A20b |
| A20b | RabbitMQ | Activity Log Bridge | Consume `wallet.credited` → relay to OutSystems | AMQP → HTTPS | Concurrent with A20a |
| A21a | Notification Service | Resend | Send wallet credited confirmation email to investor | HTTPS (external) | Concurrent with A21b |
| A21b | Notification Service | React Frontend | WebSocket push — wallet credited notification | WebSocket | Concurrent with A21a |

### Phase B: Placing a Bid (with Anti-Snipe Extension)

| Step | From | To | Action | Tech | Notes |
|------|------|----|--------|------|-------|
| B1 | Investor | React Frontend | Browse marketplace listings | Browser | |
| B2 | React Frontend | KONG | `GET /api/listings` | HTTPS | |
| B3 | KONG | Marketplace Service | Fetch listings from market_db read-model | REST/JSON | |
| B4 | Marketplace Service | React Frontend | Return filtered listings with current deadlines | REST response | |
| B5 | Investor | React Frontend | Place bid | Browser | |
| B6 | React Frontend | KONG | `POST /api/bids` | HTTPS | |
| B7 | KONG | Bidding Orchestrator :5011 | Route | REST/JSON | |
| B8 | Bidding Orchestrator | Bidding Service | `POST /bids` — validate + create bid, fetch previous highest bidder | HTTP | |
| B9 | Bidding Orchestrator | Payment Service | `LockEscrow` — lock bid amount from investor wallet | gRPC :50051 | Idempotency key attached |
| B10a | *(If outbid)* Bidding Orchestrator | RabbitMQ | Publish `bid.outbid` | AMQP | Concurrent with B10b fan-out |
| B10b | *(If outbid)* RabbitMQ | Payment Service | Consume `bid.outbid` → release previous bidder's escrow to wallet | AMQP (choreography) | Concurrent with B10c |
| B10c | *(If outbid)* RabbitMQ | Notification Service | Consume `bid.outbid` → notify outbid investor | AMQP | Concurrent with B10b |
| B10d | *(If outbid)* Notification Service | Resend | Send outbid email to previous highest bidder | HTTPS (external) | Concurrent with B10e |
| B10e | *(If outbid)* Notification Service | React Frontend | WebSocket push — outbid notification | WebSocket | Concurrent with B10d |
| B11 | Bidding Orchestrator | Marketplace Service | `GET /listings/{id}` — check if within `ANTI_SNIPE_WINDOW_SECONDS` (default 300s) | HTTP | |
| B12a | *(If within window)* Bidding Orchestrator | Temporal Server | Signal `extend_deadline` to `AuctionCloseWorkflow` — restart timer | Temporal SDK | Concurrent with B12b, B12c |
| B12b | *(If within window)* Bidding Orchestrator | Marketplace Service | `PATCH /listings/{id}` — update displayed deadline (+300s) | HTTP | Concurrent with B12a, B12c |
| B12c | *(If within window)* Bidding Orchestrator | RabbitMQ | Publish `auction.extended` | AMQP | Concurrent with B12a, B12b |
| B13 | Bidding Orchestrator | RabbitMQ | Publish `bid.placed` | AMQP | |
| B14a | RabbitMQ | Notification Service | Consume `bid.placed` → notify seller | AMQP | Concurrent with B14b |
| B14b | RabbitMQ | Activity Log Bridge | Consume → relay to OutSystems | AMQP → HTTPS | Concurrent with B14a |
| B15a | Notification Service | Resend | Send new bid email to seller | HTTPS (external) | Concurrent with B15b |
| B15b | Notification Service | React Frontend | WebSocket push — new bid notification to seller | WebSocket | Concurrent with B15a |

### Phase C: Auction Closes (Timer Expires)

| Step | From | To | Action | Tech | Notes |
|------|------|----|--------|------|-------|
| C1 | AuctionCloseWorkflow | — | Final 5-min timer expires with no `extend_deadline` signal | Temporal internal | Anti-snipe window passed |
| C2 | Temporal Worker | Bidding Service | `GET /bids?invoice_token={token}` — fetch all offers | HTTP | |
| C3 | *(Zero bids)* Temporal Worker | RabbitMQ | Publish `auction.expired` → **flow ends** | AMQP | |
| C4 | Temporal Worker | Invoice Service | `verify_invoice_available` — confirm still LISTED | HTTP | Step 1 |
| C5 | Temporal Worker | Payment Service | `ConvertEscrowToLoan` — convert winner's escrow | gRPC :50051 | Step 2 |
| C6 | Temporal Worker | Payment Service | `CreateLoan` — create loan with due_date | gRPC :50051 | Step 3 |
| C7 | Temporal Worker | Temporal Server | Start `LoanMaturityWorkflow` as child (ID: `loan-{loan_id}`) | Temporal SDK | Step 4 — fire-and-forget |
| C8 | Temporal Worker | Payment Service | `ReleaseFundsToSeller` — transfer principal to seller wallet | gRPC :50051 | Step 5 |
| C9 | Temporal Worker | Invoice Service | `PATCH /invoices/{token}` → FINANCED | HTTP | Step 6 |
| C10 | Temporal Worker | Marketplace Service | `DELETE /listings/{id}` — delist | HTTP | Step 7 |
| C11 | Temporal Worker | Bidding Service | `accept_offer` (winner) | HTTP | Step 8 |
| C12 | Temporal Worker | Bidding Service | `reject_offer` (all losers — **parallel**) | HTTP | Step 9 |
| C12b | Temporal Worker | Payment Service | `ReleaseEscrow` (PENDING losers only — **parallel**) | gRPC :50051 | OUTBID losers already had escrow released during bid placement (2B); only investors whose bids were never the highest remain PENDING with locked escrow at settlement |
| C13 | Temporal Worker | RabbitMQ | Publish `auction.closed.winner` + `auction.closed.loser` (per loser) | AMQP | Step 10 |
| C14a | RabbitMQ | Notification Service | Consume `auction.closed.*` | AMQP | Concurrent with C14b |
| C14b | RabbitMQ | Activity Log Bridge | Consume → relay to OutSystems | AMQP → HTTPS | Concurrent with C14a |
| C15a | Notification Service | Resend | Send auction result emails to winner, losers, and seller | HTTPS (external) | Concurrent with C15b |
| C15b | Notification Service | React Frontend | WebSocket push — auction result notification | WebSocket | Concurrent with C15a |

---

## Scenario 3: Loan Maturity and Business Default

### Phase A: Loan Comes Due

| Step | From | To | Action | Tech | Notes |
|------|------|----|--------|------|-------|
| A1 | LoanMaturityWorkflow | — | Durable timer fires on `due_date` (days/weeks after auction) | Temporal internal | Child of AuctionCloseWorkflow |
| A2 | Temporal Worker | Payment Service | `UpdateLoanStatus` → DUE | gRPC :50051 | |
| A3 | Temporal Worker | RabbitMQ | Publish `loan.due` | AMQP | |
| A4a | RabbitMQ | Notification Service | Consume `loan.due` | AMQP | Concurrent with A4b |
| A4b | RabbitMQ | Activity Log Bridge | Consume `loan.due` → relay to OutSystems | AMQP → HTTPS | Concurrent with A4a |
| A5a | Notification Service | Resend | Send loan due email to business | HTTPS (external) | Concurrent with A5b |
| A5b | Notification Service | React Frontend | WebSocket push — loan due notification | WebSocket | Concurrent with A5a |
| A6 | LoanMaturityWorkflow | — | Start repayment window (`DEMO_REPAYMENT_WINDOW_SECONDS` / `REPAYMENT_WINDOW_SECONDS`, default 86400s) — if window expires unpaid, flow continues to Phase B | Temporal internal | |

### Phase B: Business Defaults (repayment window expires)

| Step | From | To | Action | Tech | Notes |
|------|------|----|--------|------|-------|
| B1 | LoanMaturityWorkflow | — | Repayment window timer expires unpaid | Temporal internal | Continues from Phase A |
| B2 | Temporal Worker | Payment Service | `GetLoan` — confirm still DUE | gRPC :50051 | |
| B3 | Temporal Worker | Payment Service | `UpdateLoanStatus` → OVERDUE | gRPC :50051 | |
| B4 | Temporal Worker | RabbitMQ | Publish `loan.overdue` | AMQP | **Four-consumer choreography begins** |
| B5a | RabbitMQ | Invoice Service | `invoice_loan_updates` → mark invoice DEFAULTED | AMQP | Consumer 1 — concurrent with B5b/c/d |
| B5b | RabbitMQ | Payment Service | `payment_loan_updates` → calculate 5% penalty | AMQP | Consumer 2 — concurrent with B5a/c/d |
| B5c | RabbitMQ | User Service | `user_loan_updates` → set business account_status → DEFAULTED | AMQP | Consumer 3 — concurrent with B5a/b/d |
| B5d | RabbitMQ | Notification Service | `notification_loan_updates` → consume `loan.overdue` | AMQP | Consumer 4 — concurrent with B5a/b/c |
| B6 | RabbitMQ | Activity Log Bridge | Consume `loan.overdue` → relay to OutSystems | AMQP → HTTPS | |
| B7a | Notification Service | Resend | Send default emails to business + investor | HTTPS (external) | Concurrent with B7b |
| B7b | Notification Service | React Frontend | WebSocket push — loan overdue/default notification | WebSocket | Concurrent with B7a |
| B8 | Temporal Worker | Marketplace Service | `DELETE /listings?seller_id={id}` — bulk delist all defaulting seller's active listings | HTTP | Prevents further auctions |
| B9 | LoanMaturityWorkflow | — | **Workflow ends** | Temporal internal | |
