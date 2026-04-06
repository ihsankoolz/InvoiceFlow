from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.routers import invoices

app = FastAPI(
    title="Invoice Orchestrator",
    description="Orchestrates the full Scenario 1 invoice listing flow: user check, invoice creation, UEN validation, marketplace listing, Temporal workflow start, and RabbitMQ publish.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Invoice Workflow", "description": "Full Scenario 1 orchestration endpoints"},
        {"name": "Health", "description": "Health check"},
    ],
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
    return {"status": "healthy", "service": "invoice-orchestrator"}


app.include_router(invoices.router)
