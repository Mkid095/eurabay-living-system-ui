"""
Trade state management for active trade management.

Defines the state machine for tracking trade lifecycle.
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime


class TradeState(Enum):
    """Trade states throughout lifecycle."""

    PENDING = "pending"
    OPEN = "open"
    PARTIAL = "partial"
    CLOSED = "closed"


@dataclass
class TradeStateTransition:
    """Record of a state transition."""

    from_state: TradeState
    to_state: TradeState
    timestamp: datetime
    reason: str


@dataclass
class TradePosition:
    """Represents a trading position."""

    ticket: int
    symbol: str
    direction: str  # "BUY" or "SELL"
    entry_price: float
    current_price: float
    volume: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    entry_time: datetime
    profit: float
    swap: float
    commission: float

    # State tracking
    state: TradeState = TradeState.OPEN
    state_history: list[TradeStateTransition] = field(default_factory=list)

    def get_trade_age_seconds(self) -> int:
        """Get the age of this trade in seconds."""
        return int((datetime.utcnow() - self.entry_time).total_seconds())

    def transition_state(self, new_state: TradeState, reason: str = "") -> None:
        """Transition to a new state with logging."""
        transition = TradeStateTransition(
            from_state=self.state,
            to_state=new_state,
            timestamp=datetime.utcnow(),
            reason=reason,
        )
        self.state_history.append(transition)
        self.state = new_state


class TradeStateMachine:
    """
    Manages state transitions for trades.

    Enforces valid state transitions and tracks state history.
    """

    # Valid state transitions: from_state -> [valid_to_states]
    VALID_TRANSITIONS: dict[TradeState, list[TradeState]] = {
        TradeState.PENDING: [TradeState.OPEN, TradeState.CLOSED],
        TradeState.OPEN: [TradeState.PARTIAL, TradeState.CLOSED],
        TradeState.PARTIAL: [TradeState.PARTIAL, TradeState.CLOSED],
        TradeState.CLOSED: [],  # Terminal state
    }

    @classmethod
    def can_transition(cls, from_state: TradeState, to_state: TradeState) -> bool:
        """Check if a state transition is valid."""
        valid_targets = cls.VALID_TRANSITIONS.get(from_state, [])
        return to_state in valid_targets

    @classmethod
    def validate_transition(
        cls, from_state: TradeState, to_state: TradeState
    ) -> None:
        """
        Validate a state transition.

        Raises:
            ValueError: If transition is invalid.
        """
        if not cls.can_transition(from_state, to_state):
            raise ValueError(
                f"Invalid state transition: {from_state.value} -> {to_state.value}"
            )

    @classmethod
    def get_state(cls, position: TradePosition) -> TradeState:
        """Get the current state of a position."""
        return position.state
