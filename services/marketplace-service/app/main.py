from fastapi import FastAPI
from strawberry.fastapi import GraphQLRouter

from app.routers.listings import router as listings_router
from app.graphql.schema import schema

app = FastAPI(title="Marketplace Service", version="1.0.0")

# Mount REST routes
app.include_router(listings_router)

# Mount GraphQL endpoint
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "marketplace-service"}
