import json
from typing import Dict, List

from fastapi import WebSocket


class WebSocketManager:
    """Manages active WebSocket connections and provides methods for
    pushing real-time messages to connected users."""

    def __init__(self):
        # Maps user_id (str) -> list of active WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket) -> None:
        """Accept and register a new WebSocket connection for a user.

        Args:
            user_id: The ID of the connecting user.
            websocket: The FastAPI WebSocket instance.
        """
        # TODO: Accept the websocket and add to active_connections
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    async def disconnect(self, user_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket connection for a user.

        Args:
            user_id: The ID of the disconnecting user.
            websocket: The WebSocket instance to remove.
        """
        # TODO: Remove the websocket from active_connections
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict) -> None:
        """Send a JSON message to all active connections for a specific user.

        Args:
            user_id: Target user ID.
            message: Dictionary payload to send as JSON.
        """
        # TODO: Send message to all connections for the given user_id
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass

    async def broadcast_to_users(self, user_ids: list, message: dict) -> None:
        """Send a JSON message to multiple users.

        Args:
            user_ids: List of user IDs to broadcast to.
            message: Dictionary payload to send as JSON.
        """
        # TODO: Iterate over user_ids and call send_to_user for each
        for user_id in user_ids:
            await self.send_to_user(str(user_id), message)


# Singleton instance used across the application
ws_manager = WebSocketManager()
