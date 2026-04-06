"""
Notification Service — FastAPI application entry point.

Pure RabbitMQ consumer that listens for all events and sends notifications
via email (Resend) and real-time WebSocket push to the frontend.
"""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app import config
from app.consumers.event_consumer import EventConsumer
from app.database import Base, engine
from app.routers import notifications
from app.services.websocket_manager import ws_manager

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start RabbitMQ consumer on startup, clean up on shutdown."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass  # DB unavailable in test/CI environments; conftest handles table creation
    consumer_task = None
    try:
        consumer = EventConsumer(
            rabbitmq_url=config.RABBITMQ_URL,
            websocket_manager=ws_manager,
        )
        consumer_task = asyncio.create_task(consumer.start())
        print("[notification-service] RabbitMQ consumer started")
    except Exception as e:
        print(f"[notification-service] Could not start consumer: {e}")
    yield
    if consumer_task is not None:
        consumer_task.cancel()
        try:
            await consumer_task
        except (asyncio.CancelledError, Exception):
            pass
    print("[notification-service] RabbitMQ consumer stopped")


app = FastAPI(
    title="Notification Service",
    description="Listens for all events via RabbitMQ and sends email (Resend) + real-time WebSocket notifications to the frontend via Nginx.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "Notifications", "description": "Fetch and manage notification records"},
        {"name": "Health", "description": "Health check"},
    ],
    lifespan=lifespan,
)
Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST router
app.include_router(notifications.router)


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok", "service": "notification-service"}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """
    WebSocket connection for real-time push notifications.

    The frontend connects here after login. The Notification Service pushes
    events (invoice.listed, bid.placed, wallet.credited, loan.due, etc.)
    through Nginx to this endpoint as they are consumed from RabbitMQ.
    """
    await ws_manager.connect(str(user_id), websocket)
    try:
        while True:
            # Keep connection alive — client doesn't send meaningful data
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(str(user_id), websocket)
