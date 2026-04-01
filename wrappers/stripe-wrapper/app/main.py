"""Stripe Wrapper — wraps the Stripe API for creating checkout sessions."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers import checkout

app = FastAPI(
    title="Stripe Wrapper",
    description="Wraps the Stripe API for creating checkout sessions. Outbound only.",
    version="1.0.0",
    docs_url="/docs",
)
Instrumentator().instrument(app).expose(app)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "stripe-wrapper"}


app.include_router(checkout.router)
