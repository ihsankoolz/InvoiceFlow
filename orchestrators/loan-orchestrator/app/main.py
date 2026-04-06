import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers import loans

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.consumers.stripe_consumer import LoanStripeConsumer
    consumer = LoanStripeConsumer()
    try:
        await consumer.start()
        logger.info("LoanStripeConsumer started.")
    except Exception as e:
        logger.warning("Could not start LoanStripeConsumer: %s", e)
    yield
    await consumer.stop()


app = FastAPI(
    title="Loan Orchestrator",
    description="Orchestrates loan repayment via Stripe and confirms repayment via Temporal. Also exposes loan listing for the frontend.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Loans", "description": "List loans by investor or seller"},
        {"name": "Repayment", "description": "Initiate and confirm loan repayment — Scenario 3 repayment flow"},
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
    return {"status": "healthy", "service": "loan-orchestrator"}


app.include_router(loans.router)
