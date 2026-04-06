import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.consumers.loan_consumer import LoanEventConsumer
from app.routers import auth, users

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the RabbitMQ consumer as a background task on startup."""
    task = None
    try:
        consumer = LoanEventConsumer()
        task = asyncio.create_task(consumer.start())
        logger.info("LoanEventConsumer background task started.")
    except Exception as e:
        logger.warning("Could not start LoanEventConsumer: %s", e)
    yield
    if task is not None:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
        logger.info("LoanEventConsumer background task cancelled.")


app = FastAPI(
    title="User Service",
    description="Manages user accounts, authentication, and account status (ACTIVE/DEFAULTED).",
    version="1.0.0",
    openapi_tags=[
        {"name": "Auth", "description": "Register and login endpoints"},
        {"name": "Users", "description": "User lookup and status management"},
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

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "user-service"}
