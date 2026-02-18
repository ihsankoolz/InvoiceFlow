# InvoiceFlow - Architecture Documentation

> **Detailed technical architecture, design decisions, and system diagrams**

## Table of Contents

- [System Architecture Overview](#system-architecture-overview)
- [Microservices Detailed Design](#microservices-detailed-design)
- [Database Schemas](#database-schemas)
- [Communication Patterns](#communication-patterns)
- [Scenario Flows](#scenario-flows)
- [Design Decisions & Rationale](#design-decisions--rationale)
- [Security Architecture](#security-architecture)
- [Scalability & Performance](#scalability--performance)
- [Error Handling & Resilience](#error-handling--resilience)

---

## System Architecture Overview

### SOA Layer Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                              │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │               React Frontend (Port 8080)                  │     │
│  │  • Business Dashboard    • Marketplace Page               │     │
│  │  • Investor Dashboard    • Authentication                 │     │
│  └──────────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────┘
                                ↓ HTTP/S
┌────────────────────────────────────────────────────────────────────┐
│                       API GATEWAY LAYER                             │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │     KONG API Gateway (BTL #1) - Port 8000/8001           │     │
│  │                                                            │     │
│  │  Plugins:                                                 │     │
│  │  ├── Rate Limiting (100 req/min per user)                │     │
│  │  ├── JWT Authentication                                   │     │
│  │  ├── CORS                                                 │     │
│  │  ├── Request Logging                                      │     │
│  │  └── Response Transformation                              │     │
│  │                                                            │     │
│  │  Routes:                                                  │     │
│  │  ├── /api/users      → user-service:5000                 │     │
│  │  ├── /api/invoices   → invoice-service:5001              │     │
│  │  ├── /api/marketplace → marketplace-service:5002         │     │
│  │  ├── /api/offers     → bidding-service:5003              │     │
│  │  └── /api/payments   → payment-service:5004              │     │
│  └──────────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────┘
                     ↓ REST/gRPC/GraphQL
┌────────────────────────────────────────────────────────────────────┐
│                    BUSINESS LOGIC LAYER                             │
│                                                                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │    User     │  │  Invoice    │  │ Marketplace │               │
│  │  Service    │  │  Service    │  │  Service    │               │
│  │   :5000     │  │   :5001     │  │   :5002     │               │
│  │             │  │             │  │             │               │
│  │ Flask/REST  │  │ Flask/REST  │  │ Flask/REST  │               │
│  │             │  │ + RabbitMQ  │  │ + GraphQL   │               │
│  │             │  │  Consumer   │  │  (BTL #3)   │               │
│  └─────────────┘  └─────────────┘  └─────────────┘               │
│                                                                     │
│  ┌─────────────┐  ┌──────────────────────────────┐               │
│  │  Bidding    │  │    Payment Service            │               │
│  │  Service    │  │       :5004                   │               │
│  │   :5003     │  │                               │               │
│  │             │  │  Node.js/Express              │               │
│  │ Flask/REST  │  │  + gRPC Server (BTL #2)       │               │
│  │ Orchestrator│  │  + RabbitMQ Publisher         │               │
│  └─────────────┘  └──────────────────────────────┘               │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐     │
│  │                    BACKGROUND JOBS                        │     │
│  │                                                            │     │
│  │  ┌─────────────────────┐  ┌─────────────────────┐        │     │
│  │  │  Auction Closer     │  │  Maturity Checker   │        │     │
│  │  │  (Every 1 hour)     │  │  (Daily at 00:00)   │        │     │
│  │  │                     │  │                     │        │     │
│  │  │  • Find expired     │  │  • Find loans due   │        │     │
│  │  │  • Select winner    │  │  • Mark DUE         │        │     │
│  │  │  • Trigger orchest. │  │  • Start 24h window │        │     │
│  │  │  • Refund losers    │  │  • Notify borrower  │        │     │
│  │  └─────────────────────┘  └─────────────────────┘        │     │
│  └──────────────────────────────────────────────────────────┘     │
└────────────────────────────────────────────────────────────────────┘
                     ↓ HTTP/gRPC
┌────────────────────────────────────────────────────────────────────┐
│                     INTEGRATION LAYER                               │
│                                                                     │
│  ┌────────────────────┐          ┌────────────────────┐           │
│  │   OutSystems       │          │    RabbitMQ        │           │
│  │  (External API)    │          │  Message Broker    │           │
│  │                    │          │     :5672          │           │
│  │  Invoice Validator │          │                    │           │
│  │  POST /validate    │          │  Exchange:         │           │
│  │                    │          │  • loan_events     │           │
│  │  Returns:          │          │                    │           │
│  │  {                 │          │  Queues:           │           │
│  │    valid: bool,    │          │  • invoice_updates │           │
│  │    score: 0-100    │          │                    │           │
│  │  }                 │          │  Routing Keys:     │           │
│  │                    │          │  • loan.repaid     │           │
│  └────────────────────┘          └────────────────────┘           │
└────────────────────────────────────────────────────────────────────┘
                     ↓ SQL
┌────────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                   │
│                                                                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐     │
│  │ MySQL   │ │ MySQL   │ │ MySQL   │ │ MySQL   │ │ MySQL   │     │
│  │ user_db │ │invoice  │ │market   │ │bidding  │ │payment  │     │
│  │         │ │  _db    │ │ _db     │ │  _db    │ │  _db    │     │
│  │         │ │         │ │         │ │         │ │         │     │
│  │ users   │ │invoices │ │listings │ │offers   │ │wallets  │     │
│  │         │ │owner    │ │         │ │trans    │ │bid_esc  │     │
│  │         │ │  _hist  │ │         │ │  act    │ │loans    │     │
│  │         │ │         │ │         │ │         │ │escrow   │     │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘     │
└────────────────────────────────────────────────────────────────────┘
```

---

## Microservices Detailed Design

### Service 1: User Service

**Technology**: Python 3.9 + Flask  
**Port**: 5000  
**Database**: user_db (MySQL)

#### Responsibilities
- User registration (BUSINESS, INVESTOR)
- Login with JWT token generation
- User profile management
- Authentication middleware

#### API Endpoints
```
POST   /register          Create new user account
POST   /login             Authenticate & get JWT token
GET    /profile/{userId}  Get user profile
PUT    /profile/{userId}  Update user profile
GET    /health            Health check
```

#### Key Features
- **Password Hashing**: bcrypt with salt rounds = 10
- **JWT Tokens**: HS256, 24-hour expiry
- **Rate Limiting**: Max 5 login attempts per 15 minutes (via KONG)

#### Dependencies
- Flask 2.3
- PyJWT 2.8
- bcrypt 4.0
- mysql-connector-python 8.0

---

### Service 2: Invoice Service

**Technology**: Python 3.9 + Flask  
**Port**: 5001  
**Database**: invoice_db (MySQL)

#### Responsibilities
- Generate unique invoice tokens (8 chars alphanumeric)
- Store invoice records
- Call OutSystems validator API
- Track invoice status lifecycle
- Consume RabbitMQ events (loan.repaid)

#### API Endpoints
```
POST   /invoices/create              Create new invoice
POST   /invoices/validate            Validate via OutSystems
GET    /invoices/{token}             Get invoice details
PUT    /invoices/{token}/status      Update invoice status
GET    /invoices/seller/{sellerId}   Get seller's invoices
```

#### Invoice Status Lifecycle
```
CREATED → VALIDATED → LISTED → FINANCED → REPAID
    ↓
REJECTED (if validation fails)
```

#### OutSystems Integration
```python
import requests

def validate_invoice(invoice_data):
    url = os.getenv('OUTSYSTEMS_API_URL') + '/validate'
    headers = {
        'Authorization': f'Bearer {OUTSYSTEMS_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    response = requests.post(
        url,
        json={
            'invoice_number': invoice_data['invoice_number'],
            'amount': invoice_data['amount'],
            'due_date': invoice_data['due_date'],
            'debtor_name': invoice_data['debtor_name']
        },
        headers=headers,
        timeout=10  # 10 second timeout
    )
    
    if response.status_code == 200:
        result = response.json()
        return {
            'valid': result['valid'],
            'score': result['score'],
            'risk_level': result.get('risk_level', 'UNKNOWN')
        }
    else:
        raise Exception(f"Validation failed: {response.text}")
```

#### RabbitMQ Consumer
```python
import pika
import json

def start_consumer():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters('rabbitmq')
    )
    channel = connection.channel()
    
    # Declare exchange
    channel.exchange_declare(
        exchange='loan_events',
        exchange_type='topic',
        durable=True
    )
    
    # Declare queue
    result = channel.queue_declare(
        queue='invoice_loan_updates',
        durable=True
    )
    
    # Bind queue
    channel.queue_bind(
        exchange='loan_events',
        queue='invoice_loan_updates',
        routing_key='loan.repaid'
    )
    
    # Consume messages
    channel.basic_consume(
        queue='invoice_loan_updates',
        on_message_callback=callback,
        auto_ack=False  # Manual acknowledgment
    )
    
    print('Invoice Service: Listening for loan events...')
    channel.start_consuming()

def callback(ch, method, properties, body):
    event = json.loads(body)
    
    if method.routing_key == 'loan.repaid':
        invoice_token = event['invoice_token']
        
        # Update invoice status
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "UPDATE invoices SET status = 'REPAID' WHERE invoice_token = %s",
            (invoice_token,)
        )
        db.commit()
        
        print(f"✅ Invoice {invoice_token} marked as REPAID")
        
        # Manual acknowledgment
        ch.basic_ack(delivery_tag=method.delivery_tag)
```

---

### Service 3: Marketplace Service

**Technology**: Python 3.9 + Flask + GraphQL (graphql-core-next)  
**Port**: 5002  
**Database**: marketplace_db (MySQL)

#### Responsibilities
- List validated invoices with bid deadlines
- Calculate urgency levels (URGENT, HIGH, MEDIUM, LOW)
- Search and filter listings
- Track auction expiry
- Remove sold invoices
- Expose GraphQL endpoint (BTL #3)

#### REST API Endpoints
```
GET    /marketplace/invoices          Get all active listings
GET    /marketplace/invoices/{token}  Get specific listing
POST   /marketplace/list/{token}      Create listing
DELETE /marketplace/delist/{token}    Remove listing
GET    /marketplace/expired            Get expired listings
PUT    /marketplace/expire/{token}    Mark listing as expired
```

#### GraphQL Schema (BTL #3)
```graphql
type Listing {
  invoice_token: String!
  seller_id: Int!
  seller: User!
  debtor_name: String!
  amount: Float!
  asking_discount: Float!
  due_date: String!
  validation_score: Int
  bid_deadline: String!
  urgency_level: UrgencyLevel!
  hours_remaining: Int!
  is_expiring_soon: Boolean!
  current_bids: [Bid!]!
  bid_count: Int!
  highest_bid: Float
  status: ListingStatus!
  listed_at: String!
}

type Bid {
  id: Int!
  investor: User!
  offer_amount: Float!
  discount_rate: Float!
  created_at: String!
}

type User {
  id: Int!
  email: String!
  user_type: UserType!
  company_name: String
}

enum UrgencyLevel {
  LOW
  MEDIUM
  HIGH
  URGENT
}

enum ListingStatus {
  ACTIVE
  SOLD
  EXPIRED
}

enum UserType {
  BUSINESS
  INVESTOR
}

type Query {
  marketplaceListings(
    minAmount: Float
    maxAmount: Float
    urgency: UrgencyLevel
    minScore: Int
    sort: String
  ): [Listing!]!
  
  listing(token: String!): Listing
}
```

#### Urgency Level Calculation
```python
def calculate_urgency(bid_period_hours):
    if bid_period_hours <= 24:
        return 'URGENT'
    elif bid_period_hours <= 48:
        return 'HIGH'
    elif bid_period_hours <= 120:  # 5 days
        return 'MEDIUM'
    else:
        return 'LOW'
```

---

### Service 4: Bidding Service (Orchestrator)

**Technology**: Python 3.9 + Flask  
**Port**: 5003  
**Database**: bidding_db (MySQL)

#### Responsibilities
- Manage investor bids
- Lock funds immediately when bid placed
- Orchestrate loan disbursement (8-step workflow)
- Handle rollback on failure
- Run auction closer cron (every hour)

#### API Endpoints
```
POST   /offers/submit           Submit new bid (locks funds)
GET    /offers/invoice/{token}  Get all bids for invoice
PUT    /offers/{id}/auto-accept Trigger orchestration (called by cron)
PUT    /offers/{id}/reject      Reject offer (refund escrow)
DELETE /offers/{id}/cancel      Cancel offer (refund escrow)
GET    /health                  Health check
```

#### Orchestration Flow (8 Steps)

```python
def orchestrate_loan_disbursement(offer_id):
    """
    Orchestrates the complete loan disbursement process
    Called when auction closes and winner is selected
    """
    offer = get_offer(offer_id)
    loan_id = str(uuid.uuid4())
    rollback_steps = []
    
    try:
        # ──────────────────────────────────────────────────
        # STEP 0: Save transaction
        # ──────────────────────────────────────────────────
        save_transaction(loan_id, status='INITIATED')
        
        # ──────────────────────────────────────────────────
        # STEP 1: Verify invoice available
        # ──────────────────────────────────────────────────
        resp = requests.get(
            f"http://invoice-service:5001/invoices/{offer['invoice_token']}",
            timeout=5
        )
        
        if resp.status_code != 200:
            raise Exception("Invoice service unavailable")
        
        invoice = resp.json()['data']
        
        if invoice['status'] != 'LISTED':
            raise Exception(f"Invoice not available (status: {invoice['status']})")
        
        # ──────────────────────────────────────────────────
        # STEP 2: Convert bid_escrow → loan_escrow
        # ──────────────────────────────────────────────────
        # Funds already locked in bid_escrow
        # Just need to convert the escrow type
        resp = requests.post(
            "http://payment-service:5004/payments/bid-escrow-to-loan",
            json={
                "bid_id": offer_id,
                "loan_id": loan_id
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            raise Exception(f"Escrow conversion failed: {resp.json()['error']}")
        
        rollback_steps.append('revert_escrow')
        
        # ──────────────────────────────────────────────────
        # STEP 3: Create loan record
        # ──────────────────────────────────────────────────
        resp = requests.post(
            "http://payment-service:5004/loans/create",
            json={
                "loan_id": loan_id,
                "invoice_token": offer['invoice_token'],
                "lender_id": offer['investor_id'],
                "borrower_id": invoice['seller_id'],
                "principal": offer['offer_amount'],
                "amount_due": invoice['amount'],
                "due_date": invoice['due_date']
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            raise Exception("Loan creation failed")
        
        # ──────────────────────────────────────────────────
        # STEP 4: Release funds to seller (BAKERY RECEIVES)
        # ──────────────────────────────────────────────────
        # *** SCENARIO 2 ENDS HERE ***
        resp = requests.post(
            "http://payment-service:5004/payments/escrow-release",
            json={
                "transaction_id": loan_id,
                "seller_id": invoice['seller_id']
            },
            timeout=5
        )
        
        if resp.status_code != 200:
            raise Exception("Payment release failed")
        
        print(f"✅ Funds disbursed to bakery: ${offer['offer_amount']}")
        print(f"🎉 SCENARIO 2 COMPLETE")
        
        # ──────────────────────────────────────────────────
        # STEP 5: Update invoice status to FINANCED
        # ──────────────────────────────────────────────────
        requests.put(
            f"http://invoice-service:5001/invoices/{offer['invoice_token']}/status",
            json={"status": "FINANCED"},
            timeout=5
        )
        
        # ──────────────────────────────────────────────────
        # STEP 6: Delist from marketplace
        # ──────────────────────────────────────────────────
        requests.delete(
            f"http://marketplace-service:5002/marketplace/delist/{offer['invoice_token']}",
            timeout=5
        )
        
        # ──────────────────────────────────────────────────
        # STEP 7: Complete transaction
        # ──────────────────────────────────────────────────
        save_transaction(loan_id, status='COMPLETED')
        
        # ──────────────────────────────────────────────────
        # STEP 8: Update offer status
        # ──────────────────────────────────────────────────
        update_offer(offer_id, status='ACCEPTED')
        
        return {"success": True, "loan_id": loan_id}
        
    except Exception as e:
        # ──────────────────────────────────────────────────
        # ROLLBACK SEQUENCE
        # ──────────────────────────────────────────────────
        print(f"❌ Orchestration failed: {str(e)}")
        
        if 'revert_escrow' in rollback_steps:
            # Convert loan_escrow back to bid_escrow
            requests.post(
                "http://payment-service:5004/payments/loan-escrow-to-bid",
                json={"loan_id": loan_id, "bid_id": offer_id}
            )
        
        save_transaction(loan_id, status='FAILED')
        raise e
```

#### Auction Closer Cron Job
```python
# cron/auction_closer.py
import schedule
import time
from datetime import datetime

def close_expired_auctions():
    """
    Runs every hour:
    1. Find expired listings
    2. Get pending bids
    3. Select highest bidder
    4. Trigger orchestration
    5. Refund losing bidders
    """
    print(f"⏰ [AUCTION CLOSER] Running at {datetime.now()}")
    
    # Get expired listings
    resp = requests.get("http://marketplace-service:5002/marketplace/expired")
    expired_listings = resp.json()['data']
    
    for listing in expired_listings:
        invoice_token = listing['invoice_token']
        
        # Get all pending offers
        offers_resp = requests.get(
            f"http://localhost:5003/offers/invoice/{invoice_token}"
        )
        offers = offers_resp.json()['data']
        pending_offers = [o for o in offers if o['status'] == 'PENDING']
        
        if not pending_offers:
            # No bids - mark as expired
            requests.put(
                f"http://marketplace-service:5002/marketplace/expire/{invoice_token}"
            )
            continue
        
        # Sort by offer amount (highest first)
        pending_offers.sort(key=lambda x: x['offer_amount'], reverse=True)
        
        highest_bid = pending_offers[0]
        losing_bids = pending_offers[1:]
        
        try:
            # Accept winner (triggers orchestration)
            requests.put(
                f"http://localhost:5003/offers/{highest_bid['id']}/auto-accept"
            )
            
            print(f"✅ Winner: Bid {highest_bid['id']} - ${highest_bid['offer_amount']}")
            
            # Refund losers
            for losing_bid in losing_bids:
                requests.post(
                    "http://payment-service:5004/payments/bid-escrow-refund",
                    json={"bid_id": losing_bid['id']}
                )
                
                requests.put(
                    f"http://localhost:5003/offers/{losing_bid['id']}/reject",
                    json={"reason": "OUTBID"}
                )
                
                print(f"💰 Refunded bid {losing_bid['id']}")
                
        except Exception as e:
            print(f"❌ Error closing auction: {str(e)}")

# Schedule: Every hour
schedule.every(1).hours.do(close_expired_auctions)

print("🚀 Auction closer started - runs every hour")
while True:
    schedule.run_pending()
    time.sleep(60)  # Check every minute
```

---

### Service 5: Payment Service

**Technology**: Node.js 18 + Express + gRPC  
**Port**: 5004 (HTTP), 50051 (gRPC)  
**Database**: payment_db (MySQL)

#### Responsibilities
- Manage user wallets
- Lock/release bid escrow
- Convert bid escrow ↔ loan escrow
- Create and manage loans
- Process manual repayments
- Publish RabbitMQ events
- Expose gRPC endpoints (BTL #2)
- Run maturity checker cron (daily at midnight)

#### REST API Endpoints
```
GET    /wallets/{userId}              Get wallet balance
POST   /payments/bid-escrow-lock      Lock funds for bid
POST   /payments/bid-escrow-refund    Refund losing bid
POST   /payments/bid-escrow-to-loan   Convert escrow type
POST   /payments/loan-escrow-to-bid   Revert escrow (rollback)
POST   /payments/escrow-release       Release to seller
POST   /loans/create                  Create loan record
POST   /payments/loan-repayment       Process manual repayment
GET    /loans/due-today               Get loans maturing today
PUT    /loans/{loanId}/mark-due       Start 24h repayment window
```

#### gRPC Definitions (BTL #2)
```protobuf
// grpc/payment.proto
syntax = "proto3";

package payment;

service PaymentService {
  // High-performance critical operations
  rpc LockBidEscrow(BidEscrowRequest) returns (BidEscrowResponse);
  rpc ReleaseBidEscrow(BidEscrowRequest) returns (BidEscrowResponse);
  rpc ConvertEscrow(ConvertEscrowRequest) returns (ConvertEscrowResponse);
  rpc GetWalletBalance(WalletRequest) returns (WalletResponse);
}

message BidEscrowRequest {
  int32 bid_id = 1;
  int32 investor_id = 2;
  double amount = 3;
}

message BidEscrowResponse {
  bool success = 1;
  string message = 2;
  double locked_amount = 3;
}

message ConvertEscrowRequest {
  int32 bid_id = 1;
  string loan_id = 2;
}

message ConvertEscrowResponse {
  bool success = 1;
  string message = 2;
}

message WalletRequest {
  int32 user_id = 1;
}

message WalletResponse {
  int32 user_id = 1;
  double balance = 2;
  string currency = 3;
}
```

#### gRPC Server Implementation
```javascript
// grpc/server.js
const grpc = require('@grpc/grpc-js');
const protoLoader = require('@grpc/proto-loader');

const PROTO_PATH = './grpc/payment.proto';

const packageDefinition = protoLoader.loadSync(PROTO_PATH);
const paymentProto = grpc.loadPackageDefinition(packageDefinition).payment;

// Implement gRPC methods
const paymentServiceImpl = {
  LockBidEscrow: async (call, callback) => {
    const { bid_id, investor_id, amount } = call.request;
    
    try {
      // Same logic as REST endpoint, but faster
      const result = await lockBidEscrowDB(bid_id, investor_id, amount);
      
      callback(null, {
        success: true,
        message: 'Escrow locked successfully',
        locked_amount: amount
      });
    } catch (error) {
      callback({
        code: grpc.status.INTERNAL,
        details: error.message
      });
    }
  },
  
  // ... other methods
};

// Start gRPC server
const server = new grpc.Server();
server.addService(paymentProto.PaymentService.service, paymentServiceImpl);
server.bindAsync(
  '0.0.0.0:50051',
  grpc.ServerCredentials.createInsecure(),
  () => {
    console.log('gRPC server running on port 50051');
    server.start();
  }
);
```

#### Maturity Checker Cron Job
```javascript
// cron/maturity_checker.js
const schedule = require('node-schedule');
const axios = require('axios');

// Run every day at midnight (00:00)
schedule.scheduleJob('0 0 * * *', async function() {
  console.log(`⏰ [MATURITY CHECKER] Running at ${new Date()}`);
  
  try {
    // Find loans due today
    const response = await axios.get('http://localhost:5004/loans/due-today');
    const dueLoans = response.data.data;
    
    if (dueLoans.length === 0) {
      console.log('✅ No loans due today');
      return;
    }
    
    console.log(`📋 Found ${dueLoans.length} loans reaching maturity today`);
    
    for (const loan of dueLoans) {
      // START 24-HOUR REPAYMENT WINDOW
      const windowStart = new Date();
      const windowEnd = new Date(windowStart.getTime() + (24 * 60 * 60 * 1000));
      
      // Update loan status to DUE
      await axios.put(`http://localhost:5004/loans/${loan.loan_id}/mark-due`, {
        repayment_window_start: windowStart.toISOString(),
        repayment_window_end: windowEnd.toISOString()
      });
      
      console.log(`📅 Loan ${loan.loan_id} marked as DUE - 24h window started`);
      
      // NOTIFY BAKERY (borrower)
      console.log(`📧 Notification sent to borrower ${loan.borrower_id}`);
      console.log(`   "Your loan of $${loan.amount_due} is due. Pay within 24 hours."`);
    }
  } catch (error) {
    console.error('❌ Maturity checker error:', error.message);
  }
});

console.log('🚀 Maturity checker started - runs daily at midnight');
```

---

## Database Schemas

### user_db

```sql
CREATE DATABASE user_db;
USE user_db;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  user_type ENUM('BUSINESS', 'INVESTOR') NOT NULL,
  company_name VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_email (email),
  INDEX idx_user_type (user_type)
);

-- Sample data
INSERT INTO users (email, password_hash, user_type, company_name) VALUES
('bakery@test.com', '$2b$10$...', 'BUSINESS', 'Happy Bakery'),
('investor@test.com', '$2b$10$...', 'INVESTOR', NULL);
```

### invoice_db

```sql
CREATE DATABASE invoice_db;
USE invoice_db;

CREATE TABLE invoices (
  id INT AUTO_INCREMENT PRIMARY KEY,
  invoice_token VARCHAR(20) UNIQUE NOT NULL,
  invoice_number VARCHAR(100) NOT NULL,
  seller_id INT NOT NULL,
  debtor_name VARCHAR(255) NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'USD',
  issue_date DATE NOT NULL,
  due_date DATE NOT NULL,
  document_url TEXT,
  status ENUM('CREATED', 'VALIDATED', 'LISTED', 'FINANCED', 'REPAID', 'REJECTED') DEFAULT 'CREATED',
  validation_score INT,
  bid_period_hours INT DEFAULT 72,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  UNIQUE KEY unique_invoice (seller_id, invoice_number),
  INDEX idx_seller (seller_id),
  INDEX idx_status (status),
  INDEX idx_token (invoice_token)
);

CREATE TABLE ownership_history (
  id INT AUTO_INCREMENT PRIMARY KEY,
  invoice_token VARCHAR(20) NOT NULL,
  from_user_id INT,
  to_user_id INT NOT NULL,
  transfer_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  transaction_type VARCHAR(50) NOT NULL,
  transfer_amount DECIMAL(12,2),
  
  FOREIGN KEY (invoice_token) REFERENCES invoices(invoice_token),
  INDEX idx_invoice (invoice_token),
  INDEX idx_to_user (to_user_id)
);
```

### marketplace_db

```sql
CREATE DATABASE marketplace_db;
USE marketplace_db;

CREATE TABLE listings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  invoice_token VARCHAR(20) UNIQUE NOT NULL,
  seller_id INT NOT NULL,
  debtor_name VARCHAR(255) NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  asking_discount DECIMAL(5,2) NOT NULL,
  due_date DATE NOT NULL,
  validation_score INT,
  
  -- Bidding period fields
  bid_deadline DATETIME NOT NULL,
  urgency_level ENUM('LOW', 'MEDIUM', 'HIGH', 'URGENT') DEFAULT 'MEDIUM',
  
  status ENUM('ACTIVE', 'SOLD', 'EXPIRED') DEFAULT 'ACTIVE',
  listed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_status (status),
  INDEX idx_amount (amount),
  INDEX idx_deadline (bid_deadline),
  INDEX idx_urgency (urgency_level),
  INDEX idx_score (validation_score),
  INDEX idx_composite (status, urgency_level, bid_deadline)
);
```

### bidding_db

```sql
CREATE DATABASE bidding_db;
USE bidding_db;

CREATE TABLE offers (
  id INT AUTO_INCREMENT PRIMARY KEY,
  invoice_token VARCHAR(20) NOT NULL,
  investor_id INT NOT NULL,
  discount_rate DECIMAL(5,2) NOT NULL,
  offer_amount DECIMAL(12,2) NOT NULL,
  status ENUM('PENDING', 'ACCEPTED', 'REJECTED', 'CANCELLED', 'FAILED') DEFAULT 'PENDING',
  rejection_reason VARCHAR(255),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_invoice (invoice_token),
  INDEX idx_investor (investor_id),
  INDEX idx_status (status),
  INDEX idx_composite (invoice_token, status)
);

CREATE TABLE transactions (
  id INT AUTO_INCREMENT PRIMARY KEY,
  transaction_id VARCHAR(36) UNIQUE NOT NULL,
  invoice_token VARCHAR(20) NOT NULL,
  buyer_id INT NOT NULL,
  seller_id INT NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  status ENUM('INITIATED', 'COMPLETED', 'FAILED') NOT NULL,
  failure_reason TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  completed_at TIMESTAMP NULL,
  
  INDEX idx_transaction (transaction_id),
  INDEX idx_status (status)
);
```

### payment_db

```sql
CREATE DATABASE payment_db;
USE payment_db;

CREATE TABLE wallets (
  user_id INT PRIMARY KEY,
  balance DECIMAL(12,2) DEFAULT 0,
  currency VARCHAR(3) DEFAULT 'USD',
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  CHECK (balance >= 0)
);

CREATE TABLE bid_escrow (
  id INT AUTO_INCREMENT PRIMARY KEY,
  bid_id INT NOT NULL,
  investor_id INT NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  status ENUM('LOCKED', 'RELEASED', 'REFUNDED') NOT NULL,
  locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  released_at TIMESTAMP NULL,
  
  UNIQUE KEY unique_bid (bid_id),
  INDEX idx_investor (investor_id),
  INDEX idx_status (status)
);

CREATE TABLE escrow (
  id INT AUTO_INCREMENT PRIMARY KEY,
  transaction_id VARCHAR(36) UNIQUE NOT NULL,
  investor_id INT NOT NULL,
  amount DECIMAL(12,2) NOT NULL,
  status ENUM('LOCKED', 'RELEASED') NOT NULL,
  locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  released_at TIMESTAMP NULL,
  
  INDEX idx_transaction (transaction_id),
  INDEX idx_status (status)
);

CREATE TABLE loans (
  id INT AUTO_INCREMENT PRIMARY KEY,
  loan_id VARCHAR(36) UNIQUE NOT NULL,
  invoice_token VARCHAR(20) NOT NULL,
  lender_id INT NOT NULL,
  borrower_id INT NOT NULL,
  principal DECIMAL(12,2) NOT NULL,
  amount_due DECIMAL(12,2) NOT NULL,
  disbursed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  due_date DATE NOT NULL,
  
  -- Repayment window tracking (SCENARIO 3)
  repayment_window_start DATETIME NULL,
  repayment_window_end DATETIME NULL,
  repaid_at TIMESTAMP NULL,
  
  status ENUM('ACTIVE', 'DUE', 'REPAID', 'OVERDUE', 'DEFAULTED') DEFAULT 'ACTIVE',
  
  INDEX idx_invoice (invoice_token),
  INDEX idx_lender (lender_id),
  INDEX idx_borrower (borrower_id),
  INDEX idx_status (status),
  INDEX idx_due_date (due_date)
);

CREATE TABLE payments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  from_user_id INT,
  to_user_id INT,
  amount DECIMAL(12,2) NOT NULL,
  payment_type VARCHAR(50),
  reference_id VARCHAR(100),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  INDEX idx_from (from_user_id),
  INDEX idx_to (to_user_id),
  INDEX idx_reference (reference_id)
);
```

---

## Communication Patterns

### 1. Synchronous HTTP/REST

**Used For**: Most inter-service communication

```
Bidding Service → Invoice Service: GET /invoices/{token}
Bidding Service → Payment Service: POST /payments/escrow-lock
Marketplace Service → Invoice Service: GET /invoices/{token}
```

**Advantages**:
- Simple request/response
- Easy to debug
- Well-understood pattern

**Disadvantages**:
- Blocking calls
- Coupled services
- Latency adds up

---

### 2. Synchronous gRPC (BTL #2)

**Used For**: High-performance payment operations

```
Bidding Service → Payment Service (gRPC): LockBidEscrow()
```

**Why gRPC Instead of REST**:
- **3-5x faster**: Binary Protocol Buffers vs JSON parsing
- **Type safety**: Prevents amount: "abc" bugs
- **Automatic retries**: Built-in retry logic
- **Streaming**: Future support for real-time balance updates

**Performance Comparison**:
```
REST:  50-70ms average latency
gRPC:  10-15ms average latency
Savings: 35-60ms per call × 10 calls = 350-600ms per auction
```

---

### 3. Asynchronous RabbitMQ (Choreography)

**Used For**: Event-driven decoupling (Scenario 3)

```
Payment Service → RabbitMQ: Publish "loan.repaid"
                    ↓
                Invoice Service: Consume event → Update status
```

**Exchange Configuration**:
```yaml
Exchange: loan_events
Type: topic
Durable: true

Queues:
  - invoice_loan_updates (routing_key: loan.repaid)
  
Bindings:
  loan_events --[loan.repaid]--> invoice_loan_updates
```

**Why Choreography for Scenario 3**:
- ✅ Invoice Service doesn't need to know about Payment Service
- ✅ Easy to add more consumers (e.g., Notification Service)
- ✅ Reliable delivery (persistent messages + manual ack)

**Why NOT Choreography for Scenario 2**:
- ❌ Need transactional consistency (orchestration provides this)
- ❌ Need rollback capability (can't "un-publish" an event)
- ❌ Complex 8-step workflow (orchestration is clearer)

---

### 4. GraphQL (BTL #3)

**Used For**: Complex frontend queries

**Traditional REST Problem**:
```javascript
// Frontend needs to make 3 API calls
const listing = await fetch('/api/marketplace/invoices/INV-123');
const seller = await fetch(`/api/users/${listing.seller_id}`);
const bids = await fetch(`/api/offers/invoice/INV-123`);

// Total latency: 50ms + 50ms + 50ms = 150ms
```

**GraphQL Solution**:
```javascript
// Frontend makes 1 API call
const query = `{
  listing(token: "INV-123") {
    invoice_token
    amount
    seller {
      company_name
      email
    }
    current_bids {
      offer_amount
      investor {
        email
      }
    }
  }
}`;

const data = await fetch('/graphql', {
  method: 'POST',
  body: JSON.stringify({ query })
});

// Total latency: 50ms (single call)
```

---

## Scenario Flows

### Scenario 1: Invoice Submission & Listing

```
┌─────────┐                ┌──────────┐              ┌──────────┐
│ Frontend│                │  User    │              │ Invoice  │
│         │                │ Service  │              │ Service  │
└────┬────┘                └────┬─────┘              └────┬─────┘
     │                          │                         │
     │ 1. POST /login           │                         │
     │─────────────────────────>│                         │
     │                          │                         │
     │ 2. JWT token             │                         │
     │<─────────────────────────│                         │
     │                          │                         │
     │ 3. POST /invoices/create (+ JWT)                  │
     │───────────────────────────────────────────────────>│
     │                          │                         │
     │                          │  4. Generate token      │
     │                          │     (INV-Ax7K2p)        │
     │                          │                         │
     │                          │  5. Store invoice       │
     │                          │     status=CREATED      │
     │                          │                         │
                                                          │
┌──────────┐                                             │
│OutSystems│                                             │
│Validator │                                             │
└────┬─────┘                                             │
     │                                                    │
     │ 6. POST /validate                                 │
     │<───────────────────────────────────────────────────│
     │                                                    │
     │ 7. {valid: true, score: 85}                       │
     │────────────────────────────────────────────────────>│
     │                                                    │
     │                          │  8. Update invoice      │
     │                          │     score=85            │
     │                          │     status=VALIDATED    │
     │                                                    │
┌──────────┐                                             │
│Marketplace│                                            │
│ Service  │                                             │
└────┬─────┘                                             │
     │                                                    │
     │ 9. POST /marketplace/list/INV-Ax7K2p              │
     │<───────────────────────────────────────────────────│
     │                                                    │
     │ 10. Calculate urgency                             │
     │     bid_deadline = NOW() + 48h                    │
     │     urgency = 'HIGH'                              │
     │                                                    │
     │ 11. Create listing                                │
     │     status=ACTIVE                                 │
     │                                                    │
     │ 12. Success response                              │
     │────────────────────────────────────────────────────>│
     │                                                    │
     │                          │ 13. Success response    │
     │<───────────────────────────────────────────────────│
     │                          │                         │
┌────┴────┐                                              │
│ Frontend│                                              │
│         │                                              │
│ ✅ Invoice listed!                                     │
│ Bidding closes in 48 hours                            │
└─────────┘
```

**Services Involved**: User (JWT), Invoice (create + validate), OutSystems (external), Marketplace (list)

---

### Scenario 2: Auction & Orchestrated Purchase

```
Phase 1: Bidding (User-Driven)

┌─────────┐          ┌──────────┐          ┌─────────┐         ┌─────────┐
│Investor │          │Marketplace│          │ Bidding │         │ Payment │
│Frontend │          │ Service  │          │ Service │         │ Service │
└────┬────┘          └────┬─────┘          └────┬────┘         └────┬────┘
     │                    │                     │                    │
     │ Browse listings    │                     │                    │
     │───────────────────>│                     │                    │
     │                    │                     │                    │
     │ [Display invoices] │                     │                    │
     │<───────────────────│                     │                    │
     │                    │                     │                    │
     │ Click "Place Bid"  │                     │                    │
     │                    │                     │                    │
     │ POST /offers/submit                      │                    │
     │─────────────────────────────────────────>│                    │
     │                    │                     │                    │
     │                    │  Check deadline     │                    │
     │                    │  Save offer         │                    │
     │                    │  status=PENDING     │                    │
     │                    │                     │                    │
     │                    │   Lock funds (gRPC) │                    │
     │                    │     LockBidEscrow() │                    │
     │                    │─────────────────────────────────────────>│
     │                    │                     │                    │
     │                    │                     │   Check wallet     │
     │                    │                     │   Deduct $47k      │
     │                    │                     │   Create bid_escrow│
     │                    │                     │   status=LOCKED    │
     │                    │                     │                    │
     │                    │                     │ ✅ Escrow locked    │
     │                    │<─────────────────────────────────────────│
     │                    │                     │                    │
     │ ✅ Bid placed! $47k held in escrow        │                    │
     │<─────────────────────────────────────────│                    │


Phase 2: Auction Close (System-Driven - Cron Job)

┌────────────┐        ┌──────────┐        ┌─────────┐        ┌─────────┐
│Auction     │        │Marketplace│        │ Bidding │        │ Invoice │
│Closer Cron │        │ Service  │        │ Service │        │ Service │
└────┬───────┘        └────┬─────┘        └────┬────┘        └────┬────┘
     │                     │                   │                   │
     │ ⏰ Runs every hour   │                   │                   │
     │                     │                   │                   │
     │ GET /marketplace/expired                │                   │
     │────────────────────>│                   │                   │
     │                     │                   │                   │
     │ [INV-Ax7K2p expired]│                   │                   │
     │<────────────────────│                   │                   │
     │                     │                   │                   │
     │ GET /offers/invoice/INV-Ax7K2p          │                   │
     │────────────────────────────────────────>│                   │
     │                     │                   │                   │
     │ [3 bids: $46k, $45.5k, $47k]            │                   │
     │<────────────────────────────────────────│                   │
     │                     │                   │                   │
     │ Sort by amount      │                   │                   │
     │ Winner: $47k bid    │                   │                   │
     │                     │                   │                   │
     │ PUT /offers/125/auto-accept              │                   │
     │────────────────────────────────────────>│                   │
     │                     │                   │                   │
     │                     │   ╔═══════════════════════════════════╗
     │                     │   ║    ORCHESTRATION STARTS           ║
     │                     │   ╚═══════════════════════════════════╝
     │                     │                   │                   │
     │                     │   Step 1: Verify invoice              │
     │                     │                   GET /invoices/{token}│
     │                     │                   │──────────────────>│
     │                     │                   │                   │
     │                     │                   │ [status: LISTED]  │
     │                     │                   │<──────────────────│
     │                     │                   │                   │
     │                     │   Step 2-4: (see orchestration code)  │
     │                     │                   │                   │
     │                     │   Step 4: Release funds to bakery     │
     │                     │   💰 Bakery receives $47k             │
     │                     │   🎉 SCENARIO 2 ENDS                  │
     │                     │                   │                   │
     │                     │   Step 5: Update invoice              │
     │                     │                   PUT /invoices/status│
     │                     │                   │──────────────────>│
     │                     │                   │  status=FINANCED  │
     │                     │                   │                   │
     │                     │   Step 6: Delist  │                   │
     │       DELETE /delist│                   │                   │
     │<────────────────────────────────────────│                   │
     │                     │                   │                   │
     │ ✅ Orchestration complete                │                   │
     │<────────────────────────────────────────│                   │
     │                     │                   │                   │
     │ Refund losing bids ($46k, $45.5k)       │                   │
     │────────────────────────────────────────>│                   │
```

**Services Involved**: Marketplace (browse), Bidding (submit offer + orchestrator), Payment (gRPC escrow + loans), Invoice (status update)

---

### Scenario 3: Loan Maturity & Manual Repayment (Choreography)

```
Day 1 (Loan Created)
─────────────────────
Loan status: ACTIVE
Due date: 2026-05-10 (60 days)



Day 60 (Maturity Date - 2026-05-10 00:00)
──────────────────────────────────────────

┌────────────┐                       ┌─────────┐
│  Maturity  │                       │ Payment │
│Checker Cron│                       │ Service │
└────┬───────┘                       └────┬────┘
     │                                    │
     │ ⏰ Runs daily at midnight           │
     │                                    │
     │ GET /loans/due-today               │
     │───────────────────────────────────>│
     │                                    │
     │ [loan_id: uuid-789-xyz]            │
     │<───────────────────────────────────│
     │                                    │
     │ PUT /loans/{id}/mark-due           │
     │   {                                │
     │     window_start: 00:00            │
     │     window_end: 23:59 (next day)   │
     │   }                                │
     │───────────────────────────────────>│
     │                                    │
     │                   Loan status → DUE │
     │                   24h window started│
     │                                    │
     │ 📧 Notify bakery                    │
     │ "Pay $50k within 24 hours"         │
     │                                    │



Within 24 Hours (e.g., 2026-05-10 14:30)
─────────────────────────────────────────

┌─────────┐                  ┌─────────┐                  ┌─────────┐
│ Bakery  │                  │ Payment │                  │RabbitMQ │
│Frontend │                  │ Service │                  │         │
└────┬────┘                  └────┬────┘                  └────┬────┘
     │                            │                            │
     │ Click "Repay Loan"         │                            │
     │                            │                            │
     │ POST /payments/loan-repayment                           │
     │───────────────────────────>│                            │
     │                            │                            │
     │           Check loan status=DUE ✅                       │
     │           Check wallet ≥ $50k ✅                         │
     │                            │                            │
     │           Debit bakery: -$50k                           │
     │           Credit investor: +$50k                        │
     │           Update loan: status=REPAID                    │
     │                            │                            │
     │ ✅ Repayment successful     │                            │
     │<───────────────────────────│                            │
     │                            │                            │
     │           Publish event    │                            │
     │           "loan.repaid"    │                            │
     │                            │───────────────────────────>│
     │                            │                            │
     │                            │  Exchange: loan_events     │
     │                            │  Routing: loan.repaid      │
     │                            │                            │
                                                               │
┌─────────┐                                                   │
│ Invoice │                                                   │
│ Service │                                                   │
│Consumer │                                                   │
└────┬────┘                                                   │
     │                                                        │
     │ Consume event                                          │
     │<───────────────────────────────────────────────────────│
     │                                                        │
     │ Update invoice                                         │
     │ status → REPAID                                        │
     │                                                        │
     │ Manual ACK ✅                                           │
     │────────────────────────────────────────────────────────>│
     │                                                        │
     
┌─────────┐
│Investor │
│Frontend │
└────┬────┘
     │
     │ 📧 Notification
     │ "Payment received! $50k deposited"
     │ "Your profit: $3k (6.4% return)"
     │
     
🎉 SCENARIO 3 COMPLETE
```

**Services Involved**: Payment (maturity cron + repayment + RabbitMQ publisher), Invoice (RabbitMQ consumer)

---

## Design Decisions & Rationale

### Why 5 Services Instead of 3?

**Alternative**: Combine Bidding + Payment into one service

**Why We Separated**:
1. **Different responsibilities**: Bidding = business logic, Payment = financial operations
2. **Security**: Payment Service handles money → stricter access controls
3. **Technology fit**: Payment needs Node.js for gRPC, Bidding uses Python
4. **Scalability**: Payment Service has higher load (every transaction) than Bidding
5. **Team distribution**: 2 team members can work in parallel

---

### Why Orchestration for Scenario 2?

**Alternative**: Choreography with events

**Why Orchestration**:
1. **Transactional consistency**: Need all 8 steps to succeed or rollback
2. **Clear workflow**: Easier to understand and debug
3. **Rollback capability**: Can revert escrow if ownership transfer fails
4. **Error handling**: Central point to catch and handle failures

**Drawbacks** (and why we accept them):
- Single point of failure (Bidding Service down = no purchases)
  - **Mitigation**: Health checks + automatic restart (Docker)
- Tight coupling (Bidding knows about Invoice, Payment, Marketplace)
  - **Acceptance**: This is acceptable for a critical transaction flow

---

### Why Choreography for Scenario 3?

**Alternative**: Orchestration (Payment Service calls Invoice Service)

**Why Choreography**:
1. **Loose coupling**: Payment doesn't need to know about Invoice Service
2. **Extensibility**: Easy to add Notification Service, Analytics Service
3. **Eventual consistency**: It's okay if invoice status updates a few seconds later
4. **Resilience**: If Invoice Service is down, event stays in queue

---

### Why gRPC for Payment Operations? (BTL #2)

**Alternative**: Use REST for everything

**Why gRPC**:
1. **Performance**: 3-5x faster (10ms vs 50ms per call)
2. **Type safety**: Prevents `amount: "abc"` bugs
3. **Learning opportunity**: Beyond-the-labs requirement
4. **Real-world relevance**: Payment companies (Stripe, PayPal) use gRPC

**Tradeoffs**:
- **Complexity**: Need .proto files, code generation
- **Debugging**: Harder than REST (can't use Postman)
- **Team learning**: 12 hours to implement

---

### Why GraphQL for Marketplace? (BTL #3)

**Alternative**: REST with multiple endpoints

**Why GraphQL**:
1. **Performance**: 1 API call instead of 3-5 (150ms → 50ms)
2. **Frontend flexibility**: Mobile app needs less data than web
3. **Self-documenting**: GraphQL Playground auto-generates docs
4. **Learning opportunity**: Beyond-the-labs requirement

**Tradeoffs**:
- **N+1 query problem**: Need DataLoader to batch database queries
- **Caching complexity**: Can't use HTTP caching (always POST)
- **Team learning**: 10 hours to implement

---

### Why KONG API Gateway? (BTL #1)

**Alternative**: Frontend calls services directly

**Why KONG**:
1. **Rate limiting**: Prevent bid spam (max 10 bids/minute)
2. **Authentication**: JWT validation in one place (don't repeat in 5 services)
3. **Observability**: Centralized logging
4. **Production-ready**: Real companies use KONG (Samsung, Yahoo, Expedia)

**Tradeoffs**:
- **Single point of failure**: If KONG down, entire system down
  - **Mitigation**: Health checks + auto-restart
- **Learning curve**: Declarative config (kong.yml)
- **Team effort**: 8 hours to setup

---

## Security Architecture

### Authentication Flow (JWT)

```
1. User registers → Password hashed with bcrypt (10 rounds)
2. User logs in → Server generates JWT:
   {
     "user_id": 123,
     "user_type": "INVESTOR",
     "exp": 1234567890  // 24 hours from now
   }
3. User stores JWT in localStorage
4. Every API call → Include header:
   Authorization: Bearer eyJhbGc...
5. KONG validates JWT → Passes to service with user context
6. Service uses user_id from JWT (trusted)
```

### API Key Protection (OutSystems)

```python
headers = {
    'Authorization': f'Bearer {OUTSYSTEMS_API_KEY}',
    'Content-Type': 'application/json'
}

# Store API key in environment variable
OUTSYSTEMS_API_KEY = os.getenv('OUTSYSTEMS_API_KEY')
```

### Database Security

```sql
-- Prevent negative balances
ALTER TABLE wallets ADD CHECK (balance >= 0);

-- Prevent duplicate bid escrow
ALTER TABLE bid_escrow ADD UNIQUE KEY unique_bid (bid_id);

-- Prevent invoice duplication
ALTER TABLE invoices ADD UNIQUE KEY (seller_id, invoice_number);
```

### Input Validation

```python
from pydantic import BaseModel, validator

class InvoiceCreateRequest(BaseModel):
    invoice_number: str
    amount: float
    due_date: date
    
    @validator('amount')
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 10_000_000:
            raise ValueError('Amount exceeds maximum')
        return v
```

---

## Scalability & Performance

### Bottleneck Analysis

| Component | Current Capacity | Bottleneck Risk | Solution |
|-----------|-----------------|-----------------|----------|
| KONG Gateway | 10,000 req/s | Low | Single instance OK for demo |
| User Service | 500 req/s | Low | Stateless, easy to scale |
| Invoice Service | 300 req/s | Medium | OutSystems API is external bottleneck |
| Marketplace Service | 1,000 req/s | Low | Read-heavy, add caching |
| Bidding Service | 200 req/s | **High** | Orchestration is sequential |
| Payment Service | 400 req/s | Medium | Database transactions |
| MySQL | 10,000 queries/s | Low | Separate DBs prevent contention |
| RabbitMQ | 50,000 msgs/s | Low | Overkill for our volume |

### Optimization Opportunities

1. **Add Redis Caching**:
   ```python
   # Cache marketplace listings (1 minute TTL)
   @cache('marketplace:listings', ttl=60)
   def get_marketplace_listings():
       return db.query(...)
   ```

2. **Database Indexes**:
   ```sql
   CREATE INDEX idx_composite ON listings(status, urgency_level, bid_deadline);
   ```

3. **Connection Pooling**:
   ```python
   pool = mysql.connector.pooling.MySQLConnectionPool(
       pool_name="mypool",
       pool_size=10
   )
   ```

---

## Error Handling & Resilience

### Idempotency

**Problem**: Network retry causes duplicate bid escrow lock

**Solution**:
```javascript
// Check if bid_id already has locked escrow
const [existing] = await connection.query(
  'SELECT * FROM bid_escrow WHERE bid_id = ?',
  [bid_id]
);

if (existing.length > 0) {
  return res.json({ success: true, message: "Already locked" });
}
```

### Retry Logic

```python
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

session = requests.Session()
retry = Retry(
    total=3,
    backoff_factor=1,  # 1s, 2s, 4s
    status_forcelist=[500, 502, 503, 504]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount('http://', adapter)

# Usage
response = session.get('http://invoice-service:5001/invoices/123')
```

### Circuit Breaker

```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60)
def call_outsystems_validator(invoice_data):
    return requests.post(OUTSYSTEMS_URL, json=invoice_data)
```

### Graceful Degradation

```python
try:
    validation = call_outsystems_validator(invoice_data)
except:
    # Fallback: Mark as PENDING_VALIDATION
    validation = {'valid': None, 'score': None}
    invoice.status = 'PENDING_VALIDATION'
```

---

## Monitoring & Observability

### Health Checks

```python
@app.route('/health')
def health():
    db_status = check_db_connection()
    rabbitmq_status = check_rabbitmq_connection()
    
    return {
        'status': 'healthy' if (db_status and rabbitmq_status) else 'degraded',
        'service': 'invoice-service',
        'timestamp': datetime.now().isoformat(),
        'dependencies': {
            'database': db_status,
            'rabbitmq': rabbitmq_status
        }
    }
```

### Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(service)s] %(levelname)s: %(message)s'
)

logger = logging.getLogger('invoice-service')

logger.info(f"Invoice {token} created by user {user_id}")
logger.error(f"OutSystems validation failed: {error}")
```

### Metrics (Future Enhancement)

```python
from prometheus_client import Counter, Histogram

invoice_created = Counter('invoices_created_total', 'Total invoices created')
validation_duration = Histogram('validation_duration_seconds', 'Validation latency')

with validation_duration.time():
    result = validate_invoice(data)

invoice_created.inc()
```

---

**Last Updated**: February 18, 2026  
**Version**: 1.0.0  
**Team**: InvoiceFlow (SMU IS213 AY2025/26)
