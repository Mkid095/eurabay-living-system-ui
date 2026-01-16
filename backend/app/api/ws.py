"""
WebSocket router for real-time data streaming.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Set, Optional
import json
import asyncio

from app.core.logging import logger
from app.core.config import settings

ws_router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """
    Manage WebSocket connections for real-time data streaming.
    """

    def __init__(self) -> None:
        self.active_connections: Set[WebSocket] = set()
        self.heartbeat_tasks: dict[WebSocket, asyncio.Task] = {}

    async def connect(self, websocket: WebSocket, token: Optional[str] = None) -> bool:
        """
        Accept a new WebSocket connection with optional token validation.

        Args:
            websocket: The WebSocket connection
            token: Optional authentication token

        Returns:
            True if connection was accepted, False otherwise
        """
        # Validate token if provided (authentication check)
        # For now, accept all connections - authentication can be added later
        # In production, validate JWT token here
        if token:
            # TODO: Implement proper JWT token validation
            logger.debug(f"WebSocket connection with token: {token[:10]}...")
        else:
            logger.debug("WebSocket connection without token (development mode)")

        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")

        # Start heartbeat task for this connection
        task = asyncio.create_task(self._heartbeat(websocket))
        self.heartbeat_tasks[websocket] = task

        return True

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection and stop heartbeat."""
        self.active_connections.discard(websocket)

        # Cancel heartbeat task if exists
        if websocket in self.heartbeat_tasks:
            task = self.heartbeat_tasks.pop(websocket)
            if not task.done():
                task.cancel()

        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")

    async def _heartbeat(self, websocket: WebSocket) -> None:
        """
        Send periodic heartbeat messages to keep connection alive.

        Sends a ping message every WS_HEARTBEAT_INTERVAL seconds.
        """
        try:
            while True:
                await asyncio.sleep(settings.WS_HEARTBEAT_INTERVAL)
                if websocket in self.active_connections:
                    try:
                        await websocket.send_json({
                            "type": "ping",
                            "timestamp": asyncio.get_event_loop().time()
                        })
                    except Exception:
                        # Connection is dead, will be cleaned up
                        break
        except asyncio.CancelledError:
            # Task was cancelled (connection closed)
            pass

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
async def websocket_stream(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="Optional authentication token")
) -> None:
    """
    WebSocket endpoint for real-time data streaming.

    Streams:
    - Price updates for volatility indices
    - Trading signals
    - Trade execution events
    - Position updates
    - Performance metrics

    Args:
        websocket: The WebSocket connection
        token: Optional authentication token for connection validation
    """
    # Accept connection with optional token validation
    await manager.connect(websocket, token)

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

            # Handle ping/pong for heartbeat (client-initiated)
            if message.get("type") == "ping":
                await manager.send_personal(
                    {"type": "pong", "timestamp": asyncio.get_event_loop().time()},
                    websocket
                )
            # Handle pong response (client responding to server ping)
            elif message.get("type") == "pong":
                logger.debug("Received pong from client")

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
