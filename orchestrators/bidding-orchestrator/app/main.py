import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers import bids, wallet, webhooks

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.consumers.stripe_consumer import StripeWebhookConsumer

    consumer = StripeWebhookConsumer()
    try:
        await consumer.start()
        logger.info("StripeWebhookConsumer started.")
    except Exception as e:
        logger.warning("Could not start StripeWebhookConsumer: %s", e)
    yield
    await consumer.stop()


app = FastAPI(
    title="Bidding Orchestrator",
    description="Orchestrates wallet top-up (via Stripe) and bid placement (with anti-snipe extension). Entry point from KONG for all investor bidding actions.",
    version="1.0.0",
    openapi_tags=[
        {
            "name": "Bidding",
            "description": "Place bids and list bids — full Scenario 2B orchestration",
        },
        {"name": "Wallet", "description": "Wallet balance, top-up, and transaction history"},
        {"name": "Health", "description": "Health check"},
    ],
    lifespan=lifespan,
)
Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "bidding-orchestrator"}


app.include_router(bids.router)
app.include_router(wallet.router)
app.include_router(webhooks.router)
