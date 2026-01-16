"""
Trade state management for active trade management.

Defines the state machine for tracking trade lifecycle.
"""

import logging
from enum import Enum
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Type checking import to avoid circular dependency
if TYPE_CHECKING:
    from typing import Any


class TradeState(Enum):
    """
    Trade states throughout lifecycle.

    States:
        PENDING: Order sent, not yet filled
        OPEN: Position open, initial management
        BREAKEVEN: SL moved to entry price
        PARTIAL: Partial profit taken
        SCALED_IN: Additional size added to position
        SCALED_OUT: Partial size closed
        CLOSED: Position fully closed (terminal state)
    """

    PENDING = "pending"
    OPEN = "open"
    BREAKEVEN = "breakeven"
    PARTIAL = "partial"
    SCALED_IN = "scaled_in"
    SCALED_OUT = "scaled_out"
    CLOSED = "closed"

    def __str__(self) -> str:
        """Return string representation of state."""
        return self.value


@dataclass
class TradeStateTransition:
    """
    Record of a state transition.

    Attributes:
        from_state: State before transition
        to_state: State after transition
        timestamp: When the transition occurred
        reason: Human-readable reason for the transition
        trade_ticket: Associated position ticket
    """

    from_state: TradeState
    to_state: TradeState
    timestamp: datetime
    reason: str
    trade_ticket: int

    def to_dict(self) -> dict:
        """Convert transition to dictionary for database storage."""
        return {
            "from_state": self.from_state.value,
            "to_state": self.to_state.value,
            "timestamp": self.timestamp.isoformat(),
            "reason": self.reason,
            "trade_ticket": self.trade_ticket,
        }


@dataclass
class TradePosition:
    """
    Represents a trading position.

    Attributes:
        ticket: Unique position identifier
        symbol: Trading symbol (e.g., "EURUSD")
        direction: "BUY" or "SELL"
        entry_price: Price at position entry
        current_price: Current market price
        volume: Position size in lots
        stop_loss: Stop loss price (optional)
        take_profit: Take profit price (optional)
        entry_time: When position was opened
        profit: Current unrealized profit/loss
        swap: Accumulated swap fees
        commission: Trading commissions
        state: Current trade state
        state_history: List of all state transitions
    """

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
        """
        Transition to a new state with logging and history tracking.

        Args:
            new_state: The state to transition to
            reason: Human-readable reason for the transition

        Raises:
            ValueError: If the transition is invalid
        """
        # Validate transition before executing
        TradeStateMachine.validate_transition(self.state, new_state)

        old_state = self.state
        transition = TradeStateTransition(
            from_state=self.state,
            to_state=new_state,
            timestamp=datetime.utcnow(),
            reason=reason,
            trade_ticket=self.ticket,
        )

        # Log the transition
        logger.info(
            f"State transition for position {self.ticket} ({self.symbol} {self.direction}): "
            f"{old_state.value} -> {new_state.value} | Reason: {reason}"
        )

        # Update state and history
        self.state_history.append(transition)
        self.state = new_state

    def get_state_history(self) -> list[TradeStateTransition]:
        """
        Get the complete state history for this position.

        Returns:
            List of all state transitions in chronological order
        """
        return self.state_history.copy()

    def has_been_in_state(self, state: TradeState) -> bool:
        """
        Check if position has ever been in a specific state.

        Args:
            state: TradeState to check

        Returns:
            True if position has been in the state (including current state)
        """
        # Check current state first
        if self.state == state:
            return True

        # Check history
        return any(
            transition.to_state == state or transition.from_state == state
            for transition in self.state_history
        )

    def get_current_state_duration_seconds(self) -> int:
        """
        Get how long the position has been in its current state.

        Returns:
            Duration in seconds since last state transition
        """
        if not self.state_history:
            return self.get_trade_age_seconds()

        # Get the most recent transition
        last_transition = self.state_history[-1]
        return int((datetime.utcnow() - last_transition.timestamp).total_seconds())


class TradeStateMachine:
    """
    Manages state transitions for trades.

    Enforces valid state transitions and tracks state history.
    Provides state-based rule enforcement for trade management.

    State Transition Rules:
        PENDING -> OPEN: When order is filled
        PENDING -> CLOSED: When order is cancelled/rejected

        OPEN -> BREAKEVEN: When SL is moved to entry price
        OPEN -> PARTIAL: When partial profit is taken
        OPEN -> SCALED_IN: When additional size is added
        OPEN -> SCALED_OUT: When partial position is closed
        OPEN -> CLOSED: When position is fully closed

        BREAKEVEN -> PARTIAL: When partial profit is taken after breakeven
        BREAKEVEN -> SCALED_IN: When additional size is added after breakeven
        BREAKEVEN -> SCALED_OUT: When partial position is closed after breakeven
        BREAKEVEN -> CLOSED: When position is fully closed

        PARTIAL -> PARTIAL: Multiple partial closes allowed
        PARTIAL -> SCALED_IN: Can scale in after partial profit (if profitable)
        PARTIAL -> SCALED_OUT: Can scale out further after partial
        PARTIAL -> CLOSED: When remaining position is closed

        SCALED_IN -> PARTIAL: Can take partial profit after scaling in
        SCALED_IN -> SCALED_OUT: Can scale out after scaling in
        SCALED_IN -> CLOSED: When position is closed

        SCALED_OUT -> SCALED_OUT: Multiple scale-outs allowed
        SCALED_OUT -> CLOSED: When position is fully closed

        CLOSED: Terminal state (no transitions allowed)
    """

    # Valid state transitions: from_state -> [valid_to_states]
    VALID_TRANSITIONS: dict[TradeState, list[TradeState]] = {
        TradeState.PENDING: [TradeState.OPEN, TradeState.CLOSED],
        TradeState.OPEN: [
            TradeState.BREAKEVEN,
            TradeState.PARTIAL,
            TradeState.SCALED_IN,
            TradeState.SCALED_OUT,
            TradeState.CLOSED,
        ],
        TradeState.BREAKEVEN: [
            TradeState.PARTIAL,
            TradeState.SCALED_IN,
            TradeState.SCALED_OUT,
            TradeState.CLOSED,
        ],
        TradeState.PARTIAL: [
            TradeState.PARTIAL,
            TradeState.SCALED_IN,
            TradeState.SCALED_OUT,
            TradeState.CLOSED,
        ],
        TradeState.SCALED_IN: [
            TradeState.PARTIAL,
            TradeState.SCALED_OUT,
            TradeState.CLOSED,
        ],
        TradeState.SCALED_OUT: [TradeState.SCALED_OUT, TradeState.CLOSED],
        TradeState.CLOSED: [],  # Terminal state
    }

    @classmethod
    def can_transition(cls, from_state: TradeState, to_state: TradeState) -> bool:
        """
        Check if a state transition is valid.

        Args:
            from_state: Current state
            to_state: Target state

        Returns:
            True if transition is valid
        """
        valid_targets = cls.VALID_TRANSITIONS.get(from_state, [])
        return to_state in valid_targets

    @classmethod
    def validate_transition(
        cls, from_state: TradeState, to_state: TradeState
    ) -> None:
        """
        Validate a state transition.

        Args:
            from_state: Current state
            to_state: Target state

        Raises:
            ValueError: If transition is invalid
        """
        if not cls.can_transition(from_state, to_state):
            raise ValueError(
                f"Invalid state transition: {from_state.value} -> {to_state.value}. "
                f"Valid transitions from {from_state.value}: "
                f"{[s.value for s in cls.VALID_TRANSITIONS.get(from_state, [])]}"
            )

    @classmethod
    def get_state(cls, position: TradePosition) -> TradeState:
        """
        Get the current state of a position.

        Args:
            position: TradePosition to query

        Returns:
            Current TradeState
        """
        return position.state

    @classmethod
    def can_scale_out(cls, position: TradePosition) -> bool:
        """
        Check if position can scale out (state-based rule).

        Position can scale out if:
        - Currently in OPEN, BREAKEVEN, PARTIAL, or SCALED_IN state
        - Has not been fully closed

        Args:
            position: TradePosition to check

        Returns:
            True if scale-out is allowed
        """
        return position.state in [
            TradeState.OPEN,
            TradeState.BREAKEVEN,
            TradeState.PARTIAL,
            TradeState.SCALED_IN,
        ]

    @classmethod
    def can_scale_in(cls, position: TradePosition) -> bool:
        """
        Check if position can scale in (state-based rule).

        Position can scale in if:
        - Currently in OPEN, BREAKEVEN, or PARTIAL state
        - Has not already scaled in (to avoid over-leveraging)

        Args:
            position: TradePosition to check

        Returns:
            True if scale-in is allowed
        """
        # Can scale in from OPEN, BREAKEVEN, or PARTIAL states
        # But NOT if already in SCALED_IN state (to prevent excessive sizing)
        allowed_states = [TradeState.OPEN, TradeState.BREAKEVEN, TradeState.PARTIAL]

        if position.state not in allowed_states:
            return False

        # Cannot scale in if already scaled in (prevent excessive position sizing)
        if position.has_been_in_state(TradeState.SCALED_IN):
            logger.debug(
                f"Position {position.ticket} has already been scaled in, "
                f"preventing additional scale-in"
            )
            return False

        return True

    @classmethod
    def is_closed(cls, position: TradePosition) -> bool:
        """
        Check if position is closed.

        Args:
            position: TradePosition to check

        Returns:
            True if position is in CLOSED state
        """
        return position.state == TradeState.CLOSED

    @classmethod
    def is_active(cls, position: TradePosition) -> bool:
        """
        Check if position is active (not closed).

        Args:
            position: TradePosition to check

        Returns:
            True if position is not in CLOSED state
        """
        return position.state != TradeState.CLOSED

    @classmethod
    def get_valid_next_states(cls, position: TradePosition) -> list[TradeState]:
        """
        Get list of valid next states for a position.

        Args:
            position: TradePosition to query

        Returns:
            List of valid TradeState values
        """
        return cls.VALID_TRANSITIONS.get(position.state, []).copy()

    @classmethod
    def get_state_description(cls, state: TradeState) -> str:
        """
        Get human-readable description of a state.

        Args:
            state: TradeState to describe

        Returns:
            Human-readable description
        """
        descriptions = {
            TradeState.PENDING: "Order sent, awaiting fill",
            TradeState.OPEN: "Position open, active management",
            TradeState.BREAKEVEN: "Stop loss moved to breakeven",
            TradeState.PARTIAL: "Partial profit taken",
            TradeState.SCALED_IN: "Position size increased",
            TradeState.SCALED_OUT: "Partial position closed",
            TradeState.CLOSED: "Position fully closed",
        }
        return descriptions.get(state, "Unknown state")


class TradeStateTracker:
    """
    Tracks state history in a database for persistence and analysis.

    This class provides an interface for storing and retrieving
    state transition history from a database. The actual database
    implementation can be swapped out (SQLite, PostgreSQL, etc.)
    """

    def __init__(self):
        """Initialize the state tracker."""
        self._transitions: list[TradeStateTransition] = []
        logger.info("TradeStateTracker initialized")

    def store_transition(self, transition: TradeStateTransition) -> None:
        """
        Store a state transition in the database.

        Args:
            transition: TradeStateTransition to store
        """
        # In a real implementation, this would write to a database
        # For now, store in memory
        self._transitions.append(transition)
        logger.debug(
            f"Stored transition for position {transition.trade_ticket}: "
            f"{transition.from_state.value} -> {transition.to_state.value}"
        )

    def get_transitions_for_position(
        self, ticket: int
    ) -> list[TradeStateTransition]:
        """
        Get all state transitions for a specific position.

        Args:
            ticket: Position ticket number

        Returns:
            List of TradeStateTransition records
        """
        return [
            t for t in self._transitions if t.trade_ticket == ticket
        ]

    def get_all_transitions(self) -> list[TradeStateTransition]:
        """
        Get all stored state transitions.

        Returns:
            List of all TradeStateTransition records
        """
        return self._transitions.copy()

    def clear_history(self) -> None:
        """Clear all stored transition history."""
        self._transitions.clear()
        logger.debug("Trade state history cleared")

    def export_to_csv(self, filepath: str) -> None:
        """
        Export state transition history to CSV file.

        Args:
            filepath: Path to output CSV file
        """
        import csv

        with open(filepath, "w", newline="") as csvfile:
            fieldnames = [
                "trade_ticket",
                "from_state",
                "to_state",
                "timestamp",
                "reason",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for transition in self._transitions:
                writer.writerow({
                    "trade_ticket": transition.trade_ticket,
                    "from_state": transition.from_state.value,
                    "to_state": transition.to_state.value,
                    "timestamp": transition.timestamp.isoformat(),
                    "reason": transition.reason,
                })

        logger.info(f"Exported {len(self._transitions)} transitions to {filepath}")
