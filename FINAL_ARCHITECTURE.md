# InvoiceFlow — Architecture (Updated)

**SMU IS213 · Enterprise Solution Development · AY2025/26**

InvoiceFlow is an invoice factoring marketplace where businesses list invoices for auction and investors bid to finance them. The platform handles the full lifecycle: invoice listing, competitive bidding, fund disbursement, loan tracking, and debt resolution.

---

## Three User Scenarios

### Scenario 1: Business Lists Invoice for Auction

A business uploads an invoice PDF, the system extracts key fields (pdfplumber), validates the debtor's UEN against Singapore's ACRA registry (via ACRA Wrapper → data.gov.sg), lists it on the marketplace with an urgency level, and starts a countdown timer for the auction.

**Services involved:** Invoice Orchestrator (composite), User Service, Invoice Service, Marketplace Service, ACRA Wrapper (wrapper), data.gov.sg (external), MinIO, Temporal Server, RabbitMQ, Notification Service (includes Resend), Activity Log Bridge → OutSystems

**Temporal Workflow triggered:** AuctionCloseWorkflow — started by Invoice Orchestrator after the invoice is successfully listed. Sets durable timers for T-12h warning, T-1h warning, and the bid deadline.

**Communication patterns:** Synchronous orchestration (Invoice Orchestrator → atomics via direct HTTP), async event publishing to RabbitMQ for notifications and audit logging.

---

### Scenario 2: Investor Bids on Invoice (with Anti-Snipe Protection) and Wins Auction

An investor tops up their wallet via Stripe, browses the marketplace, and places a bid (escrow locked immediately via gRPC). If this bid outbids a previous highest bidder, the previous bidder's escrow is released immediately back to their wallet via choreography. The system implements anti-snipe protection: if a bid is placed within the final 5 minutes of the auction, the deadline automatically extends by 5 minutes, giving other investors a fair window to respond. This extension can trigger repeatedly — every bid in the final 5 minutes resets the 5-minute window. When no new bids arrive within the final window and the (possibly extended) timer expires, only the winning bidder has escrow locked. Temporal then executes the financial workflow: convert escrow, create loan, release funds to seller, update statuses, delist, and notify all parties.

**Anti-snipe mechanism:** When Bidding Orchestrator processes a new bid, it checks if the auction is within its final `ANTI_SNIPE_WINDOW_SECONDS` (default 300s / 5 minutes, configurable via env var). If so, it sends a Temporal Signal (`extend_deadline`) to the running AuctionCloseWorkflow. The workflow receives the signal, cancels its current timer, and restarts the countdown. The Marketplace Service also updates the listing's displayed deadline so the frontend reflects the extension in real time.

**Stripe webhook path:** Stripe posts a webhook to KONG, which routes it to the Webhook Router service. The Webhook Router verifies the Stripe-Signature HMAC and publishes a normalised `stripe.checkout.completed` event (with a `type` field) to RabbitMQ. Bidding Orchestrator consumes events with `type=wallet_topup` and starts WalletTopUpWorkflow.

**Services involved:** Bidding Orchestrator (composite), Bidding Service, Payment Service (gRPC), Marketplace Service, Invoice Service, Webhook Router, Stripe Wrapper (wrapper), Stripe (external), Temporal Server + Worker, RabbitMQ, Notification Service (includes Resend), Activity Log Bridge → OutSystems

**Temporal Workflows triggered:**
- **WalletTopUpWorkflow** — started by Bidding Orchestrator when it consumes `stripe.checkout.completed` (type=wallet_topup) from RabbitMQ. Credits investor wallet via gRPC.
- **AuctionCloseWorkflow** — already running from Scenario 1. Listens for `extend_deadline` signals from Bidding Orchestrator. When the (possibly extended) timer fires with no further signals, the Temporal Worker executes the 10-step financial settlement. After `create_loan`, it starts LoanMaturityWorkflow as a child workflow.

**Communication patterns:** gRPC for escrow locking (idempotent, binary, fast), Temporal SDK for durable workflows and signals, AMQP for event fan-out.

---

### Scenario 3: Loan Maturity and Business Default

The LoanMaturityWorkflow (already running as a child of AuctionCloseWorkflow) fires when the loan's due date arrives. It marks the loan DUE, notifies the business, and starts a 24-hour repayment window. If the business repays via Stripe in time, the frontend redirects to the success page, which calls the Loan Orchestrator `confirm-repayment` endpoint, starting LoanRepaymentWorkflow. The Temporal Worker then marks the loan REPAID via gRPC and publishes `loan.repaid` to RabbitMQ; four consumers react via choreography: Invoice Service marks the invoice REPAID, Payment Service credits the investor's wallet, User Service resets the business account to ACTIVE, and Notification Service alerts both parties. If the business does not repay within the window, LoanMaturityWorkflow marks the loan OVERDUE via gRPC and publishes `loan.overdue`; the same four-consumer choreography applies, with Invoice Service marking the invoice DEFAULTED, Payment Service calculating a 5% penalty, User Service setting the account to DEFAULTED, and Notification Service alerting both parties. Temporal then bulk-delists all the defaulting seller's active listings.

**Services involved:** Loan Orchestrator (composite), Webhook Router, Payment Service, Invoice Service, User Service, Marketplace Service, Stripe Wrapper (wrapper), Stripe (external), Temporal Worker, RabbitMQ, Notification Service (includes Resend), Activity Log Bridge → OutSystems

**Temporal Workflows involved:**
- **LoanMaturityWorkflow** — started as a child workflow inside AuctionCloseWorkflow after `create_loan`. NOT started by any composite service directly.
- **LoanRepaymentWorkflow** — started by Loan Orchestrator after the Stripe success redirect calls `confirm-repayment`, OR when Loan Orchestrator consumes `stripe.checkout.completed` (type=loan_repayment). Marks loan REPAID via gRPC and publishes `loan.repaid`.

**Communication patterns:** Temporal durable timer (24h countdown), four-consumer fan-out choreography on both `loan.repaid` and `loan.overdue` (4 separate RabbitMQ queues each), synchronous HTTP for repayment initiation through Loan Orchestrator.

---

## Four Temporal Workflows

### 1. AuctionCloseWorkflow

**Started by:** Invoice Orchestrator → Temporal Server (Temporal SDK)
**Triggered when:** Invoice is successfully listed on the marketplace
**Workflow ID:** `auction-{invoice_token}`
**Task queue:** `invoiceflow-queue`

**What it does:**
1. Waits for `bid_period_hours` using Temporal's durable timer (survives crashes)
2. Sends T-12h auction closing warning (publishes `auction.closing.warning` to RabbitMQ)
3. Sends T-1h auction closing warning (publishes `auction.closing.warning` to RabbitMQ)
4. **Anti-snipe loop:** In the final `ANTI_SNIPE_SECONDS` window (default 300s, configurable via env var), the workflow listens for `extend_deadline` signals. Each signal resets the timer. The loop exits only when the timer expires with no new signal.
5. Timer expires — fetches all offers from Bidding Service (direct HTTP)
6. If zero bids → publishes `auction.expired` and ends
7. If bids exist → picks highest bidder as winner, runs the 10-step financial workflow:

| Step | Activity | Target Service | Technology |
|------|----------|----------------|------------|
| 1 | verify_invoice_available | Invoice Service | Direct HTTP |
| 2 | convert_escrow_to_loan | Payment Service | gRPC :50051 |
| 3 | create_loan | Payment Service | gRPC :50051 |
| 4 | **Start LoanMaturityWorkflow** | Temporal Server | Child workflow — fire-and-forget (`start_child_workflow`) |
| 5 | release_funds_to_seller | Payment Service | gRPC :50051 |
| 6 | update_invoice_status → FINANCED | Invoice Service | Direct HTTP |
| 7 | delist_from_marketplace | Marketplace Service | Direct HTTP |
| 8 | accept_offer (winner) | Bidding Service | Direct HTTP |
| 9 | reject_offer (all losers — **parallel**) | Bidding Service | Direct HTTP |
| 10 | publish_auction_outcome_events | RabbitMQ | AMQP publish |

**Note on escrow:** By auction close, only the winning bidder has funds in escrow. All previous bidders' escrow was already released immediately when they were outbid (via `bid.outbid` → Payment Service choreography). There is no refund step at auction close.

**Anti-snipe implementation detail:** The workflow uses `workflow.wait_condition()` with an `ANTI_SNIPE_SECONDS` timeout (env var, default 300s) inside a loop. When Bidding Orchestrator detects a bid within the anti-snipe window, it calls `workflow_handle.signal('extend_deadline')` via the Temporal SDK. The workflow receives the signal, sets a flag, and re-enters the loop with a fresh timer. The loop must check the signal flag before waiting (in case a signal arrived during the preceding `sleep_until`), then reset the flag only after confirming the check. The Bidding Orchestrator checks the same window via `ANTI_SNIPE_WINDOW_SECONDS` (env var, default 300s) when comparing the current time against the marketplace listing deadline.

**Ends when:** All steps complete (or all retries exhausted → failure recorded for manual intervention).

---

### 2. LoanMaturityWorkflow

**Started by:** Temporal Worker as a child workflow inside AuctionCloseWorkflow, after `create_loan` succeeds
**NOT started by any composite service**
**Workflow ID:** `loan-{loan_id}`

**What it does:**
1. Durable timer waits until `due_date` (could be days or weeks)
2. Marks loan DUE via Payment Service (gRPC :50051)
3. Publishes `loan.due` to RabbitMQ → Notification Service emails the business
4. Starts repayment window using `wait_condition` with timeout (`DEMO_REPAYMENT_WINDOW_SECONDS` in demo mode, `REPAYMENT_WINDOW_SECONDS` in production, default 86400s / 24h) — exits early if `repayment_confirmed` signal arrives from LoanRepaymentWorkflow
5. If signal received (or loan status already REPAID) → workflow ends cleanly
6. If timeout expires without signal → fetches loan status to confirm, then marks loan OVERDUE via gRPC, publishes `loan.overdue` to RabbitMQ
7. Four consumers react independently (choreography — see Choreography-Driven Flows)
8. Bulk-delists all defaulting seller's listings via Marketplace Service (direct HTTP)

**Signal handler:** `repayment_confirmed` — sent by LoanRepaymentWorkflow after marking the loan REPAID. Causes the repayment window to exit immediately rather than sleeping the full duration.

**Ends when:** Repayment window check completes (either repaid or overdue + delist done).

---

### 3. LoanRepaymentWorkflow

**Started by:** Loan Orchestrator → Temporal Server (Temporal SDK), triggered either via `POST /api/loans/{id}/confirm-repayment` (after Stripe success redirect) or when Loan Orchestrator consumes `stripe.checkout.completed` (type=loan_repayment) from RabbitMQ
**Workflow ID:** `loan-repay-{loan_id}`

**What it does:**
1. Marks loan REPAID via Payment Service (`UpdateLoanStatus` gRPC :50051)
2. Signals `repayment_confirmed` to the running `LoanMaturityWorkflow` (ID: `loan-{loan_id}`) — causes the maturity workflow to exit its repayment window early rather than sleeping the full duration
3. Fetches full loan details via Payment Service (`GetLoan` gRPC :50051)
4. Fetches seller and investor details via User Service (direct HTTP)
5. Publishes `loan.repaid` to RabbitMQ → four-consumer choreography begins

**Ends when:** Loan marked REPAID and event published.

---

### 4. WalletTopUpWorkflow

**Started by:** Bidding Orchestrator → Temporal Server (Temporal SDK), triggered when Bidding Orchestrator consumes `stripe.checkout.completed` (type=wallet_topup) from RabbitMQ
**Workflow ID:** `wallet-topup-{stripe_session_id}` (idempotent — same session ID prevents duplicate processing)

**What it does:**
1. Credits investor wallet via Payment Service (`CreditWallet` gRPC :50051)
2. Fetches investor details via User Service (direct HTTP)
3. Publishes `wallet.credited` to RabbitMQ → Notification Service sends confirmation email + WebSocket push

**Ends when:** Wallet credited and event published.

---

## Service Inventory

### Composite Services (3)

| Service | Port | Technology | Scenario |
|---------|------|------------|----------|
| Invoice Orchestrator | :5010 | Python / FastAPI | Scenario 1 — invoice creation, UEN validation, listing |
| Bidding Orchestrator | :5011 | Python / FastAPI | Scenario 2 — bid placement, escrow locking, wallet top-up, Stripe event handling |
| Loan Orchestrator | :5012 | Python / FastAPI | Scenario 3 — repayment initiation, debt resolution |

Composite services orchestrate atomic services via direct HTTP (inside Docker network). They never call each other. They publish events to RabbitMQ but do NOT connect to Notification Service or Activity Log Bridge directly.

### Atomic Services (7)

| Service | Port | Technology | Database | Notes |
|---------|------|------------|----------|-------|
| User Service | :5000 | Python / FastAPI | user_db (MySQL :3306) | Registration, login, JWT, account status. Calls data.gov.sg directly for seller UEN validation at registration. Also a RabbitMQ consumer for `loan.repaid` and `loan.overdue` (account status updates via choreography) |
| Invoice Service | :5001 | Python / FastAPI | invoice_db (MySQL :3307) | Invoice CRUD, PDF upload, pdfplumber, MinIO storage, status tracking. Also a RabbitMQ consumer for `loan.repaid` and `loan.overdue` |
| Marketplace Service | :5002 | Python / FastAPI | market_db (MySQL :3308) | Listings read-model, urgency levels, filtering. Denormalises `current_bid` and `bid_count` from events |
| Bidding Service | :5003 | Python / FastAPI | bidding_db (MySQL :3309) | Bid CRUD, offer accept/reject/outbid management |
| Payment Service | :5004 / :50051 | Node.js / Express + gRPC | payment_db (MySQL :3310) | Wallets, escrow, loans. REST :5004 for reads; gRPC :50051 for all writes. Also a RabbitMQ consumer for `bid.outbid` (escrow release), `loan.repaid` (credit investor wallet), and `loan.overdue` (calculate penalty). Idempotency key duplicates are logged at WARN level for observability. **BTL #1** |
| Notification Service | :5005 | Python / FastAPI | notification_db (MySQL :3311) | RabbitMQ consumer for all events; WebSocket push to frontend; Resend email delivery. Persists notifications to notification_db (last 50 per user served via API) |
| Webhook Router | :5013 | Python / FastAPI | None | Receives inbound Stripe webhooks, verifies Stripe-Signature HMAC, publishes normalised `stripe.checkout.completed` event to RabbitMQ. Decouples all downstream consumers from Stripe's raw payload shape |

Atomic services never call each other directly. All inter-atomic coordination goes through composite services or RabbitMQ choreography. Notification Service and Activity Log Bridge are pure RabbitMQ consumers — no composite service connects to them. User Service, Invoice Service, and Payment Service also consume specific events via RabbitMQ for choreography-driven flows (`loan.repaid`, `loan.overdue`, `bid.outbid`). This keeps account status updates (User Service), invoice status updates (Invoice Service), and financial operations (Payment Service) each within their domain owner.

### Read-Only Monitor (1)

| Service | Port | Technology | Notes |
|---------|------|------------|-------|
| DLQ Monitor | :5014 | Python / FastAPI | Read-only RabbitMQ Management API inspector. Queries queues ending in `.dlq` and reports message depths. Does not consume or acknowledge messages |

### Wrapper Services (2)

| Service | Port | Technology | Wraps | Called By |
|---------|------|------------|-------|----------|
| ACRA Wrapper | :5007 | Python / FastAPI | data.gov.sg ACRA UEN registry | Invoice Orchestrator (debtor UEN validation per invoice) |
| Stripe Wrapper | :5008 | Python / FastAPI | Stripe API (checkout sessions) | Bidding Orchestrator (wallet top-up checkout), Loan Orchestrator (loan repayment checkout) |

Note: Stripe Wrapper handles **outbound** calls only (creating checkout sessions). **Inbound** Stripe webhooks go through KONG → Webhook Router — the Stripe Wrapper is bypassed on the inbound path.

### Bridge Service (1)

| Service | Technology | Purpose | Called By |
|---------|------------|---------|----------|
| Activity Log Bridge | Python (pika) | RabbitMQ consumer with `#` wildcard routing key. Relays all domain events to the OutSystems Activity Log REST API. Constructs an `EventRequest` with `event_type`, `payload`, `source_service`, `invoice_token`, `user_id`, `timestamp`, and `severity`. Uses manual ack — on OutSystems failure, nacks without requeue so the message is routed to `outsystems_audit_queue.dlq`. On startup, retries the RabbitMQ connection up to 15 times (5s delay) to handle slow broker initialisation. No HTTP endpoints of its own | RabbitMQ (push) → OutSystems (HTTPS) |

### OutSystems Service (Activity Log)

| Service | Technology | Database | Notes |
|---------|------------|----------|-------|
| Activity Log (OutSystems) | OutSystems Platform | OutSystems internal DB | Receives all events forwarded by Activity Log Bridge. Maintains full audit trail with timestamps, event types, and payloads. Manages its own database internally — no separate MySQL instance |

### External Services

| Service | Purpose | Called By |
|---------|---------|----------|
| data.gov.sg | ACRA UEN registry (seller + debtor validation) | User Service (seller UEN at registration, direct), ACRA Wrapper (debtor UEN per invoice) |
| Stripe | Payment processing, hosted checkout, webhooks | Stripe Wrapper (outbound checkout sessions), Stripe → KONG → Webhook Router (inbound webhook) |
| Resend | Transactional email delivery | Notification Service (built-in, no wrapper) |

### Infrastructure

| Component | Port | Purpose |
|-----------|------|---------|
| KONG API Gateway | :8000 | JWT auth, rate limiting, CORS, routing. **External traffic only.** **BTL #2** |
| RabbitMQ | :5672 / :15672 | Topic exchange (`invoiceflow_events`). Async event delivery, DLQ per consumer |
| Temporal Server | :7233 | Durable workflow state, timers, task queues |
| Temporal Worker | — | Polls Temporal Server, executes workflow activities. Calls atomic services directly |
| Temporal UI | :8088 | Workflow viewer / debugger (dev tool) |
| MinIO | :9000 | Self-hosted S3-compatible file storage for invoice PDFs |

### Observability Stack

| Tool | Host Port | Purpose |
|------|-----------|---------|
| Prometheus | :9090 | Metrics scraping from all Python services. Alert rules in `alert_rules.yml` fire when any `.dlq` queue depth exceeds 5 messages (`DLQDepthHigh` alert) |
| Grafana | :3001 (maps to container :3000) | Dashboards |
| Loki | :3100 | Log aggregation |
| Promtail | — | Docker log shipping to Loki |
| Tempo | :3200 / :4317 / :4318 | Distributed tracing (OTLP). All Python services emit traces via OpenTelemetry (OTLP HTTP) |

---

## All Connections

### Presentation → Gateway

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 1 | Business uses app | Business → React Frontend | Browser |
| 2 | Investor uses app | Investor → React Frontend | Browser |
| 3 | All API requests | React Frontend → KONG | HTTPS |

### Gateway → Composites / Services

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 4 | Scenario 1 routes (`/api/invoices*`) | KONG → Invoice Orchestrator | REST/JSON |
| 5 | Scenario 2 bid + wallet routes (`/api/bids*`, `/api/wallet/*`) | KONG → Bidding Orchestrator | REST/JSON |
| 6 | Scenario 3 loan routes (`/api/loans*`) | KONG → Loan Orchestrator | REST/JSON |
| 7 | Notification read endpoints (`/api/notifications*`) | KONG → Notification Service | REST (direct, bypasses composites) |
| 8 | Stripe webhook (inbound) (`/api/webhooks/stripe`) | KONG → Webhook Router | REST/JSON (Stripe-Signature header forwarded) |

### Stripe Two-Direction Paths

Stripe communication runs in two directions — these are separate paths through the architecture:

| Direction | Path | Purpose |
|-----------|------|---------|
| Outbound (your system calls Stripe) | Orchestrator → Stripe Wrapper → Stripe | Create checkout sessions for wallet top-up or loan repayment |
| Inbound (Stripe calls your system) | Stripe → KONG → Webhook Router → RabbitMQ → Orchestrator → Temporal | Webhook confirms payment, triggers WalletTopUpWorkflow or LoanRepaymentWorkflow |

Stripe webhook safeguards: Webhook Router recomputes the Stripe-Signature using the shared secret + payload body — mismatches are rejected. The `stripe_session_id` in the Temporal workflow ID (`wallet-topup-{session_id}`) ensures Temporal refuses duplicate workflows if Stripe fires the same webhook twice.

### Composites → Wrappers

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 9 | Debtor UEN validation | Invoice Orchestrator → ACRA Wrapper | REST/JSON |
| 10 | Checkout session (wallet top-up) | Bidding Orchestrator → Stripe Wrapper | REST/JSON |
| 11 | Checkout session (loan repayment) | Loan Orchestrator → Stripe Wrapper | REST/JSON |

### Wrappers → External APIs

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 12 | ACRA UEN lookup (debtor) | ACRA Wrapper → data.gov.sg | HTTPS (external) |
| 13 | Stripe API calls (outbound only) | Stripe Wrapper → Stripe | HTTPS (external) |

### Atomics → External APIs (direct)

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 14 | ACRA UEN lookup (seller at registration) | User Service → data.gov.sg | HTTPS (external, direct — ACRA Wrapper not involved) |

### Composites → Atomics (direct HTTP inside Docker network)

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 15 | Account status check | Invoice Orchestrator → User Service | HTTP (direct) |
| 16 | Invoice create / upload / status | Invoice Orchestrator → Invoice Service | HTTP (direct) |
| 17 | List on marketplace | Invoice Orchestrator → Marketplace Service | HTTP (direct) |
| 18 | Bid placement / management | Bidding Orchestrator → Bidding Service | HTTP (direct) |
| 19 | Anti-snipe: check + update listing deadline | Bidding Orchestrator → Marketplace Service | HTTP (direct) |
| 20 | Escrow lock | Bidding Orchestrator → Payment Service | gRPC :50051 |
| 21 | Repayment checkout initiation | Loan Orchestrator → Payment Service | gRPC :50051 (GetLoan) |

### Composites → Temporal (start / signal workflows)

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 22 | Start AuctionCloseWorkflow | Invoice Orchestrator → Temporal Server | Temporal SDK |
| 23 | Start WalletTopUpWorkflow | Bidding Orchestrator → Temporal Server | Temporal SDK |
| 23a | Signal `extend_deadline` on AuctionCloseWorkflow | Bidding Orchestrator → Temporal Server | Temporal SDK (signal) |
| 24 | Start LoanRepaymentWorkflow | Loan Orchestrator → Temporal Server | Temporal SDK |
| 24a | Signal `repayment_confirmed` on LoanMaturityWorkflow | Temporal Worker (LoanRepaymentWorkflow) → Temporal Server | Temporal SDK (signal) — causes maturity workflow to exit repayment window early |

Invoice Orchestrator starts AuctionCloseWorkflow after an invoice is listed. Bidding Orchestrator starts WalletTopUpWorkflow after consuming `stripe.checkout.completed` (wallet_topup). Bidding Orchestrator signals running AuctionCloseWorkflow instances for anti-snipe deadline extensions. Loan Orchestrator starts LoanRepaymentWorkflow after the Stripe repayment confirm call. Loan Orchestrator does NOT start LoanMaturityWorkflow — that is started internally by the Temporal Worker as a child of AuctionCloseWorkflow.

### Temporal Internal

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 25 | Poll for tasks | Temporal Worker → Temporal Server | Temporal SDK (long-poll) |
| 26 | View workflows | Temporal UI → Temporal Server | HTTP |
| 27 | Start LoanMaturityWorkflow (child) | Temporal Worker → Temporal Server | Temporal SDK (internal, fire-and-forget) |

### Temporal Worker → Atomics (during workflow execution)

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 28 | Verify / update invoice status | Temporal Worker → Invoice Service | HTTP (direct) |
| 29 | Delist listing / bulk delist by seller | Temporal Worker → Marketplace Service | HTTP (direct) |
| 30 | Get offers / accept / reject offers | Temporal Worker → Bidding Service | HTTP (direct) |
| 31 | Convert escrow, create loan, release funds, credit wallet, update/check loan status | Temporal Worker → Payment Service | gRPC :50051 |
| 32 | Get user details (email) | Temporal Worker → User Service | HTTP (direct) |

### Publishing to RabbitMQ (async)

| # | Event(s) | Published By | Technology |
|---|----------|-------------|------------|
| 33 | `invoice.listed`, `invoice.rejected` | Invoice Orchestrator | AMQP (publish) |
| 34 | `bid.placed`, `bid.outbid`, `bid.confirmed`, `auction.extended` | Bidding Orchestrator | AMQP (publish) |
| 35 | `stripe.checkout.completed` | Webhook Router | AMQP (publish) |
| 36 | `auction.closing.warning`, `auction.expired`, `auction.closed.winner`, `auction.closed.loser`, `loan.due`, `loan.overdue`, `loan.repaid`, `wallet.credited` | Temporal Worker | AMQP (publish) |

### RabbitMQ → Consumers (async)

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 37 | All events (`#` wildcard) | RabbitMQ → Notification Service | AMQP (consume) |
| 38 | All events (`#` wildcard) | RabbitMQ → Activity Log Bridge → OutSystems | AMQP (consume) → HTTPS |
| 39 | `stripe.checkout.completed` (type=wallet_topup) | RabbitMQ → Bidding Orchestrator | AMQP (consume) |
| 40 | `stripe.checkout.completed` (type=loan_repayment) | RabbitMQ → Loan Orchestrator | AMQP (consume) |
| 41 | `loan.overdue` (queue: `invoice_loan_updates`) | RabbitMQ → Invoice Service | AMQP (consume) |
| 42 | `loan.overdue` (queue: `payment_loan_updates`) | RabbitMQ → Payment Service | AMQP (consume) |
| 43 | `loan.overdue` (queue: `user_loan_updates`) | RabbitMQ → User Service | AMQP (consume) |
| 44 | `loan.repaid` (queue: `invoice_repaid_updates`) | RabbitMQ → Invoice Service | AMQP (consume) |
| 45 | `loan.repaid` (queue: `payment_repaid_updates`) | RabbitMQ → Payment Service | AMQP (consume) |
| 46 | `loan.repaid` (queue: `user_repaid_updates`) | RabbitMQ → User Service | AMQP (consume) |
| 47 | `bid.outbid` (queue: `payment_outbid_updates`) | RabbitMQ → Payment Service | AMQP (consume) |

Separate queues are required for each fan-out consumer. A single queue with multiple consumers results in round-robin delivery (only one gets each message). Separate queues each bound to the same routing key ensure all target services receive every message independently.

**Fan-out summary:**

| Event | Queues | Consumers |
|-------|--------|-----------|
| `loan.overdue` | 4 queues | Invoice Service, Payment Service, User Service, Notification Service (via wildcard) |
| `loan.repaid` | 4 queues | Invoice Service, Payment Service, User Service, Notification Service (via wildcard) |
| `bid.outbid` | 2 queues | Payment Service, Notification Service (via wildcard) |

### Notification → External

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 48 | Send transactional emails | Notification Service → Resend | HTTPS (external) |
| 49 | Push real-time notifications | Notification Service → React Frontend | WebSocket |

### Atomics → Databases

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 50 | User CRUD | User Service → user_db | MySQL :3306 |
| 51 | Invoice CRUD | Invoice Service → invoice_db | MySQL :3307 |
| 52 | Listing CRUD | Marketplace Service → market_db | MySQL :3308 |
| 53 | Offer CRUD | Bidding Service → bidding_db | MySQL :3309 |
| 54 | Wallet / escrow / loan CRUD | Payment Service → payment_db | MySQL :3310 |
| 55 | Notification CRUD | Notification Service → notification_db | MySQL :3311 |
| 56 | Event / error log writes | Activity Log Bridge → OutSystems → OutSystems internal DB | HTTPS → OutSystems managed |
| 57 | PDF storage | Invoice Service → MinIO | S3 API :9000 |

---

## Beyond-The-Labs (BTL) Features

| # | Feature | Where | Justification |
|---|---------|-------|---------------|
| BTL #1 | gRPC | Payment Service :50051 | Binary Protocol Buffers for all financial write operations — faster than REST/JSON. Idempotency keys on all operations prevent double-charging on Temporal retries. Called by Bidding Orchestrator, Loan Orchestrator, and Temporal Worker directly (gRPC requires HTTP/2, incompatible with KONG HTTP/1.1). |
| BTL #2 | KONG API Gateway | External boundary | JWT validation, rate limiting (100 req/min), CORS, correlation IDs (`X-Correlation-ID`). Handles all external-facing traffic. Internal service-to-service calls bypass KONG entirely. |

---

## Service Reuse Across Scenarios

| Service | Scenario 1 | Scenario 2 | Scenario 3 |
|---------|------------|------------|------------|
| User Service | Account status check at listing | Authentication | account_status → DEFAULTED / ACTIVE (via choreography) |
| Invoice Service | Create, validate, upload PDF | FINANCED status update (Temporal) | REPAID / DEFAULTED status (via choreography) |
| Marketplace Service | Create listing | Browse + deadline extension (anti-snipe) + delist on auction win | Bulk delist on default |
| Bidding Service | — | Bid placement + offer accept/reject | — |
| Payment Service | — | Escrow lock (gRPC), loan create, fund release, escrow release on outbid | Loan status updates (gRPC), investor wallet credit on repayment (via choreography), penalty calc on default |
| Notification Service | Listed / rejection alerts | All bid + auction events + wallet credited | Loan due + repaid + default alerts |
| Webhook Router | — | Receives Stripe webhook for wallet top-up | Receives Stripe webhook for loan repayment |
| Activity Log Bridge | All events logged to OutSystems | All events logged to OutSystems | All events logged to OutSystems |

---

## Architectural Rules

1. **KONG handles external traffic only.** React frontend and Stripe webhooks go through KONG. All internal service-to-service calls use direct HTTP via Docker hostnames (e.g., `http://invoice-service:5001`).
2. **Atomic services never call each other.** All inter-atomic coordination goes through composite services or RabbitMQ choreography.
3. **Notification Service and Activity Log Bridge are RabbitMQ-only consumers.** No composite service connects to them. They react to events asynchronously.
4. **User Service, Invoice Service, and Payment Service also consume specific RabbitMQ events.** They react to `loan.repaid`, `loan.overdue`, and `bid.outbid` via choreography. This does not violate rule #2 — they are reacting to events independently, not calling each other.
5. **Resend lives inside Notification Service.** It's an infrastructure dependency (like MySQL), not a separate wrapper service.
6. **Temporal is pure infrastructure.** The Temporal Server + Worker are not classified as composite services. They provide durable workflow execution as a platform capability.
7. **gRPC bypasses KONG by design.** gRPC requires persistent HTTP/2 connections, which are incompatible with KONG's HTTP/1.1 proxy. This is a documented architectural exception.
8. **Separate RabbitMQ queues for fan-out.** Any event consumed by multiple services requires one queue per consumer, each bound to the same routing key. A single shared queue results in round-robin delivery (only one consumer gets each message).
9. **Each microservice owns its own database exclusively.** No shared databases. Each service's database runs on a unique port to avoid conflicts in Docker Compose.
10. **Stripe Wrapper is outbound-only.** Inbound Stripe webhooks go through KONG → Webhook Router, which verifies signatures and publishes normalised events to RabbitMQ. The Stripe Wrapper is bypassed on the inbound path.
11. **Webhook Router owns Stripe webhook intake.** It is the single entry point for all Stripe events. Downstream orchestrators consume normalised events from RabbitMQ rather than raw Stripe payloads, decoupling them from Stripe's schema.
12. **Repayment and default flows are symmetrical.** Both `loan.repaid` and `loan.overdue` use the same four-consumer choreography pattern — the Temporal Worker publishes to RabbitMQ, and Invoice Service + Payment Service + User Service + Notification Service each react independently.
13. **Notification Service persists to notification_db.** Notifications are stored in MySQL (notification_db, :3311) — not in-memory. The API serves the last 50 per user ordered by `created_at DESC`.
14. **WebSocket connections bypass KONG.** The React frontend connects directly to Notification Service (`ws://notification-service:5005/ws/{user_id}`) for real-time push. KONG's HTTP/1.1 proxy does not natively support WebSocket upgrade. The frontend (`NotificationContext.jsx`) implements exponential backoff reconnect — starting at 1s, doubling on each failure, capped at 30s — so transient disconnects recover automatically without user action.

---

## RabbitMQ Event Catalog

| Event | Published By | Consumed By | Trigger |
|-------|-------------|-------------|---------|
| `invoice.listed` | Invoice Orchestrator | Notification Service, Activity Log Bridge | Invoice successfully listed on marketplace |
| `invoice.rejected` | Invoice Orchestrator | Notification Service, Activity Log Bridge | Debtor UEN validation failed |
| `bid.placed` | Bidding Orchestrator | Marketplace Service, Notification Service, Activity Log Bridge | New bid submitted — Marketplace Service updates `current_bid` and `bid_count` read-model |
| `bid.confirmed` | Bidding Orchestrator | Notification Service, Activity Log Bridge | Bid acknowledged to bidder |
| `bid.outbid` | Bidding Orchestrator | Payment Service, Notification Service, Activity Log Bridge | Previous highest bidder outbid → Payment Service releases previous bidder's escrow |
| `auction.extended` | Bidding Orchestrator | Marketplace Service, Notification Service, Activity Log Bridge | Anti-snipe: bid placed in final 5 min, deadline extended by 5 min — Marketplace Service updates displayed deadline |
| `stripe.checkout.completed` | Webhook Router | Bidding Orchestrator (wallet_topup), Loan Orchestrator (loan_repayment) | Stripe confirms payment; type field routes to correct orchestrator |
| `wallet.credited` | Temporal Worker (WalletTopUpWorkflow) | Notification Service, Activity Log Bridge | Stripe top-up confirmed and wallet credited |
| `auction.closing.warning` | Temporal Worker (AuctionCloseWorkflow) | Notification Service, Activity Log Bridge | T-12h or T-1h before deadline |
| `auction.closed.winner` | Temporal Worker (AuctionCloseWorkflow) | Notification Service, Activity Log Bridge | Auction ended, winner selected |
| `auction.closed.loser` | Temporal Worker (AuctionCloseWorkflow) | Notification Service, Activity Log Bridge | Auction ended, each losing bidder notified |
| `auction.expired` | Temporal Worker (AuctionCloseWorkflow) | Notification Service, Activity Log Bridge | Auction ended with zero bids |
| `loan.due` | Temporal Worker (LoanMaturityWorkflow) | Notification Service, Activity Log Bridge | Loan due date arrived |
| `loan.overdue` | Temporal Worker (LoanMaturityWorkflow) | Invoice Service, Payment Service, User Service, Notification Service, Activity Log Bridge | Repayment window expired unpaid |
| `loan.repaid` | Temporal Worker (LoanRepaymentWorkflow) | Invoice Service, Payment Service, User Service, Notification Service, Activity Log Bridge | Business repaid via Stripe; LoanRepaymentWorkflow confirmed and published |

---

## Choreography-Driven Flows

### loan.overdue (4 consumers)

Published by Temporal Worker (LoanMaturityWorkflow) when repayment window expires unpaid. Four separate queues, each bound to routing key `loan.overdue`:

| Queue | Consumer | Action |
|-------|----------|--------|
| `invoice_loan_updates` | Invoice Service | Marks invoice status → DEFAULTED |
| `payment_loan_updates` | Payment Service | Calculates 5% penalty |
| `user_loan_updates` | User Service | Sets business `account_status` → DEFAULTED |
| `notification_loan_updates` | Notification Service | Emails both business and investor; WebSocket push |

### loan.repaid (4 consumers)

Published by Temporal Worker (LoanRepaymentWorkflow) after loan marked REPAID. Four separate queues, each bound to routing key `loan.repaid`:

| Queue | Consumer | Action |
|-------|----------|--------|
| `invoice_repaid_updates` | Invoice Service | Marks invoice status → REPAID |
| `payment_repaid_updates` | Payment Service | Credits investor wallet |
| `user_repaid_updates` | User Service | Resets business `account_status` → ACTIVE |
| `notification_repaid_updates` | Notification Service | Emails both business and investor; WebSocket push |

This makes the repayment and default flows symmetrical — both fully choreography-driven, removing direct coupling from the Temporal Worker to atomics for post-event status updates.

### bid.outbid (2 consumers)

Published by Bidding Orchestrator when a new highest bid is placed. Two separate queues:

| Queue | Consumer | Action |
|-------|----------|--------|
| `payment_outbid_updates` | Payment Service | Releases previous bidder's escrow back to their wallet immediately |
| `notification_outbid_updates` | Notification Service | Notifies the outbid investor by email + WebSocket push |

Escrow is released immediately on outbid rather than waiting for auction close, minimising capital locked for losing investors throughout the auction period.

---

## Detailed Scenario Flows (Service-to-Service)

These flows show every service interaction in order for each scenario. Steps labelled Xa/Xb/Xc occur **concurrently**.

---

### Scenario 1: Business Lists Invoice for Auction

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

### Scenario 2: Investor Bids on Invoice (with Anti-Snipe) and Wins Auction

#### Phase A: Wallet Top-Up via Stripe

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

#### Phase B: Placing a Bid (with Anti-Snipe Extension)

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

#### Phase C: Auction Closes (Timer Expires)

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
| C14a | RabbitMQ | Notification Service | Consume → email winner + each loser + seller; WebSocket push | AMQP | Concurrent with C14b |
| C14b | RabbitMQ | Activity Log Bridge | Consume → relay to OutSystems | AMQP → HTTPS | Concurrent with C14a |

---

### Scenario 3: Loan Maturity and Business Default

#### Phase A: Loan Comes Due

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

#### Phase B: Business Defaults (repayment window expires)

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



## Databases

| Service | Database | Engine | Docker Port |
|---------|----------|--------|-------------|
| User Service | `user_db` | MySQL | :3306 |
| Invoice Service | `invoice_db` | MySQL | :3307 |
| Marketplace Service | `market_db` | MySQL | :3308 |
| Bidding Service | `bidding_db` | MySQL | :3309 |
| Payment Service | `payment_db` | MySQL | :3310 |
| Notification Service | `notification_db` | MySQL | :3311 |
| OutSystems (Activity Log) | OutSystems internal | OutSystems managed | — |

Schema migrations are managed with **Alembic** for all Python/SQLAlchemy services. Fresh deployments can also use the `databases/*/init.sql` scripts directly. Payment Service uses Sequelize (Node.js ORM).

---

## Technology Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | React 18 + Vite + TailwindCSS (dev :3000) |
| API Gateway | KONG :8000 — DB-less declarative mode (`gateway/kong.yml`) |
| Composite Services | Python / FastAPI (:5010, :5011, :5012) |
| Atomic Services | Python / FastAPI (:5000, :5001, :5002, :5003, :5005); Node.js / Express (:5004) |
| Wrapper Services | Python / FastAPI (:5007 ACRA, :5008 Stripe) |
| Bridge Service | Python + pika (RabbitMQ client) — no HTTP server |
| Databases | MySQL (one per service, :3306–:3311) |
| File Storage | MinIO :9000 (S3-compatible) |
| Message Broker | RabbitMQ :5672 (AMQP, topic exchange `invoiceflow_events`); dead-letter queues via `x-dead-letter-exchange` |
| Workflow Engine | Temporal Server :7233 + Worker (Python SDK) + UI :8088 |
| Payments | Stripe (external) via Stripe Wrapper (outbound) and Webhook Router → RabbitMQ (inbound) |
| UEN Validation | User Service → data.gov.sg (seller at registration), ACRA Wrapper → data.gov.sg (debtor per invoice) |
| Email | Resend (inside Notification Service) |
| Tracing | OpenTelemetry (OTLP HTTP) → Tempo :3200 |
| Metrics | Prometheus :9090 → Grafana :3001 |
| Logging | structlog → Promtail → Loki :3100 |
| External Audit Log | Activity Log Bridge → OutSystems Platform |
| CI/CD | GitHub Actions — see below |

---

## CI/CD Pipeline

### Overview

The pipeline is defined in `.github/workflows/ci.yml` and runs on every push to any branch, and on pull requests targeting `main`. Deployment only triggers on pushes to `main` after all checks pass.

### CI — Continuous Integration (all branches)

| Job | What it does |
|-----|-------------|
| `lint` | Runs `ruff check` across all Python code (excludes generated proto files) |
| `test-temporal-worker` | Installs deps, runs pytest in `temporal-worker/` |
| `test-bidding-service` | Installs deps, runs pytest in `services/bidding-service/` |
| `test-invoice-service` | Installs deps, runs pytest in `services/invoice-service/` |
| `test-marketplace-service` | Installs deps, runs pytest in `services/marketplace-service/` |
| `test-notification-service` | Installs deps, runs pytest in `services/notification-service/` |
| `test-user-service` | Installs deps, runs pytest in `services/user-service/` |
| `test-frontend` | Installs npm deps, runs `npm test` in `frontend/` |

All jobs run in parallel on `ubuntu-latest`.

### CD — Continuous Deployment (`main` branch only)

| Job | Trigger | What it does |
|-----|---------|-------------|
| `deploy` | Push to `main`, only after all CI jobs pass | SSHs into the EC2 instance, runs `git pull origin main` and `docker compose up --build -d` |

**Frontend** is deployed separately via Vercel, which auto-deploys on every push to `main`.

### Secrets required (stored in GitHub repository secrets)

| Secret | Purpose |
|--------|---------|
| `EC2_HOST` | Public IP or hostname of the EC2 instance |
| `EC2_USER` | SSH username (e.g. `ubuntu`) |
| `EC2_SSH_KEY` | Private key used to SSH into the EC2 instance |

### Deployment flow

```
Push to main
    │
    ├─ All CI jobs run in parallel (lint + 7 test jobs)
    │
    └─ All pass → deploy job SSHs into EC2
                      │
                      ├─ git pull origin main
                      └─ docker compose up --build -d
                              (rebuilds changed images, restarts affected containers)

Push to other branches / PRs → CI only, no deploy
```

---

## Demo Mode

Demo mode shortens all Temporal workflow timers so all three user scenarios can be demonstrated end-to-end in under 1.5 minutes each. It is controlled entirely via environment variables — no code changes required.

### Activation

Set the following in your `.env` file (and `.env` on the EC2 instance for production demo):

```bash
DEMO_MODE=true
DEMO_AUCTION_SECONDS=90        # AuctionCloseWorkflow: skips T-12h/T-1h warnings, runs single 90s countdown
DEMO_LOAN_MATURITY_SECONDS=90  # LoanMaturityWorkflow: fires after 90s instead of loan due_date
DEMO_REPAYMENT_WINDOW_SECONDS=60  # LoanMaturityWorkflow: repayment window is 60s instead of 86400s
ANTI_SNIPE_SECONDS=15          # AuctionCloseWorkflow: anti-snipe loop window is 15s
ANTI_SNIPE_WINDOW_SECONDS=15   # Bidding Orchestrator: triggers signal if bid placed within 15s of deadline
```

### Timing overview

| Scenario | Production timing | Demo timing |
|----------|------------------|-------------|
| Scenario 1: invoice listing to auction start | Immediate | Immediate |
| Scenario 2: auction countdown | `bid_period_hours` (hours/days) | 90s (`DEMO_AUCTION_SECONDS`) |
| Scenario 2: anti-snipe window | 300s (5 min) | 15s (`ANTI_SNIPE_SECONDS` / `ANTI_SNIPE_WINDOW_SECONDS`) |
| Scenario 3: loan maturity (time until loan due) | Days/weeks | 90s (`DEMO_LOAN_MATURITY_SECONDS`) |
| Scenario 3: repayment window | 86400s (24h) | 60s (`DEMO_REPAYMENT_WINDOW_SECONDS`) |

### Services affected

| Service | What changes |
|---------|-------------|
| Temporal Worker (`temporal-worker/`) | `AuctionCloseWorkflow` skips T-12h/T-1h warnings; uses `DEMO_AUCTION_SECONDS` for countdown. `LoanMaturityWorkflow` fires after `DEMO_LOAN_MATURITY_SECONDS`; uses `DEMO_REPAYMENT_WINDOW_SECONDS` for repayment window |
| Invoice Orchestrator (`orchestrators/invoice-orchestrator/`) | `calculate_deadline()` uses `DEMO_AUCTION_SECONDS` when `DEMO_MODE=true` so the marketplace listing deadline matches the Temporal timer |
| Bidding Orchestrator (`orchestrators/bidding-orchestrator/`) | Anti-snipe check uses `ANTI_SNIPE_WINDOW_SECONDS` env var (both in demo and production — defaults to 300s) |

### Notes

- In demo mode, `AuctionCloseWorkflow` does **not** publish T-12h or T-1h closing warnings — the auction is too short for these to be meaningful.
- The `invoice-orchestrator` deadline calculation must match `DEMO_AUCTION_SECONDS` so the anti-snipe comparison (current time vs. displayed deadline) stays in sync.
- `ANTI_SNIPE_SECONDS` and `ANTI_SNIPE_WINDOW_SECONDS` are separate env vars because they govern different services (Temporal Worker and Bidding Orchestrator respectively). Set both to the same value in demo mode.
