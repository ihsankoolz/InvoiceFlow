# InvoiceFlow - Invoice Factoring Marketplace

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docs.docker.com/compose/)
[![Microservices](https://img.shields.io/badge/Architecture-Microservices-green.svg)](https://microservices.io/)

> **SMU IS213 Enterprise Solution Development - Academic Project**  
> A production-grade invoice factoring marketplace using microservices architecture

## 📋 Table of Contents

- [Executive Summary](#executive-summary)
- [Business Problem](#business-problem)
- [Solution Overview](#solution-overview)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Beyond-The-Labs Features](#beyond-the-labs-features)
- [Quick Start](#quick-start)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Implementation Roadmap](#implementation-roadmap)
- [API Documentation](#api-documentation)
- [Team Contributions](#team-contributions)
- [Testing](#testing)
- [Deployment](#deployment)

---

## 🎯 Executive Summary

**InvoiceFlow** is a digital invoice factoring marketplace that helps SMEs (Small and Medium Enterprises) overcome cash flow constraints caused by long invoice payment cycles (30-90 days). Businesses can upload invoices, list them for auction, and sell them at a discount to investors seeking short-term returns.

### Key Metrics
- **Target Users**: 1000+ SMEs, 500+ investors
- **Average Transaction**: $10,000 - $100,000
- **Typical Discount**: 5-15%
- **Payment Cycle**: 30-90 days reduced to <24 hours

---

## 💡 Business Problem

### The Cash Flow Gap
Small businesses (e.g., bakeries, suppliers, contractors) face a critical problem:
1. **Deliver goods/services** → Customer receives invoice
2. **Wait 30-90 days** → Customer pays on due date
3. **Cash flow stuck** → Cannot pay suppliers, employees, or invest in growth

### Traditional Solutions (Limitations)
- **Bank loans**: Slow approval, high interest, requires collateral
- **Invoice factoring companies**: High fees (10-20%), complex contracts
- **Personal savings**: Limited, risky

### Our Solution
**InvoiceFlow Marketplace** enables:
- ✅ Instant liquidity (within 24-72 hours)
- ✅ Competitive rates through auction mechanism
- ✅ Transparent validation via OutSystems
- ✅ Automated escrow & settlement
- ✅ Lower fees (5-10% vs 10-20% traditional)

---

## 🏗️ Solution Overview

### Three Core User Scenarios

#### **Scenario 1: Business Lists Invoice for Auction**
```
Bakery submits invoice → OutSystems validates → Listed on marketplace
├── Invoice: $50,000 due in 60 days
├── Validation score: 85/100
├── Auction period: 48 hours
└── Status: ACTIVE
```

**Services**: User, Invoice, OutSystems (external), Marketplace

#### **Scenario 2: Investor Bids & Wins Auction** (Orchestration)
```
Multiple investors bid → Funds locked immediately → Auction closes → Winner selected
├── Investor A: $46,000 (locked)
├── Investor B: $45,500 (locked)
├── Investor C: $47,000 (locked) ← WINNER
└── Orchestration: Convert escrow → Create loan → Disburse $47k to bakery → Refund losers
```

**Services**: Marketplace, Bidding (orchestrator), Payment, Invoice

**Orchestration Steps**:
1. Verify invoice available
2. Convert winning bid escrow → loan escrow
3. Create loan record (principal: $47k, amount_due: $50k, due_date: 60 days)
4. Release $47k to bakery **[SCENARIO 2 ENDS]**
5. Refund losing bids
6. Delist from marketplace

#### **Scenario 3: Loan Maturity & Manual Repayment** (Choreography)
```
Maturity date arrives → 24h repayment window → Bakery repays manually → Investor receives funds
├── Day 60: Cron marks loan DUE
├── Notification: "Pay $50k within 24 hours"
├── Bakery clicks "Repay Loan" → $50k transferred
├── RabbitMQ event: "loan.repaid"
└── Invoice Service: status → REPAID
```

**Services**: Payment (publisher), Invoice (consumer - RabbitMQ)

---

## 🏛️ Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed diagrams and design decisions.

### High-Level Overview

```
┌─────────────────────────────────────────────────────────┐
│            PRESENTATION LAYER (React)                    │
│                  Port 8080                               │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│          KONG API GATEWAY (BTL #1)                       │
│     Rate Limiting • JWT Validation • Routing             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                 MICROSERVICES LAYER                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │
│  │  User    │ │ Invoice  │ │Marketplace│ │ Bidding  │   │
│  │  :5000   │ │  :5001   │ │   :5002   │ │  :5003   │   │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │
│                                                          │
│            ┌──────────────────────────┐                 │
│            │   Payment Service        │                 │
│            │      :5004               │                 │
│            │   gRPC Server (BTL #2)   │                 │
│            └──────────────────────────┘                 │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│              INTEGRATION LAYER                           │
│  ┌────────────────┐        ┌──────────────┐             │
│  │  OutSystems    │        │  RabbitMQ    │             │
│  │  (Validator)   │        │   :5672      │             │
│  └────────────────┘        └──────────────┘             │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│                   DATA LAYER                             │
│  MySQL Databases (5) + RabbitMQ Message Broker           │
└─────────────────────────────────────────────────────────┘
```

### Service Responsibilities

| Service | Port | Database | Key Responsibilities |
|---------|------|----------|---------------------|
| **User Service** | 5000 | user_db | Authentication (JWT), Registration, User profiles |
| **Invoice Service** | 5001 | invoice_db | Invoice creation, OutSystems validation, RabbitMQ consumer |
| **Marketplace Service** | 5002 | marketplace_db | Listing management, Auction deadline tracking, Search/filter |
| **Bidding Service** | 5003 | bidding_db | Bid management, **Orchestration**, Auction closer cron |
| **Payment Service** | 5004 | payment_db | Wallets, Bid/loan escrow, **gRPC server**, Maturity cron |

### Cron Jobs

| Cron Job | Schedule | Purpose |
|----------|----------|---------|
| **Auction Closer** | Every 1 hour | Close expired auctions, select highest bidder, trigger orchestration |
| **Maturity Checker** | Daily at 00:00 | Mark loans DUE, start 24h repayment window, notify borrowers |

---

## 🛠️ Technology Stack

### Backend Services
- **User, Invoice, Marketplace, Bidding**: Python 3.9 + Flask
- **Payment Service**: Node.js 18 + Express (for gRPC support)
- **OutSystems**: Low-code platform for invoice validation

### Databases
- **MySQL 8.0**: 5 separate databases (one per service)
- **RabbitMQ 3**: Message broker for event-driven choreography

### Communication Protocols
- **REST**: HTTP/JSON for most inter-service calls
- **gRPC** (BTL #2): High-performance payment operations
- **GraphQL** (BTL #3): Complex marketplace queries
- **RabbitMQ**: Asynchronous event publishing (loan.repaid)

### Infrastructure
- **Docker**: Containerization of all services
- **Docker Compose**: Multi-container orchestration
- **KONG API Gateway** (BTL #1): Centralized routing, rate limiting, authentication

### Frontend
- **React 18**: UI framework
- **Axios**: HTTP client
- **React Router**: Navigation
- **Tailwind CSS**: Styling

---

## 🚀 Beyond-The-Labs Features

> **Note**: RabbitMQ is covered in class (Module W5_3_Communication_TechnologiesMessaging.pdf), so it does NOT count as BTL.

### 1. KONG API Gateway ⭐ **[PRIMARY BTL]**

**What it is**: Open-source API gateway that sits in front of all microservices.

**Why it's BTL**: Not covered in labs. Requires independent research on:
- Declarative configuration (kong.yml)
- Rate limiting plugins
- JWT authentication plugin
- Service discovery

**Implementation**:
```yaml
# kong.yml
services:
  - name: user-service
    url: http://user-service:5000
    routes:
      - name: user-route
        paths:
          - /api/users
    plugins:
      - name: rate-limiting
        config:
          minute: 100
      - name: jwt
```

**Benefits for Our Scenario**:
- ✅ Single entry point for all API requests
- ✅ Rate limiting prevents bid spam (max 10 bids/minute)
- ✅ JWT validation at gateway (don't replicate in each service)
- ✅ Request logging for audit trail

**Justification**: 
Production-grade marketplaces require centralized API management to prevent abuse (e.g., bot bidding), ensure authentication consistency, and provide observability. KONG provides enterprise-level features without vendor lock-in.

---

### 2. gRPC for Payment Service ⭐ **[SECONDARY BTL]**

**What it is**: High-performance RPC framework using Protocol Buffers (binary serialization).

**Why it's BTL**: Not covered in labs. Requires:
- Learning Protocol Buffers syntax (.proto files)
- Code generation (protoc compiler)
- Bidirectional streaming concepts

**Implementation**:
```protobuf
// payment.proto
service PaymentService {
  rpc LockBidEscrow(BidEscrowRequest) returns (BidEscrowResponse);
  rpc ConvertToLoanEscrow(ConvertRequest) returns (ConvertResponse);
}

message BidEscrowRequest {
  int32 bid_id = 1;
  int32 investor_id = 2;
  double amount = 3;
}
```

**Use Cases**:
- Bidding Service → Payment Service: `LockBidEscrow()` (gRPC)
- Bidding Service → Invoice Service: `GetInvoice()` (still REST)

**Benefits for Our Scenario**:
- ✅ 3-5x faster than REST for critical payment operations
- ✅ Strong typing (prevents amount: "abc" bugs)
- ✅ Automatic retry/timeout handling

**Justification**:
Financial transactions require low latency and type safety. During auction close, the orchestrator makes ~10 payment calls sequentially. gRPC reduces latency from ~50ms/call (REST) to ~10ms/call, saving 400ms per auction.

---

### 3. GraphQL for Marketplace Queries ⭐ **[TERTIARY BTL]**

**What it is**: Query language that lets clients request exactly the data they need.

**Why it's BTL**: Not covered in labs. Requires:
- Schema design (GraphQL SDL)
- Resolver implementation
- Query optimization (N+1 problem)

**Implementation**:
```graphql
# schema.graphql
type Listing {
  invoice_token: String!
  amount: Float!
  asking_discount: Float!
  urgency_level: String!
  bid_deadline: String!
  seller: User!
  current_bids: [Bid!]!
  validation_score: Int
}

type Query {
  marketplaceListings(
    minAmount: Float
    maxAmount: Float
    urgency: String
    sort: String
  ): [Listing!]!
}
```

**Client Query Example**:
```graphql
query GetMarketplace {
  marketplaceListings(urgency: "HIGH", minAmount: 10000) {
    invoice_token
    amount
    bid_deadline
    seller {
      company_name
    }
    current_bids {
      offer_amount
      investor {
        email
      }
    }
  }
}
```

**Benefits for Our Scenario**:
- ✅ Reduce API calls: Get listing + seller + bids in ONE request (vs 3 REST calls)
- ✅ Frontend flexibility: Mobile app needs less data than web app
- ✅ Self-documenting API (GraphQL Playground)

**Justification**:
Marketplace frontends need complex nested data (listings with seller info, current bid count, validation details). REST forces multiple round-trips or over-fetching. GraphQL reduces from 5 API calls to 1, improving page load by 300-500ms.

---

### BTL Comparison

| Feature | Complexity | Impact | Lines of Code | Research Time |
|---------|-----------|--------|---------------|---------------|
| KONG Gateway | Medium | High | ~100 (config) | 8 hours |
| gRPC | High | Medium | ~300 | 12 hours |
| GraphQL | Medium | Medium | ~200 | 10 hours |

**Total Estimated Effort**: 30 hours (spread across 2 team members)

---

## ⚡ Quick Start

### Prerequisites
```bash
# Check installations
docker --version          # Need 20.10+
docker-compose --version  # Need 1.29+
node --version           # Need 18+
python --version         # Need 3.9+
```

### One-Command Startup
```bash
# Clone repo
git clone https://github.com/YOUR_USERNAME/invoiceflow-esd.git
cd invoiceflow-esd

# Copy environment template
cp .env.example .env

# Add your OutSystems API URL
nano .env  # Add OUTSYSTEMS_API_URL=https://your-app.outsystemscloud.com

# Start all services
docker-compose up --build

# Access application
open http://localhost:8080          # Frontend
open http://localhost:8001          # KONG Admin
open http://localhost:15672         # RabbitMQ Management (guest/guest)
```

### Test Accounts
```
Business User:
  Email: bakery@test.com
  Password: BakeryPass123

Investor User:
  Email: investor@test.com
  Password: InvestPass123
```

---

## 🔧 Development Setup

### Local Development (Without Docker)

#### 1. Setup MySQL Databases
```bash
# Install MySQL
brew install mysql         # macOS
sudo apt install mysql     # Ubuntu

# Create databases
mysql -u root -p < databases/user-init.sql
mysql -u root -p < databases/invoice-init.sql
mysql -u root -p < databases/marketplace-init.sql
mysql -u root -p < databases/bidding-init.sql
mysql -u root -p < databases/payment-init.sql
```

#### 2. Setup RabbitMQ
```bash
# Install RabbitMQ
brew install rabbitmq      # macOS
sudo apt install rabbitmq  # Ubuntu

# Start RabbitMQ
rabbitmq-server

# Enable management plugin
rabbitmq-plugins enable rabbitmq_management
```

#### 3. Run Services

**User Service**:
```bash
cd services/user-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
# Runs on http://localhost:5000
```

**Invoice Service**:
```bash
cd services/invoice-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py &
python rabbitmq_consumer.py &
# Runs on http://localhost:5001
```

**Marketplace Service**:
```bash
cd services/marketplace-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
# Runs on http://localhost:5002
```

**Bidding Service + Auction Closer**:
```bash
cd services/bidding-service
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py &
python cron/auction_closer.py &
# Runs on http://localhost:5003
```

**Payment Service + Maturity Checker**:
```bash
cd services/payment-service
npm install
node app.js &
node cron/maturity_checker.js &
# Runs on http://localhost:5004
```

**Frontend**:
```bash
cd frontend
npm install
npm start
# Runs on http://localhost:3000 (proxies to :8080 in Docker)
```

---

## 📁 Project Structure

```
invoiceflow-esd/
├── README.md                          # This file
├── ARCHITECTURE.md                    # Detailed architecture documentation
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore rules
├── docker-compose.yml                 # Multi-container orchestration
│
├── databases/                         # SQL initialization scripts
│   ├── user-init.sql
│   ├── invoice-init.sql
│   ├── marketplace-init.sql
│   ├── bidding-init.sql
│   └── payment-init.sql
│
├── services/
│   ├── user-service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app.py                    # Flask application
│   │   ├── models/
│   │   │   └── user.py
│   │   ├── routes/
│   │   │   ├── auth.py               # Login, register
│   │   │   └── profile.py
│   │   └── utils/
│   │       └── jwt_handler.py
│   │
│   ├── invoice-service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app.py
│   │   ├── routes/
│   │   │   ├── invoices.py
│   │   │   └── validation.py
│   │   ├── integrations/
│   │   │   └── outsystems.py         # OutSystems API client
│   │   └── rabbitmq_consumer.py      # Listens for loan.repaid
│   │
│   ├── marketplace-service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app.py
│   │   └── routes/
│   │       ├── listings.py
│   │       └── search.py
│   │
│   ├── bidding-service/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app.py
│   │   ├── routes/
│   │   │   └── offers.py
│   │   ├── orchestrator.py           # Orchestration logic
│   │   └── cron/
│   │       └── auction_closer.py     # Runs every hour
│   │
│   └── payment-service/
│       ├── Dockerfile
│       ├── package.json
│       ├── app.js                    # Express + gRPC server
│       ├── routes/
│       │   ├── wallets.js
│       │   ├── bid-escrow.js
│       │   ├── loan-escrow.js
│       │   └── loans.js
│       ├── grpc/
│       │   ├── payment.proto         # gRPC definitions
│       │   └── server.js             # gRPC server implementation
│       ├── rabbitmq/
│       │   └── publisher.js
│       └── cron/
│           └── maturity_checker.js   # Runs daily at midnight
│
├── gateway/                           # KONG API Gateway (BTL #1)
│   ├── kong.yml                      # Declarative config
│   └── docker-compose.override.yml
│
├── frontend/                          # React application
│   ├── Dockerfile
│   ├── package.json
│   ├── public/
│   └── src/
│       ├── App.js
│       ├── components/
│       │   ├── Auth/
│       │   │   ├── Login.js
│       │   │   └── Register.js
│       │   ├── Business/
│       │   │   ├── CreateInvoice.js
│       │   │   └── MyInvoices.js
│       │   ├── Marketplace/
│       │   │   ├── ListingsPage.js
│       │   │   └── PlaceBid.js
│       │   └── Investor/
│       │       ├── MyBids.js
│       │       └── MyLoans.js
│       ├── api/
│       │   ├── axios.js              # REST client
│       │   ├── graphql.js            # GraphQL client (BTL #3)
│       │   └── endpoints.js
│       └── utils/
│           └── auth.js
│
├── docs/                              # Additional documentation
│   ├── API.md                        # API documentation
│   ├── DEPLOYMENT.md                 # Deployment guide
│   └── TESTING.md                    # Testing strategy
│
└── scripts/                           # Utility scripts
    ├── seed-data.sh                  # Load test data
    └── reset-db.sh                   # Reset all databases
```

---

## 🗓️ Implementation Roadmap

### Week 9: Foundation & Core Services (Feb 10-16)

#### Day 1-2: Setup & Documentation ✅
- [x] Create Git repository
- [x] Write README.md & ARCHITECTURE.md
- [x] Setup project structure
- [x] Create database schemas
- [x] Write docker-compose.yml

#### Day 3-4: Simple Services
- [ ] User Service (authentication, JWT)
- [ ] Invoice Service (create, validate - mock OutSystems for now)
- [ ] Marketplace Service (list, search)
- [ ] Test inter-service HTTP communication

#### Day 5-7: Build OutSystems & Payment Basics
- [ ] Build actual OutSystems validator service
- [ ] Payment Service: wallets, bid escrow lock/refund
- [ ] Test Scenario 1 end-to-end (invoice creation → listing)

---

### Week 10: Complex Logic (Feb 17-23)

#### Day 1-3: Bidding & Orchestration
- [ ] Bidding Service: submit offers
- [ ] Auction closer cron job (runs every hour)
- [ ] Orchestration logic (8 steps)
- [ ] Rollback mechanisms
- [ ] Test Scenario 2 end-to-end (bid → auction close → funds disbursed)

#### Day 4-5: Loan Management
- [ ] Payment Service: loan creation, loan escrow
- [ ] Maturity checker cron (runs daily at midnight)
- [ ] Manual repayment endpoint
- [ ] Test 24-hour repayment window logic

#### Day 6-7: RabbitMQ Choreography
- [ ] Setup RabbitMQ exchanges (loan_events)
- [ ] Payment Service: publish loan.repaid event
- [ ] Invoice Service: consume event, update status
- [ ] Test Scenario 3 end-to-end (maturity → repayment → event → invoice updated)

---

### Week 11: BTL & Frontend (Feb 24 - Mar 2)

#### Day 1-2: KONG API Gateway
- [ ] Install KONG in docker-compose
- [ ] Configure services in kong.yml
- [ ] Add rate limiting plugin (10 bids/minute)
- [ ] Add JWT plugin
- [ ] Test all routes through KONG

#### Day 3-4: gRPC Implementation
- [ ] Write payment.proto file
- [ ] Generate gRPC code (protoc)
- [ ] Implement gRPC server in Payment Service
- [ ] Update Bidding Service to use gRPC client
- [ ] Benchmark: REST vs gRPC performance

#### Day 5: GraphQL Endpoint
- [ ] Add graphql-yoga to Marketplace Service
- [ ] Define schema (Listing, Bid, User types)
- [ ] Implement resolvers
- [ ] Test complex queries in GraphQL Playground

#### Day 6-7: Frontend Development
- [ ] Build login/register pages
- [ ] Business dashboard (create invoice)
- [ ] Marketplace page (browse, filter, bid)
- [ ] Investor dashboard (my bids, my loans)
- [ ] Connect to GraphQL endpoint for marketplace

---

### Week 12: Integration & Testing (Mar 3-9)

#### Day 1-3: End-to-End Testing
- [ ] Test all 3 scenarios with real data
- [ ] Test concurrent bids (race conditions)
- [ ] Test auction closer with multiple listings
- [ ] Test maturity checker with 10+ loans
- [ ] Test RabbitMQ message reliability

#### Day 4-5: Error Handling & Edge Cases
- [ ] Insufficient funds at bid placement
- [ ] Auction with zero bids
- [ ] Bakery insufficient funds at repayment
- [ ] Bakery misses 24h window
- [ ] OutSystems API down (retry logic)

#### Day 6-7: Documentation & Code Cleanup
- [ ] Write API.md (Swagger/OpenAPI)
- [ ] Add code comments
- [ ] Update README with final instructions
- [ ] Record demo video (3 minutes)

---

### Week 13: Presentation Prep (Mar 10-16)

#### Day 1-2: Create Presentation Slides
- [ ] Problem & solution (2 slides)
- [ ] Architecture diagram (1 slide)
- [ ] Scenario 1 demo (2 slides)
- [ ] Scenario 2 demo (2 slides)
- [ ] Scenario 3 demo (2 slides)
- [ ] BTL justification (2 slides)
- [ ] Challenges & learnings (1 slide)

#### Day 3-4: Rehearse Demo
- [ ] Practice live demo on 3 laptops
- [ ] Test without internet (localhost only)
- [ ] Prepare backup demo video
- [ ] Time the presentation (max 15 minutes)

#### Day 5: Final Submission
- [ ] Write project report (6 pages)
- [ ] Create video.txt with YouTube link
- [ ] Zip code and data files
- [ ] Submit on eLearn 30 min before class

---

## 📡 API Documentation

See [docs/API.md](./docs/API.md) for complete API reference.

### Quick Reference

#### Authentication
```bash
# Register
POST /api/users/register
{
  "email": "bakery@test.com",
  "password": "pass123",
  "user_type": "BUSINESS",
  "company_name": "Happy Bakery"
}

# Login
POST /api/users/login
{
  "email": "bakery@test.com",
  "password": "pass123"
}
# Returns: {"token": "eyJhbGc..."}
```

#### Invoice Management
```bash
# Create invoice
POST /api/invoices/create
Authorization: Bearer <token>
{
  "invoice_number": "INV-001",
  "debtor_name": "Hotel ABC",
  "amount": 50000,
  "due_date": "2026-05-10",
  "bid_period_hours": 48
}

# Get invoice
GET /api/invoices/INV-Ax7K2p
```

#### Marketplace
```bash
# Get listings (REST)
GET /api/marketplace/invoices?sort=urgency&minAmount=10000

# Get listings (GraphQL - BTL #3)
POST /graphql
{
  marketplaceListings(urgency: "HIGH") {
    invoice_token
    amount
    bid_deadline
    current_bids { offer_amount }
  }
}
```

#### Bidding
```bash
# Submit bid
POST /api/offers/submit
{
  "invoice_token": "INV-Ax7K2p",
  "investor_id": 5,
  "offer_amount": 47000,
  "discount_rate": 6.0
}
# Immediately locks $47k in bid_escrow
```

#### Payment (gRPC - BTL #2)
```protobuf
// Lock bid escrow
rpc LockBidEscrow(BidEscrowRequest) returns (BidEscrowResponse);

message BidEscrowRequest {
  int32 bid_id = 1;
  int32 investor_id = 2;
  double amount = 3;
}
```

---

## 👥 Team Contributions

| Member | Primary Services | Responsibilities |
|--------|-----------------|------------------|
| **Member 1** | User Service, Frontend Auth | Authentication, JWT, Login/Register UI |
| **Member 2** | Invoice Service, OutSystems | Invoice creation, Validation integration, RabbitMQ consumer |
| **Member 3** | Marketplace Service, GraphQL | Listings, Search, GraphQL endpoint (BTL #3) |
| **Member 4** | Bidding Service, Orchestration | Offers, Auction closer cron, Orchestration logic |
| **Member 5** | Payment Service, gRPC | Wallets, Escrow, Loans, gRPC server (BTL #2), Maturity cron |
| **Member 6** | KONG Gateway, Docker, Frontend | KONG setup (BTL #1), Docker Compose, React UI |

---

## 🧪 Testing

### Manual Testing Checklist

#### Scenario 1: Invoice Listing
- [ ] Business can register and login
- [ ] Invoice creation form works
- [ ] OutSystems validation called successfully
- [ ] Invoice appears in marketplace
- [ ] Urgency level calculated correctly
- [ ] Bid deadline displayed properly

#### Scenario 2: Auction & Purchase
- [ ] Investor can place bid
- [ ] Funds locked immediately in bid_escrow
- [ ] Multiple investors can bid on same invoice
- [ ] Auction closer cron runs every hour
- [ ] Highest bidder selected
- [ ] Orchestration completes all 8 steps
- [ ] Losing bids refunded
- [ ] Invoice status changed to FINANCED
- [ ] Bakery receives funds

#### Scenario 3: Repayment
- [ ] Maturity checker runs daily at midnight
- [ ] Loan marked DUE on maturity date
- [ ] 24-hour repayment window started
- [ ] Bakery can repay loan manually
- [ ] Investor receives funds
- [ ] RabbitMQ event published
- [ ] Invoice status changed to REPAID

### Load Testing
```bash
# Test concurrent bids (10 investors, same invoice)
./scripts/load-test-bids.sh

# Test auction closer with 100 expired listings
./scripts/load-test-auctions.sh
```

---

## 🚀 Deployment

### Production Considerations

#### Environment Variables
```bash
# .env.production
NODE_ENV=production
JWT_SECRET=<strong-secret>
OUTSYSTEMS_API_URL=https://prod.outsystemscloud.com
KONG_ADMIN_URL=http://kong:8001
RABBITMQ_URL=amqp://rabbitmq:5672
MYSQL_ROOT_PASSWORD=<strong-password>
```

#### Docker Compose (Production)
```yaml
# docker-compose.prod.yml
services:
  mysql-user:
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
    volumes:
      - /var/lib/mysql-user:/var/lib/mysql  # Persistent storage
    restart: always

  kong:
    environment:
      KONG_LOG_LEVEL: info
    restart: always
```

#### Monitoring
- **Logs**: `docker-compose logs -f <service>`
- **Health Checks**: `/health` endpoint on each service
- **RabbitMQ**: http://localhost:15672 (guest/guest)
- **KONG**: http://localhost:8001 (admin API)

---

## 📚 Additional Resources

- [ARCHITECTURE.md](./ARCHITECTURE.md) - Detailed architecture documentation
- [docs/API.md](./docs/API.md) - Complete API reference
- [docs/DEPLOYMENT.md](./docs/DEPLOYMENT.md) - Production deployment guide
- [docs/TESTING.md](./docs/TESTING.md) - Testing strategies

### External References
- [Microservices Patterns](https://microservices.io/patterns/index.html)
- [KONG Documentation](https://docs.konghq.com/)
- [gRPC Documentation](https://grpc.io/docs/)
- [GraphQL Documentation](https://graphql.org/learn/)
- [RabbitMQ Tutorials](https://www.rabbitmq.com/getstarted.html)

---

## 📄 License

This project is for academic purposes only (SMU IS213).

---

## 🙋 Support

For questions or issues:
1. Check [ARCHITECTURE.md](./ARCHITECTURE.md) for design decisions
2. See [docs/API.md](./docs/API.md) for API usage
3. Contact team members via Telegram group

---

**Last Updated**: February 18, 2026  
**Version**: 1.0.0  
**Team**: InvoiceFlow (SMU IS213 AY2025/26)
