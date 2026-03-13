# InvoiceFlow — Team Playbook

**Your step-by-step guide from zero to working demo.**

Read this top to bottom. If you're stuck at any point, come back here and find the phase you're in.

---

## Phase 0: Before You Write Any Code

### 0.1 — Read the architecture document first

Open `Final_Architecture_MK_2.md`. Don't skim it. Read:

1. The **Three User Scenarios** section — understand the full story of what InvoiceFlow does
2. The **Service Inventory** — find your assigned service, note its type (atomic/composite/wrapper), port, and technology
3. The **Detailed Scenario Flows** — trace the exact path your service appears in. Note who calls you and who you call.
4. The **Architectural Rules** — these are non-negotiable. If your code violates any of them, it will need to be rewritten.

### 0.2 — Read YOUR section of the build instructions

Open `BUILD_INSTRUCTIONS_V2.md`. Go directly to your assigned service section. Read:

1. **Purpose** — one paragraph on what your service does
2. **Project Structure** — this is your folder layout, follow it exactly
3. **Database Schema** — if your service has a DB, this is your `init.sql`
4. **API Endpoints** — every endpoint you need to build, with request/response shapes
5. **Key Classes** — the classes you need to write and their methods
6. **Who Calls This Service** — so you know your consumers and what they expect
7. **How to Test** — how to verify your service works

### 0.3 — Set up your local environment

Make sure you have installed:

- **Docker Desktop** (latest)
- **Python 3.11+** (for FastAPI services)
- **Node.js 20+** (for Payment Service only)
- **Postman** (for API testing)
- **Git** (obviously)
- A code editor (VS Code recommended)

### 0.4 — Clone the repo and understand the folder structure

```
invoiceflow/
├── user-service/
├── invoice-service/
├── marketplace-service/
├── bidding-service/
├── payment-service/
├── notification-service/
├── invoice-orchestrator/
├── bidding-orchestrator/
├── loan-orchestrator/
├── acra-wrapper/
├── stripe-wrapper/
├── temporal-worker/
├── kong/
│   └── kong.yml
├── docker-compose.yml
└── README.md
```

Each service is its own folder with its own `Dockerfile`, dependencies, and code. You only need to work inside your assigned service folder(s).

---

## Phase 1: Scaffold Your Service

### 1.1 — Create the folder structure

Copy the project structure from the build instructions for your service. Create every folder and empty `__init__.py` file.

```bash
# Example for Invoice Service
mkdir -p invoice-service/app/{models,schemas,routers,services,consumers}
touch invoice-service/app/__init__.py
touch invoice-service/app/models/__init__.py
touch invoice-service/app/schemas/__init__.py
touch invoice-service/app/routers/__init__.py
touch invoice-service/app/services/__init__.py
touch invoice-service/app/consumers/__init__.py
```

### 1.2 — Create your database init script

If your service has a database, create an `init.sql` file with the schema from the build instructions. This will be mounted into the MySQL Docker container.

```sql
-- invoice-service/init.sql
CREATE DATABASE IF NOT EXISTS invoice_db;
USE invoice_db;

CREATE TABLE invoices (
    -- copy schema from build instructions
);
```

### 1.3 — Create your Dockerfile

Copy the template from the build instructions Common Patterns section and change the port number.

### 1.4 — Create requirements.txt (or package.json)

Copy the dependencies list from your service's build instructions section. **Pin the versions** — don't just write `fastapi`, write `fastapi==0.115.0`.

### 1.5 — Create your FastAPI app entry point

In `app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Your Service Name",
    description="What it does.",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "your-service-name"}
```

### 1.6 — Add your Docker Compose entry

Add your service + its database to `docker-compose.yml`. Check the build instructions for the template. Make sure you set `depends_on` with `condition: service_healthy` for your DB and RabbitMQ.

### 1.7 — Verify the scaffold runs

```bash
docker compose up your-service your-db
```

Open `http://localhost:<your-port>/docs` in a browser. You should see Swagger UI with just the `/health` endpoint. Hit it. If you see `{"status": "ok"}`, you're good. Move on.

---

## Phase 2: Build Your Endpoints (One at a Time)

Don't try to build everything at once. Go endpoint by endpoint.

### 2.1 — For each endpoint, follow this order:

**Step A — Pydantic schemas first.** Define the request and response models in `schemas/`. These drive everything: Swagger docs, validation, serialization.

**Step B — SQLAlchemy model (if new table).** Define the ORM model in `models/`. Make sure it matches your `init.sql` schema exactly.

**Step C — Service class.** Write the business logic method in `services/`. This is where the real work happens. The router should be thin — just call the service class.

**Step D — Router endpoint.** Wire up the FastAPI route in `routers/`. It should accept the Pydantic request model, call the service class, and return the Pydantic response model.

**Step E — Test it immediately.** Don't wait until you've written all endpoints. Test each one right after you build it.

### 2.2 — How to test each endpoint

**Option A — Swagger UI (fastest for quick checks):**
1. Open `http://localhost:<port>/docs`
2. Click the endpoint → "Try it out" → fill in the fields → "Execute"
3. Check the response body and status code

**Option B — Postman (better for saving and reusing tests):**
1. Create a new Collection called "InvoiceFlow"
2. Add a folder for your service
3. Add a request for each endpoint
4. Save them — you'll reuse these for integration testing later

**Option C — curl (if you prefer the terminal):**
```bash
# GET
curl http://localhost:5001/health

# POST with JSON body
curl -X POST http://localhost:5001/invoices \
  -H "Content-Type: application/json" \
  -d '{"seller_id": 1, "debtor_uen": "53298394W", "amount": 5000}'

# PATCH
curl -X PATCH http://localhost:5001/invoices/abc-123/status \
  -H "Content-Type: application/json" \
  -d '{"status": "LISTED"}'
```

### 2.3 — If your service has a RabbitMQ consumer

Build the HTTP endpoints first. Get them working. Then add the consumer:

1. Add `rabbitmq` to your `depends_on` in Docker Compose
2. Write the consumer class in `consumers/`
3. Start it as a background task in `main.py` using FastAPI's lifespan
4. Test it by publishing a message manually via the RabbitMQ Management UI at `http://localhost:15672` (login: guest / guest)

### 2.4 — If your service uses gRPC (Payment Service)

1. Write the `.proto` file first — this IS your API contract
2. Generate stubs from the proto file
3. Implement the gRPC handlers
4. Test with `grpcurl`:
   ```bash
   # List available services
   grpcurl -plaintext localhost:50051 list
   
   # Call a method
   grpcurl -plaintext -d '{"user_id": 1, "amount": "500.00", "idempotency_key": "test-1"}' \
     localhost:50051 payment.PaymentService/CreditWallet
   ```

---

## Phase 3: Integrate with Other Services

Once your endpoints work in isolation, start connecting to the services you depend on (or that depend on you).

### 3.1 — Coordinate with your teammates

Before integrating, agree on:
- **Exact endpoint paths and request/response shapes** — they should match the build instructions, but double-check with each other
- **Docker service names** — these are the hostnames you'll use for internal calls (e.g., `http://invoice-service:5001`)
- **Which services need to be running** for your integration test to work

### 3.2 — Start dependent services together

```bash
# Example: testing Invoice Orchestrator needs these running
docker compose up invoice-orchestrator user-service invoice-service marketplace-service acra-wrapper \
  user-db invoice-db market-db minio rabbitmq temporal
```

### 3.3 — Test the integration via Swagger / Postman

Call your composite service endpoint and trace the full flow:
- Did it call the downstream atomics correctly?
- Did the database records get created?
- Did the RabbitMQ events get published? (Check `http://localhost:15672` → Queues)
- Did Temporal workflows start? (Check `http://localhost:8088`)

### 3.4 — Common integration problems and fixes

| Problem | Likely Cause | Fix |
|---------|-------------|-----|
| `Connection refused` to another service | Service not running, or wrong hostname | Check `docker compose ps`, use Docker service names not `localhost` |
| `404` from downstream service | Endpoint path mismatch | Compare your URL with the downstream service's Swagger docs |
| RabbitMQ consumer not receiving messages | Wrong exchange name, routing key, or queue not bound | Check exchange is `invoiceflow_events` (topic type), verify binding in RabbitMQ Management UI |
| gRPC call fails | Proto file mismatch, wrong port | Ensure both sides use the same `.proto`, and the port is `50051` |
| Temporal workflow doesn't start | Worker not running, wrong task queue | Check `temporal-worker` logs, ensure task queue is `invoiceflow-queue` |
| `502` from KONG | Upstream service not healthy | Check the upstream service's `/health` endpoint directly |

---

## Phase 4: Set Up Postman for Full Testing

### 4.1 — Create a Postman Environment

Create an environment called "InvoiceFlow Local" with these variables:

| Variable | Initial Value |
|----------|--------------|
| `base_url` | `http://localhost:8000` |
| `jwt_token` | *(leave empty)* |
| `seller_id` | *(leave empty)* |
| `investor_id` | *(leave empty)* |
| `invoice_token` | *(leave empty)* |
| `loan_id` | *(leave empty)* |

### 4.2 — Create the Collection structure

```
InvoiceFlow/
├── Auth/
│   ├── Register Seller
│   ├── Register Investor
│   └── Login
├── Scenario 1 — Invoice Listing/
│   └── POST Create Invoice
├── Scenario 2 — Bidding/
│   ├── POST Top Up Wallet
│   ├── POST Place Bid
│   └── GraphQL — Browse Listings
├── Scenario 3 — Loan Repayment/
│   ├── POST Initiate Repayment
│   └── POST Confirm Repayment
└── Direct Service Tests/
    ├── User Service/
    ├── Invoice Service/
    ├── Payment Service (gRPC)/
    └── ...
```

### 4.3 — Auto-save tokens with Postman Scripts

In your **Login** request, go to the **Scripts → Post-response** tab and add:

```javascript
var res = pm.response.json();
pm.environment.set("jwt_token", res.access_token);
```

Then at the **Collection level**, go to **Authorization** → set type to **Bearer Token** → value `{{jwt_token}}`. Every request in the collection will inherit this automatically.

### 4.4 — Chain requests by saving IDs

In the **Register Seller** request, add a post-response script:
```javascript
var res = pm.response.json();
pm.environment.set("seller_id", res.id);
```

In the **Create Invoice** request:
```javascript
var res = pm.response.json();
pm.environment.set("invoice_token", res.invoice_token);
```

Now subsequent requests can use `{{invoice_token}}` in their URL or body, and Postman fills it in automatically.

### 4.5 — Add assertions to catch regressions

In the **Scripts → Post-response** tab of each request:

```javascript
// Check status code
pm.test("Status 200", () => pm.response.to.have.status(200));

// Check response shape
pm.test("Has invoice_token", () => {
    var res = pm.response.json();
    pm.expect(res.invoice_token).to.be.a("string");
});

// Check specific values
pm.test("Status is LISTED", () => {
    var res = pm.response.json();
    pm.expect(res.status).to.eql("LISTED");
});
```

### 4.6 — Run full scenario with Collection Runner

1. Click your collection → **Run**
2. Postman runs every request in order (top to bottom)
3. All assertions run automatically
4. Green = pass, red = something broke

This is your regression test. Run it after any code change.

### 4.7 — Testing GraphQL in Postman

For Marketplace Service GraphQL queries:
- Method: `POST`
- URL: `{{base_url}}/graphql`
- Body → GraphQL tab:
  ```graphql
  query {
    listings(status: "ACTIVE", minAmount: 1000) {
      id
      invoiceToken
      amount
      urgencyLevel
      deadline
    }
  }
  ```

### 4.8 — Testing gRPC in Postman

Postman supports gRPC natively:
1. New Request → select **gRPC** (not HTTP)
2. Server URL: `localhost:50051`
3. Import the `payment.proto` file
4. Postman auto-generates forms for each RPC method
5. Fill in the fields and click **Invoke**

### 4.9 — Testing Stripe Webhooks

Postman can't easily fake Stripe signatures. Use the Stripe CLI instead:

```bash
# Install Stripe CLI, then:
stripe listen --forward-to localhost:8000/api/webhooks/stripe

# In another terminal, trigger a test event:
stripe trigger checkout.session.completed
```

---

## Phase 5: End-to-End Demo Run

This is your final check before presentation. Run the full stack and walk through every scenario.

### 5.1 — Start everything

```bash
docker compose up --build
```

Wait until all health checks pass. Check with:
```bash
docker compose ps
```

Every service should show `healthy` or `running`.

### 5.2 — Walk through Scenario 1

1. Register a SELLER (with valid UEN) → Login → Get JWT
2. Create invoice with a PDF upload via KONG
3. Verify: invoice created, listing on marketplace, AuctionCloseWorkflow running in Temporal UI, notification email sent, activity log entry in OutSystems

### 5.3 — Walk through Scenario 2

1. Register an INVESTOR → Login → Top up wallet via Stripe test checkout
2. Place a bid → verify escrow locked
3. Place a higher bid from a second investor → verify first investor's escrow released
4. Wait for auction close → verify full 10-step workflow executes
5. (Optional) Test anti-snipe by bidding in the last 5 minutes

### 5.4 — Walk through Scenario 3

1. Wait for loan due date (use short demo timer)
2. **Repayment path:** Initiate repayment → Stripe checkout → Confirm → verify `loan.repaid` choreography (4 consumers react)
3. **Default path:** Let repayment window expire → verify `loan.overdue` choreography (4 consumers react) + bulk delist

### 5.5 — Check all the "proof" touchpoints

These are what the instructors will look for:
- **KONG**: Requests going through the gateway (check KONG logs)
- **gRPC**: Payment Service handling financial operations over gRPC (show `.proto` file + grpcurl demo)
- **GraphQL**: Investor browsing marketplace via GraphQL (show GraphQL playground or Postman)
- **RabbitMQ**: Events flowing through queues (show Management UI)
- **Temporal**: Workflows running with durable timers (show Temporal UI)
- **OutSystems**: Activity log entries (show OutSystems UI)
- **Choreography**: Multiple consumers reacting independently to same event (show separate queues in RabbitMQ)

---

## Quick Reference: Useful URLs When Running Locally

| What | URL |
|------|-----|
| KONG (all API requests go here) | `http://localhost:8000` |
| RabbitMQ Management UI | `http://localhost:15672` (guest/guest) |
| Temporal UI | `http://localhost:8088` |
| MinIO Console | `http://localhost:9001` (minioadmin/minioadmin) |
| User Service Swagger | `http://localhost:5000/docs` |
| Invoice Service Swagger | `http://localhost:5001/docs` |
| Marketplace REST Swagger | `http://localhost:5002/docs` |
| Marketplace GraphQL | `http://localhost:5002/graphql` |
| Bidding Service Swagger | `http://localhost:5003/docs` |
| Payment Service REST Swagger | `http://localhost:5004/docs` |
| Notification Service Swagger | `http://localhost:5005/docs` |
| Invoice Orchestrator Swagger | `http://localhost:5010/docs` |
| Bidding Orchestrator Swagger | `http://localhost:5011/docs` |
| Loan Orchestrator Swagger | `http://localhost:5012/docs` |
| ACRA Wrapper Swagger | `http://localhost:5007/docs` |
| Stripe Wrapper Swagger | `http://localhost:5008/docs` |

---

## If You're Stuck

1. **Check the service logs:** `docker compose logs <service-name> --tail 50`
2. **Check if it's running:** `docker compose ps`
3. **Check the Swagger docs:** Hit `http://localhost:<port>/docs` directly — if Swagger loads, FastAPI is running fine
4. **Check RabbitMQ:** `http://localhost:15672` → Queues tab → see if messages are sitting undelivered
5. **Check Temporal:** `http://localhost:8088` → see if workflows are in a failed state
6. **Re-read the build instructions** for your service — the answer is usually in the "Key Classes" or "Important Logic" section
7. **Ask the team** — someone else's service might be the issue, not yours
