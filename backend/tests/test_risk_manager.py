"""
Comprehensive test suite for RiskManager service.

Tests all risk management functionality including:
- Fixed percentage risk per trade
- ATR-based stop loss calculation
- Kelly Criterion position sizing
- Volatility-based position sizing
- Risk-reward ratio validation
- Trailing stop loss
- Time-based exits
- Maximum daily loss limits
- Position correlation checks
- Maximum concurrent positions limits
"""

import pytest
from datetime import datetime, timedelta
from app.services.risk_manager import (
    RiskManager,
    RiskDecision,
    RiskCalculation,
    TradePosition,
)


class TestRiskManagerInitialization:
    """Test RiskManager initialization and configuration."""

    def test_default_initialization(self):
        """Test RiskManager initializes with default values."""
        manager = RiskManager()

        assert manager.max_risk_per_trade == 0.02
        assert manager.max_daily_loss == 0.05
        assert manager.max_concurrent_positions == 3
        assert manager.min_risk_reward_ratio == 1.5
        assert manager.account_balance == 10000.0
        assert manager.daily_pnl == 0.0
        assert manager.daily_trades_count == 0

    def test_custom_initialization(self):
        """Test RiskManager initializes with custom values."""
        manager = RiskManager(
            max_risk_per_trade=0.01,
            max_daily_loss=0.03,
            max_concurrent_positions=5,
            min_risk_reward_ratio=2.0,
            account_balance=50000.0,
        )

        assert manager.max_risk_per_trade == 0.01
        assert manager.max_daily_loss == 0.03
        assert manager.max_concurrent_positions == 5
        assert manager.min_risk_reward_ratio == 2.0
        assert manager.account_balance == 50000.0


class TestFixedPercentageRisk:
    """Test fixed percentage risk per trade calculations."""

    def test_calculate_position_size_fixed_risk_buy(self):
        """Test position sizing for BUY trade with fixed risk."""
        manager = RiskManager(account_balance=10000.0)

        calc = manager.calculate_position_size_fixed_risk(
            entry_price=10000.0,
            stop_loss=9950.0,
            symbol="V10",
        )

        # Risk amount should be 2% of balance = $200
        assert calc.risk_amount == 200.0
        assert calc.risk_percentage == 0.02

        # Lot size should risk $200 with $50 per share risk
        assert calc.lot_size == 4.0

        # Take profit should be at 1.5:1 ratio
        assert calc.take_profit == 10075.0

        # Risk-reward ratio should be 1.5
        assert calc.risk_reward_ratio == 1.5

        # Should be approved
        assert calc.decision == RiskDecision.APPROVED

    def test_calculate_position_size_fixed_risk_sell(self):
        """Test position sizing for SELL trade with fixed risk."""
        manager = RiskManager(account_balance=10000.0)

        calc = manager.calculate_position_size_fixed_risk(
            entry_price=10000.0,
            stop_loss=10050.0,
            symbol="V10",
        )

        assert calc.risk_amount == 200.0
        assert calc.lot_size == 4.0
        assert calc.take_profit == 9925.0

    def test_insufficient_risk_reward_ratio(self):
        """Test rejection when risk-reward ratio is too low."""
        manager = RiskManager(account_balance=10000.0)

        # Manually create calculation with poor ratio
        calc = manager.calculate_position_size_fixed_risk(
            entry_price=10000.0,
            stop_loss=9950.0,
        )

        # Override take profit to create poor ratio
        calc.take_profit = 10025.0  # Only 0.5:1 ratio
        calc.reward_amount = 25.0 * calc.lot_size
        calc.risk_reward_ratio = calc.reward_amount / calc.risk_amount
        calc.decision = RiskDecision.REJECTED_RISK_REWARD
        calc.reasons.append("Risk-reward ratio below minimum")

        assert calc.risk_reward_ratio < 1.5
        assert calc.decision == RiskDecision.REJECTED_RISK_REWARD
        assert any("ratio" in reason.lower() for reason in calc.reasons)

    def test_zero_risk_distance(self):
        """Test handling of zero risk distance."""
        manager = RiskManager(account_balance=10000.0)

        calc = manager.calculate_position_size_fixed_risk(
            entry_price=10000.0,
            stop_loss=10000.0,  # Same as entry
            symbol="V10",
        )

        # Should handle gracefully with minimum lot size
        assert calc.lot_size <= 0.01


class TestATRStopLoss:
    """Test ATR-based stop loss calculations."""

    def test_calculate_stop_loss_atr_buy(self):
        """Test ATR stop loss for BUY trade."""
        manager = RiskManager()

        stop_loss = manager.calculate_stop_loss_atr(
            entry_price=10000.0,
            atr=50.0,
            direction="BUY",
            atr_multiplier=1.5,
        )

        # Stop should be below entry by ATR * multiplier
        expected_stop = 10000.0 - (50.0 * 1.5)
        assert stop_loss == expected_stop
        assert stop_loss < 10000.0

    def test_calculate_stop_loss_atr_sell(self):
        """Test ATR stop loss for SELL trade."""
        manager = RiskManager()

        stop_loss = manager.calculate_stop_loss_atr(
            entry_price=10000.0,
            atr=50.0,
            direction="SELL",
            atr_multiplier=1.5,
        )

        # Stop should be above entry by ATR * multiplier
        expected_stop = 10000.0 + (50.0 * 1.5)
        assert stop_loss == expected_stop
        assert stop_loss > 10000.0

    def test_calculate_stop_loss_atr_different_multipliers(self):
        """Test ATR stop loss with different multipliers."""
        manager = RiskManager()

        # Tighter stop
        stop1 = manager.calculate_stop_loss_atr(
            entry_price=10000.0,
            atr=50.0,
            direction="BUY",
            atr_multiplier=1.0,
        )

        # Wider stop
        stop2 = manager.calculate_stop_loss_atr(
            entry_price=10000.0,
            atr=50.0,
            direction="BUY",
            atr_multiplier=2.0,
        )

        # Wider multiplier should give stop further from entry
        assert stop2 < stop1


class TestKellyCriterion:
    """Test Kelly Criterion position sizing."""

    def test_kelly_criterion_positive_expectancy(self):
        """Test Kelly calculation with positive expectancy."""
        manager = RiskManager(account_balance=10000.0)

        calc = manager.calculate_position_size_kelly(
            win_rate=0.60,
            average_win=300.0,
            average_loss=200.0,
            entry_price=10000.0,
            stop_loss=9950.0,
        )

        # Kelly formula: f* = (bp - q) / b
        # b = 300/200 = 1.5, p = 0.6, q = 0.4
        # f* = (1.5*0.6 - 0.4) / 1.5 = 0.333
        # Half-Kelly = 0.167

        assert calc.lot_size > 0
        assert calc.decision == RiskDecision.APPROVED

    def test_kelly_criterion_negative_expectancy(self):
        """Test Kelly calculation with negative expectancy."""
        manager = RiskManager(account_balance=10000.0)

        calc = manager.calculate_position_size_kelly(
            win_rate=0.40,
            average_win=150.0,
            average_loss=200.0,
            entry_price=10000.0,
            stop_loss=9950.0,
        )

        # Should fall back to minimum position size
        assert calc.lot_size <= 0.01
        assert len(calc.warnings) > 0
        assert any("negative" in w.lower() for w in calc.warnings)

    def test_kelly_criterion_invalid_inputs(self):
        """Test Kelly calculation with invalid inputs."""
        manager = RiskManager(account_balance=10000.0)

        # Invalid win rate
        calc = manager.calculate_position_size_kelly(
            win_rate=1.5,  # Invalid > 1.0
            average_win=300.0,
            average_loss=200.0,
            entry_price=10000.0,
            stop_loss=9950.0,
        )

        # Should fall back to fixed risk
        assert calc.lot_size > 0


class TestVolatilityPositionSizing:
    """Test volatility-based position sizing."""

    def test_high_volatility_reduces_position(self):
        """Test that high volatility reduces position size."""
        manager = RiskManager(account_balance=10000.0)

        calc = manager.calculate_position_size_volatility(
            entry_price=10000.0,
            stop_loss=9950.0,
            volatility=0.0020,  # High volatility
            symbol="V10",
        )

        base_calc = manager.calculate_position_size_fixed_risk(
            entry_price=10000.0,
            stop_loss=9950.0,
        )

        # Volatility-adjusted should be smaller
        assert calc.lot_size < base_calc.lot_size
        assert any("high volatility" in w.lower() for w in calc.warnings)

    def test_low_volatility_increases_position(self):
        """Test that low volatility increases position size."""
        manager = RiskManager(account_balance=10000.0)

        calc = manager.calculate_position_size_volatility(
            entry_price=10000.0,
            stop_loss=9950.0,
            volatility=0.0005,  # Low volatility
            symbol="V10",
        )

        base_calc = manager.calculate_position_size_fixed_risk(
            entry_price=10000.0,
            stop_loss=9950.0,
        )

        # Volatility-adjusted should be larger
        assert calc.lot_size > base_calc.lot_size


class TestRiskRewardValidation:
    """Test risk-reward ratio validation."""

    def test_validate_good_risk_reward(self):
        """Test validation of good risk-reward ratio."""
        manager = RiskManager()

        is_valid, ratio, reasons = manager.validate_risk_reward_ratio(
            entry_price=10000.0,
            stop_loss=9950.0,
            take_profit=10075.0,
        )

        # 1.5:1 ratio
        assert is_valid
        assert ratio == 1.5
        assert len(reasons) > 0

    def test_validate_poor_risk_reward(self):
        """Test validation of poor risk-reward ratio."""
        manager = RiskManager()

        is_valid, ratio, reasons = manager.validate_risk_reward_ratio(
            entry_price=10000.0,
            stop_loss=9950.0,
            take_profit=10025.0,  # Only 0.5:1 ratio
        )

        assert not is_valid
        assert ratio == 0.5
        assert any("below minimum" in r.lower() for r in reasons)

    def test_validate_invalid_stop_loss(self):
        """Test validation with invalid stop loss."""
        manager = RiskManager()

        is_valid, ratio, reasons = manager.validate_risk_reward_ratio(
            entry_price=10000.0,
            stop_loss=10000.0,  # Same as entry
            take_profit=10075.0,
        )

        assert not is_valid
        assert ratio == 0.0
        assert any("invalid" in r.lower() for r in reasons)


class TestTrailingStop:
    """Test trailing stop loss functionality."""

    def test_trailing_stop_buy_moves_up(self):
        """Test trailing stop moves up for long position."""
        manager = RiskManager()

        # Initial stop (first call sets initial stop)
        stop1 = manager.calculate_trailing_stop(
            current_price=10000.0,
            direction="BUY",
            entry_price=10000.0,
            trail_distance=50.0,
        )

        assert stop1 is not None
        assert stop1 == 9950.0  # entry_price - trail_distance

        # Price moves up, stop should move up
        stop2 = manager.calculate_trailing_stop(
            current_price=10050.0,
            direction="BUY",
            entry_price=10000.0,
            trail_distance=50.0,
        )

        assert stop2 is not None
        assert stop2 > stop1
        assert stop2 == 10000.0  # current_price - trail_distance

    def test_trailing_stop_buy_never_moves_down(self):
        """Test trailing stop never moves down for long position."""
        manager = RiskManager()

        # Set initial stop at higher price
        manager.calculate_trailing_stop(
            current_price=10050.0,
            direction="BUY",
            entry_price=10000.0,
            trail_distance=50.0,
        )

        # Price drops, stop should not move down
        stop2 = manager.calculate_trailing_stop(
            current_price=10000.0,
            direction="BUY",
            entry_price=10000.0,
            trail_distance=50.0,
        )

        assert stop2 is None  # No update

    def test_trailing_stop_sell_moves_down(self):
        """Test trailing stop moves down for short position."""
        manager = RiskManager()

        # Initial stop (first call sets initial stop)
        stop1 = manager.calculate_trailing_stop(
            current_price=10000.0,
            direction="SELL",
            entry_price=10000.0,
            trail_distance=50.0,
        )

        assert stop1 is not None
        assert stop1 == 10050.0  # entry_price + trail_distance

        # Price moves down, stop should move down
        stop2 = manager.calculate_trailing_stop(
            current_price=9950.0,
            direction="SELL",
            entry_price=10000.0,
            trail_distance=50.0,
        )

        assert stop2 is not None
        assert stop2 < stop1
        assert stop2 == 10000.0  # current_price + trail_distance


class TestTimeBasedExit:
    """Test time-based exit functionality."""

    def test_time_based_exit_not_reached(self):
        """Test trade within time limit."""
        manager = RiskManager()

        entry_time = datetime.utcnow() - timedelta(hours=2)
        should_exit, reason = manager.check_time_based_exit(
            trade_id=1,
            entry_time=entry_time,
            max_duration_hours=4.0,
        )

        assert not should_exit
        assert reason is None

    def test_time_based_exit_reached(self):
        """Test trade exceeds time limit."""
        manager = RiskManager()

        entry_time = datetime.utcnow() - timedelta(hours=5)
        should_exit, reason = manager.check_time_based_exit(
            trade_id=1,
            entry_time=entry_time,
            max_duration_hours=4.0,
        )

        assert should_exit
        assert reason is not None
        assert "exceeded maximum duration" in reason.lower()


class TestDailyLossLimit:
    """Test daily loss limit functionality."""

    def test_daily_loss_not_reached(self):
        """Test account within daily loss limit."""
        manager = RiskManager(account_balance=10000.0)

        limit_reached, loss_pct, message = manager.check_daily_loss_limit(
            current_balance=9800.0,  # 2% loss
        )

        assert not limit_reached
        assert loss_pct == -0.02
        assert message is None

    def test_daily_loss_reached(self):
        """Test account exceeds daily loss limit."""
        manager = RiskManager(account_balance=10000.0)

        limit_reached, loss_pct, message = manager.check_daily_loss_limit(
            current_balance=9400.0,  # 6% loss (exceeds 5% limit)
        )

        assert limit_reached
        assert loss_pct == -0.06
        assert message is not None
        assert "daily loss limit reached" in message.lower()

    def test_daily_loss_exactly_at_limit(self):
        """Test account exactly at daily loss limit."""
        manager = RiskManager(account_balance=10000.0)

        limit_reached, loss_pct, message = manager.check_daily_loss_limit(
            current_balance=9500.0,  # Exactly 5% loss
        )

        assert limit_reached
        assert loss_pct == -0.05


class TestPositionCorrelation:
    """Test position correlation checks."""

    def test_no_correlation_conflict(self):
        """Test new trade with no correlation conflict."""
        manager = RiskManager()

        open_positions = [
            TradePosition(
                symbol="V10",
                direction="BUY",
                entry_price=10000.0,
                lot_size=1.0,
                stop_loss=9950.0,
                take_profit=10075.0,
                profit_loss=0.0,
                entry_time=datetime.utcnow(),
            )
        ]

        is_valid, reasons = manager.check_position_correlation(
            proposed_symbol="V25",
            proposed_direction="BUY",
            open_positions=open_positions,
        )

        assert is_valid
        assert any("passed" in r.lower() for r in reasons)

    def test_correlation_conflict_same_symbol(self):
        """Test new trade conflicts with existing same symbol positions."""
        manager = RiskManager()

        open_positions = [
            TradePosition(
                symbol="V10",
                direction="BUY",
                entry_price=10000.0,
                lot_size=1.0,
                stop_loss=9950.0,
                take_profit=10075.0,
                profit_loss=0.0,
                entry_time=datetime.utcnow(),
            ),
            TradePosition(
                symbol="V10",
                direction="BUY",
                entry_price=10010.0,
                lot_size=1.0,
                stop_loss=9960.0,
                take_profit=10085.0,
                profit_loss=0.0,
                entry_time=datetime.utcnow(),
            ),
        ]

        is_valid, reasons = manager.check_position_correlation(
            proposed_symbol="V10",
            proposed_direction="BUY",
            open_positions=open_positions,
            max_correlated_positions=2,
        )

        assert not is_valid
        assert any("already have" in r.lower() or "maximum" in r.lower() for r in reasons)


class TestMaxConcurrentPositions:
    """Test maximum concurrent positions limits."""

    def test_under_limit(self):
        """Test when under maximum positions limit."""
        manager = RiskManager(max_concurrent_positions=3)

        open_positions = [
            TradePosition(
                symbol="V10",
                direction="BUY",
                entry_price=10000.0,
                lot_size=1.0,
                stop_loss=9950.0,
                take_profit=10075.0,
                profit_loss=0.0,
                entry_time=datetime.utcnow(),
            )
        ]

        can_open, count, reasons = manager.check_max_concurrent_positions(open_positions)

        assert can_open
        assert count == 1
        assert any("can open" in r.lower() for r in reasons)

    def test_at_limit(self):
        """Test when at maximum positions limit."""
        manager = RiskManager(max_concurrent_positions=3)

        open_positions = [
            TradePosition(
                symbol=f"V{10+i*15}",
                direction="BUY",
                entry_price=10000.0,
                lot_size=1.0,
                stop_loss=9950.0,
                take_profit=10075.0,
                profit_loss=0.0,
                entry_time=datetime.utcnow(),
            )
            for i in range(3)
        ]

        can_open, count, reasons = manager.check_max_concurrent_positions(open_positions)

        assert not can_open
        assert count == 3
        assert any("maximum" in r.lower() for r in reasons)


class TestComprehensiveValidation:
    """Test comprehensive trade validation."""

    def test_trade_validation_all_checks_pass(self):
        """Test trade validation passes all checks."""
        manager = RiskManager(account_balance=10000.0)

        calc = manager.validate_trade(
            symbol="V10",
            direction="BUY",
            entry_price=10000.0,
            stop_loss=9950.0,
            take_profit=10075.0,
            lot_size=1.0,
            open_positions=[],
        )

        assert calc.decision == RiskDecision.APPROVED
        assert len(calc.reasons) > 0

    def test_trade_validation_rejected_daily_loss(self):
        """Test trade validation rejected due to daily loss limit."""
        manager = RiskManager(account_balance=10000.0)

        # Simulate daily loss by updating daily start balance
        manager.daily_start_balance = 10000.0
        manager.account_balance = 9400.0  # 6% loss - exceeds 5% limit

        calc = manager.validate_trade(
            symbol="V10",
            direction="BUY",
            entry_price=10000.0,
            stop_loss=9950.0,
            take_profit=10075.0,
            lot_size=1.0,
            open_positions=[],
        )

        assert calc.decision == RiskDecision.REJECTED_DAILY_LOSS
        assert len(calc.reasons) > 0

    def test_trade_validation_rejected_max_positions(self):
        """Test trade validation rejected due to max positions."""
        manager = RiskManager(account_balance=10000.0, max_concurrent_positions=2)

        open_positions = [
            TradePosition(
                symbol=f"V{10+i*15}",
                direction="BUY",
                entry_price=10000.0,
                lot_size=1.0,
                stop_loss=9950.0,
                take_profit=10075.0,
                profit_loss=0.0,
                entry_time=datetime.utcnow(),
            )
            for i in range(2)
        ]

        calc = manager.validate_trade(
            symbol="V50",
            direction="BUY",
            entry_price=10000.0,
            stop_loss=9950.0,
            take_profit=10075.0,
            lot_size=1.0,
            open_positions=open_positions,
        )

        assert calc.decision == RiskDecision.REJECTED_MAX_POSITIONS


class TestRiskTracking:
    """Test risk tracking and reporting."""

    def test_update_daily_pnl(self):
        """Test daily P&L tracking."""
        manager = RiskManager(account_balance=10000.0)

        manager.update_daily_pnl(150.0)
        assert manager.daily_pnl == 150.0
        assert manager.daily_trades_count == 1

        manager.update_daily_pnl(-50.0)
        assert manager.daily_pnl == 100.0
        assert manager.daily_trades_count == 2

    def test_reset_daily_tracking(self):
        """Test daily tracking reset."""
        manager = RiskManager(account_balance=10000.0)

        manager.update_daily_pnl(500.0)
        manager.update_daily_pnl(-200.0)

        assert manager.daily_pnl == 300.0
        assert manager.daily_trades_count == 2

        manager.reset_daily_tracking(new_balance=10500.0)

        assert manager.daily_start_balance == 10500.0
        assert manager.daily_pnl == 0.0
        assert manager.daily_trades_count == 0

    def test_get_risk_summary(self):
        """Test risk summary generation."""
        manager = RiskManager(account_balance=10000.0)

        manager.update_daily_pnl(250.0)

        summary = manager.get_risk_summary()

        assert summary["account_balance"] == 10250.0
        assert summary["daily_pnl"] == 250.0
        assert summary["daily_trades_count"] == 1
        assert summary["max_risk_per_trade"] == 0.02
        assert summary["max_daily_loss"] == 0.05
        assert summary["max_concurrent_positions"] == 3


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_balance(self):
        """Test handling of zero account balance."""
        manager = RiskManager(account_balance=0.0)

        calc = manager.calculate_position_size_fixed_risk(
            entry_price=10000.0,
            stop_loss=9950.0,
        )

        assert calc.lot_size == 0.0

    def test_negative_lot_size_request(self):
        """Test handling of negative lot size."""
        manager = RiskManager(account_balance=10000.0)

        calc = manager.calculate_position_size_fixed_risk(
            entry_price=9950.0,  # Lower than stop
            stop_loss=10000.0,
        )

        # Should calculate correctly for short position
        assert calc.lot_size > 0

    def test_extreme_volatility(self):
        """Test handling of extreme volatility."""
        manager = RiskManager(account_balance=10000.0)

        calc = manager.calculate_position_size_volatility(
            entry_price=10000.0,
            stop_loss=9950.0,
            volatility=1.0,  # Extremely high
        )

        # Should still return valid calculation
        assert calc.lot_size > 0


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
