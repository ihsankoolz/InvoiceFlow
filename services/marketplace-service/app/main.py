import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from app.routers.listings import router as listings_router
from app.graphql.schema import schema

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.consumers.marketplace_consumer import MarketplaceEventConsumer
    consumer = MarketplaceEventConsumer()
    try:
        await consumer.start()
        logger.info("MarketplaceEventConsumer started.")
    except Exception as e:
        logger.warning("Could not start MarketplaceEventConsumer: %s", e)
    yield
    await consumer.stop()


app = FastAPI(title="Marketplace Service", version="1.0.0", lifespan=lifespan)

# Mount REST routes
app.include_router(listings_router)

# Mount GraphQL endpoint
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "marketplace-service"}
