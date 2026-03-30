from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from strawberry.fastapi import GraphQLRouter

from app.routers import bids, wallet, webhooks, listings
from app.graphql.schema import schema

app = FastAPI(title="Bidding Orchestrator")

graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/api/graphql")

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
app.include_router(listings.router)
