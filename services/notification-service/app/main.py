"""
Notification Service — FastAPI application entry point.

Pure RabbitMQ consumer that listens for all events and sends notifications
via email (Resend) and real-time WebSocket push to the frontend.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from app.routers import notifications
from app.services.websocket_manager import ws_manager
from app.consumers.event_consumer import EventConsumer
from app import config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start RabbitMQ consumer on startup, clean up on shutdown."""
    consumer = EventConsumer(
        rabbitmq_url=config.RABBITMQ_URL,
        websocket_manager=ws_manager,
    )
    consumer_task = asyncio.create_task(consumer.start())
    print("[notification-service] RabbitMQ consumer started")
    yield
    consumer_task.cancel()
    try:
        await consumer_task
    except asyncio.CancelledError:
        pass
    print("[notification-service] RabbitMQ consumer stopped")


app = FastAPI(
    title="Notification Service",
    description="Listens for all events via RabbitMQ and sends email (Resend) + WebSocket notifications.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

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
    """WebSocket endpoint for real-time push notifications to frontend."""
    await ws_manager.connect(str(user_id), websocket)
    try:
        while True:
            # Keep connection alive — client doesn't send meaningful data
            await websocket.receive_text()
    except WebSocketDisconnect:
        await ws_manager.disconnect(str(user_id), websocket)
