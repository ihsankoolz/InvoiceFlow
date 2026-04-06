import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.consumers.loan_consumer import LoanEventConsumer
from app.routers import invoices

logger = logging.getLogger(__name__)

loan_consumer = LoanEventConsumer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: start RabbitMQ consumer on startup, stop on shutdown."""
    try:
        await loan_consumer.start()
        logger.info("LoanEventConsumer started successfully.")
    except Exception as e:
        logger.warning(f"Could not start LoanEventConsumer: {e}")
    yield
    await loan_consumer.stop()
    logger.info("LoanEventConsumer stopped.")


app = FastAPI(
    title="Invoice Service",
    description="Manages invoice upload, PDF extraction via pdfplumber, MinIO PDF storage, and invoice status lifecycle.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Invoices", "description": "Create, retrieve, and update invoice records"},
        {
            "name": "Status",
            "description": "Invoice status transitions (LISTED, REJECTED, FINANCED, REPAID, DEFAULTED)",
        },
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


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "invoice-service"}


app.include_router(invoices.router)
