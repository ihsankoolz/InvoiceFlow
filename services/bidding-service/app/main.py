from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.database import Base, engine
from app.routers import bids


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass  # DB unavailable in test/CI environments; conftest handles table creation
    yield


app = FastAPI(
    title="Bidding Service",
    description="Manages bid records for invoice auctions. Called internally by the Bidding Orchestrator and Temporal Worker.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Bids", "description": "Bid creation, retrieval, and status transitions"},
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
def health_check():
    return {"status": "healthy", "service": "bidding-service"}


app.include_router(bids.router)
