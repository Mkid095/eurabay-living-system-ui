"""
WebSocket router for real-time data streaming.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Set
import json
import asyncio

from app.core.logging import logger

ws_router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    Manage WebSocket connections for real-time data streaming.
    """

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return

        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending WebSocket message: {e}")
                disconnected.add(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    async def send_personal(self, message: dict, websocket: WebSocket) -> None:
        """Send a message to a specific WebSocket client."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal WebSocket message: {e}")


# Global connection manager instance
manager = ConnectionManager()


@ws_router.websocket("/stream")
async def websocket_stream(websocket: WebSocket) -> None:
    """
    WebSocket endpoint for real-time data streaming.

    Streams:
    - Price updates for volatility indices
    - Trading signals
    - Trade execution events
    - Position updates
    - Performance metrics
    """
    await manager.connect(websocket)

    try:
        # Send welcome message
        await manager.send_personal(
            {
                "type": "connected",
                "message": "Connected to EURABAY Living System",
                "timestamp": asyncio.get_event_loop().time()
            },
            websocket
        )

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle ping/pong for heartbeat
            if message.get("type") == "ping":
                await manager.send_personal(
                    {"type": "pong", "timestamp": asyncio.get_event_loop().time()},
                    websocket
                )

            # Handle subscription requests
            elif message.get("type") == "subscribe":
                channels = message.get("channels", [])
                logger.info(f"Client subscribed to channels: {channels}")
                await manager.send_personal(
                    {
                        "type": "subscribed",
                        "channels": channels,
                        "timestamp": asyncio.get_event_loop().time()
                    },
                    websocket
                )

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        manager.disconnect(websocket)
