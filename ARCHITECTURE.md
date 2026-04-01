# InvoiceFlow — Architecture

## Overview

InvoiceFlow is an invoice-financing marketplace built as a set of loosely-coupled microservices. Sellers upload invoices; investors bid on them; winning bids trigger Temporal workflows that lock escrow, create loans, and route Stripe payments back to sellers.

```
Browser (React/Vite)
       │
       ▼
  Kong API Gateway  (:8000)
       │  JWT validation, rate-limiting, CORS, correlation-id
       │
  ┌────┴────────────────────────────────────────────────────┐
  │                        Services                         │
  │                                                         │
  │  user-service          (:5000)  — auth, JWT             │
  │  invoice-orchestrator  (:5010)  — invoice lifecycle     │
  │  bidding-orchestrator  (:5011)  — bid + wallet APIs     │
  │  loan-orchestrator     (:5012)  — loan repayment         │
  │  marketplace-service   (:5002)  — listings read model   │
  │  notification-service  (:5005)  — in-memory + email     │
  │  webhook-router        (:5013)  — Stripe webhook intake │
  │  dlq-monitor           (:5014)  — DLQ depth inspector   │
  └─────────────────────────────────────────────────────────┘
       │                          │
  RabbitMQ (topic exchange)   Temporal (workflow engine)
       │                          │
  ┌────┴──────┐            temporal-worker (Python SDK)
  │  *.dlq    │            — InvoiceListingWorkflow
  │  exchange │            — BidWorkflow
  └───────────┘            — AuctionClosedWorkflow
                           — WalletTopUpWorkflow
                           — LoanRepaymentWorkflow
```

---

## Services

### user-service (port 5000)
FastAPI + MySQL (`user_db`). Issues HS256 JWTs. SELLER registration validates UEN against data.gov.sg ACRA API.

### invoice-orchestrator (port 5010)
Receives PDF uploads, extracts fields, stores to MinIO, creates an invoice record (invoice-service), and starts `InvoiceListingWorkflow` in Temporal which lists the invoice on the marketplace.

### invoice-service (port 5001, internal)
CRUD over `invoice_db`. Owned by invoice-orchestrator; not directly routed through Kong.

### bidding-orchestrator (port 5011)
Handles `POST /api/bids` and wallet top-up. On bid placement starts `BidWorkflow` which locks escrow via payment-service (gRPC). Consumes `stripe.checkout.completed` events to credit wallets via `WalletTopUpWorkflow`.

### bidding-service (port 5003, internal)
CRUD over `bidding_db` (bids table). Called by bidding-orchestrator.

### marketplace-service (port 5002)
Read-model service: listings are written on invoice creation and updated by event consumers (`bid.placed`, `auction.closed.*`). Provides `GET /api/listings` and `GET /api/listings/{id}` — single SQL query, no N+1.

### loan-orchestrator (port 5012)
Manages active loans. Exposes `GET /api/loans`, `POST /api/loans/{id}/repay`, and `POST /api/loans/{id}/confirm-repayment`. Consumes `stripe.checkout.completed` for loan repayments and starts `LoanRepaymentWorkflow`.

### payment-service (port 5004, internal — gRPC)
Node.js gRPC server. Manages wallets, escrow locking/releasing, and loan creation in `payment_db`. Called by bidding-orchestrator and temporal-worker.

### notification-service (port 5005)
Consumes all domain events from RabbitMQ and dispatches email (Resend) + WebSocket push. Stores recent notifications in an in-memory list (last 50 per user). Exposes `GET/PATCH /api/notifications`.

### webhook-router (port 5013)
Receives `POST /api/webhooks/stripe`, verifies Stripe-Signature HMAC, and publishes a normalised `stripe.checkout.completed` event to RabbitMQ. This decouples all downstream consumers from Stripe's raw payload shape.

### dlq-monitor (port 5014)
Read-only inspector: queries the RabbitMQ Management API for queues whose name ends in `.dlq` and reports message depths. No messages are consumed or acknowledged.

### temporal-worker
Python Temporal worker that executes workflow and activity code. Workflows: `InvoiceListingWorkflow`, `BidWorkflow`, `AuctionClosedWorkflow`, `WalletTopUpWorkflow`, `LoanRepaymentWorkflow`.

---

## Messaging

All services publish and subscribe via a single RabbitMQ **topic exchange** (`invoiceflow_events`).

| Event key | Publisher | Subscribers |
|---|---|---|
| `invoice.listed` | temporal-worker | notification-service, marketplace-service |
| `bid.placed` | temporal-worker | notification-service, marketplace-service |
| `auction.closed.funded` | temporal-worker | notification-service, marketplace-service |
| `auction.closed.unfunded` | temporal-worker | notification-service, marketplace-service |
| `auction.extended` | temporal-worker | notification-service, marketplace-service |
| `loan.created` | temporal-worker | notification-service |
| `loan.repaid` | temporal-worker | notification-service |
| `stripe.checkout.completed` | webhook-router | bidding-orchestrator, loan-orchestrator |

**Dead-letter queue**: every consumer declares its queue with `x-dead-letter-exchange: invoiceflow_dlq`. Messages that fail after processing are nack'd (no requeue) and land in `<queue>.dlq`. The dlq-monitor exposes their depth without consuming them.

---

## Databases

| Service | Database | Engine |
|---|---|---|
| user-service | `user_db` | MySQL |
| invoice-service | `invoice_db` | MySQL |
| marketplace-service | `market_db` | MySQL |
| bidding-service | `bidding_db` | MySQL |
| payment-service | `payment_db` | MySQL |

Schema migrations are managed with **Alembic** for all Python/SQLAlchemy services. Fresh deployments can also use the `databases/*/init.sql` scripts directly.

---

## API Gateway (Kong)

Kong runs in DB-less declarative mode (`gateway/kong.yml`). Global plugins:

- **cors** — allows `http://localhost:3000`
- **rate-limiting** — 100 req/min per IP (local policy)
- **correlation-id** — injects/echoes `X-Correlation-ID` on every request

JWT authentication is applied per-service (all routes except `/api/auth` and `/api/webhooks/stripe`). The JWT consumer credential key is `invoiceflow`; the secret matches `JWT_SECRET`.

---

## Observability

| Tool | Purpose | Port |
|---|---|---|
| Prometheus | Metrics scraping | 9090 |
| Grafana | Dashboards | 3000 |
| Loki | Log aggregation | 3100 |
| Promtail | Docker log shipping | — |
| Tempo | Distributed tracing (OTLP) | 3200 / 4317 / 4318 |

All Python services emit structured logs via **structlog** and traces via **OpenTelemetry** (OTLP HTTP → Tempo). Trace IDs are propagated through `X-Correlation-ID`.

---

## Frontend

React 18 + Vite + TailwindCSS. Communicates exclusively through Kong (`/api/*`). Auth state is held in `AuthContext` (JWT stored in localStorage). Protected routes redirect to `/login` when unauthenticated. An `ErrorBoundary` wraps the entire app to catch unexpected render errors.

---

## Local Development

```bash
cp .env.example .env          # fill in secrets
docker compose up --build     # starts all services
```

Kong is available at `http://localhost:8000`. Grafana at `http://localhost:3000`.
