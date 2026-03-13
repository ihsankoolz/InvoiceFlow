# InvoiceFlow

**SMU IS213 · Enterprise Solution Development · AY2025/26**

InvoiceFlow is an invoice factoring marketplace where businesses list invoices for auction and investors bid to finance them. The platform handles the full lifecycle: invoice listing, competitive bidding with anti-snipe protection, fund disbursement via Stripe, loan tracking with Temporal durable workflows, and debt resolution with choreography-driven event fan-out.

---

## Prerequisites

- **Docker Desktop** (latest)
- **Python 3.11+** (for local development of FastAPI services)
- **Node.js 20+** (for Payment Service local development)
- **Git**

---

## Quick Start

```bash
# Clone the repo
git clone <repo-url>
cd invoiceflow

# Copy environment file and fill in secrets
cp .env.example .env

# Start the full stack
docker compose up --build
```

Wait for all health checks to pass, then verify:

```bash
docker compose ps
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [Final_Architecture_MK_2.md](Final_Architecture_MK_2.md) | Authoritative architecture (v4.3) — services, connections, protocols, rules |
| [BUILD_INSTRUCTIONS_V2.md](BUILD_INSTRUCTIONS_V2.md) | Detailed build instructions per service — endpoints, schemas, classes, test steps |
| [TEAM_GUIDE.md](TEAM_GUIDE.md) | Step-by-step team playbook from zero to working demo |

---

## Service URLs

| Service | URL | Notes |
|---------|-----|-------|
| **KONG API Gateway** | http://localhost:8000 | All external traffic enters here |
| **RabbitMQ Management** | http://localhost:15672 | guest / guest |
| **Temporal UI** | http://localhost:8088 | Monitor workflows |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin |
| User Service | http://localhost:5000/docs | Swagger UI |
| Invoice Service | http://localhost:5001/docs | Swagger UI |
| Marketplace Service | http://localhost:5002/docs | REST Swagger |
| Marketplace GraphQL | http://localhost:5002/graphql | GraphQL playground |
| Bidding Service | http://localhost:5003/docs | Swagger UI |
| Payment Service | http://localhost:5004/docs | Swagger UI (REST read-only) |
| Notification Service | http://localhost:5005/docs | Swagger UI |
| Invoice Orchestrator | http://localhost:5010/docs | Swagger UI |
| Bidding Orchestrator | http://localhost:5011/docs | Swagger UI |
| Loan Orchestrator | http://localhost:5012/docs | Swagger UI |
| ACRA Wrapper | http://localhost:5007/docs | Swagger UI |
| Stripe Wrapper | http://localhost:5008/docs | Swagger UI |

---

## Project Structure

```
invoiceflow/
├── services/                    # Atomic services (direct DB access)
│   ├── user-service/            # :5000  Python/FastAPI · user_db
│   ├── invoice-service/         # :5001  Python/FastAPI · invoice_db
│   ├── marketplace-service/     # :5002  Python/FastAPI + Strawberry GraphQL · market_db
│   ├── bidding-service/         # :5003  Python/FastAPI · bidding_db
│   ├── payment-service/         # :5004/:50051  Node.js/Express + gRPC · payment_db
│   └── notification-service/    # :5005  Python/FastAPI + WebSocket
├── orchestrators/               # Composite services (no direct DB access)
│   ├── invoice-orchestrator/    # :5010  Scenario 1 — invoice listing flow
│   ├── bidding-orchestrator/    # :5011  Scenario 2 — bidding, escrow, Stripe, anti-snipe
│   └── loan-orchestrator/       # :5012  Scenario 3 — loan repayment flow
├── wrappers/                    # Third-party API wrappers
│   ├── acra-wrapper/            # :5007  data.gov.sg ACRA UEN validation
│   └── stripe-wrapper/          # :5008  Stripe Checkout Session creation
├── temporal-worker/             # Temporal Worker — all workflow + activity definitions
│   ├── workflows/               # AuctionCloseWorkflow, LoanMaturityWorkflow, WalletTopUpWorkflow
│   ├── activities/              # invoice, bidding, payment (gRPC), marketplace, rabbitmq
│   └── clients/                 # HTTPClient, PaymentGRPCClient
├── gateway/
│   └── kong.yml                 # Declarative KONG config — routes, JWT, rate-limiting, CORS
├── databases/                   # Per-service MySQL init scripts
│   ├── user-db/init.sql
│   ├── invoice-db/init.sql
│   ├── market-db/init.sql
│   ├── bidding-db/init.sql
│   └── payment-db/init.sql
├── proto/
│   └── payment.proto            # gRPC service definition (8 RPCs)
├── docker-compose.yml           # Full stack — all services, DBs, RabbitMQ, MinIO, Temporal, KONG
└── .env.example                 # All environment variables grouped by service
```

---

## Architecture Overview

```
Frontend (React)
      │
      ▼
KONG API Gateway :8000   ← JWT validation, rate limiting, CORS, routing
      │
      ├─→ Invoice Orchestrator :5010   → Invoice Service, Marketplace Service, ACRA Wrapper
      │                                 → Temporal (start AuctionCloseWorkflow)
      │
      ├─→ Bidding Orchestrator :5011   → Bidding Service, Marketplace Service
      │                                 → Payment Service (gRPC: LockEscrow)
      │                                 → Stripe Wrapper (wallet top-up)
      │                                 → Temporal (signal extend_deadline / start WalletTopUpWorkflow)
      │
      ├─→ Loan Orchestrator :5012      → Payment Service (gRPC: GetLoan, UpdateLoanStatus)
      │                                 → Stripe Wrapper (loan repayment)
      │                                 → RabbitMQ (publish loan.repaid)
      │
      └─→ User Service / Notification Service (direct, read-only)

Temporal Worker  ← polls invoiceflow-queue
  ├── AuctionCloseWorkflow  (timer → anti-snipe → 10-step settlement → start LoanMaturityWorkflow)
  ├── LoanMaturityWorkflow  (sleep until due → check repaid → mark OVERDUE if not)
  └── WalletTopUpWorkflow   (credit wallet → publish wallet.credited)

RabbitMQ  exchange: invoiceflow_events  (topic)
  bid.placed, bid.outbid
  auction.closed.winner, auction.closed.loser, auction.closing.warning, auction.extended
  loan.repaid   → 4 consumers (Invoice, Payment, User, Notification)
  loan.overdue  → 4 consumers (Invoice, Payment, User, Notification)
  wallet.credited
```

---

## Scaffold Status

All 13 services are scaffolded with:

- Complete folder structures and `__init__.py` files
- **Complete**: models, schemas, `config.py`, `database.py`, `docker-compose` entries
- **Skeleton**: service classes with correct method signatures, step-by-step docstrings, and `TODO` bodies
- **Skeleton**: router endpoints with correct decorators, `response_model`, and `TODO` bodies

To implement a service, open [BUILD_INSTRUCTIONS_V2.md](BUILD_INSTRUCTIONS_V2.md), find your service's section, and fill in the `TODO` bodies following the docstrings.

---

## Key Environment Variables

Copy `.env.example` to `.env` and replace placeholder values before running:

| Variable | Description |
|----------|-------------|
| `JWT_SECRET` | Secret key for JWT signing (User Service) |
| `STRIPE_SECRET_KEY` | Stripe API key (`sk_test_...`) |
| `STRIPE_WEBHOOK_SECRET` | Stripe webhook signing secret (`whsec_...`) |
| `RESEND_API_KEY` | Resend transactional email API key |

All other variables (service URLs, DB connections, RabbitMQ, MinIO, Temporal) default to Docker Compose service hostnames and work out of the box.
