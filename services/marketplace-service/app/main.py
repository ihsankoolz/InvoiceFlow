import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers.listings import router as listings_router
from app.routers.public_listings import router as public_listings_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer = None
    try:
        from app.consumers.marketplace_consumer import MarketplaceEventConsumer
        consumer = MarketplaceEventConsumer()
        await consumer.start()
        logger.info("MarketplaceEventConsumer started.")
    except Exception as e:
        logger.warning("Could not start MarketplaceEventConsumer: %s", e)
    yield
    if consumer is not None:
        await consumer.stop()


app = FastAPI(
    title="Marketplace Service",
    description="Manages auction listings. Internal CRUD endpoints for orchestrators + public read-model endpoints for the frontend via KONG.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Listings", "description": "Internal CRUD — used by orchestrators and Temporal Worker"},
        {"name": "Public Listings", "description": "Read-model endpoints — used by frontend via KONG/Nginx"},
        {"name": "Health", "description": "Health check"},
    ],
    lifespan=lifespan,
)
Instrumentator().instrument(app).expose(app)

# Internal CRUD endpoints (used by other services)
app.include_router(listings_router)

# Public read-model endpoints (used by frontend via Kong)
app.include_router(public_listings_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "marketplace-service"}
