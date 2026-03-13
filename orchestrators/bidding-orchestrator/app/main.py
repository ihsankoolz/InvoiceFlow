from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import bids, wallet, webhooks

app = FastAPI(title="Bidding Orchestrator")

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
