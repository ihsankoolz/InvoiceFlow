from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import loans

app = FastAPI(title="Loan Orchestrator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "loan-orchestrator"}


app.include_router(loans.router)
