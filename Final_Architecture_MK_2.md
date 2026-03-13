# InvoiceFlow — Architecture v4.3

**SMU IS213 · Enterprise Solution Development · AY2025/26**

InvoiceFlow is an invoice factoring marketplace where businesses list invoices for auction and investors bid to finance them. The platform handles the full lifecycle: invoice listing, competitive bidding, fund disbursement, loan tracking, and debt resolution.

---

## Three User Scenarios

### Scenario 1: Business Lists Invoice for Auction

A business uploads an invoice PDF, the system extracts key fields (pdfplumber), validates the debtor's UEN against Singapore's ACRA registry (via ACRA Wrapper → data.gov.sg), lists it on the marketplace with an urgency level, and starts a countdown timer for the auction.

**Services involved:** Invoice Orchestrator (composite), User Service, Invoice Service, Marketplace Service, ACRA Wrapper (wrapper), data.gov.sg (external), MinIO, Temporal Server, RabbitMQ, Notification Service (includes Resend), OutSystems (Activity Log)

**Temporal Workflow triggered:** AuctionCloseWorkflow — started by Invoice Orchestrator after the invoice is successfully listed. Sets durable timers for T-12h warning, T-1h warning, and the bid deadline.

**Communication patterns:** Synchronous orchestration (Invoice Orchestrator → atomics via direct HTTP), async event publishing to RabbitMQ for notifications and logging.

---

### Scenario 2: Investor Bids on Invoice (with Anti-Snipe Protection) and Wins Auction

An investor tops up their wallet via Stripe, browses the marketplace (GraphQL), and places a bid (escrow locked immediately via gRPC). If this bid outbids a previous highest bidder, the previous bidder's escrow is released immediately back to their wallet via choreography. The system implements anti-snipe protection: if a bid is placed within the final 5 minutes of the auction, the deadline automatically extends by 5 minutes from the time of that bid, giving other investors a fair window to respond. This prevents last-second "sniping" where a bidder waits until the final moments to place an uncontestable bid. The extension can trigger repeatedly — every bid in the final 5 minutes resets the 5-minute window. When no new bids arrive within the final window and the (possibly extended) timer expires, only the winning bidder has escrow locked. Temporal then executes the financial workflow: convert escrow, create loan, release funds to seller, update statuses, delist, and notify all parties.

**Anti-snipe mechanism:** When Bidding Orchestrator processes a new bid, it checks if the auction is within its final 5 minutes. If so, it sends a Temporal Signal (`extend_deadline`) to the running AuctionCloseWorkflow. The workflow receives the signal, cancels its current timer, and restarts a new 5-minute timer. The Marketplace Service also updates the listing's displayed deadline so the frontend reflects the extension in real time. This is implemented using Temporal's signal feature — the workflow listens for `extend_deadline` signals in a loop alongside its countdown timer.

**Services involved:** Bidding Orchestrator (composite), Bidding Service, Payment Service (gRPC), Marketplace Service (GraphQL), Invoice Service, Stripe Wrapper (wrapper), Stripe (external), Temporal Server + Worker, RabbitMQ, Notification Service (includes Resend), OutSystems (Activity Log)

**Temporal Workflows triggered:**
- **WalletTopUpWorkflow** — started by Bidding Orchestrator when Stripe webhook confirms payment. Credits investor wallet.
- **AuctionCloseWorkflow** — already running from Scenario 1. Listens for `extend_deadline` signals from Bidding Orchestrator. When the (possibly extended) timer fires with no further signals, the Temporal Worker executes the 10-step orchestration. After `create_loan`, it starts LoanMaturityWorkflow as a child workflow.

**Communication patterns:** gRPC for escrow locking (idempotent, binary, fast), GraphQL for marketplace queries (BTL #3), Temporal SDK for durable workflows and signals, AMQP for event fan-out.

---

### Scenario 3: Loan Maturity and Business Default

The LoanMaturityWorkflow (already running as a child of AuctionCloseWorkflow) fires when the loan's due date arrives. It marks the loan DUE, notifies the business, and starts a 24-hour repayment window. If the business repays via Stripe in time, Loan Orchestrator publishes `loan.repaid` to RabbitMQ and four consumers react via choreography: Invoice Service marks the invoice REPAID, Payment Service credits the investor's wallet, User Service resets the business account to ACTIVE, and Notification Service alerts both parties. If the business does not repay, Temporal marks the loan OVERDUE and publishes `loan.overdue` to RabbitMQ. Four independent consumers react via choreography: Invoice Service marks the invoice DEFAULTED, Payment Service calculates a 5% penalty, User Service sets the business account to DEFAULTED, and Notification Service alerts both parties. Temporal then bulk-delists all the defaulting seller's active listings.

**Services involved:** Loan Orchestrator (composite), Payment Service, Invoice Service, User Service, Marketplace Service, Stripe Wrapper (wrapper), Stripe (external), Temporal Worker, RabbitMQ, Notification Service (includes Resend), OutSystems (Activity Log)

**Temporal Workflow involved:** LoanMaturityWorkflow — started as a child workflow inside AuctionCloseWorkflow after `create_loan`. NOT started by any composite service directly.

**Communication patterns:** Temporal durable timer (24h countdown), four-consumer fan-out choreography on both `loan.repaid` and `loan.overdue` (4 separate RabbitMQ queues each), synchronous HTTP for repayment initiation through Loan Orchestrator.

---

## Three Temporal Workflows

### 1. AuctionCloseWorkflow

**Started by:** Invoice Orchestrator → Temporal Server (Temporal SDK)
**Triggered when:** Invoice is successfully listed on the marketplace
**Workflow ID:** `auction-{invoice_token}`
**Task queue:** `invoiceflow-queue`

**What it does:**
1. Waits for `bid_period_hours` using Temporal's durable timer (survives crashes)
2. Sends T-12h auction closing warning (publishes to RabbitMQ)
3. Sends T-1h auction closing warning (publishes to RabbitMQ)
4. **Anti-snipe loop:** In the final 5 minutes, the workflow listens for `extend_deadline` signals. Each signal cancels the current timer and restarts a 5-minute countdown. The loop exits only when the timer expires with no new signal received.
5. Timer expires — fetches all offers from Bidding Service (direct HTTP)
6. If zero bids → expires the listing and ends
7. If bids exist → picks highest bidder as winner, runs the 10-step financial workflow:

| Step | Activity | Target Service | Technology |
|------|----------|----------------|------------|
| 1 | verify_invoice_available | Invoice Service | Direct HTTP |
| 2 | convert_escrow_to_loan | Payment Service | gRPC :50051 |
| 3 | create_loan | Payment Service | gRPC :50051 |
| 4 | **Start LoanMaturityWorkflow** | Temporal Server | Child workflow — fire-and-forget (SDK `start_child_workflow`) |
| 5 | release_funds_to_seller | Payment Service | gRPC :50051 |
| 6 | update_invoice_status → FINANCED | Invoice Service | Direct HTTP |
| 7 | delist_from_marketplace | Marketplace Service | Direct HTTP |
| 8 | accept_offer (winner) | Bidding Service | Direct HTTP |
| 9 | reject_offer (all losers — parallel) | Bidding Service | Direct HTTP |
| 10 | publish_auction_outcome_events | RabbitMQ | AMQP publish |

**Note on escrow:** By auction close, only the winning bidder has funds in escrow. All previous bidders' escrow was already released immediately when they were outbid (via `bid.outbid` → Payment Service choreography). There is no refund step at auction close.

**Anti-snipe implementation detail:** The workflow uses `workflow.wait_condition()` with a 5-minute timeout inside a loop. When Bidding Orchestrator detects a bid in the final 5 minutes, it calls `workflow_handle.signal('extend_deadline')` via the Temporal SDK. The workflow receives the signal, sets a flag, and re-enters the loop with a fresh 5-minute timer. If the timeout expires with no signal, the loop exits and the auction closes. Important: the loop must check if a signal was already received before waiting (in case a signal arrived during the preceding `sleep_until`), then reset the flag only after confirming the check. This ensures the timer is durable (survives crashes) and the extension logic is deterministic.

**Scaling note:** Each active auction listing runs its own independent workflow instance. The practical scaling boundary is the Temporal Worker — if many auctions close simultaneously, additional Worker instances can be deployed. They poll the same `invoiceflow-queue` and Temporal distributes tasks automatically.

**Ends when:** All steps complete (or all retries exhausted → failure recorded for manual intervention).

---

### 2. LoanMaturityWorkflow

**Started by:** Temporal Worker as a child workflow inside AuctionCloseWorkflow, after `create_loan` succeeds
**NOT started by any composite service**
**Workflow ID:** `loan-{loan_id}`

**What it does:**
1. Durable timer waits until `due_date` (could be days or weeks)
2. Marks loan as DUE via Payment Service (direct HTTP)
3. Publishes `loan.due` to RabbitMQ → Notification Service emails the business
4. Starts repayment window timer (120s demo / 86400s production)
5. Timer expires → checks if loan was repaid via Payment Service (direct HTTP)
6. If repaid → workflow ends cleanly
7. If not repaid → marks loan OVERDUE, publishes `loan.overdue` to RabbitMQ
8. Four consumers react independently (choreography — see below)
9. Bulk-delists all defaulting seller's listings via Marketplace Service (direct HTTP)

**Ends when:** Repayment window check completes (either repaid or overdue + delist done).

---

### 3. WalletTopUpWorkflow

**Started by:** Bidding Orchestrator → Temporal Server (Temporal SDK), triggered when Stripe webhook confirms a successful checkout session for a wallet top-up
**Workflow ID:** `wallet-topup-{stripe_session_id}` (idempotent — same session ID prevents duplicate processing)

**What it does:**
1. Credits investor wallet via Payment Service (direct HTTP)
2. Publishes `wallet.credited` to RabbitMQ → Notification Service sends confirmation email + WebSocket push

**Ends when:** Wallet credited and event published.

---

## Service Inventory

### Composite Services (3)

| Service | Port | Technology | Scenario |
|---------|------|------------|----------|
| Invoice Orchestrator | :5010 | Python / FastAPI | Scenario 1 — invoice creation, UEN validation, listing |
| Bidding Orchestrator | :5011 | Python / FastAPI | Scenario 2 — bid placement, escrow locking, wallet top-up, Stripe webhook handling |
| Loan Orchestrator | :5012 | Python / FastAPI | Scenario 3 — repayment initiation, debt resolution |

Composite services orchestrate atomic services via direct HTTP (inside Docker network). They never call each other. They publish events to RabbitMQ but do NOT connect to Notification Service or OutSystems (Activity Log) directly.

### Atomic Services (6)

| Service | Port | Technology | Database | Notes |
|---------|------|------------|----------|-------|
| User Service | :5000 | Python / FastAPI | user_db (MySQL :3306) | Registration, login, JWT, account status. Calls data.gov.sg directly for seller UEN validation at registration. Also a RabbitMQ consumer for `loan.repaid` and `loan.overdue` (account status updates via choreography) |
| Invoice Service | :5001 | Python / FastAPI | invoice_db (MySQL :3307) | Invoice CRUD, PDF upload, pdfplumber, status tracking. Also a RabbitMQ consumer for `loan.repaid` and `loan.overdue` |
| Marketplace Service | :5002 | Python / FastAPI + GraphQL | market_db (MySQL :3308) | Listings, urgency levels, search. **BTL #3** |
| Bidding Service | :5003 | Python / FastAPI | bidding_db (MySQL :3309) | Bid management, offer CRUD |
| Payment Service | :5004 / :50051 | Node.js / Express + gRPC | payment_db (MySQL :3310) | Wallets, escrow, loans. Also a RabbitMQ consumer for `bid.outbid` (escrow release), `loan.repaid` (credit investor wallet), and `loan.overdue` (calculate penalty). **BTL #2** |
| Notification Service | :5005 | Python / FastAPI | No database | RabbitMQ consumer, WebSocket push, Resend email (built-in). **NO DB** |

Atomic services never call each other directly. All inter-atomic coordination goes through composite services or RabbitMQ choreography. Notification Service is a pure RabbitMQ consumer — no composite service connects to it. User Service, Invoice Service, and Payment Service also consume specific events via RabbitMQ for choreography-driven flows (`loan.repaid`, `loan.overdue`, `bid.outbid`). This keeps account status updates (User Service), invoice status updates (Invoice Service), and financial operations (Payment Service) each within their domain owner.

### Wrapper Services (2)

| Service | Technology | Wraps | Called By |
|---------|------------|-------|----------|
| ACRA Wrapper | Python / FastAPI | data.gov.sg ACRA UEN registry | Invoice Orchestrator (debtor UEN validation) |
| Stripe Wrapper | Python / FastAPI | Stripe API (checkout sessions) | Bidding Orchestrator (outbound only), Loan Orchestrator (outbound only) |

Note: Stripe Wrapper handles **outbound** calls only (creating checkout sessions). **Inbound** Stripe webhooks go through KONG → Bidding Orchestrator directly — the Stripe Wrapper is bypassed on the webhook path.

### OutSystems Service (Activity Log)

| Service | Technology | Database | Notes |
|---------|------------|----------|-------|
| Activity Log (OutSystems) | OutSystems Platform | OutSystems internal DB | RabbitMQ consumer, event audit trail, error logging. Replaces the previous Python-based Activity Log Service. Built entirely in OutSystems as a low-code application. |

OutSystems Activity Log is a pure RabbitMQ consumer — no composite service connects to it directly. It subscribes to all events via the `#` wildcard routing key and maintains a full audit trail. Because OutSystems manages its own database internally, there is no separate MySQL instance for this service.

### External Services

| Service | Purpose | Called By |
|---------|---------|----------|
| data.gov.sg | ACRA UEN registry (seller + debtor validation) | User Service (seller UEN at registration), ACRA Wrapper (debtor UEN per invoice) |
| Stripe | Payment processing, hosted checkout, webhooks | Stripe Wrapper (outbound), Stripe → KONG → Bidding Orchestrator (inbound webhook) |
| Resend | Transactional email delivery | Notification Service (built-in, no wrapper) |

### Infrastructure

| Component | Port | Purpose |
|-----------|------|---------|
| KONG API Gateway | :8000 | JWT auth, rate limiting, CORS, routing. **External traffic only.** **BTL #1** |
| RabbitMQ | :5672 / :15672 | Topic exchange (`invoiceflow_events`). Async event delivery |
| Temporal Server | :7233 | Durable workflow state, timers, task queues |
| Temporal Worker | — | Polls Temporal Server, executes workflow activities. Calls atomic services directly |
| Temporal UI | :8088 | Workflow viewer / debugger (dev tool) |
| MinIO | :9000 | Self-hosted S3-compatible file storage for invoice PDFs |

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
| 4 | Scenario 1 routes | KONG → Invoice Orchestrator | REST/JSON |
| 5 | Scenario 2 routes | KONG → Bidding Orchestrator | REST/JSON |
| 6 | Scenario 3 routes | KONG → Loan Orchestrator | REST/JSON |
| 7 | Notification read endpoints | KONG → Notification Service | REST (direct, bypasses composites) |
| 8 | Stripe webhook (inbound) | KONG → Bidding Orchestrator | REST/JSON (Stripe-Signature verified) |

### Stripe Two-Direction Paths

Stripe communication runs in two directions — these are separate arrows in the architecture diagram:

| Direction | Path | Purpose |
|-----------|------|---------|
| Outbound (your system calls Stripe) | Orchestrator → Stripe Wrapper → Stripe | Create checkout sessions for wallet top-up or loan repayment |
| Inbound (Stripe calls your system) | Stripe → KONG → Bidding Orchestrator → Temporal | Webhook confirms payment, triggers WalletTopUpWorkflow |

Stripe webhook safeguards: Every webhook includes a `Stripe-Signature` header. Bidding Orchestrator recomputes the signature using the shared secret + payload body — mismatches are rejected. Webhooks older than 5 minutes are rejected to prevent replay attacks. The workflow ID `wallet-topup-{stripe_session_id}` ensures Temporal refuses duplicate workflows if Stripe fires the same webhook twice.

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
| 14 | ACRA UEN lookup (seller at registration) | User Service → data.gov.sg | HTTPS (external, direct) |

User Service calls data.gov.sg directly for seller UEN validation at registration — the ACRA Wrapper is not involved here. The ACRA Wrapper is used exclusively by Invoice Orchestrator for debtor UEN validation per invoice.

### Composites → Atomics (direct HTTP inside Docker network)

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 15 | Account status check | Invoice Orchestrator → User Service | HTTP (direct) |
| 16 | Invoice create / upload / status | Invoice Orchestrator → Invoice Service | HTTP (direct) |
| 17 | List on marketplace | Invoice Orchestrator → Marketplace Service | HTTP (direct) |
| 18 | Bid placement / management | Bidding Orchestrator → Bidding Service | HTTP (direct) |
| 19 | Escrow lock / wallet ops | Bidding Orchestrator → Payment Service | gRPC :50051 |
| 20 | Repayment initiation (Stripe checkout) | Loan Orchestrator → Payment Service | gRPC :50051 |

Note: Both Bidding Orchestrator and Loan Orchestrator use gRPC for Payment Service calls — all financial operations use the same protocol for consistency and idempotency key support. Account status updates (ACTIVE/DEFAULTED) are handled via RabbitMQ choreography by User Service — Loan Orchestrator does not call User Service directly.

### Composites → Temporal (start workflows)

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 22 | Start AuctionCloseWorkflow | Invoice Orchestrator → Temporal Server | Temporal SDK |
| 23 | Start WalletTopUpWorkflow | Bidding Orchestrator → Temporal Server | Temporal SDK |

Invoice Orchestrator starts AuctionCloseWorkflow after an invoice is successfully listed. Bidding Orchestrator starts WalletTopUpWorkflow after a Stripe webhook confirms wallet top-up payment. Bidding Orchestrator also signals running AuctionCloseWorkflow instances for anti-snipe deadline extensions. Loan Orchestrator does NOT start any workflow — LoanMaturityWorkflow is started internally by the Temporal Worker as a child of AuctionCloseWorkflow.

### Composites → Temporal (signal workflows)

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 23a | Signal `extend_deadline` on AuctionCloseWorkflow | Bidding Orchestrator → Temporal Server | Temporal SDK (signal) |

When a bid arrives within the final 5 minutes of an auction, Bidding Orchestrator uses the Temporal SDK to send a signal to the running AuctionCloseWorkflow for that invoice. This extends the auction deadline by 5 minutes.

### Temporal Internal

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 24 | Poll for tasks | Temporal Worker → Temporal Server | Temporal SDK (long-poll) |
| 25 | View workflows | Temporal UI → Temporal Server | HTTP |
| 26 | Start LoanMaturityWorkflow (child) | Temporal Worker → Temporal Server | Temporal SDK (internal) |

### Temporal Worker → Atomics (during workflow execution)

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 27 | Verify / update invoice status | Temporal Worker → Invoice Service | HTTP (direct) |
| 28 | Delist listing / bulk delist by seller | Temporal Worker → Marketplace Service | HTTP (direct) |
| 29 | Get offers / accept / reject offers | Temporal Worker → Bidding Service | HTTP (direct) |
| 30 | Create loan, convert escrow, release funds, update/check loan status | Temporal Worker → Payment Service | gRPC :50051 |

### Publishing to RabbitMQ (async)

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 31 | Events: invoice.listed, invoice.rejected, etc. | Invoice Orchestrator → RabbitMQ | AMQP (publish) |
| 32 | Events: bid.placed, bid.outbid, etc. | Bidding Orchestrator → RabbitMQ | AMQP (publish) |
| 33 | Events: loan.repaid, etc. | Loan Orchestrator → RabbitMQ | AMQP (publish) |
| 34 | Events: auction.closed.winner/loser, loan.due, loan.overdue, wallet.credited | Temporal Worker → RabbitMQ | AMQP (publish) |

### RabbitMQ → Consumers (async)

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 35 | All events (notifications + email + WebSocket) | RabbitMQ → Notification Service | AMQP (consume) |
| 36 | All events (# wildcard — full audit trail) | RabbitMQ → OutSystems (Activity Log) | AMQP (consume) |
| 37 | loan.overdue (fan-out queue: invoice_loan_updates) | RabbitMQ → Invoice Service | AMQP (consume) |
| 38 | loan.overdue (fan-out queue: payment_loan_updates) | RabbitMQ → Payment Service | AMQP (consume) |
| 38a | loan.overdue (fan-out queue: user_loan_updates) | RabbitMQ → User Service | AMQP (consume) |
| 39 | loan.repaid (fan-out queue: invoice_repaid_updates) | RabbitMQ → Invoice Service | AMQP (consume) |
| 40 | loan.repaid (fan-out queue: payment_repaid_updates) | RabbitMQ → Payment Service | AMQP (consume) |
| 40a | loan.repaid (fan-out queue: user_repaid_updates) | RabbitMQ → User Service | AMQP (consume) |
| 41 | bid.outbid (fan-out queue: payment_outbid_updates) | RabbitMQ → Payment Service | AMQP (consume) |

Separate queues are required for each fan-out consumer. A single queue with multiple consumers would result in round-robin delivery (only one gets each message). Separate queues each bound to the same routing key ensures all target services receive every message independently.

**Fan-out summary:**

| Event | Queues | Consumers |
|-------|--------|-----------|
| loan.overdue | 4 queues | Invoice Service, Payment Service, User Service, Notification Service (via wildcard) |
| loan.repaid | 4 queues | Invoice Service, Payment Service, User Service, Notification Service (via wildcard) |
| bid.outbid | 2 queues | Payment Service, Notification Service (via wildcard) |

### Notification → External

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 42 | Send transactional emails | Notification Service → Resend | HTTPS (external) |
| 43 | Push real-time notifications | Notification Service → React Frontend | WebSocket |

### Atomics → Databases

| # | Call | From → To | Technology |
|---|------|-----------|------------|
| 44 | User CRUD | User Service → user_db | MySQL :3306 |
| 45 | Invoice CRUD | Invoice Service → invoice_db | MySQL :3307 |
| 46 | Listing CRUD | Marketplace Service → market_db | MySQL :3308 |
| 47 | Offer CRUD | Bidding Service → bidding_db | MySQL :3309 |
| 48 | Wallet / escrow / loan CRUD | Payment Service → payment_db | MySQL :3310 |
| 49 | Event / error log writes | OutSystems (Activity Log) → OutSystems internal DB | OutSystems managed |
| 50 | PDF storage | Invoice Service → MinIO | S3 API :9000 |

---

## Beyond-The-Labs (BTL) Features

| # | Feature | Where | Justification |
|---|---------|-------|---------------|
| BTL #1 | KONG API Gateway | External boundary | JWT validation, rate limiting, CORS, correlation IDs. Handles all external-facing traffic. Internal service-to-service calls bypass KONG entirely. |
| BTL #2 | gRPC | Payment Service :50051 | Binary Protocol Buffers for all financial operations — faster than REST/JSON (~10-15ms vs ~50-70ms). Idempotency keys on all operations prevent double-charging on Temporal retries. Called by Bidding Orchestrator, Loan Orchestrator, and Temporal Worker directly (gRPC requires HTTP/2, incompatible with KONG HTTP/1.1). |
| BTL #3 | GraphQL + DataLoader | Marketplace Service :5002 | Investors query listings with flexible field selection and filtering. DataLoader batches N+1 database queries. Replaces multiple REST endpoints with a single GraphQL endpoint. |

---

## Service Reuse Across Scenarios

| Service | Scenario 1 | Scenario 2 | Scenario 3 |
|---------|------------|------------|------------|
| User Service | Account status check | Authentication | account_status → DEFAULTED / ACTIVE (via choreography) |
| Invoice Service | Create, validate, list | FINANCED status update | REPAID / DEFAULTED status (via choreography) |
| Marketplace Service | Create listing | Browse (GraphQL) + deadline extension (anti-snipe) + delist on auction win | Bulk delist on default |
| Bidding Service | — | Bid placement + offer accept/reject | — |
| Payment Service | — | Escrow lock (gRPC), loans, Stripe top-up, fund release, escrow release on outbid | Penalty calc, investor wallet credit on repayment (via choreography) |
| Notification Service | Listed / rejection alerts | All bid + auction events | Loan due + repaid + default alerts |
| OutSystems (Activity Log) | All events logged | All events logged | All events logged |

---

## Architectural Rules

1. **KONG handles external traffic only.** React frontend and Stripe webhooks go through KONG. All internal service-to-service calls use direct HTTP via Docker hostnames (e.g., `http://invoice-service:5001`).
2. **Atomic services never call each other.** All inter-atomic coordination goes through composite services or RabbitMQ choreography.
3. **Notification Service and OutSystems (Activity Log) are RabbitMQ-only consumers.** No composite service connects to them. They react to events asynchronously.
4. **User Service, Invoice Service, and Payment Service also consume specific RabbitMQ events.** They react to `loan.repaid`, `loan.overdue`, and `bid.outbid` via choreography. This does not violate rule #2 — they are reacting to events independently, not calling each other. User Service owns account_status changes, Invoice Service owns invoice status changes, and Payment Service owns wallet/escrow/penalty operations.
5. **Resend lives inside Notification Service.** It's an infrastructure dependency (like MySQL), not a separate wrapper service.
6. **Temporal is pure infrastructure.** The Temporal Server + Worker are not classified as composite services. They provide durable workflow execution as a platform capability.
7. **gRPC bypasses KONG by design.** gRPC requires persistent HTTP/2 connections, which are incompatible with KONG's HTTP/1.1 proxy. This is a documented architectural exception.
8. **Separate RabbitMQ queues for fan-out.** Any event consumed by multiple services requires one queue per consumer, each bound to the same routing key. A single shared queue would result in round-robin (only one consumer gets each message).
9. **Each microservice owns its own database exclusively.** No shared databases. Each service's database runs on a unique port to avoid conflicts in Docker Compose.
10. **Stripe Wrapper is outbound-only.** Inbound Stripe webhooks go through KONG → Bidding Orchestrator for wallet top-ups. Loan repayment confirmation uses a redirect-based flow (Stripe success URL → frontend → Loan Orchestrator `confirm-repayment` endpoint).
11. **Repayment and default flows are symmetrical.** Both `loan.repaid` and `loan.overdue` use the same four-consumer choreography pattern — Loan Orchestrator/Temporal Worker publishes to RabbitMQ, and Invoice Service + Payment Service + User Service + Notification Service each react independently.
12. **WebSocket connections bypass KONG.** The React frontend connects directly to Notification Service (`ws://notification-service:5005/ws/{user_id}`) for real-time push notifications. KONG's HTTP/1.1 proxy does not natively support WebSocket upgrade — if WebSocket must go through KONG, configure the `websocket` protocol on the route.

---

## RabbitMQ Event Catalog

| Event | Published By | Consumed By | Trigger |
|-------|-------------|-------------|---------|
| invoice.listed | Invoice Orchestrator | Notification, OutSystems (Activity Log) | Invoice successfully listed on marketplace |
| invoice.rejected | Invoice Orchestrator | Notification, OutSystems (Activity Log) | Debtor UEN validation failed |
| bid.placed | Bidding Orchestrator | Notification, OutSystems (Activity Log) | New bid submitted |
| bid.outbid | Bidding Orchestrator | Payment Service, Notification, OutSystems (Activity Log) | Previous highest bidder outbid → Payment Service releases previous bidder's escrow |
| wallet.credited | Temporal Worker | Notification, OutSystems (Activity Log) | Stripe top-up confirmed |
| auction.closing.warning | Temporal Worker | Notification, OutSystems (Activity Log) | T-12h or T-1h before deadline |
| auction.extended | Bidding Orchestrator | Notification, OutSystems (Activity Log) | Anti-snipe: bid placed in final 5 min, deadline extended by 5 min |
| auction.closed.winner | Temporal Worker | Notification, OutSystems (Activity Log) | Auction ended, winner selected |
| auction.closed.loser | Temporal Worker | Notification, OutSystems (Activity Log) | Auction ended, loser notified (escrow already released on outbid) |
| auction.expired | Temporal Worker | Notification, OutSystems (Activity Log) | Auction ended with zero bids |
| loan.due | Temporal Worker | Notification, OutSystems (Activity Log) | Loan due date arrived |
| loan.overdue | Temporal Worker | Invoice Service, Payment Service, User Service, Notification, OutSystems (Activity Log) | Repayment window expired unpaid |
| loan.repaid | Loan Orchestrator | Invoice Service, Payment Service, User Service, Notification, OutSystems (Activity Log) | Business repaid via Stripe |

---

## Choreography-Driven Flows

### loan.overdue (4 consumers)

Published by Temporal Worker when repayment window expires unpaid. Four separate queues, each bound to routing key `loan.overdue`:

| Queue | Consumer | Action |
|-------|----------|--------|
| invoice_loan_updates | Invoice Service | Marks invoice status → DEFAULTED |
| payment_loan_updates | Payment Service | Calculates 5% penalty |
| user_loan_updates | User Service | Sets business account_status → DEFAULTED |
| notification_loan_updates | Notification Service | Emails both business and investor |

### loan.repaid (4 consumers)

Published by Loan Orchestrator after Stripe confirms repayment. Four separate queues, each bound to routing key `loan.repaid`:

| Queue | Consumer | Action |
|-------|----------|--------|
| invoice_repaid_updates | Invoice Service | Marks invoice status → REPAID |
| payment_repaid_updates | Payment Service | Credits investor wallet |
| user_repaid_updates | User Service | Resets business account_status → ACTIVE |
| notification_repaid_updates | Notification Service | Emails both business and investor |

This makes the repayment and default flows symmetrical — both fully choreography-driven, removing direct coupling from orchestrators to atomics for post-event status updates.

### bid.outbid (2 consumers)

Published by Bidding Orchestrator when a new highest bid is placed. Two separate queues:

| Queue | Consumer | Action |
|-------|----------|--------|
| payment_outbid_updates | Payment Service | Releases previous bidder's escrow back to their wallet immediately |
| notification_outbid_updates | Notification Service | Notifies the outbid investor |

This reduces capital locked in escrow for losing investors throughout the auction period — escrow is released immediately on outbid rather than waiting for auction close.

---

## Detailed Scenario Flows (Service-to-Service)

These flows show every service interaction in order for each scenario. Use these to trace the exact path through the system diagram.

### Scenario 1 Flow: Business Lists Invoice for Auction

**Trigger:** Business clicks "List Invoice" in the React frontend.

| Step | From | To | Call / Action | Technology | Notes |
|------|------|----|---------------|------------|-------|
| 1 | Business | React Frontend | Upload invoice PDF + fill form | Browser | |
| 2 | React Frontend | KONG | `POST /api/invoices` (JWT + PDF) | HTTPS | |
| 3 | KONG | Invoice Orchestrator | Route to :5010 | REST/JSON | JWT validated by KONG |
| 4 | Invoice Orchestrator | User Service | `GET /users/{user_id}` — check account status is ACTIVE | HTTP (direct) | Rejects if DEFAULTED |
| 5 | Invoice Orchestrator | Invoice Service | `POST /invoices` — create invoice record + upload PDF to MinIO | HTTP (direct) | Invoice Service stores PDF in MinIO internally |
| 6 | Invoice Service | MinIO | Store invoice PDF | S3 API :9000 | Internal to Invoice Service |
| 7 | Invoice Service | Invoice Orchestrator | Returns invoice with extracted fields (pdfplumber) | HTTP response | |
| 8 | Invoice Orchestrator | ACRA Wrapper | `POST /validate-uen` — validate debtor UEN | REST/JSON | |
| 9 | ACRA Wrapper | data.gov.sg | ACRA UEN registry lookup (debtor) | HTTPS (external) | |
| 10 | ACRA Wrapper | Invoice Orchestrator | Returns UEN validation result | REST response | |
| 11a | *(If UEN invalid)* Invoice Orchestrator | Invoice Service | `PATCH /invoices/{id}` → status REJECTED | HTTP (direct) | |
| 11b | *(If UEN invalid)* Invoice Orchestrator | RabbitMQ | Publish `invoice.rejected` | AMQP | → Notification Service + OutSystems (Activity Log) |
| 11c | *(If UEN invalid)* | | **Flow ends** | | |
| 12 | Invoice Orchestrator | Marketplace Service | `POST /listings` — create listing with urgency level + deadline | HTTP (direct) | |
| 13 | Invoice Orchestrator | Invoice Service | `PATCH /invoices/{id}` → status LISTED | HTTP (direct) | |
| 14 | Invoice Orchestrator | Temporal Server | Start `AuctionCloseWorkflow` (workflow ID: `auction-{invoice_token}`) | Temporal SDK | Durable timer begins |
| 15 | Invoice Orchestrator | RabbitMQ | Publish `invoice.listed` | AMQP | |
| 16 | RabbitMQ | Notification Service | Consume `invoice.listed` → email business confirmation | AMQP | |
| 17 | Notification Service | Resend | Send email | HTTPS (external) | |
| 18 | Notification Service | React Frontend | Push real-time notification | WebSocket | |
| 19 | RabbitMQ | OutSystems (Activity Log) | Consume `invoice.listed` → write audit log | AMQP | |

**Temporal (background, after listing):**

| Step | From | To | Call / Action | Technology |
|------|------|----|---------------|------------|
| T1 | Temporal Worker | Temporal Server | Poll `invoiceflow-queue` for AuctionCloseWorkflow tasks | Temporal SDK |
| T2 | AuctionCloseWorkflow | — | Durable timer running for `bid_period_hours` | Temporal internal |
| T3 | AuctionCloseWorkflow | RabbitMQ | At T-12h: publish `auction.closing.warning` | AMQP |
| T4 | AuctionCloseWorkflow | RabbitMQ | At T-1h: publish `auction.closing.warning` | AMQP |

---

### Scenario 2 Flow: Investor Bids on Invoice (with Anti-Snipe) and Wins Auction

This flow has three phases: (A) Wallet Top-Up, (B) Bidding with Anti-Snipe, (C) Auction Close.

#### Phase A: Wallet Top-Up via Stripe

| Step | From | To | Call / Action | Technology | Notes |
|------|------|----|---------------|------------|-------|
| A1 | Investor | React Frontend | Click "Top Up Wallet" | Browser | |
| A2 | React Frontend | KONG | `POST /api/wallet/topup` | HTTPS | |
| A3 | KONG | Bidding Orchestrator | Route to :5011 | REST/JSON | |
| A4 | Bidding Orchestrator | Stripe Wrapper | `POST /create-checkout-session` (wallet top-up) | REST/JSON | |
| A5 | Stripe Wrapper | Stripe | Create Checkout Session | HTTPS (external) | |
| A6 | Stripe | Stripe Wrapper | Returns checkout URL | HTTPS response | |
| A7 | Stripe Wrapper | Bidding Orchestrator | Returns checkout URL | REST response | |
| A8 | Bidding Orchestrator | React Frontend | Returns checkout URL → redirect investor | REST response | |
| A9 | Investor | Stripe | Completes payment on Stripe hosted checkout | Browser redirect | |
| A10 | Stripe | KONG | Webhook `checkout.session.completed` | HTTPS (Stripe-Signature) | |
| A11 | KONG | Bidding Orchestrator | Route webhook to :5011 | REST/JSON | Signature verified |
| A12 | Bidding Orchestrator | Temporal Server | Start `WalletTopUpWorkflow` (ID: `wallet-topup-{session_id}`) | Temporal SDK | Idempotent |
| A13 | Temporal Worker | Payment Service | Credit investor wallet | HTTP (direct) | |
| A14 | Temporal Worker | RabbitMQ | Publish `wallet.credited` | AMQP | |
| A15 | RabbitMQ | Notification Service | Consume → email + WebSocket push | AMQP | |
| A16 | RabbitMQ | OutSystems (Activity Log) | Consume → audit log | AMQP | |

#### Phase B: Placing a Bid (with Anti-Snipe Extension)

| Step | From | To | Call / Action | Technology | Notes |
|------|------|----|---------------|------------|-------|
| B1 | Investor | React Frontend | Browse marketplace listings | Browser | |
| B2 | React Frontend | KONG | GraphQL query `{ listings(filter: ...) { ... } }` | HTTPS | |
| B3 | KONG | Marketplace Service | Execute GraphQL query (BTL #3, DataLoader batching) | GraphQL | |
| B4 | Marketplace Service | React Frontend | Returns filtered listings with current deadlines | GraphQL response | |
| B5 | Investor | React Frontend | Place bid on selected invoice | Browser | |
| B6 | React Frontend | KONG | `POST /api/bids` | HTTPS | |
| B7 | KONG | Bidding Orchestrator | Route to :5011 | REST/JSON | |
| B8 | Bidding Orchestrator | Bidding Service | `POST /bids` — validate bid, check for previous highest bidder | HTTP (direct) | Returns previous highest bid if outbid occurred |
| B9 | Bidding Orchestrator | Payment Service | `LockEscrow` — lock bid amount from investor wallet | gRPC :50051 | Idempotency key attached |
| B10 | *(If outbid occurred)* Bidding Orchestrator | RabbitMQ | Publish `bid.outbid` (previous highest bidder info) | AMQP | |
| B10a | RabbitMQ | Payment Service | Consume `bid.outbid` → release previous bidder's escrow | AMQP (choreography) | |
| B10b | RabbitMQ | Notification Service | Consume `bid.outbid` → notify outbid investor | AMQP | |
| B11 | Bidding Orchestrator | Marketplace Service | `GET /listings/{id}` — check if auction is within final 5 minutes | HTTP (direct) | Compare current time vs deadline |
| B12 | *(If within 5 min)* Bidding Orchestrator | Temporal Server | Signal `extend_deadline` to `AuctionCloseWorkflow` (ID: `auction-{invoice_token}`) | Temporal SDK (signal) | Workflow restarts 5-min timer |
| B13 | *(If within 5 min)* Bidding Orchestrator | Marketplace Service | `PATCH /listings/{id}` — update displayed deadline (+5 min) | HTTP (direct) | Frontend reflects new deadline |
| B14 | *(If within 5 min)* Bidding Orchestrator | RabbitMQ | Publish `auction.extended` | AMQP | → Notification + OutSystems (Activity Log) |
| B15 | Bidding Orchestrator | RabbitMQ | Publish `bid.placed` | AMQP | |
| B16 | RabbitMQ | Notification Service | Consume `bid.placed` → notify seller of new bid | AMQP | |
| B17 | RabbitMQ | OutSystems (Activity Log) | Consume `bid.placed` → audit log | AMQP | |

#### Phase C: Auction Closes (Timer Expires)

| Step | From | To | Call / Action | Technology | Notes |
|------|------|----|---------------|------------|-------|
| C1 | AuctionCloseWorkflow | — | Final 5-min timer expires with no `extend_deadline` signal | Temporal internal | Anti-snipe window passed |
| C2 | Temporal Worker | Bidding Service | `GET /bids?invoice_token={token}` — fetch all offers | HTTP (direct) | |
| C3 | Temporal Worker | Invoice Service | `verify_invoice_available` — confirm invoice still LISTED | HTTP (direct) | Step 1 |
| C4 | Temporal Worker | Payment Service | `convert_escrow_to_loan` — convert winner's escrowed funds to loan | gRPC :50051 | Step 2 |
| C5 | Temporal Worker | Payment Service | `create_loan` — create loan record | gRPC :50051 | Step 3 |
| C6 | Temporal Worker | Temporal Server | Start `LoanMaturityWorkflow` as child — fire-and-forget (ID: `loan-{loan_id}`) | Temporal SDK | Step 4 |
| C7 | Temporal Worker | Payment Service | `release_funds_to_seller` — transfer to seller wallet | gRPC :50051 | Step 5 |
| C8 | Temporal Worker | Invoice Service | `PATCH /invoices/{id}` → status FINANCED | HTTP (direct) | Step 6 |
| C9 | Temporal Worker | Marketplace Service | `DELETE /listings/{id}` — delist | HTTP (direct) | Step 7 |
| C10 | Temporal Worker | Bidding Service | `accept_offer` (winner) | HTTP (direct) | Step 8 |
| C11 | Temporal Worker | Bidding Service | `reject_offer` (all losers — **parallel**) | HTTP (direct) | Step 9 |
| C12 | Temporal Worker | RabbitMQ | Publish `auction.closed.winner` + `auction.closed.loser` (per loser) | AMQP | Step 10 — no refund needed, escrow already released on outbid |
| C13 | RabbitMQ | Notification Service | Consume → email winner + all losers + seller | AMQP | |
| C14 | RabbitMQ | OutSystems (Activity Log) | Consume → audit log | AMQP | |

---

### Scenario 3 Flow: Loan Maturity and Business Default

This flow has two branches: (A) Loan Comes Due + Repayment Window, then either (B) Business Repays or (C) Business Defaults.

#### Phase A: Loan Maturity (Due Date Arrives)

| Step | From | To | Call / Action | Technology | Notes |
|------|------|----|---------------|------------|-------|
| A1 | LoanMaturityWorkflow | — | Durable timer fires on `due_date` | Temporal internal | Could be days/weeks after auction |
| A2 | Temporal Worker | Payment Service | `PATCH /loans/{id}` → status DUE | HTTP (direct) | |
| A3 | Temporal Worker | RabbitMQ | Publish `loan.due` | AMQP | |
| A4 | RabbitMQ | Notification Service | Consume `loan.due` → email business "your loan is due" | AMQP | |
| A5 | Notification Service | Resend | Send email | HTTPS (external) | |
| A6 | Notification Service | React Frontend | Push real-time notification to business | WebSocket | |
| A7 | RabbitMQ | OutSystems (Activity Log) | Consume `loan.due` → audit log | AMQP | |
| A8 | LoanMaturityWorkflow | — | Start repayment window timer (120s demo / 86400s prod) | Temporal internal | 24h in production |

#### Phase B: Business Repays Successfully (within repayment window)

| Step | From | To | Call / Action | Technology | Notes |
|------|------|----|---------------|------------|-------|
| B1 | Business | React Frontend | Click "Repay Loan" | Browser | |
| B2 | React Frontend | KONG | `POST /api/loans/{id}/repay` | HTTPS | |
| B3 | KONG | Loan Orchestrator | Route to :5012 | REST/JSON | |
| B4 | Loan Orchestrator | Stripe Wrapper | `POST /create-checkout-session` (loan repayment) | REST/JSON | |
| B5 | Stripe Wrapper | Stripe | Create Checkout Session | HTTPS (external) | |
| B6 | Stripe | Business | Business completes payment on Stripe hosted checkout | Browser redirect | |
| B7 | Stripe | Business (browser) | Redirect to success URL (React frontend) | Browser redirect | Frontend renders success page |
| B8 | React Frontend | KONG | `POST /api/loans/{id}/confirm-repayment` with `{ stripe_session_id }` | HTTPS | Frontend calls confirm endpoint |
| B9 | KONG | Loan Orchestrator | Route to :5012 | REST/JSON | |
| B10 | Loan Orchestrator | Payment Service | `UpdateLoanStatus` → status REPAID | gRPC :50051 | |
| B11 | Loan Orchestrator | RabbitMQ | Publish `loan.repaid` | AMQP | **Four-consumer choreography begins** |
| B12 | RabbitMQ | Invoice Service | Consume `loan.repaid` (queue: `invoice_repaid_updates`) → mark invoice REPAID | AMQP | Consumer 1 |
| B13 | RabbitMQ | Payment Service | Consume `loan.repaid` (queue: `payment_repaid_updates`) → credit investor wallet | AMQP | Consumer 2 |
| B14 | RabbitMQ | User Service | Consume `loan.repaid` (queue: `user_repaid_updates`) → reset business account_status ACTIVE | AMQP | Consumer 3 |
| B15 | RabbitMQ | Notification Service | Consume `loan.repaid` (queue: `notification_repaid_updates`) → email both parties | AMQP | Consumer 4 |
| B16 | Notification Service | Resend | Send emails to business + investor | HTTPS (external) | |
| B17 | RabbitMQ | OutSystems (Activity Log) | Consume `loan.repaid` → audit log | AMQP | |
| B18 | LoanMaturityWorkflow | — | Repayment window check finds loan REPAID → **workflow ends cleanly** | Temporal internal | |

#### Phase C: Business Defaults (repayment window expires unpaid)

| Step | From | To | Call / Action | Technology | Notes |
|------|------|----|---------------|------------|-------|
| C1 | LoanMaturityWorkflow | — | Repayment window timer expires | Temporal internal | |
| C2 | Temporal Worker | Payment Service | `GetLoan` — check loan status, still DUE (not repaid) | gRPC :50051 | |
| C3 | Temporal Worker | Payment Service | `UpdateLoanStatus` → status OVERDUE | gRPC :50051 | |
| C4 | Temporal Worker | RabbitMQ | Publish `loan.overdue` | AMQP | **Four-consumer choreography begins** |
| C5 | RabbitMQ | Invoice Service | Consume `loan.overdue` (queue: `invoice_loan_updates`) → mark invoice DEFAULTED | AMQP | Consumer 1 |
| C6 | RabbitMQ | Payment Service | Consume `loan.overdue` (queue: `payment_loan_updates`) → calculate 5% penalty | AMQP | Consumer 2 |
| C7 | RabbitMQ | User Service | Consume `loan.overdue` (queue: `user_loan_updates`) → set business account_status → DEFAULTED | AMQP | Consumer 3 |
| C8 | RabbitMQ | Notification Service | Consume `loan.overdue` (queue: `notification_loan_updates`) → email both parties | AMQP | Consumer 4 |
| C9 | Notification Service | Resend | Send emails to business + investor | HTTPS (external) | |
| C10 | RabbitMQ | OutSystems (Activity Log) | Consume `loan.overdue` → audit log | AMQP | |
| C11 | Temporal Worker | Marketplace Service | `DELETE /listings?seller_id={id}` — bulk delist all defaulting seller's active listings | HTTP (direct) | Prevents further auctions |
| C12 | LoanMaturityWorkflow | — | **Workflow ends** | Temporal internal | |

---

## Technology Stack Summary

| Layer | Technology |
|-------|-----------|
| Frontend | React :8080 |
| API Gateway | KONG :8000 (BTL #1) |
| Composite Services | Python / FastAPI (:5010, :5011, :5012) |
| Atomic Services | Python / FastAPI (:5000–:5005), Node.js / Express (:5004) |
| Databases | MySQL (one per service, :3306–:3310) |
| File Storage | MinIO :9000 (S3-compatible) |
| Message Broker | RabbitMQ :5672 (AMQP, topic exchange) |
| Workflow Engine | Temporal Server :7233 + Worker (Python SDK) + UI :8088 |
| Payments | Stripe (external) via Stripe Wrapper (outbound) and KONG (inbound webhook) |
| UEN Validation | User Service → data.gov.sg (seller), ACRA Wrapper → data.gov.sg (debtor) |
| Email | Resend (inside Notification Service) |
| Deployment | Docker + Docker Compose |
