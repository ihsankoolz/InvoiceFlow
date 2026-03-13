from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import invoices

app = FastAPI(title="Invoice Orchestrator")

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
