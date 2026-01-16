"""
API routes for active trade management.

This module implements all REST API endpoints for controlling and monitoring
active trade management as specified in US-011.
"""

import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from .schemas import (
    TradePositionResponse,
    TradeStateResponse,
    ManualCloseRequest,
    ManualStopLossRequest,
    ManualTakeProfitRequest,
    PauseManagementRequest,
    ResumeManagementRequest,
    ActionSuccessResponse,
    PerformanceMetrics,
    ErrorResponse,
    TradeUpdateMessage,
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/trades", tags=["trades"])


class TradeManager:
    """
    Mock trade manager for API demonstration.

    In production, this would integrate with:
    - ActiveTradeManager for position monitoring
    - ManualOverrideManager for manual controls
    - PerformanceComparator for metrics
    """

    def __init__(self):
        """Initialize with mock data."""
        self._positions: dict[int, dict] = {}
        self._paused: set[int] = set()
        self._websocket_clients: list[WebSocket] = []

    async def get_all_positions(self) -> list[dict]:
        """Get all active positions."""
        return list(self._positions.values())

    async def get_position(self, ticket: int) -> Optional[dict]:
        """Get position by ticket."""
        return self._positions.get(ticket)

    async def close_position(
        self, ticket: int, reason: str, user: str
    ) -> dict:
        """Close position."""
        if ticket not in self._positions:
            raise ValueError(f"Position {ticket} not found")
        # Mock close operation
        self._positions[ticket]["closed"] = True
        self._positions[ticket]["closed_at"] = datetime.now()
        self._positions[ticket]["closed_by"] = user
        self._positions[ticket]["close_reason"] = reason
        return {"success": True, "ticket": ticket}

    async def pause_management(self, ticket: int, reason: str, user: str) -> dict:
        """Pause active management for position."""
        if ticket not in self._positions:
            raise ValueError(f"Position {ticket} not found")
        self._paused.add(ticket)
        return {"success": True, "ticket": ticket}

    async def resume_management(self, ticket: int, reason: str, user: str) -> dict:
        """Resume active management for position."""
        if ticket not in self._positions:
            raise ValueError(f"Position {ticket} not found")
        self._paused.discard(ticket)
        return {"success": True, "ticket": ticket}

    async def set_stop_loss(self, ticket: int, sl: float, reason: str, user: str) -> dict:
        """Set manual stop loss."""
        if ticket not in self._positions:
            raise ValueError(f"Position {ticket} not found")
        self._positions[ticket]["stop_loss"] = sl
        return {"success": True, "ticket": ticket}

    async def set_take_profit(self, ticket: int, tp: float, reason: str, user: str) -> dict:
        """Set manual take profit."""
        if ticket not in self._positions:
            raise ValueError(f"Position {ticket} not found")
        self._positions[ticket]["take_profit"] = tp
        return {"success": True, "ticket": ticket}

    async def get_performance_metrics(self) -> dict:
        """Get performance metrics."""
        return {
            "actively_managed_win_rate": 0.68,
            "set_and_forget_win_rate": 0.55,
            "actively_managed_profit_factor": 2.1,
            "set_and_forget_profit_factor": 1.6,
            "actively_managed_total_profit": 15250.0,
            "set_and_forget_total_profit": 11200.0,
            "improvement_percentage": 36.2,
            "trailing_stop_savings": 2850.0,
            "breakeven_preventions": 23,
            "partial_profit_banked": 4200.0,
            "holding_time_reduction": 0.32,
            "total_trades_analyzed": 150,
        }

    def add_websocket_client(self, websocket: WebSocket):
        """Add WebSocket client."""
        self._websocket_clients.append(websocket)

    def remove_websocket_client(self, websocket: WebSocket):
        """Remove WebSocket client."""
        if websocket in self._websocket_clients:
            self._websocket_clients.remove(websocket)

    async def broadcast_trade_update(self, message: dict):
        """Broadcast trade update to all connected clients."""
        disconnected = []
        for client in self._websocket_clients:
            try:
                await client.send_json(message)
            except Exception:
                disconnected.append(client)
        # Remove disconnected clients
        for client in disconnected:
            self.remove_websocket_client(client)


# Global trade manager instance
trade_manager = TradeManager()


@router.get("/active", response_model=list[TradePositionResponse])
async def get_active_trades():
    """
    Get all actively managed trades.

    Returns a list of all positions currently being actively managed.
    """
    try:
        positions = await trade_manager.get_all_positions()
        return [
            TradePositionResponse(
                ticket=p.get("ticket", 0),
                symbol=p.get("symbol", ""),
                direction=p.get("direction", "BUY"),
                entry_price=p.get("entry_price", 0.0),
                current_price=p.get("current_price", 0.0),
                volume=p.get("volume", 0.0),
                stop_loss=p.get("stop_loss"),
                take_profit=p.get("take_profit"),
                entry_time=p.get("entry_time", datetime.now()),
                profit=p.get("profit", 0.0),
                swap=p.get("swap", 0.0),
                commission=p.get("commission", 0.0),
                state=p.get("state", "open"),
                trade_age_seconds=p.get("trade_age_seconds", 0.0),
                is_paused=p.get("ticket", 0) in trade_manager._paused,
            )
            for p in positions
        ]
    except Exception as e:
        logger.error(f"Error fetching active trades: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch active trades",
        )


@router.get("/{ticket:int}/state", response_model=TradeStateResponse)
async def get_trade_state(ticket: int):
    """
    Get trade state and history.

    Returns the current state and complete state transition history for a trade.
    """
    try:
        position = await trade_manager.get_position(ticket)
        if position is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Trade {ticket} not found",
            )

        # Mock state history
        return TradeStateResponse(
            ticket=ticket,
            current_state=position.get("state", "open"),
            state_history=[
                {
                    "from_state": "pending",
                    "to_state": "open",
                    "timestamp": position.get("entry_time", datetime.now()),
                    "reason": "Position opened",
                }
            ],
            total_state_changes=1,
            first_state_time=position.get("entry_time", datetime.now()),
            last_state_time=datetime.now(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching trade state: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch trade state",
        )


@router.post("/{ticket:int}/close", response_model=ActionSuccessResponse)
async def close_trade(ticket: int, request: ManualCloseRequest):
    """
    Manually close a position.

    Immediately closes the specified position and records the reason.
    """
    try:
        result = await trade_manager.close_position(
            ticket, request.reason, request.user
        )
        logger.info(
            f"Position {ticket} closed by user {request.user}: {request.reason}"
        )

        # Broadcast update via WebSocket
        await trade_manager.broadcast_trade_update({
            "event_type": "position_closed",
            "ticket": ticket,
            "timestamp": datetime.now().isoformat(),
            "user": request.user,
            "reason": request.reason,
        })

        return ActionSuccessResponse(
            success=True,
            message=f"Position {ticket} closed successfully",
            ticket=ticket,
            action="close",
            timestamp=datetime.now(),
        )
    except ValueError as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error closing position: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to close position",
        )


@router.post("/{ticket:int}/pause", response_model=ActionSuccessResponse)
async def pause_trade_management(ticket: int, request: PauseManagementRequest):
    """
    Pause active management for a position.

    Stops all automated management actions (trailing stop, breakeven, etc.)
    for the specified position.
    """
    try:
        result = await trade_manager.pause_management(
            ticket, request.reason, request.user
        )
        logger.info(
            f"Management paused for position {ticket} by user {request.user}: {request.reason}"
        )

        # Broadcast update via WebSocket
        await trade_manager.broadcast_trade_update({
            "event_type": "management_paused",
            "ticket": ticket,
            "timestamp": datetime.now().isoformat(),
            "user": request.user,
            "reason": request.reason,
        })

        return ActionSuccessResponse(
            success=True,
            message=f"Management paused for position {ticket}",
            ticket=ticket,
            action="pause",
            timestamp=datetime.now(),
        )
    except ValueError as e:
        logger.error(f"Error pausing management: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error pausing management: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause management",
        )


@router.post("/{ticket:int}/resume", response_model=ActionSuccessResponse)
async def resume_trade_management(ticket: int, request: ResumeManagementRequest):
    """
    Resume active management for a position.

    Resumes all automated management actions for the specified position.
    """
    try:
        result = await trade_manager.resume_management(
            ticket, request.reason, request.user
        )
        logger.info(
            f"Management resumed for position {ticket} by user {request.user}: {request.reason}"
        )

        # Broadcast update via WebSocket
        await trade_manager.broadcast_trade_update({
            "event_type": "management_resumed",
            "ticket": ticket,
            "timestamp": datetime.now().isoformat(),
            "user": request.user,
            "reason": request.reason,
        })

        return ActionSuccessResponse(
            success=True,
            message=f"Management resumed for position {ticket}",
            ticket=ticket,
            action="resume",
            timestamp=datetime.now(),
        )
    except ValueError as e:
        logger.error(f"Error resuming management: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error resuming management: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume management",
        )


@router.put("/{ticket:int}/sl", response_model=ActionSuccessResponse)
async def set_stop_loss(ticket: int, request: ManualStopLossRequest):
    """
    Manually set stop loss for a position.

    Updates the stop loss level for the specified position.
    """
    try:
        result = await trade_manager.set_stop_loss(
            ticket, request.stop_loss, request.reason, request.user
        )
        logger.info(
            f"Stop loss set to {request.stop_loss} for position {ticket} by user {request.user}"
        )

        # Broadcast update via WebSocket
        await trade_manager.broadcast_trade_update({
            "event_type": "stop_loss_updated",
            "ticket": ticket,
            "timestamp": datetime.now().isoformat(),
            "stop_loss": request.stop_loss,
            "user": request.user,
        })

        return ActionSuccessResponse(
            success=True,
            message=f"Stop loss updated for position {ticket}",
            ticket=ticket,
            action="set_stop_loss",
            timestamp=datetime.now(),
        )
    except ValueError as e:
        logger.error(f"Error setting stop loss: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error setting stop loss: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set stop loss",
        )


@router.put("/{ticket:int}/tp", response_model=ActionSuccessResponse)
async def set_take_profit(ticket: int, request: ManualTakeProfitRequest):
    """
    Manually set take profit for a position.

    Updates the take profit level for the specified position.
    """
    try:
        result = await trade_manager.set_take_profit(
            ticket, request.take_profit, request.reason, request.user
        )
        logger.info(
            f"Take profit set to {request.take_profit} for position {ticket} by user {request.user}"
        )

        # Broadcast update via WebSocket
        await trade_manager.broadcast_trade_update({
            "event_type": "take_profit_updated",
            "ticket": ticket,
            "timestamp": datetime.now().isoformat(),
            "take_profit": request.take_profit,
            "user": request.user,
        })

        return ActionSuccessResponse(
            success=True,
            message=f"Take profit updated for position {ticket}",
            ticket=ticket,
            action="set_take_profit",
            timestamp=datetime.now(),
        )
    except ValueError as e:
        logger.error(f"Error setting take profit: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error setting take profit: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set take profit",
        )


@router.get("/performance", response_model=PerformanceMetrics)
async def get_performance_metrics():
    """
    Get performance metrics comparing active vs passive management.

    Returns comprehensive performance comparison showing the value
    added by active trade management.
    """
    try:
        metrics = await trade_manager.get_performance_metrics()
        return PerformanceMetrics(**metrics)
    except Exception as e:
        logger.error(f"Error fetching performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch performance metrics",
        )


@router.websocket("/ws/trades")
async def websocket_trades(websocket: WebSocket):
    """
    WebSocket endpoint for real-time trade updates.

    Clients connect to this endpoint to receive real-time updates
    for all trade management actions.
    """
    await websocket.accept()
    trade_manager.add_websocket_client(websocket)
    logger.info("WebSocket client connected")

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "event_type": "connected",
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to trade updates stream",
        })

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            # Echo back or process client messages if needed
            logger.debug(f"Received WebSocket message: {data}")

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
        trade_manager.remove_websocket_client(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        trade_manager.remove_websocket_client(websocket)
