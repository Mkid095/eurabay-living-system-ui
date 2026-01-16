"""
API schemas for active trade management.

This module defines Pydantic models for request/response validation
for all API endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class TradeState(str, Enum):
    """Trade state enumeration matching core.trade_state.TradeState."""

    PENDING = "pending"
    OPEN = "open"
    BREAKEVEN = "breakeven"
    PARTIAL = "partial"
    SCALED_IN = "scaled_in"
    SCALED_OUT = "scaled_out"
    CLOSED = "closed"


class Direction(str, Enum):
    """Trade direction."""

    BUY = "BUY"
    SELL = "SELL"


class AlertPriority(str, Enum):
    """Alert priority levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    """Types of management alerts."""

    TRAILING_STOP = "trailing_stop"
    BREAKEVEN = "breakeven"
    PARTIAL_PROFIT = "partial_profit"
    POSITION_CLOSED = "position_closed"
    MANUAL_OVERRIDE = "manual_override"
    HOLDING_LIMIT = "holding_limit"


class TradeStateTransition(BaseModel):
    """State transition record."""

    from_state: str
    to_state: str
    timestamp: datetime
    reason: str


class TradePositionResponse(BaseModel):
    """Trade position response model."""

    ticket: int
    symbol: str
    direction: str
    entry_price: float
    current_price: float
    volume: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    entry_time: datetime
    profit: float
    swap: float
    commission: float
    state: str
    trade_age_seconds: float
    is_paused: bool = False


class TradeStateResponse(BaseModel):
    """Trade state response model."""

    ticket: int
    current_state: str
    state_history: list[TradeStateTransition]
    total_state_changes: int
    first_state_time: Optional[datetime]
    last_state_time: Optional[datetime]


class ManualCloseRequest(BaseModel):
    """Request to manually close a position."""

    reason: str = Field(..., description="Reason for manual closure")
    user: str = Field(..., description="User performing the action")


class ManualStopLossRequest(BaseModel):
    """Request to manually set stop loss."""

    stop_loss: float = Field(..., description="New stop loss price", gt=0)
    reason: str = Field(..., description="Reason for manual SL change")
    user: str = Field(..., description="User performing the action")


class ManualTakeProfitRequest(BaseModel):
    """Request to manually set take profit."""

    take_profit: float = Field(..., description="New take profit price", gt=0)
    reason: str = Field(..., description="Reason for manual TP change")
    user: str = Field(..., description="User performing the action")


class PauseManagementRequest(BaseModel):
    """Request to pause active management."""

    reason: str = Field(..., description="Reason for pausing management")
    user: str = Field(..., description="User performing the action")


class ResumeManagementRequest(BaseModel):
    """Request to resume active management."""

    reason: str = Field(..., description="Reason for resuming management")
    user: str = Field(..., description="User performing the action")


class ActionSuccessResponse(BaseModel):
    """Response for successful action."""

    success: bool
    message: str
    ticket: int
    action: str
    timestamp: datetime


class PerformanceMetrics(BaseModel):
    """Performance metrics for active vs passive comparison."""

    actively_managed_win_rate: float
    set_and_forget_win_rate: float
    actively_managed_profit_factor: float
    set_and_forget_profit_factor: float
    actively_managed_total_profit: float
    set_and_forget_total_profit: float
    improvement_percentage: float
    trailing_stop_savings: float
    breakeven_preventions: int
    partial_profit_banked: float
    holding_time_reduction: float
    total_trades_analyzed: int


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str
    detail: Optional[str] = None
    ticket: Optional[int] = None


class TradeUpdateMessage(BaseModel):
    """WebSocket trade update message."""

    event_type: str = Field(..., description="Type of event: update, state_change, closed")
    ticket: int
    timestamp: datetime
    data: dict


class AlertResponse(BaseModel):
    """Management alert response model."""

    alert_id: str
    alert_type: AlertType
    priority: AlertPriority
    ticket: int
    symbol: str
    message: str
    timestamp: datetime
    data: dict = Field(default_factory=dict)


class AlertDigestResponse(BaseModel):
    """Alert digest response model."""

    digest_id: str
    start_time: datetime
    end_time: datetime
    total_alerts: int
    alerts_by_type: dict[str, int]
    alerts_by_priority: dict[str, int]
    alerts: list[AlertResponse]


class AlertsListResponse(BaseModel):
    """Response for alerts list endpoint."""

    alerts: list[AlertResponse]
    total_count: int
    filtered: bool = False
