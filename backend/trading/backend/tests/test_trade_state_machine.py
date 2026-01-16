"""
Unit tests for TradeStateMachine.

Tests the trade state machine functionality including:
- State definitions (PENDING, OPEN, BREAKEVEN, PARTIAL, SCALED_IN, SCALED_OUT, CLOSED)
- State transitions with validation
- State history tracking
- State-based rule enforcement (can_scale_in, can_scale_out)
- Invalid transition prevention
- State tracking and persistence
- Export functionality
"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta

from backend.core import (
    TradeState,
    TradeStateMachine,
    TradeStateTransition,
    TradeStateTracker,
    TradePosition,
)


@pytest.fixture
def sample_position():
    """Create a sample trade position for testing."""
    return TradePosition(
        ticket=12345,
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.0850,
        current_price=1.0870,
        volume=0.1,
        stop_loss=1.0800,
        take_profit=1.0950,
        entry_time=datetime.utcnow(),
        profit=200.0,
        swap=0.5,
        commission=1.0,
        state=TradeState.OPEN,
    )


@pytest.fixture
def state_tracker():
    """Create a TradeStateTracker for testing."""
    return TradeStateTracker()


class TestTradeState:
    """Test suite for TradeState enum."""

    def test_all_states_defined(self):
        """Test that all required states are defined."""
        required_states = [
            "PENDING",
            "OPEN",
            "BREAKEVEN",
            "PARTIAL",
            "SCALED_IN",
            "SCALED_OUT",
            "CLOSED",
        ]

        for state_name in required_states:
            assert hasattr(TradeState, state_name)
            state = getattr(TradeState, state_name)
            assert isinstance(state, TradeState)

    def test_state_string_representation(self):
        """Test that states have correct string values."""
        assert str(TradeState.PENDING) == "pending"
        assert str(TradeState.OPEN) == "open"
        assert str(TradeState.BREAKEVEN) == "breakeven"
        assert str(TradeState.PARTIAL) == "partial"
        assert str(TradeState.SCALED_IN) == "scaled_in"
        assert str(TradeState.SCALED_OUT) == "scaled_out"
        assert str(TradeState.CLOSED) == "closed"


class TestTradeStateTransition:
    """Test suite for TradeStateTransition dataclass."""

    def test_transition_creation(self):
        """Test creating a state transition record."""
        from_state = TradeState.OPEN
        to_state = TradeState.BREAKEVEN
        timestamp = datetime.utcnow()
        reason = "Profit target reached"
        trade_ticket = 12345

        transition = TradeStateTransition(
            from_state=from_state,
            to_state=to_state,
            timestamp=timestamp,
            reason=reason,
            trade_ticket=trade_ticket,
        )

        assert transition.from_state == from_state
        assert transition.to_state == to_state
        assert transition.timestamp == timestamp
        assert transition.reason == reason
        assert transition.trade_ticket == trade_ticket

    def test_transition_to_dict(self):
        """Test converting transition to dictionary."""
        transition = TradeStateTransition(
            from_state=TradeState.OPEN,
            to_state=TradeState.BREAKEVEN,
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            reason="Test transition",
            trade_ticket=12345,
        )

        result = transition.to_dict()

        assert result["from_state"] == "open"
        assert result["to_state"] == "breakeven"
        assert result["timestamp"] == "2024-01-01T12:00:00"
        assert result["reason"] == "Test transition"
        assert result["trade_ticket"] == 12345


class TestTradeStateMachine:
    """Test suite for TradeStateMachine validation and rules."""

    def test_valid_transitions_from_pending(self):
        """Test valid transitions from PENDING state."""
        # PENDING can go to OPEN or CLOSED
        assert TradeStateMachine.can_transition(TradeState.PENDING, TradeState.OPEN)
        assert TradeStateMachine.can_transition(TradeState.PENDING, TradeState.CLOSED)
        # But not to other states
        assert not TradeStateMachine.can_transition(TradeState.PENDING, TradeState.BREAKEVEN)
        assert not TradeStateMachine.can_transition(TradeState.PENDING, TradeState.PARTIAL)

    def test_valid_transitions_from_open(self):
        """Test valid transitions from OPEN state."""
        # OPEN can go to BREAKEVEN, PARTIAL, SCALED_IN, SCALED_OUT, CLOSED
        assert TradeStateMachine.can_transition(TradeState.OPEN, TradeState.BREAKEVEN)
        assert TradeStateMachine.can_transition(TradeState.OPEN, TradeState.PARTIAL)
        assert TradeStateMachine.can_transition(TradeState.OPEN, TradeState.SCALED_IN)
        assert TradeStateMachine.can_transition(TradeState.OPEN, TradeState.SCALED_OUT)
        assert TradeStateMachine.can_transition(TradeState.OPEN, TradeState.CLOSED)
        # But not back to PENDING
        assert not TradeStateMachine.can_transition(TradeState.OPEN, TradeState.PENDING)

    def test_valid_transitions_from_breakeven(self):
        """Test valid transitions from BREAKEVEN state."""
        assert TradeStateMachine.can_transition(TradeState.BREAKEVEN, TradeState.PARTIAL)
        assert TradeStateMachine.can_transition(TradeState.BREAKEVEN, TradeState.SCALED_IN)
        assert TradeStateMachine.can_transition(TradeState.BREAKEVEN, TradeState.SCALED_OUT)
        assert TradeStateMachine.can_transition(TradeState.BREAKEVEN, TradeState.CLOSED)
        # Cannot go back to OPEN or PENDING
        assert not TradeStateMachine.can_transition(TradeState.BREAKEVEN, TradeState.OPEN)
        assert not TradeStateMachine.can_transition(TradeState.BREAKEVEN, TradeState.PENDING)

    def test_valid_transitions_from_partial(self):
        """Test valid transitions from PARTIAL state."""
        # PARTIAL can go to PARTIAL again (multiple partials)
        assert TradeStateMachine.can_transition(TradeState.PARTIAL, TradeState.PARTIAL)
        assert TradeStateMachine.can_transition(TradeState.PARTIAL, TradeState.SCALED_IN)
        assert TradeStateMachine.can_transition(TradeState.PARTIAL, TradeState.SCALED_OUT)
        assert TradeStateMachine.can_transition(TradeState.PARTIAL, TradeState.CLOSED)

    def test_valid_transitions_from_scaled_in(self):
        """Test valid transitions from SCALED_IN state."""
        assert TradeStateMachine.can_transition(TradeState.SCALED_IN, TradeState.PARTIAL)
        assert TradeStateMachine.can_transition(TradeState.SCALED_IN, TradeState.SCALED_OUT)
        assert TradeStateMachine.can_transition(TradeState.SCALED_IN, TradeState.CLOSED)
        # Cannot scale in again from SCALED_IN (prevents excessive sizing)
        assert not TradeStateMachine.can_transition(TradeState.SCALED_IN, TradeState.SCALED_IN)

    def test_valid_transitions_from_scaled_out(self):
        """Test valid transitions from SCALED_OUT state."""
        assert TradeStateMachine.can_transition(TradeState.SCALED_OUT, TradeState.SCALED_OUT)
        assert TradeStateMachine.can_transition(TradeState.SCALED_OUT, TradeState.CLOSED)

    def test_closed_is_terminal_state(self):
        """Test that CLOSED is a terminal state (no outgoing transitions)."""
        valid_from_closed = TradeStateMachine.VALID_TRANSITIONS[TradeState.CLOSED]
        assert valid_from_closed == []
        assert not TradeStateMachine.can_transition(TradeState.CLOSED, TradeState.OPEN)
        assert not TradeStateMachine.can_transition(TradeState.CLOSED, TradeState.BREAKEVEN)

    def test_validate_transition_success(self):
        """Test successful transition validation."""
        # Should not raise exception
        TradeStateMachine.validate_transition(TradeState.OPEN, TradeState.BREAKEVEN)
        TradeStateMachine.validate_transition(TradeState.PENDING, TradeState.OPEN)

    def test_validate_transition_failure(self):
        """Test that invalid transitions raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            TradeStateMachine.validate_transition(TradeState.CLOSED, TradeState.OPEN)

        assert "Invalid state transition" in str(exc_info.value)
        assert "closed" in str(exc_info.value).lower()
        assert "open" in str(exc_info.value).lower()

    def test_validate_transition_includes_valid_targets(self):
        """Test that validation error includes valid target states."""
        with pytest.raises(ValueError) as exc_info:
            TradeStateMachine.validate_transition(TradeState.OPEN, TradeState.PENDING)

        error_msg = str(exc_info.value)
        # Should list valid transitions from OPEN
        assert "breakeven" in error_msg
        assert "partial" in error_msg

    def test_get_state(self):
        """Test getting current state of position."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0870,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=200.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.OPEN,
        )

        assert TradeStateMachine.get_state(position) == TradeState.OPEN

    def test_can_scale_out_from_open(self):
        """Test that positions can scale out from OPEN state."""
        assert TradeStateMachine.can_scale_out(
            TradePosition(
                ticket=12345,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0870,
                volume=0.1,
                stop_loss=1.0800,
                take_profit=1.0950,
                entry_time=datetime.utcnow(),
                profit=200.0,
                swap=0.5,
                commission=1.0,
                state=TradeState.OPEN,
            )
        )

    def test_can_scale_out_from_breakeven(self):
        """Test that positions can scale out from BREAKEVEN state."""
        assert TradeStateMachine.can_scale_out(
            TradePosition(
                ticket=12345,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0870,
                volume=0.1,
                stop_loss=1.0850,
                take_profit=1.0950,
                entry_time=datetime.utcnow(),
                profit=200.0,
                swap=0.5,
                commission=1.0,
                state=TradeState.BREAKEVEN,
            )
        )

    def test_cannot_scale_out_from_closed(self):
        """Test that closed positions cannot scale out."""
        assert not TradeStateMachine.can_scale_out(
            TradePosition(
                ticket=12345,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0870,
                volume=0.1,
                stop_loss=None,
                take_profit=None,
                entry_time=datetime.utcnow(),
                profit=200.0,
                swap=0.5,
                commission=1.0,
                state=TradeState.CLOSED,
            )
        )

    def test_can_scale_in_from_open(self):
        """Test that positions can scale in from OPEN state."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0870,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=200.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.OPEN,
        )

        assert TradeStateMachine.can_scale_in(position)

    def test_cannot_scale_in_after_scaled_in(self):
        """Test that positions cannot scale in if already scaled in."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0870,
            volume=0.15,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=200.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.OPEN,
        )

        # Simulate previous scale-in
        position.state_history.append(
            TradeStateTransition(
                from_state=TradeState.OPEN,
                to_state=TradeState.SCALED_IN,
                timestamp=datetime.utcnow(),
                reason="Scale in at 1R profit",
                trade_ticket=12345,
            )
        )

        assert not TradeStateMachine.can_scale_in(position)

    def test_cannot_scale_in_from_scaled_in_state(self):
        """Test that positions in SCALED_IN state cannot scale in again."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0870,
            volume=0.15,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=200.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.SCALED_IN,
        )

        assert not TradeStateMachine.can_scale_in(position)

    def test_is_closed(self):
        """Test checking if position is closed."""
        closed_position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0870,
            volume=0.1,
            stop_loss=None,
            take_profit=None,
            entry_time=datetime.utcnow(),
            profit=200.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.CLOSED,
        )

        assert TradeStateMachine.is_closed(closed_position)

        open_position = TradePosition(
            ticket=12346,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0870,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=200.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.OPEN,
        )

        assert not TradeStateMachine.is_closed(open_position)

    def test_is_active(self):
        """Test checking if position is active (not closed)."""
        active_position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0870,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=200.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.OPEN,
        )

        assert TradeStateMachine.is_active(active_position)

        closed_position = TradePosition(
            ticket=12346,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0870,
            volume=0.1,
            stop_loss=None,
            take_profit=None,
            entry_time=datetime.utcnow(),
            profit=200.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.CLOSED,
        )

        assert not TradeStateMachine.is_active(closed_position)

    def test_get_valid_next_states(self):
        """Test getting valid next states for a position."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0870,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=200.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.OPEN,
        )

        valid_states = TradeStateMachine.get_valid_next_states(position)

        assert TradeState.BREAKEVEN in valid_states
        assert TradeState.PARTIAL in valid_states
        assert TradeState.SCALED_IN in valid_states
        assert TradeState.SCALED_OUT in valid_states
        assert TradeState.CLOSED in valid_states
        assert TradeState.PENDING not in valid_states

    def test_get_state_description(self):
        """Test getting human-readable state descriptions."""
        assert "awaiting fill" in TradeStateMachine.get_state_description(TradeState.PENDING).lower()
        assert "active management" in TradeStateMachine.get_state_description(TradeState.OPEN).lower()
        assert "breakeven" in TradeStateMachine.get_state_description(TradeState.BREAKEVEN).lower()
        assert "partial profit" in TradeStateMachine.get_state_description(TradeState.PARTIAL).lower()
        assert "increased" in TradeStateMachine.get_state_description(TradeState.SCALED_IN).lower()
        assert "closed" in TradeStateMachine.get_state_description(TradeState.SCALED_OUT).lower()
        assert "fully closed" in TradeStateMachine.get_state_description(TradeState.CLOSED).lower()


class TestTradePositionStateTransitions:
    """Test suite for TradePosition state transition methods."""

    def test_successful_state_transition(self, sample_position):
        """Test successful state transition with validation."""
        initial_state = sample_position.state
        assert initial_state == TradeState.OPEN

        # Transition to BREAKEVEN
        sample_position.transition_state(TradeState.BREAKEVEN, "Profit target reached")

        assert sample_position.state == TradeState.BREAKEVEN
        assert len(sample_position.state_history) == 1

        transition = sample_position.state_history[0]
        assert transition.from_state == TradeState.OPEN
        assert transition.to_state == TradeState.BREAKEVEN
        assert transition.reason == "Profit target reached"
        assert transition.trade_ticket == 12345

    def test_invalid_state_transition_raises_error(self, sample_position):
        """Test that invalid state transitions raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            sample_position.transition_state(TradeState.PENDING, "Invalid transition")

        assert "Invalid state transition" in str(exc_info.value)

    def test_multiple_state_transitions(self, sample_position):
        """Test multiple sequential state transitions."""
        # OPEN -> BREAKEVEN
        sample_position.transition_state(TradeState.BREAKEVEN, "Moved SL to breakeven")
        assert sample_position.state == TradeState.BREAKEVEN

        # BREAKEVEN -> PARTIAL
        sample_position.transition_state(TradeState.PARTIAL, "Took 50% profit at 2R")
        assert sample_position.state == TradeState.PARTIAL

        # PARTIAL -> CLOSED
        sample_position.transition_state(TradeState.CLOSED, "Closed remaining position")
        assert sample_position.state == TradeState.CLOSED

        assert len(sample_position.state_history) == 3

    def test_state_history_order(self, sample_position):
        """Test that state history maintains chronological order."""
        sample_position.transition_state(TradeState.BREAKEVEN, "Breakeven")
        sample_position.transition_state(TradeState.PARTIAL, "Partial 1")
        sample_position.transition_state(TradeState.PARTIAL, "Partial 2")

        history = sample_position.get_state_history()

        assert len(history) == 3
        assert history[0].to_state == TradeState.BREAKEVEN
        assert history[1].to_state == TradeState.PARTIAL
        assert history[2].to_state == TradeState.PARTIAL

    def test_get_state_history_returns_copy(self, sample_position):
        """Test that get_state_history returns a copy, not reference."""
        sample_position.transition_state(TradeState.BREAKEVEN, "Breakeven")

        history1 = sample_position.get_state_history()
        history2 = sample_position.get_state_history()

        # Should be equal but not same object
        assert history1 == history2
        assert history1 is not history2

    def test_has_been_in_state(self, sample_position):
        """Test checking if position has ever been in a specific state."""
        assert sample_position.has_been_in_state(TradeState.OPEN)

        sample_position.transition_state(TradeState.BREAKEVEN, "Breakeven")
        assert sample_position.has_been_in_state(TradeState.BREAKEVEN)
        assert sample_position.has_been_in_state(TradeState.OPEN)

        sample_position.transition_state(TradeState.PARTIAL, "Partial")
        assert sample_position.has_been_in_state(TradeState.PARTIAL)

        # Never been in SCALED_IN
        assert not sample_position.has_been_in_state(TradeState.SCALED_IN)

    def test_get_current_state_duration_no_transitions(self, sample_position):
        """Test state duration when no transitions have occurred."""
        duration = sample_position.get_current_state_duration_seconds()

        # Should equal trade age since no transitions
        assert duration == sample_position.get_trade_age_seconds()

    def test_get_current_state_duration_with_transitions(self, sample_position):
        """Test state duration after transitions."""
        # Create a position with older entry time
        old_position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0870,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow() - timedelta(seconds=100),
            profit=200.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.OPEN,
        )

        # Transition after some time
        import time
        time.sleep(0.1)  # Small delay
        old_position.transition_state(TradeState.BREAKEVEN, "Breakeven")

        duration = old_position.get_current_state_duration_seconds()

        # Should be less than trade age (since transition happened later)
        assert duration < old_position.get_trade_age_seconds()
        assert duration < 2  # Should be very recent


class TestTradeStateTracker:
    """Test suite for TradeStateTracker database functionality."""

    def test_store_transition(self, state_tracker):
        """Test storing a state transition."""
        transition = TradeStateTransition(
            from_state=TradeState.OPEN,
            to_state=TradeState.BREAKEVEN,
            timestamp=datetime.utcnow(),
            reason="Test transition",
            trade_ticket=12345,
        )

        state_tracker.store_transition(transition)

        assert len(state_tracker.get_all_transitions()) == 1

    def test_store_multiple_transitions(self, state_tracker):
        """Test storing multiple transitions."""
        transitions = [
            TradeStateTransition(
                from_state=TradeState.OPEN,
                to_state=TradeState.BREAKEVEN,
                timestamp=datetime.utcnow(),
                reason=f"Transition {i}",
                trade_ticket=12345,
            )
            for i in range(5)
        ]

        for transition in transitions:
            state_tracker.store_transition(transition)

        assert len(state_tracker.get_all_transitions()) == 5

    def test_get_transitions_for_position(self, state_tracker):
        """Test retrieving transitions for a specific position."""
        # Add transitions for different positions
        state_tracker.store_transition(
            TradeStateTransition(
                from_state=TradeState.OPEN,
                to_state=TradeState.BREAKEVEN,
                timestamp=datetime.utcnow(),
                reason="Position 1",
                trade_ticket=12345,
            )
        )

        state_tracker.store_transition(
            TradeStateTransition(
                from_state=TradeState.OPEN,
                to_state=TradeState.PARTIAL,
                timestamp=datetime.utcnow(),
                reason="Position 2",
                trade_ticket=12346,
            )
        )

        state_tracker.store_transition(
            TradeStateTransition(
                from_state=TradeState.BREAKEVEN,
                to_state=TradeState.PARTIAL,
                timestamp=datetime.utcnow(),
                reason="Position 1 again",
                trade_ticket=12345,
            )
        )

        # Get transitions for position 12345
        position_12345_transitions = state_tracker.get_transitions_for_position(12345)
        assert len(position_12345_transitions) == 2

        # Get transitions for position 12346
        position_12346_transitions = state_tracker.get_transitions_for_position(12346)
        assert len(position_12346_transitions) == 1

    def test_get_all_transitions_returns_copy(self, state_tracker):
        """Test that get_all_transitions returns a copy."""
        transition = TradeStateTransition(
            from_state=TradeState.OPEN,
            to_state=TradeState.BREAKEVEN,
            timestamp=datetime.utcnow(),
            reason="Test",
            trade_ticket=12345,
        )

        state_tracker.store_transition(transition)

        all1 = state_tracker.get_all_transitions()
        all2 = state_tracker.get_all_transitions()

        assert all1 == all2
        assert all1 is not all2

    def test_clear_history(self, state_tracker):
        """Test clearing transition history."""
        # Add some transitions
        for i in range(3):
            state_tracker.store_transition(
                TradeStateTransition(
                    from_state=TradeState.OPEN,
                    to_state=TradeState.BREAKEVEN,
                    timestamp=datetime.utcnow(),
                    reason=f"Transition {i}",
                    trade_ticket=12345,
                )
            )

        assert len(state_tracker.get_all_transitions()) == 3

        # Clear history
        state_tracker.clear_history()

        assert len(state_tracker.get_all_transitions()) == 0

    def test_export_to_csv(self, state_tracker):
        """Test exporting transitions to CSV file."""
        # Add some transitions
        transitions = [
            TradeStateTransition(
                from_state=TradeState.OPEN,
                to_state=TradeState.BREAKEVEN,
                timestamp=datetime(2024, 1, 1, 12, 0, 0),
                reason="First transition",
                trade_ticket=12345,
            ),
            TradeStateTransition(
                from_state=TradeState.BREAKEVEN,
                to_state=TradeState.PARTIAL,
                timestamp=datetime(2024, 1, 1, 13, 0, 0),
                reason="Second transition",
                trade_ticket=12345,
            ),
        ]

        for transition in transitions:
            state_tracker.store_transition(transition)

        # Export to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
            temp_filepath = f.name

        try:
            state_tracker.export_to_csv(temp_filepath)

            # Verify file exists and has content
            assert os.path.exists(temp_filepath)

            with open(temp_filepath, 'r') as f:
                content = f.read()

            # Check CSV headers
            assert "trade_ticket" in content
            assert "from_state" in content
            assert "to_state" in content
            assert "timestamp" in content
            assert "reason" in content

            # Check data rows
            assert "12345" in content
            assert "First transition" in content
            assert "Second transition" in content

        finally:
            # Clean up
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)


class TestStateTransitionScenarios:
    """Test realistic state transition scenarios."""

    def test_full_trade_lifecycle(self):
        """Test a complete trade lifecycle from PENDING to CLOSED."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0850,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=0.0,
            swap=0.0,
            commission=0.0,
            state=TradeState.PENDING,
        )

        # Scenario: Order filled
        position.transition_state(TradeState.OPEN, "Order filled by MT5")
        assert position.state == TradeState.OPEN

        # Scenario: Price moves favorably, move to breakeven
        position.current_price = 1.0870
        position.profit = 200.0
        position.transition_state(TradeState.BREAKEVEN, "SL moved to breakeven at 1.5R")
        assert position.state == TradeState.BREAKEVEN

        # Scenario: Take partial profit
        position.transition_state(TradeState.PARTIAL, "Closed 50% at 2R profit")
        assert position.state == TradeState.PARTIAL

        # Scenario: Scale in (add more size)
        position.transition_state(TradeState.SCALED_IN, "Added 50% more size at 3R")
        assert position.state == TradeState.SCALED_IN

        # Scenario: Scale out (reduce size)
        position.transition_state(TradeState.SCALED_OUT, "Closed 25% at 4R")
        assert position.state == TradeState.SCALED_OUT

        # Scenario: Final close
        position.transition_state(TradeState.CLOSED, "Closed remaining position at 5R")
        assert position.state == TradeState.CLOSED

        # Verify complete history
        assert len(position.state_history) == 6
        assert position.has_been_in_state(TradeState.PENDING)
        assert position.has_been_in_state(TradeState.OPEN)
        assert position.has_been_in_state(TradeState.BREAKEVEN)
        assert position.has_been_in_state(TradeState.PARTIAL)
        assert position.has_been_in_state(TradeState.SCALED_IN)
        assert position.has_been_in_state(TradeState.SCALED_OUT)
        assert position.has_been_in_state(TradeState.CLOSED)

    def test_immediate_order_cancellation(self):
        """Test scenario where order is cancelled immediately."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0850,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=0.0,
            swap=0.0,
            commission=0.0,
            state=TradeState.PENDING,
        )

        # Order cancelled before filling
        position.transition_state(TradeState.CLOSED, "Order cancelled by user")

        assert position.state == TradeState.CLOSED
        assert len(position.state_history) == 1
        assert not position.has_been_in_state(TradeState.OPEN)

    def test_multiple_partial_profit_taking(self):
        """Test multiple partial profit taking events."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0870,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=200.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.OPEN,
        )

        # First partial close
        position.transition_state(TradeState.PARTIAL, "Closed 50% at 2R")
        assert position.state == TradeState.PARTIAL

        # Second partial close
        position.transition_state(TradeState.PARTIAL, "Closed 25% at 3R")
        assert position.state == TradeState.PARTIAL

        # Third partial close
        position.transition_state(TradeState.PARTIAL, "Closed remaining at 4R")
        assert position.state == TradeState.PARTIAL

        # Should have 3 transitions to PARTIAL state
        partial_transitions = [
            t for t in position.state_history
            if t.to_state == TradeState.PARTIAL
        ]
        assert len(partial_transitions) == 3

    def test_breakeven_then_multiple_scale_outs(self):
        """Test breakeven followed by multiple scale-outs."""
        position = TradePosition(
            ticket=12345,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0870,
            volume=0.1,
            stop_loss=1.0800,
            take_profit=1.0950,
            entry_time=datetime.utcnow(),
            profit=200.0,
            swap=0.5,
            commission=1.0,
            state=TradeState.OPEN,
        )

        # Move to breakeven
        position.transition_state(TradeState.BREAKEVEN, "SL to breakeven")

        # Multiple scale-outs
        position.transition_state(TradeState.SCALED_OUT, "Closed 25% at 2R")
        position.transition_state(TradeState.SCALED_OUT, "Closed 25% at 3R")
        position.transition_state(TradeState.SCALED_OUT, "Closed 25% at 4R")

        assert position.state == TradeState.SCALED_OUT

        scale_out_transitions = [
            t for t in position.state_history
            if t.to_state == TradeState.SCALED_OUT
        ]
        assert len(scale_out_transitions) == 3
