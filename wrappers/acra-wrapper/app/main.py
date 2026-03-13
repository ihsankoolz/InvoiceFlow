"""ACRA Wrapper — wraps data.gov.sg ACRA UEN registry API for debtor UEN validation."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import uen

app = FastAPI(
    title="ACRA Wrapper",
    description="Wraps the data.gov.sg ACRA UEN registry API for debtor UEN validation.",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "acra-wrapper"}


app.include_router(uen.router)
