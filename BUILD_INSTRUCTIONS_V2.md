# InvoiceFlow — Service Build Instructions

**SMU IS213 · Enterprise Solution Development · AY2025/26**

This document provides build instructions for every service in InvoiceFlow. Each section is self-contained — a team member can take their assigned service section, read it, and build the service from scratch (or paste it into an LLM for assistance).

**Important conventions for ALL services:**
- Use **object-oriented programming** — every service should have proper classes, not just loose functions
- Every FastAPI service must expose **Swagger UI** at `/docs` (FastAPI does this automatically) — use it for testing API calls and debugging
- Add `tags`, `summary`, `description`, and `response_model` to every endpoint for clean Swagger docs
- Use **Pydantic models** for all request/response schemas (these auto-generate Swagger schemas)
- Every service runs in its own **Docker container** with its own `Dockerfile` and entry in `docker-compose.yml`
- Use **environment variables** for all configuration (ports, DB URLs, secrets) — never hardcode

---

## Table of Contents

1. [User Service](#1-user-service)
2. [Invoice Service](#2-invoice-service)
3. [Marketplace Service](#3-marketplace-service)
4. [Bidding Service](#4-bidding-service)
5. [Payment Service](#5-payment-service)
6. [Notification Service](#6-notification-service)
7. [OutSystems Activity Log](#7-outsystems-activity-log)
8. [Invoice Orchestrator](#8-invoice-orchestrator)
9. [Bidding Orchestrator](#9-bidding-orchestrator)
10. [Loan Orchestrator](#10-loan-orchestrator)
11. [ACRA Wrapper](#11-acra-wrapper)
12. [Stripe Wrapper](#12-stripe-wrapper)
13. [Temporal Worker](#13-temporal-worker)
14. [KONG API Gateway](#14-kong-api-gateway)

---

## 1. User Service

**Type:** Atomic Service
**Port:** 5000
**Technology:** Python / FastAPI
**Database:** user_db (MySQL :3306)
**Owner:** *(assign team member)*

### Purpose

Handles user registration, authentication (JWT), and account status management. Calls data.gov.sg directly to validate seller UEN at registration time. Also acts as a RabbitMQ consumer for `loan.repaid` and `loan.overdue` events to update account status via choreography.

### Swagger

- Swagger UI auto-available at `http://localhost:5000/docs`
- Use Swagger to test all endpoints during development
- Add `tags=["Users"]` or `tags=["Auth"]` to group endpoints in Swagger

### Project Structure

```
user-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, CORS, lifespan, Swagger config + RabbitMQ consumer startup
│   ├── config.py               # Environment variables (DB_URL, JWT_SECRET, RABBITMQ_URL, etc.)
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py             # SQLAlchemy ORM model: User
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py             # Pydantic models: UserCreate, UserResponse, UserLogin, TokenResponse
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py             # POST /login, POST /register
│   │   └── users.py            # GET /users/{id}, PATCH /users/{id}/status, GET /health
│   ├── services/
│   │   ├── __init__.py
│   │   ├── user_service.py     # UserService class — business logic
│   │   └── uen_validator.py    # UENValidator class — calls data.gov.sg
│   ├── consumers/
│   │   ├── __init__.py
│   │   └── loan_consumer.py    # RabbitMQ consumer: loan.repaid → ACTIVE, loan.overdue → DEFAULTED
│   └── database.py             # SQLAlchemy engine, session factory
├── Dockerfile
├── requirements.txt
└── .env
```

### Database Schema

```sql
CREATE TABLE users (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    email           VARCHAR(255) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) NOT NULL,
    role            ENUM('SELLER', 'INVESTOR') NOT NULL,
    uen             VARCHAR(20),                          -- only for SELLER
    account_status  ENUM('ACTIVE', 'DEFAULTED') DEFAULT 'ACTIVE',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### API Endpoints

| Method | Path | Request Body | Response | Description |
|--------|------|-------------|----------|-------------|
| GET | `/health` | — | `{"status": "ok", "service": "user-service"}` | Health check for Docker and KONG. |
| POST | `/register` | `UserCreate` (email, password, full_name, role, uen?) | `UserResponse` | Register new user. If role=SELLER, validate UEN against data.gov.sg before creating. Return 400 if UEN invalid. |
| POST | `/login` | `UserLogin` (email, password) | `TokenResponse` (access_token, token_type) | Verify credentials, return JWT. |
| GET | `/users/{user_id}` | — | `UserResponse` | Get user by ID. Used by Invoice Orchestrator to check account_status. |
| PATCH | `/users/{user_id}/status` | `StatusUpdate` (account_status) | `UserResponse` | Update account_status to ACTIVE or DEFAULTED. Used internally by the RabbitMQ consumer (not called by other services directly for loan flows). |

### Key Classes

**UserService** — core business logic:
- `create_user(data: UserCreate) -> User` — hash password, validate UEN if seller, save to DB
- `authenticate(email, password) -> TokenResponse` — verify password, generate JWT
- `get_user(user_id) -> User` — fetch by ID
- `update_status(user_id, status) -> User` — set ACTIVE or DEFAULTED

**UENValidator** — external API integration:
- `validate_uen(uen: str) -> bool` — calls `https://data.gov.sg/api/action/datastore_search` with the ACRA dataset to verify the UEN exists. Returns True/False.

**LoanEventConsumer (RabbitMQ):**
- Subscribes to queues: `user_repaid_updates` (routing key `loan.repaid`), `user_loan_updates` (routing key `loan.overdue`)
- On `loan.repaid` → calls `UserService.update_status(seller_id, "ACTIVE")`
- On `loan.overdue` → calls `UserService.update_status(seller_id, "DEFAULTED")`
- Start this consumer in `main.py` lifespan as a background task

### Pydantic Schemas (for Swagger)

```python
class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: Literal["SELLER", "INVESTOR"]
    uen: Optional[str] = None  # required if role=SELLER

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    uen: Optional[str]
    account_status: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class StatusUpdate(BaseModel):
    account_status: Literal["ACTIVE", "DEFAULTED"]
```

### Who Calls This Service

- **Invoice Orchestrator** → `GET /users/{id}` to check account_status is ACTIVE before listing
- **KONG** → routes `/login` and `/register` from frontend
- **RabbitMQ** → `loan.repaid`, `loan.overdue` (choreography consumer — sets account status)

### How to Test

**Tier 1 — Standalone smoke test:**
1. `docker compose up user-service user-db`
2. Open `http://localhost:5000/docs` (Swagger UI)
3. `GET /health` → should return `{"status": "ok", "service": "user-service"}`
4. `POST /register` with a test INVESTOR user (no UEN needed) → verify 200 + user returned
5. `POST /register` with a test SELLER user (with a valid UEN) → verify 200
6. `POST /login` with correct credentials → verify JWT returned
7. `POST /login` with wrong password → verify 401
8. `GET /users/{id}` → verify user details returned
9. `PATCH /users/{id}/status` with `{"account_status": "DEFAULTED"}` → verify updated

**Tier 2 — Integration test with RabbitMQ:**
1. `docker compose up user-service user-db rabbitmq`
2. Open RabbitMQ Management UI at `http://localhost:15672` (guest/guest)
3. Publish a test message to `invoiceflow_events` exchange with routing key `loan.overdue` and payload `{"seller_id": 1, "loan_id": "test-123"}`
4. Check that the user's `account_status` changed to `DEFAULTED` via `GET /users/1`
5. Publish a test message with routing key `loan.repaid` and payload `{"seller_id": 1, "loan_id": "test-123"}`
6. Check that the user's `account_status` changed back to `ACTIVE`

### Dependencies

- `fastapi`, `uvicorn`, `sqlalchemy`, `pymysql`, `pydantic`, `python-jose[cryptography]`, `passlib[bcrypt]`, `httpx`, `aio-pika`

---

## 2. Invoice Service

**Type:** Atomic Service
**Port:** 5001
**Technology:** Python / FastAPI
**Database:** invoice_db (MySQL :3307)
**File Storage:** MinIO (S3 API :9000)
**Owner:** *(assign team member)*

### Purpose

Handles invoice CRUD, PDF upload/storage, PDF text extraction (pdfplumber), and invoice status tracking. Also acts as a RabbitMQ consumer for `loan.repaid` and `loan.overdue` events (choreography).

### Swagger

- Swagger UI at `http://localhost:5001/docs`
- Tag endpoints: `tags=["Invoices"]`, `tags=["Status"]`
- PDF upload endpoint needs `File(...)` parameter — Swagger will show a file upload widget

### Project Structure

```
invoice-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app + RabbitMQ consumer startup
│   ├── config.py               # DB_URL, MINIO_ENDPOINT, MINIO_ACCESS_KEY, etc.
│   ├── models/
│   │   ├── __init__.py
│   │   └── invoice.py          # SQLAlchemy ORM: Invoice
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── invoice.py          # Pydantic: InvoiceCreate, InvoiceResponse, InvoiceStatusUpdate
│   ├── routers/
│   │   ├── __init__.py
│   │   └── invoices.py         # All invoice endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── invoice_service.py  # InvoiceService class — business logic
│   │   ├── pdf_extractor.py    # PDFExtractor class — pdfplumber wrapper
│   │   └── storage_service.py  # StorageService class — MinIO operations
│   ├── consumers/
│   │   ├── __init__.py
│   │   └── loan_consumer.py    # RabbitMQ consumer: loan.repaid, loan.overdue
│   └── database.py
├── Dockerfile
├── requirements.txt
└── .env
```

### Database Schema

```sql
CREATE TABLE invoices (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    invoice_token   VARCHAR(36) UNIQUE NOT NULL,          -- UUID, used as public identifier
    seller_id       INT NOT NULL,
    debtor_name     VARCHAR(255),
    debtor_uen      VARCHAR(20) NOT NULL,
    amount          DECIMAL(12,2) NOT NULL,
    due_date        DATE NOT NULL,
    currency        VARCHAR(3) DEFAULT 'SGD',
    pdf_url         VARCHAR(500),                         -- MinIO object path
    status          ENUM('DRAFT', 'LISTED', 'FINANCED', 'REPAID', 'DEFAULTED', 'REJECTED') DEFAULT 'DRAFT',
    extracted_data  JSON,                                 -- raw pdfplumber output
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### API Endpoints

| Method | Path | Request Body | Response | Description |
|--------|------|-------------|----------|-------------|
| GET | `/health` | — | `{"status": "ok", "service": "invoice-service"}` | Health check. |
| POST | `/invoices` | `multipart/form-data` (PDF file + seller_id, debtor_uen, amount, due_date) | `InvoiceResponse` | Create invoice, upload PDF to MinIO, extract text with pdfplumber, return invoice with extracted_data. |
| GET | `/invoices/{invoice_token}` | — | `InvoiceResponse` | Get invoice by token. |
| GET | `/invoices?seller_id={id}` | — | `List[InvoiceResponse]` | List all invoices for a seller. |
| PATCH | `/invoices/{invoice_token}/status` | `InvoiceStatusUpdate` (status) | `InvoiceResponse` | Update invoice status. Used by orchestrators and Temporal Worker. |

### Key Classes

**InvoiceService:**
- `create_invoice(data, pdf_file) -> Invoice` — save record, upload PDF, extract text
- `get_invoice(invoice_token) -> Invoice`
- `get_invoices_by_seller(seller_id) -> List[Invoice]`
- `update_status(invoice_token, status) -> Invoice`

**PDFExtractor:**
- `extract_fields(pdf_bytes) -> dict` — uses pdfplumber to extract text, returns structured data (debtor name, amount, dates, etc.)

**StorageService:**
- `upload_pdf(invoice_token, pdf_bytes) -> str` — uploads to MinIO bucket, returns object URL
- `get_pdf_url(invoice_token) -> str` — generates presigned download URL

**LoanEventConsumer (RabbitMQ):**
- Subscribes to queues: `invoice_repaid_updates` (routing key `loan.repaid`), `invoice_loan_updates` (routing key `loan.overdue`)
- On `loan.repaid` → calls `InvoiceService.update_status(token, "REPAID")`
- On `loan.overdue` → calls `InvoiceService.update_status(token, "DEFAULTED")`
- Start this consumer in `main.py` lifespan as a background task

### Who Calls This Service

- **Invoice Orchestrator** → `POST /invoices`, `PATCH /invoices/{token}/status`
- **Temporal Worker** → `GET /invoices/{token}` (verify available), `PATCH /invoices/{token}/status` (→ FINANCED)
- **RabbitMQ** → `loan.repaid`, `loan.overdue` (choreography consumer)

### How to Test

**Tier 1 — Standalone smoke test:**
1. `docker compose up invoice-service invoice-db minio`
2. Open `http://localhost:5001/docs` (Swagger UI)
3. `GET /health` → verify `{"status": "ok", "service": "invoice-service"}`
4. `POST /invoices` with a test PDF file → verify invoice created with extracted_data
5. `GET /invoices/{token}` → verify returned data matches
6. `PATCH /invoices/{token}/status` with `{"status": "LISTED"}` → verify status updated
7. Check MinIO Console (`http://localhost:9001`) to verify the PDF was uploaded

**Tier 2 — Integration test with RabbitMQ:**
1. `docker compose up invoice-service invoice-db minio rabbitmq`
2. Create a test invoice via Swagger, set status to FINANCED
3. Open RabbitMQ Management UI (`http://localhost:15672`)
4. Publish a message to `invoiceflow_events` exchange with routing key `loan.repaid` and payload `{"invoice_token": "<your-token>", "seller_id": 1}`
5. `GET /invoices/{token}` → verify status changed to REPAID
6. Repeat with routing key `loan.overdue` → verify status changed to DEFAULTED

### Dependencies

- `fastapi`, `uvicorn`, `sqlalchemy`, `pymysql`, `pydantic`, `pdfplumber`, `minio`, `aio-pika` (RabbitMQ)

---

## 3. Marketplace Service

**Type:** Atomic Service
**Port:** 5002
**Technology:** Python / FastAPI + GraphQL (Strawberry)
**Database:** market_db (MySQL :3308)
**Owner:** *(assign team member)*

### Purpose

Manages marketplace listings with urgency levels, search/filter, and GraphQL queries (BTL #3). Investors browse listings through GraphQL. Also provides REST endpoints for listing creation, update, and deletion used by orchestrators and Temporal Worker.

### Swagger

- REST Swagger UI at `http://localhost:5002/docs` — for all REST endpoints
- GraphQL Playground at `http://localhost:5002/graphql` — for investor queries
- Tag REST endpoints: `tags=["Listings"]`

### Project Structure

```
marketplace-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app + Strawberry GraphQL mount
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── listing.py          # SQLAlchemy ORM: Listing
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── listing.py          # Pydantic: ListingCreate, ListingResponse, ListingUpdate
│   ├── routers/
│   │   ├── __init__.py
│   │   └── listings.py         # REST endpoints
│   ├── graphql/
│   │   ├── __init__.py
│   │   ├── schema.py           # Strawberry schema: Query, ListingType
│   │   └── dataloader.py       # DataLoader for batching N+1 queries
│   ├── services/
│   │   ├── __init__.py
│   │   └── listing_service.py  # ListingService class
│   └── database.py
├── Dockerfile
├── requirements.txt
└── .env
```

### Database Schema

```sql
CREATE TABLE listings (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    invoice_token   VARCHAR(36) UNIQUE NOT NULL,
    seller_id       INT NOT NULL,
    debtor_uen      VARCHAR(20) NOT NULL,
    amount          DECIMAL(12,2) NOT NULL,
    urgency_level   ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL,
    deadline        DATETIME NOT NULL,                    -- auction close time (may be extended by anti-snipe)
    status          ENUM('ACTIVE', 'CLOSED', 'EXPIRED') DEFAULT 'ACTIVE',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### API Endpoints (REST)

| Method | Path | Request Body | Response | Description |
|--------|------|-------------|----------|-------------|
| GET | `/health` | — | `{"status": "ok", "service": "marketplace-service"}` | Health check. |
| POST | `/listings` | `ListingCreate` (invoice_token, seller_id, debtor_uen, amount, urgency_level, deadline) | `ListingResponse` | Create new listing. Called by Invoice Orchestrator. |
| GET | `/listings/{listing_id}` | — | `ListingResponse` | Get listing by ID. Used by Bidding Orchestrator to check deadline for anti-snipe. |
| PATCH | `/listings/{listing_id}` | `ListingUpdate` (deadline?, status?) | `ListingResponse` | Update deadline (anti-snipe extension) or status. |
| DELETE | `/listings/{listing_id}` | — | `204 No Content` | Delist. Called by Temporal Worker on auction close. |
| DELETE | `/listings?seller_id={id}` | — | `{"deleted_count": N}` | Bulk delist all active listings for a seller. Called by Temporal Worker on default. |

### GraphQL Schema (BTL #3)

```graphql
type Listing {
    id: Int!
    invoiceToken: String!
    sellerId: Int!
    debtorUen: String!
    amount: Float!
    urgencyLevel: String!
    deadline: DateTime!
    status: String!
    createdAt: DateTime!
}

type Query {
    listings(
        urgencyLevel: String
        minAmount: Float
        maxAmount: Float
        status: String = "ACTIVE"
    ): [Listing!]!

    listing(id: Int!): Listing
}
```

**DataLoader:** Use Strawberry's DataLoader to batch database queries. When an investor requests multiple listings, DataLoader collects all IDs and runs a single `SELECT ... WHERE id IN (...)` instead of N separate queries.

### Key Classes

**ListingService:**
- `create_listing(data: ListingCreate) -> Listing`
- `get_listing(listing_id) -> Listing`
- `update_listing(listing_id, data: ListingUpdate) -> Listing` — used for deadline extension and status changes
- `delete_listing(listing_id) -> None`
- `bulk_delete_by_seller(seller_id) -> int` — returns count of deleted listings

### Who Calls This Service

- **Invoice Orchestrator** → `POST /listings`
- **Bidding Orchestrator** → `GET /listings/{id}` (check deadline for anti-snipe), `PATCH /listings/{id}` (extend deadline)
- **Temporal Worker** → `DELETE /listings/{id}` (delist on auction close), `DELETE /listings?seller_id={id}` (bulk delist on default)
- **KONG → Frontend** → GraphQL queries at `/graphql` (investor browsing)

### How to Test

**Tier 1 — Standalone smoke test:**
1. `docker compose up marketplace-service market-db`
2. Open REST Swagger at `http://localhost:5002/docs`
3. `GET /health` → verify ok
4. `POST /listings` with test data → verify listing created
5. `GET /listings/{id}` → verify returned
6. `PATCH /listings/{id}` with `{"deadline": "<future-time>"}` → verify deadline updated
7. `DELETE /listings/{id}` → verify 204

**Tier 1b — GraphQL test:**
1. Open GraphQL Playground at `http://localhost:5002/graphql`
2. Run query: `{ listings(status: "ACTIVE") { id invoiceToken amount urgencyLevel deadline } }`
3. Verify the listing you created appears with correct fields
4. Run query with filters: `{ listings(minAmount: 1000, urgencyLevel: "HIGH") { id amount } }`

### Dependencies

- `fastapi`, `uvicorn`, `sqlalchemy`, `pymysql`, `pydantic`, `strawberry-graphql[fastapi]`

---

## 4. Bidding Service

**Type:** Atomic Service
**Port:** 5003
**Technology:** Python / FastAPI
**Database:** bidding_db (MySQL :3309)
**Owner:** *(assign team member)*

### Purpose

Manages bids (offers) on invoice listings. Handles bid creation, retrieval, and status updates (accepted/rejected). Does NOT handle escrow — that's Payment Service's job via the orchestrator.

### Swagger

- Swagger UI at `http://localhost:5003/docs`
- Tag endpoints: `tags=["Bids"]`, `tags=["Offers"]`

### Project Structure

```
bidding-service/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── bid.py              # SQLAlchemy ORM: Bid
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── bid.py              # Pydantic: BidCreate, BidResponse, BidStatusUpdate
│   ├── routers/
│   │   ├── __init__.py
│   │   └── bids.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── bid_service.py      # BidService class
│   └── database.py
├── Dockerfile
├── requirements.txt
└── .env
```

### Database Schema

```sql
CREATE TABLE bids (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    invoice_token   VARCHAR(36) NOT NULL,
    investor_id     INT NOT NULL,
    bid_amount      DECIMAL(12,2) NOT NULL,               -- the discount rate or amount offered
    status          ENUM('PENDING', 'ACCEPTED', 'REJECTED') DEFAULT 'PENDING',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_bid (invoice_token, investor_id)    -- one bid per investor per invoice
);
```

### API Endpoints

| Method | Path | Request Body | Response | Description |
|--------|------|-------------|----------|-------------|
| GET | `/health` | — | `{"status": "ok", "service": "bidding-service"}` | Health check. |
| POST | `/bids` | `BidCreate` (invoice_token, investor_id, bid_amount) | `BidResponse` + `previous_highest` field | Create bid. If this outbids someone, return the previous highest bidder's info (investor_id, bid_amount) so orchestrator can trigger `bid.outbid`. |
| GET | `/bids?invoice_token={token}` | — | `List[BidResponse]` | Get all bids for an invoice. Used by Temporal Worker at auction close. |
| GET | `/bids/{bid_id}` | — | `BidResponse` | Get single bid. |
| PATCH | `/bids/{bid_id}/accept` | — | `BidResponse` | Mark bid as ACCEPTED. Called by Temporal Worker for the winner. |
| PATCH | `/bids/{bid_id}/reject` | — | `BidResponse` | Mark bid as REJECTED. Called by Temporal Worker for all losers. |

### Key Classes

**BidService:**
- `create_bid(data: BidCreate) -> dict` — insert bid, check if it's the new highest, return `{"bid": Bid, "previous_highest": Bid | None}`. The `previous_highest` field tells the orchestrator who got outbid.
- `get_bids_for_invoice(invoice_token) -> List[Bid]` — ordered by bid_amount DESC
- `get_bid(bid_id) -> Bid`
- `accept_bid(bid_id) -> Bid`
- `reject_bid(bid_id) -> Bid`

### Important Logic

The `create_bid` method must:
1. Check if a bid already exists for this investor + invoice (upsert or reject)
2. Find the current highest bid for this invoice
3. Insert the new bid
4. If the new bid is higher than the previous highest, return the previous highest bidder's info in the response — the orchestrator needs this to publish `bid.outbid`

**Rollback on escrow failure:** The Bidding Orchestrator calls `POST /bids` first, then locks escrow via gRPC. If the escrow lock fails (e.g., insufficient wallet balance), the orchestrator must call `DELETE /bids/{id}` (or a cancel endpoint) to remove the orphaned bid. Add a `DELETE /bids/{bid_id}` endpoint for this rollback scenario, or include a `PATCH /bids/{bid_id}/cancel` endpoint that sets status to `CANCELLED`.

### Who Calls This Service

- **Bidding Orchestrator** → `POST /bids`, `GET /bids/{id}`
- **Temporal Worker** → `GET /bids?invoice_token={token}`, `PATCH /bids/{id}/accept`, `PATCH /bids/{id}/reject`

### How to Test

**Tier 1 — Standalone smoke test:**
1. `docker compose up bidding-service bidding-db`
2. Open `http://localhost:5003/docs` (Swagger UI)
3. `GET /health` → verify ok
4. `POST /bids` with `{"invoice_token": "test-token-1", "investor_id": 1, "bid_amount": 1000}` → verify bid created, `previous_highest` is null
5. `POST /bids` with `{"invoice_token": "test-token-1", "investor_id": 2, "bid_amount": 1500}` → verify bid created, `previous_highest` returns investor 1's info
6. `GET /bids?invoice_token=test-token-1` → verify both bids returned, ordered by amount DESC
7. `PATCH /bids/{id}/accept` → verify status changed to ACCEPTED
8. `PATCH /bids/{id}/reject` → verify status changed to REJECTED

### Dependencies

- `fastapi`, `uvicorn`, `sqlalchemy`, `pymysql`, `pydantic`

---

## 5. Payment Service

**Type:** Atomic Service
**Port:** 5004 (REST) / 50051 (gRPC)
**Technology:** Node.js / Express + gRPC (BTL #2)
**Database:** payment_db (MySQL :3310)
**Owner:** Ihsan

### Purpose

Handles all financial operations: wallets, escrow, loans, fund transfers. Exposes gRPC for all financial operations (fast, binary, idempotent) and REST for simple reads. Also a RabbitMQ consumer for `bid.outbid`, `loan.repaid`, and `loan.overdue` events.

### Swagger / Documentation

- REST Swagger: Use `swagger-ui-express` + `swagger-jsdoc` at `http://localhost:5004/docs`
- gRPC: Document via `.proto` file — the proto file IS the documentation. Share it with the team.
- Use **idempotency keys** on all gRPC write operations — if Temporal retries a call, the same key prevents double-execution

### Project Structure

```
payment-service/
├── src/
│   ├── index.js                # Express + gRPC server startup
│   ├── config.js               # Environment variables
│   ├── models/
│   │   ├── Wallet.js           # Sequelize model
│   │   ├── Escrow.js           # Sequelize model
│   │   └── Loan.js             # Sequelize model
│   ├── services/
│   │   ├── WalletService.js    # WalletService class
│   │   ├── EscrowService.js    # EscrowService class
│   │   └── LoanService.js      # LoanService class
│   ├── grpc/
│   │   ├── server.js           # gRPC server setup
│   │   └── handlers.js         # gRPC method implementations
│   ├── rest/
│   │   ├── routes.js           # Express routes (read endpoints)
│   │   └── swagger.js          # Swagger config
│   ├── consumers/
│   │   └── eventConsumer.js    # RabbitMQ consumer: bid.outbid, loan.repaid, loan.overdue
│   └── database.js             # Sequelize connection
├── proto/
│   └── payment.proto           # gRPC service definition
├── Dockerfile
├── package.json
└── .env
```

### Database Schema

```sql
CREATE TABLE wallets (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNIQUE NOT NULL,
    balance         DECIMAL(12,2) DEFAULT 0.00,
    currency        VARCHAR(3) DEFAULT 'SGD',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE escrows (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    investor_id     INT NOT NULL,
    invoice_token   VARCHAR(36) NOT NULL,
    amount          DECIMAL(12,2) NOT NULL,
    status          ENUM('LOCKED', 'CONVERTED', 'RELEASED') DEFAULT 'LOCKED',
    idempotency_key VARCHAR(100) UNIQUE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_escrow (investor_id, invoice_token)
);

CREATE TABLE loans (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    loan_id         VARCHAR(36) UNIQUE NOT NULL,          -- UUID
    invoice_token   VARCHAR(36) NOT NULL,
    investor_id     INT NOT NULL,
    seller_id       INT NOT NULL,
    principal       DECIMAL(12,2) NOT NULL,
    penalty_amount  DECIMAL(12,2) DEFAULT 0.00,
    status          ENUM('ACTIVE', 'DUE', 'REPAID', 'OVERDUE') DEFAULT 'ACTIVE',
    due_date        DATE NOT NULL,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### gRPC Service Definition (proto/payment.proto)

```protobuf
syntax = "proto3";
package payment;

service PaymentService {
    rpc LockEscrow (LockEscrowRequest) returns (EscrowResponse);
    rpc ReleaseEscrow (ReleaseEscrowRequest) returns (EscrowResponse);
    rpc ConvertEscrowToLoan (ConvertEscrowRequest) returns (EscrowResponse);
    rpc CreateLoan (CreateLoanRequest) returns (LoanResponse);
    rpc ReleaseFundsToSeller (ReleaseFundsRequest) returns (TransferResponse);
    rpc CreditWallet (CreditWalletRequest) returns (WalletResponse);
    rpc GetLoan (GetLoanRequest) returns (LoanResponse);
    rpc UpdateLoanStatus (UpdateLoanStatusRequest) returns (LoanResponse);
}

message LockEscrowRequest {
    int32 investor_id = 1;
    string invoice_token = 2;
    string amount = 3;                    // string to avoid float precision issues
    string idempotency_key = 4;           // CRITICAL: prevents double-locking on retries
}

message ReleaseEscrowRequest {
    int32 investor_id = 1;
    string invoice_token = 2;
    string idempotency_key = 3;
}

message ConvertEscrowRequest {
    int32 investor_id = 1;
    string invoice_token = 2;
    string idempotency_key = 3;
}

message CreateLoanRequest {
    string invoice_token = 1;
    int32 investor_id = 2;
    int32 seller_id = 3;
    string principal = 4;
    string due_date = 5;                  // ISO 8601 format
    string idempotency_key = 6;
}

message ReleaseFundsRequest {
    int32 seller_id = 1;
    string amount = 2;
    string invoice_token = 3;
    string idempotency_key = 4;
}

message CreditWalletRequest {
    int32 user_id = 1;
    string amount = 2;
    string idempotency_key = 3;
}

message GetLoanRequest {
    string loan_id = 1;
}

message UpdateLoanStatusRequest {
    string loan_id = 1;
    string status = 2;                    // DUE, REPAID, OVERDUE
}

message EscrowResponse { string id = 1; string status = 2; string amount = 3; }
message LoanResponse { string loan_id = 1; string status = 2; string principal = 3; string due_date = 4; int32 investor_id = 5; int32 seller_id = 6; }
message TransferResponse { bool success = 1; string message = 2; }
message WalletResponse { int32 user_id = 1; string balance = 2; }
```

### REST Endpoints (read-only + health, for frontend/debugging)

| Method | Path | Response | Description |
|--------|------|----------|-------------|
| GET | `/health` | `{"status": "ok", "service": "payment-service"}` | Health check. |
| GET | `/wallets/{user_id}` | `WalletResponse` | Get wallet balance. |
| GET | `/loans/{loan_id}` | `LoanResponse` | Get loan details. |
| GET | `/loans?investor_id={id}` | `List[LoanResponse]` | Get loans by investor. |
| GET | `/escrows?investor_id={id}` | `List[EscrowResponse]` | Get active escrows. |

### Key Classes

**WalletService:**
- `creditWallet(userId, amount, idempotencyKey)` — add funds (used for Stripe top-up and escrow release)
- `debitWallet(userId, amount)` — deduct funds (used when locking escrow)
- `getBalance(userId) -> Wallet`

**EscrowService:**
- `lockEscrow(investorId, invoiceToken, amount, idempotencyKey)` — debit wallet, create escrow record
- `releaseEscrow(investorId, invoiceToken, idempotencyKey)` — return funds to wallet, mark RELEASED
- `convertToLoan(investorId, invoiceToken, idempotencyKey)` — mark escrow CONVERTED (funds stay in system)

**LoanService:**
- `createLoan(data, idempotencyKey) -> Loan`
- `getLoan(loanId) -> Loan`
- `updateStatus(loanId, status) -> Loan`
- `releaseFundsToSeller(sellerId, amount, idempotencyKey)` — credit seller wallet
- `calculatePenalty(loanId) -> Decimal` — 5% of principal

### RabbitMQ Consumer

- `bid.outbid` (queue: `payment_outbid_updates`) → call `EscrowService.releaseEscrow(previousInvestorId, invoiceToken)` — release outbid investor's escrow immediately
- `loan.repaid` (queue: `payment_repaid_updates`) → call `WalletService.creditWallet(investorId, principal)` — credit investor wallet with repaid principal
- `loan.overdue` (queue: `payment_loan_updates`) → call `LoanService.calculatePenalty(loanId)` — apply 5% penalty to loan record

### Who Calls This Service

- **Bidding Orchestrator** → gRPC `LockEscrow`
- **Temporal Worker** → gRPC `ConvertEscrowToLoan`, `CreateLoan`, `ReleaseFundsToSeller`, `GetLoan`, `UpdateLoanStatus`
- **Loan Orchestrator** → gRPC `UpdateLoanStatus`, `GetLoan`
- **RabbitMQ** → `bid.outbid`, `loan.repaid`, `loan.overdue` (choreography)
- **KONG → Frontend** → REST read endpoints

### How to Test

**Tier 1 — Standalone smoke test:**
1. `docker compose up payment-service payment-db`
2. REST Swagger: Open `http://localhost:5004/docs`
3. `GET /health` → verify ok
4. `GET /wallets/1` → verify returns wallet (or 404 if no wallet yet)

**Tier 1b — gRPC test:**
1. Install `grpcurl`: `brew install grpcurl` (macOS) or download from GitHub
2. List available services: `grpcurl -plaintext localhost:50051 list`
3. Test `CreditWallet`: `grpcurl -plaintext -d '{"user_id": 1, "amount": "1000.00", "idempotency_key": "test-credit-1"}' localhost:50051 payment.PaymentService/CreditWallet`
4. Test `LockEscrow`: `grpcurl -plaintext -d '{"investor_id": 1, "invoice_token": "test-token", "amount": "500.00", "idempotency_key": "test-escrow-1"}' localhost:50051 payment.PaymentService/LockEscrow`
5. Verify wallet balance decreased via REST: `GET /wallets/1`
6. Test idempotency: repeat the same `LockEscrow` call with the same key → should return same result without deducting again

**Tier 2 — Integration test with RabbitMQ:**
1. `docker compose up payment-service payment-db rabbitmq`
2. Lock escrow for investor 1 on token "test-token" via gRPC
3. Publish `bid.outbid` message via RabbitMQ Management UI with payload `{"invoice_token": "test-token", "outbid_investor_id": 1}`
4. `GET /wallets/1` → verify escrow was released (balance restored)

### Dependencies

- `express`, `@grpc/grpc-js`, `@grpc/proto-loader`, `sequelize`, `mysql2`, `amqplib`, `swagger-ui-express`, `swagger-jsdoc`, `uuid`

---

## 6. Notification Service

**Type:** Atomic Service
**Port:** 5005
**Technology:** Python / FastAPI
**Database:** None
**Owner:** *(assign team member)*

### Purpose

Pure RabbitMQ consumer that listens for all events and sends notifications via email (Resend) and real-time WebSocket push to the frontend. Also exposes a REST endpoint for the frontend to fetch notification history (stored in-memory or optional lightweight storage).

### Swagger

- Swagger UI at `http://localhost:5005/docs`
- Tag endpoints: `tags=["Notifications"]`

### Project Structure

```
notification-service/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app + RabbitMQ consumer + WebSocket endpoint
│   ├── config.py               # RESEND_API_KEY, RABBITMQ_URL, etc.
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── notification.py     # Pydantic: NotificationResponse
│   ├── routers/
│   │   ├── __init__.py
│   │   └── notifications.py    # GET /notifications (read endpoint for frontend)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── email_service.py    # EmailService class — Resend integration
│   │   ├── websocket_manager.py # WebSocketManager class — manages active connections
│   │   └── notification_handler.py # NotificationHandler class — routes events to email/WS
│   ├── consumers/
│   │   ├── __init__.py
│   │   └── event_consumer.py   # RabbitMQ consumer: subscribes to all events
│   └── templates/
│       ├── invoice_listed.html
│       ├── bid_placed.html
│       ├── auction_winner.html
│       ├── loan_due.html
│       └── ...                 # email templates
├── Dockerfile
├── requirements.txt
└── .env
```

### RabbitMQ Subscription

Subscribe to **all events** using a dedicated queue with `#` wildcard routing key bound to the `invoiceflow_events` topic exchange. Every event published by any service reaches this consumer.

### Events → Actions Mapping

| Event | Email To | Email Content | WebSocket Push |
|-------|----------|---------------|----------------|
| invoice.listed | Seller | "Your invoice is now listed" | Seller |
| invoice.rejected | Seller | "Invoice rejected — invalid debtor UEN" | Seller |
| bid.placed | Seller | "New bid received on your invoice" | Seller |
| bid.outbid | Previous highest bidder | "You've been outbid" | Previous bidder |
| auction.extended | All bidders on this invoice | "Auction deadline extended by 5 min" | All bidders |
| auction.closing.warning | All bidders + seller | "Auction closing in X hours" | All bidders + seller |
| auction.closed.winner | Winner + seller | "You won the auction" / "Your invoice has been financed" | Winner + seller |
| auction.closed.loser | Each loser | "Auction ended — you did not win" | Each loser |
| auction.expired | Seller | "Auction ended with no bids" | Seller |
| wallet.credited | Investor | "Wallet top-up confirmed" | Investor |
| loan.due | Seller (borrower) | "Your loan is due — please repay" | Seller |
| loan.repaid | Seller + investor | "Loan repaid successfully" | Both |
| loan.overdue | Seller + investor | "Loan overdue — penalty applied" | Both |

### Key Classes

**EmailService:**
- `send_email(to, subject, html_body)` — calls Resend API
- Uses HTML templates from `/templates/` with variable substitution

**WebSocketManager:**
- `connect(user_id, websocket)` — register active connection
- `disconnect(user_id)` — remove connection
- `send_to_user(user_id, message)` — push JSON message to specific user
- `broadcast_to_users(user_ids, message)` — push to multiple users

**NotificationHandler:**
- `handle_event(event_type, payload)` — routes to appropriate email template + WebSocket push based on the event type mapping above

### REST Endpoint

| Method | Path | Response | Description |
|--------|------|----------|-------------|
| GET | `/health` | `{"status": "ok", "service": "notification-service"}` | Health check. |
| GET | `/notifications?user_id={id}` | `List[NotificationResponse]` | Fetch recent notifications for a user (from in-memory store). |

### WebSocket Endpoint

- `ws://localhost:5005/ws/{user_id}` — frontend connects here on login, receives real-time pushes
- **Note:** WebSocket connections should bypass KONG (KONG's HTTP/1.1 proxy does not natively handle WebSocket upgrade). The frontend connects directly to the Notification Service or KONG must be configured with the `websocket` protocol on the route.

### Who Calls This Service

- **KONG → Frontend** → `GET /notifications` (REST), `ws://` (WebSocket) — these bypass composites
- **RabbitMQ** → all events (consumer)
- **No composite service calls this directly** — architectural rule #3

### How to Test

**Tier 1 — Standalone smoke test:**
1. `docker compose up notification-service`
2. Open `http://localhost:5005/docs` (Swagger UI)
3. `GET /health` → verify ok

**Tier 1b — WebSocket test:**
1. Open browser DevTools Console and run:
   ```javascript
   const ws = new WebSocket("ws://localhost:5005/ws/1");
   ws.onmessage = (e) => console.log("Received:", JSON.parse(e.data));
   ws.onopen = () => console.log("Connected");
   ```
2. Verify "Connected" appears in console

**Tier 2 — Integration test with RabbitMQ:**
1. `docker compose up notification-service rabbitmq`
2. Keep the WebSocket connection open from Tier 1b
3. Publish a test message via RabbitMQ Management UI (`http://localhost:15672`) to `invoiceflow_events` exchange, routing key `bid.placed`, payload `{"invoice_token": "test", "investor_id": 1, "seller_id": 2, "bid_amount": 1000}`
4. Verify the WebSocket received a notification in the browser console
5. Check Resend dashboard (or logs) to verify email was attempted (will fail without valid Resend API key — that's ok, verify the attempt was made in service logs)

### Dependencies

- `fastapi`, `uvicorn`, `pydantic`, `aio-pika`, `websockets`, `resend`, `jinja2`

---

## 7. OutSystems Activity Log

**Type:** OutSystems Application (replaces previous Python-based Activity Log Service)
**Technology:** OutSystems Platform
**Database:** OutSystems internal DB (managed by platform)
**Owner:** *(assign team member)*

### Purpose

Consumes ALL RabbitMQ events and stores them as an audit trail. Built entirely in OutSystems as a low-code application. Provides a UI for viewing/filtering event logs.

### How It Works

1. **RabbitMQ Consumer:** OutSystems listens on a dedicated queue bound to `#` wildcard on the `invoiceflow_events` topic exchange — receives every event.
2. **Event Storage:** Each event is stored as a record in an OutSystems Entity (table) with timestamp, event type, payload, and source service.
3. **Log Viewer UI:** OutSystems provides a built-in web UI where team members can browse, filter, and search the activity log.

### OutSystems Entity (Data Model)

| Attribute | Type | Description |
|-----------|------|-------------|
| Id | Long Integer (auto) | Primary key |
| EventType | Text(100) | e.g., `invoice.listed`, `bid.placed`, `loan.overdue` |
| Payload | Text(5000) | JSON string of the full event payload |
| SourceService | Text(100) | Which service published the event |
| InvoiceToken | Text(36) | Extracted from payload for easy filtering |
| UserId | Integer | Extracted from payload for easy filtering |
| Timestamp | DateTime | When the event was received |
| Severity | Text(20) | INFO, WARNING, ERROR |

### RabbitMQ Integration

OutSystems can consume from RabbitMQ using:
- **OutSystems REST Consume** — if you expose a simple REST relay that forwards RabbitMQ messages
- **OutSystems Custom Connector** — direct AMQP integration via a C# extension
- **Webhook relay pattern** — a lightweight Python bridge subscribes to RabbitMQ, then POSTs each event to an OutSystems REST endpoint

The simplest approach for the team: create a tiny Python bridge (10-15 lines) that consumes from RabbitMQ and POSTs to an OutSystems exposed REST API.

### OutSystems REST API (exposed by OutSystems)

| Method | Path | Request Body | Description |
|--------|------|-------------|-------------|
| POST | `/api/activity-log/events` | `{ event_type, payload, source_service, timestamp }` | Receive and store an event |
| GET | `/api/activity-log/events?event_type={type}&invoice_token={token}` | — | Query events with filters |

### Build Steps

1. Create a new OutSystems Reactive Web App called "ActivityLog"
2. Create the Entity (table) with the schema above
3. Expose a REST API (`POST /events`) that accepts event data and creates a record
4. Build a screen with a table/list that queries the Entity, with filters for EventType, InvoiceToken, date range
5. Deploy and test by manually POSTing sample events
6. Connect via the Python RabbitMQ bridge (or direct connector)

---

## 8. Invoice Orchestrator

**Type:** Composite Service
**Port:** 5010
**Technology:** Python / FastAPI
**Owner:** *(assign team member)*

### Purpose

Orchestrates Scenario 1: invoice creation, debtor UEN validation, marketplace listing, and starting the AuctionCloseWorkflow. Calls atomic services via direct HTTP and publishes events to RabbitMQ.

### Swagger

- Swagger UI at `http://localhost:5010/docs`
- Tag endpoints: `tags=["Invoice Workflow"]`
- Use descriptive summaries so Swagger shows what each endpoint does at a glance

### Project Structure

```
invoice-orchestrator/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py               # Service URLs: USER_SERVICE_URL, INVOICE_SERVICE_URL, etc.
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── requests.py         # Pydantic: ListInvoiceRequest, ListInvoiceResponse
│   ├── routers/
│   │   ├── __init__.py
│   │   └── invoices.py         # POST /api/invoices
│   ├── services/
│   │   ├── __init__.py
│   │   ├── orchestrator.py     # InvoiceOrchestrator class — the main orchestration logic
│   │   ├── http_client.py      # HTTPClient class — reusable async HTTP client with error handling
│   │   └── rabbitmq_publisher.py # RabbitMQPublisher class — publish events
│   └── temporal/
│       ├── __init__.py
│       └── client.py           # TemporalClient class — start workflows
├── Dockerfile
├── requirements.txt
└── .env
```

### API Endpoint

| Method | Path | Request Body | Response | Description |
|--------|------|-------------|----------|-------------|
| POST | `/api/invoices` | `multipart/form-data` (PDF file + seller_id, debtor_uen, amount, due_date, bid_period_hours) | `ListInvoiceResponse` | Full Scenario 1 orchestration. |

### Orchestration Flow (what `InvoiceOrchestrator.list_invoice()` does)

This is the complete step-by-step logic. Implement each step as a method call:

```python
class InvoiceOrchestrator:
    async def list_invoice(self, data, pdf_file) -> ListInvoiceResponse:
        # Step 1: Check seller account is ACTIVE
        user = await self.http_client.get(f"{USER_SERVICE_URL}/users/{data.seller_id}")
        if user["account_status"] != "ACTIVE":
            raise HTTPException(403, "Account is defaulted")

        # Step 2: Create invoice + upload PDF
        invoice = await self.http_client.post(
            f"{INVOICE_SERVICE_URL}/invoices",
            files={"pdf": pdf_file}, data={...}
        )

        # Step 3: Validate debtor UEN via ACRA Wrapper
        uen_result = await self.http_client.post(
            f"{ACRA_WRAPPER_URL}/validate-uen",
            json={"uen": data.debtor_uen}
        )

        # Step 4: If UEN invalid → reject
        if not uen_result["valid"]:
            await self.http_client.patch(
                f"{INVOICE_SERVICE_URL}/invoices/{invoice['invoice_token']}/status",
                json={"status": "REJECTED"}
            )
            await self.publisher.publish("invoice.rejected", {...})
            raise HTTPException(400, "Invalid debtor UEN")

        # Step 5: Create marketplace listing
        listing = await self.http_client.post(
            f"{MARKETPLACE_SERVICE_URL}/listings",
            json={
                "invoice_token": invoice["invoice_token"],
                "seller_id": data.seller_id,
                "debtor_uen": data.debtor_uen,
                "amount": data.amount,
                "urgency_level": calculate_urgency(invoice["due_date"]),
                "deadline": calculate_deadline(data.bid_period_hours),
            }
        )

        # Step 6: Update invoice status to LISTED
        await self.http_client.patch(
            f"{INVOICE_SERVICE_URL}/invoices/{invoice['invoice_token']}/status",
            json={"status": "LISTED"}
        )

        # Step 7: Start AuctionCloseWorkflow via Temporal
        await self.temporal_client.start_workflow(
            "AuctionCloseWorkflow",
            workflow_id=f"auction-{invoice['invoice_token']}",
            args={"invoice_token": invoice["invoice_token"], "bid_period_hours": data.bid_period_hours},
            task_queue="invoiceflow-queue",
        )

        # Step 8: Publish success event
        await self.publisher.publish("invoice.listed", {
            "invoice_token": invoice["invoice_token"],
            "seller_id": data.seller_id,
        })

        return ListInvoiceResponse(...)
```

### Key Classes

**InvoiceOrchestrator** — as shown above, the main orchestration logic.

**HTTPClient** — reusable HTTP client with error handling:
- `get(url) -> dict`
- `post(url, json?, files?, data?) -> dict`
- `patch(url, json) -> dict`
- All methods should handle errors, timeouts, and log failures:

```python
class HTTPClient:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=5.0)

    async def get(self, url: str) -> dict:
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(504, f"Timeout calling {url}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)

    async def post(self, url: str, **kwargs) -> dict:
        try:
            response = await self.client.post(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(504, f"Timeout calling {url}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)

    async def patch(self, url: str, **kwargs) -> dict:
        try:
            response = await self.client.patch(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(504, f"Timeout calling {url}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)
```

**RabbitMQPublisher:**
- `publish(routing_key, payload)` — publish to `invoiceflow_events` topic exchange

**TemporalClient:**
- `start_workflow(workflow_name, workflow_id, args, task_queue)` — start a Temporal workflow

### Environment Variables

```env
USER_SERVICE_URL=http://user-service:5000
INVOICE_SERVICE_URL=http://invoice-service:5001
MARKETPLACE_SERVICE_URL=http://marketplace-service:5002
ACRA_WRAPPER_URL=http://acra-wrapper:5007
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672
TEMPORAL_HOST=temporal:7233
```

### Who Calls This Service

- **KONG** → `POST /api/invoices` (from frontend)

### How to Test

**Tier 1 — Smoke test (requires downstream atomics running):**
1. `docker compose up invoice-orchestrator user-service invoice-service marketplace-service acra-wrapper user-db invoice-db market-db minio rabbitmq temporal`
2. Open `http://localhost:5010/docs` (Swagger UI)
3. `POST /api/invoices` with a test PDF, valid seller_id, debtor_uen, amount, due_date, bid_period_hours
4. Verify:
   - Invoice created in Invoice Service (`http://localhost:5001/docs` → GET /invoices/{token})
   - Listing created in Marketplace Service (`http://localhost:5002/docs` → GET /listings)
   - PDF stored in MinIO Console (`http://localhost:9001`)
   - `invoice.listed` event published (check RabbitMQ Management UI → queues)
   - AuctionCloseWorkflow running in Temporal UI (`http://localhost:8088`)

**Error case tests:**
- Use a DEFAULTED seller_id → verify 403 rejection
- Use an invalid debtor UEN → verify 400 + `invoice.rejected` event published + invoice status set to REJECTED

### Dependencies

- `fastapi`, `uvicorn`, `pydantic`, `httpx`, `aio-pika`, `temporalio`

---

## 9. Bidding Orchestrator

**Type:** Composite Service
**Port:** 5011
**Technology:** Python / FastAPI
**Owner:** Ihsan

### Purpose

Orchestrates Scenario 2: bid placement with escrow locking, outbid handling, anti-snipe deadline extension, wallet top-up via Stripe, and Stripe webhook processing. This is the most complex orchestrator.

### Swagger

- Swagger UI at `http://localhost:5011/docs`
- Tag endpoints: `tags=["Bidding"]`, `tags=["Wallet"]`, `tags=["Webhook"]`

### Project Structure

```
bidding-orchestrator/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── requests.py         # Pydantic: PlaceBidRequest, TopUpRequest, etc.
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── bids.py             # POST /api/bids
│   │   ├── wallet.py           # POST /api/wallet/topup
│   │   └── webhooks.py         # POST /api/webhooks/stripe
│   ├── services/
│   │   ├── __init__.py
│   │   ├── bid_orchestrator.py     # BidOrchestrator class
│   │   ├── wallet_orchestrator.py  # WalletOrchestrator class
│   │   ├── grpc_client.py          # PaymentGRPCClient class — gRPC calls to Payment Service
│   │   ├── http_client.py          # HTTPClient class
│   │   └── rabbitmq_publisher.py
│   └── temporal/
│       ├── __init__.py
│       └── client.py
├── Dockerfile
├── requirements.txt
└── .env
```

### API Endpoints

| Method | Path | Request Body | Response | Description |
|--------|------|-------------|----------|-------------|
| POST | `/api/bids` | `PlaceBidRequest` (invoice_token, investor_id, bid_amount) | `BidResponse` | Place bid, lock escrow, handle outbid, check anti-snipe. |
| POST | `/api/wallet/topup` | `TopUpRequest` (investor_id, amount) | `{ checkout_url }` | Create Stripe checkout session for wallet top-up. |
| POST | `/api/webhooks/stripe` | Raw body (Stripe webhook payload) | `200 OK` | Handle Stripe webhook → start WalletTopUpWorkflow. |

### Orchestration Flows

**`BidOrchestrator.place_bid()`:**

```python
class BidOrchestrator:
    async def place_bid(self, data: PlaceBidRequest):
        # Step 1: Create bid in Bidding Service
        result = await self.http_client.post(
            f"{BIDDING_SERVICE_URL}/bids",
            json={"invoice_token": data.invoice_token, "investor_id": data.investor_id, "bid_amount": data.bid_amount}
        )
        bid = result["bid"]
        previous_highest = result.get("previous_highest")

        # Step 2: Lock escrow via gRPC — rollback bid if this fails
        try:
            await self.grpc_client.lock_escrow(
                investor_id=data.investor_id,
                invoice_token=data.invoice_token,
                amount=data.bid_amount,
                idempotency_key=f"escrow-{bid['id']}"
            )
        except Exception as e:
            # Rollback: delete the orphaned bid
            await self.http_client.delete(f"{BIDDING_SERVICE_URL}/bids/{bid['id']}")
            raise HTTPException(400, f"Escrow lock failed: {str(e)}")

        # Step 3: If someone was outbid → publish bid.outbid (choreography releases their escrow)
        if previous_highest:
            await self.publisher.publish("bid.outbid", {
                "invoice_token": data.invoice_token,
                "outbid_investor_id": previous_highest["investor_id"],
                "outbid_amount": previous_highest["bid_amount"],
                "new_highest_investor_id": data.investor_id,
                "new_highest_amount": data.bid_amount,
            })

        # Step 4: Check anti-snipe — is auction within final 5 minutes?
        listing = await self.http_client.get(
            f"{MARKETPLACE_SERVICE_URL}/listings/{data.listing_id}"
        )
        time_remaining = listing["deadline"] - datetime.utcnow()
        if time_remaining <= timedelta(minutes=5):
            # Signal Temporal to extend deadline
            await self.temporal_client.signal_workflow(
                workflow_id=f"auction-{data.invoice_token}",
                signal_name="extend_deadline",
            )
            # Update listing deadline in Marketplace
            new_deadline = datetime.utcnow() + timedelta(minutes=5)
            await self.http_client.patch(
                f"{MARKETPLACE_SERVICE_URL}/listings/{data.listing_id}",
                json={"deadline": new_deadline.isoformat()}
            )
            await self.publisher.publish("auction.extended", {
                "invoice_token": data.invoice_token,
                "new_deadline": new_deadline.isoformat(),
            })

        # Step 5: Publish bid.placed
        await self.publisher.publish("bid.placed", {
            "invoice_token": data.invoice_token,
            "investor_id": data.investor_id,
            "bid_amount": data.bid_amount,
        })

        return bid
```

**`WalletOrchestrator.create_topup()`:**

```python
class WalletOrchestrator:
    async def create_topup(self, data: TopUpRequest):
        # Create Stripe checkout session via Stripe Wrapper
        session = await self.http_client.post(
            f"{STRIPE_WRAPPER_URL}/create-checkout-session",
            json={"amount": data.amount, "user_id": data.investor_id, "type": "wallet_topup"}
        )
        return {"checkout_url": session["url"]}
```

**Stripe Webhook Handler:**

```python
async def handle_stripe_webhook(request: Request):
    # Step 1: Verify Stripe signature
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    # Verify signature using Stripe shared secret — reject if invalid or >5min old

    # Step 2: Parse event
    event = json.loads(payload)
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        if session["metadata"]["type"] == "wallet_topup":
            # Step 3: Start WalletTopUpWorkflow
            await temporal_client.start_workflow(
                "WalletTopUpWorkflow",
                workflow_id=f"wallet-topup-{session['id']}",  # idempotent
                args={"user_id": session["metadata"]["user_id"], "amount": session["amount_total"]},
                task_queue="invoiceflow-queue",
            )
    return {"status": "ok"}
```

### Key Classes

**PaymentGRPCClient** — wraps gRPC calls:
- `lock_escrow(investor_id, invoice_token, amount, idempotency_key)`
- Uses `grpcio` to call Payment Service at `:50051`
- Load `payment.proto` and generate stubs

### Environment Variables

```env
BIDDING_SERVICE_URL=http://bidding-service:5003
MARKETPLACE_SERVICE_URL=http://marketplace-service:5002
STRIPE_WRAPPER_URL=http://stripe-wrapper:5008
PAYMENT_SERVICE_GRPC=payment-service:50051
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672
TEMPORAL_HOST=temporal:7233
STRIPE_WEBHOOK_SECRET=whsec_...
```

### Who Calls This Service

- **KONG** → `POST /api/bids`, `POST /api/wallet/topup` (from frontend)
- **KONG** → `POST /api/webhooks/stripe` (from Stripe)

### How to Test

**Tier 1 — Bid placement (requires downstream services):**
1. `docker compose up bidding-orchestrator bidding-service marketplace-service payment-service bidding-db market-db payment-db rabbitmq temporal`
2. Open `http://localhost:5011/docs` (Swagger UI)
3. Ensure an investor has wallet balance (credit via gRPC or seed data)
4. Ensure a listing exists in Marketplace Service
5. `POST /api/bids` with `{"invoice_token": "...", "investor_id": 1, "bid_amount": 500}` → verify bid created + escrow locked
6. `POST /api/bids` with a higher amount from investor 2 → verify `bid.outbid` event published, investor 1's escrow released
7. Check RabbitMQ Management UI → verify `bid.placed` and `bid.outbid` events in queues

**Tier 1b — Wallet top-up:**
1. Also start: `stripe-wrapper`
2. `POST /api/wallet/topup` with `{"investor_id": 1, "amount": 1000}` → verify Stripe checkout URL returned
3. For webhook testing: use Stripe CLI `stripe listen --forward-to localhost:8000/api/webhooks/stripe` to forward test webhooks

**Error case tests:**
- Bid with insufficient wallet balance → verify 400 + bid rolled back (deleted from Bidding Service)
- Duplicate Stripe webhook → verify idempotent (WalletTopUpWorkflow not created twice — check Temporal UI)

### Dependencies

- `fastapi`, `uvicorn`, `pydantic`, `httpx`, `aio-pika`, `temporalio`, `grpcio`, `grpcio-tools`

---

## 10. Loan Orchestrator

**Type:** Composite Service
**Port:** 5012
**Technology:** Python / FastAPI
**Owner:** *(assign team member)*

### Purpose

Orchestrates Scenario 3 repayment flow: business initiates loan repayment via Stripe, and on success, publishes `loan.repaid` which triggers the four-consumer choreography (Invoice Service, Payment Service, User Service, Notification Service). Does NOT start any Temporal workflow — LoanMaturityWorkflow is started by Temporal Worker as a child of AuctionCloseWorkflow.

### Swagger

- Swagger UI at `http://localhost:5012/docs`
- Tag endpoints: `tags=["Loans"]`, `tags=["Repayment"]`

### Project Structure

```
loan-orchestrator/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── requests.py         # Pydantic: RepayLoanRequest, RepaymentResponse
│   ├── routers/
│   │   ├── __init__.py
│   │   └── loans.py            # POST /api/loans/{loan_id}/repay
│   ├── services/
│   │   ├── __init__.py
│   │   ├── loan_orchestrator.py    # LoanOrchestrator class
│   │   ├── grpc_client.py          # PaymentGRPCClient class
│   │   ├── http_client.py
│   │   └── rabbitmq_publisher.py
├── Dockerfile
├── requirements.txt
└── .env
```

### API Endpoints

| Method | Path | Request Body | Response | Description |
|--------|------|-------------|----------|-------------|
| POST | `/api/loans/{loan_id}/repay` | `RepayLoanRequest` (seller_id) | `{ checkout_url }` | Create Stripe checkout for loan repayment. |
| POST | `/api/loans/{loan_id}/confirm-repayment` | `{ stripe_session_id }` | `RepaymentResponse` | Called after Stripe payment confirmed. Updates loan status and publishes loan.repaid. |

### Orchestration Flow

**`LoanOrchestrator.initiate_repayment()`:**

```python
class LoanOrchestrator:
    async def initiate_repayment(self, loan_id, data: RepayLoanRequest):
        # Step 1: Get loan details
        loan = await self.grpc_client.get_loan(loan_id)
        if loan["status"] != "DUE":
            raise HTTPException(400, "Loan is not due for repayment")

        # Step 2: Create Stripe checkout session via Stripe Wrapper
        session = await self.http_client.post(
            f"{STRIPE_WRAPPER_URL}/create-checkout-session",
            json={
                "amount": float(loan["principal"]),
                "user_id": data.seller_id,
                "type": "loan_repayment",
                "loan_id": loan_id,
            }
        )
        return {"checkout_url": session["url"]}

    async def confirm_repayment(self, loan_id, stripe_session_id):
        # Step 1: Update loan status to REPAID via gRPC
        await self.grpc_client.update_loan_status(loan_id, "REPAID")

        # Step 2: Publish loan.repaid → four consumers react via choreography
        loan = await self.grpc_client.get_loan(loan_id)
        await self.publisher.publish("loan.repaid", {
            "loan_id": loan_id,
            "invoice_token": loan["invoice_token"],
            "investor_id": loan["investor_id"],
            "seller_id": loan["seller_id"],
            "principal": loan["principal"],
        })

        return RepaymentResponse(status="REPAID", loan_id=loan_id)
```

### Environment Variables

```env
PAYMENT_SERVICE_GRPC=payment-service:50051
STRIPE_WRAPPER_URL=http://stripe-wrapper:5008
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672
```

Note: Loan Orchestrator does NOT call User Service directly. Account status updates (ACTIVE/DEFAULTED) are handled by User Service consuming `loan.repaid` / `loan.overdue` events via RabbitMQ choreography.

### Who Calls This Service

- **KONG** → `POST /api/loans/{id}/repay`, `POST /api/loans/{id}/confirm-repayment` (from frontend)

### How to Test

**Tier 1 — Repayment flow (requires downstream services):**
1. `docker compose up loan-orchestrator payment-service stripe-wrapper payment-db rabbitmq`
2. Open `http://localhost:5012/docs` (Swagger UI)
3. Seed a loan in Payment Service with status DUE (via gRPC or direct DB insert)
4. `POST /api/loans/{loan_id}/repay` with `{"seller_id": 1}` → verify Stripe checkout URL returned
5. After simulating Stripe payment, call `POST /api/loans/{loan_id}/confirm-repayment` with `{"stripe_session_id": "cs_test_..."}` → verify:
   - Loan status updated to REPAID (check via `GET /loans/{id}` on Payment Service)
   - `loan.repaid` event published (check RabbitMQ Management UI)

**Error case tests:**
- Call `/repay` on a loan that is not DUE (status ACTIVE) → verify 400 rejection
- Call `/confirm-repayment` twice with the same session → verify idempotent behavior

### Dependencies

- `fastapi`, `uvicorn`, `pydantic`, `httpx`, `aio-pika`, `grpcio`, `grpcio-tools`

---

## 11. ACRA Wrapper

**Type:** Wrapper Service
**Port:** 5007
**Technology:** Python / FastAPI
**Owner:** *(assign team member — can be combined with another service)*

### Purpose

Wraps the data.gov.sg ACRA UEN registry API for debtor UEN validation. Called by Invoice Orchestrator during invoice listing.

### Swagger

- Swagger UI at `http://localhost:5007/docs`
- Tag endpoints: `tags=["UEN Validation"]`

### Project Structure

```
acra-wrapper/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py               # DATA_GOV_API_URL, dataset resource ID
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── uen.py              # Pydantic: UENValidateRequest, UENValidateResponse
│   ├── routers/
│   │   ├── __init__.py
│   │   └── uen.py              # POST /validate-uen
│   ├── services/
│   │   ├── __init__.py
│   │   └── acra_service.py     # ACRAService class
├── Dockerfile
├── requirements.txt
└── .env
```

### API Endpoint

| Method | Path | Request Body | Response | Description |
|--------|------|-------------|----------|-------------|
| POST | `/validate-uen` | `UENValidateRequest` (uen) | `UENValidateResponse` (valid, entity_name?, uen_status?) | Validate a UEN against ACRA registry. |

### Key Classes

**ACRAService:**
- `validate_uen(uen: str) -> UENValidateResponse` — calls data.gov.sg ACRA dataset API, checks if UEN exists and is active, returns entity name and validation result

### Pydantic Schemas

```python
class UENValidateRequest(BaseModel):
    uen: str

class UENValidateResponse(BaseModel):
    valid: bool
    uen: str
    entity_name: Optional[str] = None
    uen_status: Optional[str] = None      # e.g., "Registered", "Deregistered"
    message: str                          # human-readable result
```

### Who Calls This Service

- **Invoice Orchestrator** → `POST /validate-uen`

### How to Test

**Tier 1 — Standalone smoke test:**
1. `docker compose up acra-wrapper`
2. Open `http://localhost:5007/docs` (Swagger UI)
3. `POST /validate-uen` with `{"uen": "53298394W"}` (use a known valid UEN) → verify `valid: true` + entity name returned
4. `POST /validate-uen` with `{"uen": "00000000X"}` (fake UEN) → verify `valid: false`
5. Test with empty/malformed UEN → verify proper error message

### Dependencies

- `fastapi`, `uvicorn`, `pydantic`, `httpx`

---

## 12. Stripe Wrapper

**Type:** Wrapper Service
**Port:** 5008
**Technology:** Python / FastAPI
**Owner:** *(assign team member — can be combined with another service)*

### Purpose

Wraps the Stripe API for creating checkout sessions. Outbound only — creates sessions for wallet top-up and loan repayment. Inbound Stripe webhooks bypass this service entirely (they go through KONG → Bidding Orchestrator).

### Swagger

- Swagger UI at `http://localhost:5008/docs`
- Tag endpoints: `tags=["Stripe"]`

### Project Structure

```
stripe-wrapper/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py               # STRIPE_SECRET_KEY, SUCCESS_URL, CANCEL_URL
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── checkout.py         # Pydantic: CheckoutRequest, CheckoutResponse
│   ├── routers/
│   │   ├── __init__.py
│   │   └── checkout.py         # POST /create-checkout-session
│   ├── services/
│   │   ├── __init__.py
│   │   └── stripe_service.py   # StripeService class
├── Dockerfile
├── requirements.txt
└── .env
```

### API Endpoint

| Method | Path | Request Body | Response | Description |
|--------|------|-------------|----------|-------------|
| POST | `/create-checkout-session` | `CheckoutRequest` (amount, user_id, type, loan_id?) | `CheckoutResponse` (url, session_id) | Create Stripe Checkout Session. `type` is either `wallet_topup` or `loan_repayment`. |

### Key Classes

**StripeService:**
- `create_checkout_session(data: CheckoutRequest) -> CheckoutResponse` — calls `stripe.checkout.Session.create()` with line items, success/cancel URLs, and metadata (user_id, type, loan_id). Returns the hosted checkout URL.

### Pydantic Schemas

```python
class CheckoutRequest(BaseModel):
    amount: float                         # in SGD
    user_id: int
    type: Literal["wallet_topup", "loan_repayment"]
    loan_id: Optional[str] = None         # only for loan_repayment

class CheckoutResponse(BaseModel):
    url: str                              # Stripe hosted checkout URL
    session_id: str
```

### Who Calls This Service

- **Bidding Orchestrator** → `POST /create-checkout-session` (wallet top-up)
- **Loan Orchestrator** → `POST /create-checkout-session` (loan repayment)

### How to Test

**Tier 1 — Standalone smoke test:**
1. `docker compose up stripe-wrapper`
2. Open `http://localhost:5008/docs` (Swagger UI)
3. `POST /create-checkout-session` with `{"amount": 100.00, "user_id": 1, "type": "wallet_topup"}` → verify Stripe checkout URL returned
4. Open the returned URL in a browser → verify Stripe hosted checkout page loads
5. Test with `type: "loan_repayment"` and `loan_id: "test-loan-1"` → verify URL returned with correct metadata
6. Use Stripe test card `4242 4242 4242 4242` to complete a test payment

**Note:** Requires a valid `STRIPE_SECRET_KEY` (test key, starts with `sk_test_`). Get this from the Stripe Dashboard → Developers → API Keys.

### Dependencies

- `fastapi`, `uvicorn`, `pydantic`, `stripe`

---

## 13. Temporal Worker

**Type:** Infrastructure (Temporal)
**Technology:** Python (Temporal SDK)
**Owner:** *(assign team member)*

### Purpose

Polls the Temporal Server for tasks and executes all three workflow definitions: AuctionCloseWorkflow, LoanMaturityWorkflow, and WalletTopUpWorkflow. The Worker calls atomic services directly (HTTP + gRPC) during activity execution.

### Project Structure

```
temporal-worker/
├── workflows/
│   ├── __init__.py
│   ├── auction_close.py        # AuctionCloseWorkflow class
│   ├── loan_maturity.py        # LoanMaturityWorkflow class
│   └── wallet_topup.py         # WalletTopUpWorkflow class
├── activities/
│   ├── __init__.py
│   ├── invoice_activities.py   # verify_invoice, update_invoice_status
│   ├── bidding_activities.py   # get_offers, accept_offer, reject_offer
│   ├── payment_activities.py   # ALL Payment Service calls via gRPC: convert_escrow, create_loan, release_funds, get_loan, update_loan_status, credit_wallet
│   ├── marketplace_activities.py # delist_listing, bulk_delist
│   └── rabbitmq_activities.py  # publish_event
├── clients/
│   ├── __init__.py
│   ├── http_client.py
│   └── grpc_client.py          # gRPC client for Payment Service
├── worker.py                   # Main entry point — registers workflows + activities, starts polling
├── config.py
├── Dockerfile
├── requirements.txt
└── .env
```

### Workflow: AuctionCloseWorkflow

```python
@workflow.defn
class AuctionCloseWorkflow:
    def __init__(self):
        self.extend_requested = False

    @workflow.signal
    async def extend_deadline(self):
        """Signal received from Bidding Orchestrator when a bid arrives in the final 5 minutes."""
        self.extend_requested = True

    @workflow.run
    async def run(self, invoice_token: str, bid_period_hours: int):
        deadline = workflow.now() + timedelta(hours=bid_period_hours)

        # T-12h warning
        t12h = deadline - timedelta(hours=12)
        if t12h > workflow.now():
            await workflow.sleep_until(t12h)
            await workflow.execute_activity(publish_event, args=["auction.closing.warning", {...}])

        # T-1h warning
        t1h = deadline - timedelta(hours=1)
        if t1h > workflow.now():
            await workflow.sleep_until(t1h)
            await workflow.execute_activity(publish_event, args=["auction.closing.warning", {...}])

        # Wait until deadline
        await workflow.sleep_until(deadline)

        # Anti-snipe loop: keep extending while signals arrive
        # NOTE: Check flag BEFORE resetting — a signal may have arrived during sleep_until
        while True:
            if not self.extend_requested:
                try:
                    await workflow.wait_condition(
                        lambda: self.extend_requested,
                        timeout=timedelta(minutes=5)
                    )
                except asyncio.TimeoutError:
                    # No signal in 5 minutes → auction closes
                    break
            # Signal was received — reset and loop for another 5-min window
            self.extend_requested = False

        # Fetch all bids
        offers = await workflow.execute_activity(get_offers, args=[invoice_token])
        if not offers:
            await workflow.execute_activity(publish_event, args=["auction.expired", {...}])
            return

        winner = max(offers, key=lambda o: o["bid_amount"])

        # 10-step financial workflow
        await workflow.execute_activity(verify_invoice, args=[invoice_token])
        await workflow.execute_activity(convert_escrow_to_loan, args=[winner["investor_id"], invoice_token])
        loan = await workflow.execute_activity(create_loan, args=[...])
        # Fire-and-forget: start child workflow without waiting for it to complete (it runs for days/weeks)
        await workflow.start_child_workflow(LoanMaturityWorkflow.run, args=[loan["loan_id"], loan["due_date"]],
                                            id=f"loan-{loan['loan_id']}")
        await workflow.execute_activity(release_funds_to_seller, args=[...])
        await workflow.execute_activity(update_invoice_status, args=[invoice_token, "FINANCED"])
        await workflow.execute_activity(delist_listing, args=[invoice_token])
        await workflow.execute_activity(accept_offer, args=[winner["id"]])

        # Reject all losers in parallel
        losers = [o for o in offers if o["id"] != winner["id"]]
        await asyncio.gather(*[
            workflow.execute_activity(reject_offer, args=[o["id"]]) for o in losers
        ])

        # Publish outcome events
        await workflow.execute_activity(publish_event, args=["auction.closed.winner", {...}])
        for loser in losers:
            await workflow.execute_activity(publish_event, args=["auction.closed.loser", {...}])
```

### Workflow: LoanMaturityWorkflow

```python
@workflow.defn
class LoanMaturityWorkflow:
    @workflow.run
    async def run(self, loan_id: str, due_date: str):
        # Wait until due date
        await workflow.sleep_until(datetime.fromisoformat(due_date))

        # Mark loan DUE (via gRPC — all Payment Service calls use gRPC for consistency)
        await workflow.execute_activity(update_loan_status_grpc, args=[loan_id, "DUE"])
        await workflow.execute_activity(publish_event, args=["loan.due", {"loan_id": loan_id}])

        # Repayment window (120s demo / 86400s production)
        repayment_window = timedelta(seconds=int(os.getenv("REPAYMENT_WINDOW_SECONDS", "86400")))
        await workflow.sleep(repayment_window)

        # Check if repaid (via gRPC)
        loan = await workflow.execute_activity(get_loan_grpc, args=[loan_id])
        if loan["status"] == "REPAID":
            return  # Business repaid in time — done

        # Not repaid → mark OVERDUE (via gRPC)
        await workflow.execute_activity(update_loan_status_grpc, args=[loan_id, "OVERDUE"])
        await workflow.execute_activity(publish_event, args=["loan.overdue", {
            "loan_id": loan_id,
            "invoice_token": loan["invoice_token"],
            "investor_id": loan["investor_id"],
            "seller_id": loan["seller_id"],
        }])

        # Bulk delist defaulting seller's listings
        await workflow.execute_activity(bulk_delist, args=[loan["seller_id"]])
```

### Workflow: WalletTopUpWorkflow

```python
@workflow.defn
class WalletTopUpWorkflow:
    @workflow.run
    async def run(self, user_id: int, amount: float):
        # Credit wallet
        await workflow.execute_activity(credit_wallet, args=[user_id, amount])
        # Publish event
        await workflow.execute_activity(publish_event, args=["wallet.credited", {"user_id": user_id, "amount": amount}])
```

### Activities

Each activity is a function decorated with `@activity.defn`. Activities make the actual HTTP/gRPC calls to atomic services. They are retryable — if a call fails, Temporal retries automatically.

```python
@activity.defn
async def verify_invoice(invoice_token: str):
    response = await http_client.get(f"{INVOICE_SERVICE_URL}/invoices/{invoice_token}")
    if response["status"] != "LISTED":
        raise ApplicationError("Invoice not available")
    return response

@activity.defn
async def convert_escrow_to_loan(investor_id: int, invoice_token: str):
    return await grpc_client.convert_escrow(investor_id, invoice_token, idempotency_key=f"convert-{invoice_token}")

@activity.defn
async def get_loan_grpc(loan_id: str):
    """Used by LoanMaturityWorkflow to check loan status after repayment window."""
    return await grpc_client.get_loan(loan_id)

@activity.defn
async def update_loan_status_grpc(loan_id: str, status: str):
    """Used by LoanMaturityWorkflow to mark loan DUE or OVERDUE."""
    return await grpc_client.update_loan_status(loan_id, status)

# ... similar pattern for all other activities
```

### Worker Entry Point (worker.py)

```python
async def main():
    client = await Client.connect(TEMPORAL_HOST)
    worker = Worker(
        client,
        task_queue="invoiceflow-queue",
        workflows=[AuctionCloseWorkflow, LoanMaturityWorkflow, WalletTopUpWorkflow],
        activities=[verify_invoice, get_offers, accept_offer, reject_offer,
                    convert_escrow_to_loan, create_loan, release_funds_to_seller,
                    update_invoice_status, delist_listing, bulk_delist,
                    update_loan_status_grpc, get_loan_grpc, credit_wallet, publish_event],
    )
    await worker.run()
```

### Environment Variables

```env
TEMPORAL_HOST=temporal:7233
INVOICE_SERVICE_URL=http://invoice-service:5001
BIDDING_SERVICE_URL=http://bidding-service:5003
MARKETPLACE_SERVICE_URL=http://marketplace-service:5002
PAYMENT_SERVICE_GRPC=payment-service:50051
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672
REPAYMENT_WINDOW_SECONDS=120
```

Note: All Payment Service calls from the Temporal Worker now use gRPC exclusively — no HTTP fallback. The `PAYMENT_SERVICE_URL` env var has been removed.

### How to Test

**Tier 1 — Worker startup test:**
1. `docker compose up temporal temporal-worker`
2. Check logs: `docker compose logs temporal-worker` → verify "Worker started, polling invoiceflow-queue"
3. Open Temporal UI at `http://localhost:8088` → verify the worker appears under the `invoiceflow-queue` task queue

**Tier 2 — WalletTopUpWorkflow (simplest, fast feedback):**
1. `docker compose up temporal temporal-worker payment-service payment-db rabbitmq notification-service`
2. Seed an investor wallet in Payment Service
3. Start a WalletTopUpWorkflow manually via Temporal UI or CLI:
   ```bash
   temporal workflow start --type WalletTopUpWorkflow --task-queue invoiceflow-queue \
     --workflow-id wallet-topup-test-1 --input '{"user_id": 1, "amount": 500.00}'
   ```
4. Check Temporal UI → verify workflow completed
5. `GET /wallets/1` on Payment Service → verify balance increased
6. Check RabbitMQ → verify `wallet.credited` event published

**Tier 3 — AuctionCloseWorkflow (use short timer for demo):**
1. Start the full stack with `REPAYMENT_WINDOW_SECONDS=30` and a short `bid_period_hours`
2. Create an invoice listing via Invoice Orchestrator
3. Place a bid via Bidding Orchestrator
4. Watch Temporal UI → verify AuctionCloseWorkflow is running with a timer
5. Wait for timer to expire → verify the 10-step financial workflow executes:
   - Escrow converted, loan created, funds released, invoice FINANCED, listing delisted, bid accepted
   - LoanMaturityWorkflow started as child (visible in Temporal UI)

**Tier 3b — Anti-snipe test:**
1. Create listing with a very short bid period (e.g., 1 minute for testing)
2. Place a bid in the last 5 minutes of the auction
3. Verify in Temporal UI that the workflow received an `extend_deadline` signal
4. Verify in Marketplace Service that the listing deadline was extended

### Dependencies

- `temporalio`, `httpx`, `grpcio`, `grpcio-tools`, `aio-pika`

---

## 14. KONG API Gateway

**Type:** Infrastructure (BTL #1)
**Port:** 8000
**Owner:** *(assign team member — often shared)*

### Purpose

Handles ALL external-facing traffic: JWT validation, rate limiting, CORS, and routing to composite services. Internal service-to-service calls bypass KONG entirely.

### Route Configuration

Configure via KONG declarative config (`kong.yml`) or Admin API:

| Route | Upstream Service | Methods | Auth | Notes |
|-------|-----------------|---------|------|-------|
| `/api/invoices` | `http://invoice-orchestrator:5010` | POST | JWT required | Scenario 1 |
| `/api/bids` | `http://bidding-orchestrator:5011` | POST | JWT required | Scenario 2 |
| `/api/wallet/topup` | `http://bidding-orchestrator:5011` | POST | JWT required | Scenario 2 |
| `/api/webhooks/stripe` | `http://bidding-orchestrator:5011` | POST | **No JWT** | Stripe webhook — verified by Stripe signature |
| `/api/loans/*/repay` | `http://loan-orchestrator:5012` | POST | JWT required | Scenario 3 |
| `/api/loans/*/confirm-repayment` | `http://loan-orchestrator:5012` | POST | JWT required | Scenario 3 |
| `/api/notifications` | `http://notification-service:5005` | GET | JWT required | Direct to atomic (read-only) |
| `/graphql` | `http://marketplace-service:5002` | POST | JWT required | GraphQL investor queries |
| `/api/auth/login` | `http://user-service:5000` | POST | **No JWT** | Login |
| `/api/auth/register` | `http://user-service:5000` | POST | **No JWT** | Registration |

### Plugins

| Plugin | Purpose | Config |
|--------|---------|--------|
| JWT | Validate JWT on protected routes | `key_claim_name: kid`, algorithm: HS256 |
| Rate Limiting | Prevent abuse | 100 requests/min per consumer |
| CORS | Allow frontend origin | `origins: http://localhost:8080`, `methods: GET, POST, PATCH, DELETE` |
| Correlation ID | Trace requests across services | Adds `X-Correlation-ID` header |

### Docker Compose

```yaml
kong:
  image: kong:3.4
  environment:
    KONG_DATABASE: "off"
    KONG_DECLARATIVE_CONFIG: /etc/kong/kong.yml
    KONG_PROXY_LISTEN: 0.0.0.0:8000
  ports:
    - "8000:8000"
  volumes:
    - ./kong.yml:/etc/kong/kong.yml
```

### Important

- gRPC traffic (Payment Service :50051) does **NOT** go through KONG — gRPC requires HTTP/2 which KONG's HTTP/1.1 proxy doesn't support
- WebSocket connections (Notification Service) should bypass KONG — the frontend connects directly to `ws://localhost:5005/ws/{user_id}`. If WebSocket must go through KONG, configure the route with `protocols: ["ws", "wss"]`
- Stripe webhook route must **not** have JWT validation — Stripe uses its own signature verification
- KONG injects `X-User-ID` into forwarded requests for downstream service identity propagation (via the JWT plugin's credential mapping)

### How to Test

**Tier 1 — KONG routing test:**
1. `docker compose up kong user-service user-db`
2. Test unauthenticated route: `curl http://localhost:8000/api/auth/login -X POST -H "Content-Type: application/json" -d '{"email":"test@test.com","password":"test"}'` → should reach User Service (may return 401 from User Service, which is fine — it means KONG routed correctly)
3. Test protected route without JWT: `curl http://localhost:8000/api/invoices` → should return 401 from KONG (not from the upstream)
4. Test protected route with JWT: Get a token from login, then: `curl http://localhost:8000/api/invoices -H "Authorization: Bearer <token>"` → should reach Invoice Orchestrator

**Tier 1b — Verify all routes are configured:**
1. For each route in the route table above, send a request and verify it reaches the correct upstream service (check service logs)
2. Verify Stripe webhook route has no JWT: `curl -X POST http://localhost:8000/api/webhooks/stripe -d '{}'` → should reach Bidding Orchestrator (will fail signature check, but KONG should not block it)

---

## Quick Reference: Who Builds What

| Service | Type | Tech | Port | Complexity |
|---------|------|------|------|------------|
| User Service | Atomic | Python/FastAPI | 5000 | Low-Medium (JWT + UEN validation + RabbitMQ consumer) |
| Invoice Service | Atomic | Python/FastAPI | 5001 | Medium (PDF + MinIO + RabbitMQ consumer) |
| Marketplace Service | Atomic | Python/FastAPI + GraphQL | 5002 | Medium (GraphQL BTL #3) |
| Bidding Service | Atomic | Python/FastAPI | 5003 | Low |
| Payment Service | Atomic | Node.js + gRPC | 5004/50051 | High (gRPC BTL #2 + RabbitMQ consumer) |
| Notification Service | Atomic | Python/FastAPI | 5005 | Medium (RabbitMQ + WebSocket + Resend) |
| OutSystems Activity Log | OutSystems | OutSystems | — | Low (low-code) |
| Invoice Orchestrator | Composite | Python/FastAPI | 5010 | Medium |
| Bidding Orchestrator | Composite | Python/FastAPI | 5011 | High (gRPC + Temporal signals + Stripe webhooks) |
| Loan Orchestrator | Composite | Python/FastAPI | 5012 | Medium |
| ACRA Wrapper | Wrapper | Python/FastAPI | 5007 | Low |
| Stripe Wrapper | Wrapper | Python/FastAPI | 5008 | Low |
| Temporal Worker | Infra | Python/Temporal SDK | — | High (3 workflows + all activities) |
| KONG | Infra | Kong Gateway | 8000 | Low (config only) |

---

## Common Patterns (for all Python/FastAPI services)

### FastAPI App Setup with Swagger

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Invoice Service",                    # change per service
    description="Handles invoice CRUD, PDF upload, and status tracking.",
    version="1.0.0",
    docs_url="/docs",                           # Swagger UI
    redoc_url="/redoc",                         # ReDoc alternative
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with tags for Swagger grouping
app.include_router(invoice_router, prefix="/invoices", tags=["Invoices"])
```

### Pydantic Model → Swagger Schema

Every endpoint should use Pydantic models for request and response. FastAPI auto-generates Swagger schemas from these:

```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class InvoiceResponse(BaseModel):
    id: int
    invoice_token: str
    status: str
    amount: float
    created_at: datetime

    class Config:
        from_attributes = True    # allows SQLAlchemy model → Pydantic conversion

@router.get("/invoices/{token}", response_model=InvoiceResponse, summary="Get invoice by token")
async def get_invoice(token: str):
    ...
```

### OOP Service Pattern

Every service should follow this pattern — routers are thin, services contain the logic:

```python
# services/invoice_service.py
class InvoiceService:
    def __init__(self, db: Session):
        self.db = db

    def create_invoice(self, data: InvoiceCreate) -> Invoice:
        invoice = Invoice(**data.dict(), invoice_token=str(uuid4()))
        self.db.add(invoice)
        self.db.commit()
        return invoice

    def get_invoice(self, token: str) -> Invoice:
        invoice = self.db.query(Invoice).filter(Invoice.invoice_token == token).first()
        if not invoice:
            raise HTTPException(404, "Invoice not found")
        return invoice

# routers/invoices.py — thin router, delegates to service
@router.post("/invoices", response_model=InvoiceResponse, summary="Create new invoice")
async def create_invoice(data: InvoiceCreate, db: Session = Depends(get_db)):
    service = InvoiceService(db)
    return service.create_invoice(data)
```

### RabbitMQ Publisher Pattern

```python
import aio_pika
import json

class RabbitMQPublisher:
    def __init__(self, rabbitmq_url: str, exchange_name: str = "invoiceflow_events"):
        self.rabbitmq_url = rabbitmq_url
        self.exchange_name = exchange_name
        self.connection = None
        self.channel = None
        self.exchange = None

    async def connect(self):
        self.connection = await aio_pika.connect_robust(self.rabbitmq_url)
        self.channel = await self.connection.channel()
        self.exchange = await self.channel.declare_exchange(
            self.exchange_name, aio_pika.ExchangeType.TOPIC, durable=True
        )

    async def publish(self, routing_key: str, payload: dict):
        message = aio_pika.Message(
            body=json.dumps(payload).encode(),
            content_type="application/json",
        )
        await self.exchange.publish(message, routing_key=routing_key)
```

### RabbitMQ Consumer Pattern

```python
class EventConsumer:
    def __init__(self, rabbitmq_url: str, queue_name: str, routing_keys: list, handler):
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.routing_keys = routing_keys
        self.handler = handler

    async def start(self):
        connection = await aio_pika.connect_robust(self.rabbitmq_url)
        channel = await connection.channel()
        exchange = await channel.declare_exchange("invoiceflow_events", aio_pika.ExchangeType.TOPIC, durable=True)
        queue = await channel.declare_queue(self.queue_name, durable=True)
        for key in self.routing_keys:
            await queue.bind(exchange, routing_key=key)
        await queue.consume(self._on_message)

    async def _on_message(self, message: aio_pika.IncomingMessage):
        async with message.process():
            payload = json.loads(message.body)
            await self.handler(message.routing_key, payload)
```

### Dockerfile Template (Python/FastAPI)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5001"]
```

### Health Check Endpoint (add to EVERY service)

```python
@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "invoice-service"}  # change per service
```

This endpoint is used for Docker Compose `healthcheck` directives and for KONG upstream health monitoring. For services with database dependencies, consider also pinging the DB:

```python
@app.get("/health", tags=["Health"])
async def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "service": "invoice-service", "db": "connected"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "service": "invoice-service", "db": "disconnected"})
```

### Docker Compose Snippet Template

Every service section should correspond to an entry in `docker-compose.yml`. Here's the template:

```yaml
# === Atomic Service Example ===
invoice-service:
  build: ./invoice-service
  ports:
    - "5001:5001"
  environment:
    DB_URL: mysql+pymysql://root:password@invoice-db:3306/invoice_db
    MINIO_ENDPOINT: minio:9000
    MINIO_ACCESS_KEY: minioadmin
    MINIO_SECRET_KEY: minioadmin
    RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672
  depends_on:
    invoice-db:
      condition: service_healthy
    rabbitmq:
      condition: service_healthy
    minio:
      condition: service_started
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
    interval: 10s
    timeout: 5s
    retries: 3
    start_period: 15s

invoice-db:
  image: mysql:8.0
  environment:
    MYSQL_ROOT_PASSWORD: password
    MYSQL_DATABASE: invoice_db
  ports:
    - "3307:3306"
  healthcheck:
    test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
    interval: 5s
    timeout: 3s
    retries: 5

# === Composite Service Example ===
invoice-orchestrator:
  build: ./invoice-orchestrator
  ports:
    - "5010:5010"
  environment:
    USER_SERVICE_URL: http://user-service:5000
    INVOICE_SERVICE_URL: http://invoice-service:5001
    MARKETPLACE_SERVICE_URL: http://marketplace-service:5002
    ACRA_WRAPPER_URL: http://acra-wrapper:5007
    RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672
    TEMPORAL_HOST: temporal:7233
  depends_on:
    user-service:
      condition: service_healthy
    invoice-service:
      condition: service_healthy
    marketplace-service:
      condition: service_healthy
    rabbitmq:
      condition: service_healthy

# === Infrastructure ===
rabbitmq:
  image: rabbitmq:3-management
  ports:
    - "5672:5672"
    - "15672:15672"
  healthcheck:
    test: ["CMD", "rabbitmq-diagnostics", "check_running"]
    interval: 5s
    timeout: 3s
    retries: 5

minio:
  image: minio/minio
  command: server /data --console-address ":9001"
  ports:
    - "9000:9000"
    - "9001:9001"
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin
```

### HTTPClient with Error Handling (for all orchestrators)

```python
import httpx
from fastapi import HTTPException

class HTTPClient:
    def __init__(self, timeout: float = 5.0):
        self.client = httpx.AsyncClient(timeout=timeout)

    async def get(self, url: str) -> dict:
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(504, f"Timeout calling {url}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)

    async def post(self, url: str, **kwargs) -> dict:
        try:
            response = await self.client.post(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(504, f"Timeout calling {url}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)

    async def patch(self, url: str, **kwargs) -> dict:
        try:
            response = await self.client.patch(url, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            raise HTTPException(504, f"Timeout calling {url}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)

    async def delete(self, url: str) -> dict:
        try:
            response = await self.client.delete(url)
            response.raise_for_status()
            return response.json() if response.content else {}
        except httpx.TimeoutException:
            raise HTTPException(504, f"Timeout calling {url}")
        except httpx.HTTPStatusError as e:
            raise HTTPException(e.response.status_code, e.response.text)
```

### Version Pinning (requirements.txt)

**Always pin versions in `requirements.txt`** to avoid team members getting different dependency versions. Example:

```
# Python/FastAPI services
fastapi==0.115.0
uvicorn==0.30.0
sqlalchemy==2.0.35
pymysql==1.1.1
pydantic==2.9.0
httpx==0.27.0
aio-pika==9.4.3
temporalio==1.7.1

# Service-specific
pdfplumber==0.11.4          # Invoice Service
minio==7.2.9                # Invoice Service
strawberry-graphql==0.243.0 # Marketplace Service
python-jose[cryptography]==3.3.0  # User Service
passlib[bcrypt]==1.7.4      # User Service
resend==2.5.0               # Notification Service
grpcio==1.67.0              # Bidding/Loan Orchestrator, Temporal Worker
grpcio-tools==1.67.0        # Bidding/Loan Orchestrator, Temporal Worker
stripe==10.12.0             # Stripe Wrapper
```

For Node.js (Payment Service), use `package-lock.json` (auto-generated by `npm install`) and commit it to version control.

---

## End-to-End Testing Checklist

After all services are built, run the full stack and walk through each scenario:

### Scenario 1 — Invoice Listing
1. Register a SELLER with valid UEN → login → get JWT
2. `POST /api/invoices` via KONG with JWT → verify full flow:
   - Invoice created, PDF in MinIO, debtor UEN validated
   - Listing created in Marketplace, invoice status LISTED
   - AuctionCloseWorkflow running in Temporal UI
   - `invoice.listed` event visible in RabbitMQ Management UI
   - Notification email sent (check Resend dashboard or logs)
   - Activity Log entry created in OutSystems

### Scenario 2 — Bidding + Auction Close
1. Register an INVESTOR → login → get JWT
2. Top up wallet: `POST /api/wallet/topup` → complete Stripe checkout → verify wallet credited
3. Place a bid: `POST /api/bids` → verify escrow locked, `bid.placed` event published
4. Place a higher bid from a second investor → verify `bid.outbid` published, first investor's escrow released
5. Wait for auction timer to expire → verify in Temporal UI:
   - Winner's escrow converted, loan created, funds released to seller
   - LoanMaturityWorkflow started as child
   - Listing delisted, invoice FINANCED, winner ACCEPTED, loser REJECTED
   - All notification events published

### Scenario 3 — Loan Maturity + Repayment/Default
1. Wait for LoanMaturityWorkflow due_date timer (use short timer for demo)
2. Verify loan marked DUE, `loan.due` event published, business notified

**Repayment path:**
3. `POST /api/loans/{id}/repay` → complete Stripe checkout → `POST /api/loans/{id}/confirm-repayment`
4. Verify `loan.repaid` published, four consumers react:
   - Invoice → REPAID, Payment → investor wallet credited, User → account ACTIVE, Notification → emails sent

**Default path (let repayment window expire):**
3. Wait for repayment window to expire
4. Verify `loan.overdue` published, four consumers react:
   - Invoice → DEFAULTED, Payment → 5% penalty, User → account DEFAULTED, Notification → emails sent
5. Verify all seller's active listings are bulk-delisted
