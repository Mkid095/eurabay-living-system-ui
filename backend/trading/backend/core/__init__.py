"""Core trading components."""

from .active_trade_manager import ActiveTradeManager, MT5Position
from .breakeven_manager import (
    BreakevenManager,
    BreakevenConfig,
    BreakevenUpdate,
)
from .trade_state import TradeState, TradeStateMachine, TradeStateTransition
from .trade_position import TradePosition
from .trailing_stop_manager import (
    TrailingStopManager,
    TrailingStopConfig,
    TrailingStopUpdate,
)

__all__ = [
    "ActiveTradeManager",
    "MT5Position",
    "BreakevenManager",
    "BreakevenConfig",
    "BreakevenUpdate",
    "TradeState",
    "TradeStateMachine",
    "TradeStateTransition",
    "TradePosition",
    "TrailingStopManager",
    "TrailingStopConfig",
    "TrailingStopUpdate",
]
