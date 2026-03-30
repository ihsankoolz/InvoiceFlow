from fastapi import FastAPI

from app.routers.listings import router as listings_router

app = FastAPI(title="Marketplace Service", version="1.0.0")

app.include_router(listings_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "marketplace-service"}
