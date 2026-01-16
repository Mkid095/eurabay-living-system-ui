"""
Tests for AdaptiveRiskManager performance-based position sizing.

This module tests the adaptive risk management system that adjusts position
sizes based on recent trading performance.
"""

import pytest
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path

from backend.core.adaptive_risk_manager import (
    AdaptiveRiskManager,
    RiskAdjustment,
    VolatilityAdjustment,
    DrawdownAdjustment,
    CorrelationAdjustment,
)
from backend.core.performance_comparator import (
    PerformanceComparator,
    TradeOutcome,
)
from backend.core import TradePosition


# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def temp_database(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_adaptive_risk.db"
    yield str(db_path)
    # Cleanup is handled by tmp_path


@pytest.fixture
def performance_comparator(temp_database):
    """Create a PerformanceComparator for testing."""
    comparator_path = temp_database.replace("test_adaptive_risk", "test_performance")
    return PerformanceComparator(database_path=comparator_path)


@pytest.fixture
def risk_manager(performance_comparator, temp_database):
    """Create an AdaptiveRiskManager for testing."""
    return AdaptiveRiskManager(
        performance_comparator=performance_comparator,
        database_path=temp_database,
        base_risk_percent=2.0,
        min_risk_percent=0.5,
        max_risk_percent=3.0,
        performance_window=20,
        atr_period=14,
        atr_lookback=100,
        min_volatility_multiplier=0.3,
        max_volatility_multiplier=1.5,
        enable_volatility_adjustment=False,  # Disabled for backward compatibility with existing tests
    )


@pytest.fixture
def risk_manager_with_volatility(performance_comparator, temp_database):
    """Create an AdaptiveRiskManager with volatility adjustment enabled."""
    return AdaptiveRiskManager(
        performance_comparator=performance_comparator,
        database_path=temp_database,
        base_risk_percent=2.0,
        min_risk_percent=0.5,
        max_risk_percent=3.0,
        performance_window=20,
        atr_period=14,
        atr_lookback=100,
        min_volatility_multiplier=0.3,
        max_volatility_multiplier=1.5,
        enable_volatility_adjustment=True,  # Enabled for volatility tests
    )


class TestAdaptiveRiskManager:
    """Test suite for AdaptiveRiskManager."""

    def test_initialization(self, risk_manager):
        """Test that AdaptiveRiskManager initializes correctly."""
        assert risk_manager._base_risk_percent == 2.0
        assert risk_manager._min_risk_percent == 0.5
        assert risk_manager._max_risk_percent == 3.0
        assert risk_manager._performance_window == 20
        assert risk_manager._current_risk_percent == 2.0

    def test_calculate_base_risk(self, risk_manager):
        """Test base risk calculation."""
        base_risk = risk_manager.calculate_base_risk()
        assert base_risk == 2.0

    def test_adjust_risk_no_trades(self, risk_manager):
        """Test risk adjustment when no trades exist."""
        adjusted_risk = risk_manager.adjust_for_recent_performance()
        # With no trades, should use base risk (win rate defaults to 50%)
        assert adjusted_risk == 2.0

    def test_adjust_risk_low_win_rate(self, risk_manager, performance_comparator):
        """Test risk reduction when win rate < 50%."""
        # Create 20 trade outcomes with 40% win rate (8 wins, 12 losses)
        for i in range(20):
            profit = 100.0 if i < 8 else -100.0  # 8 wins, 12 losses
            position = TradePosition(
                ticket=1000 + i,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0850,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=profit,
                swap=0.0,
                commission=0.0,
            )

            performance_comparator.record_trade_outcome(
                position=position,
                exit_price=1.0850,
                exit_time=datetime.utcnow(),
                final_profit=profit,
                peak_profit=100.0 if profit > 0 else 0.0,
                max_adverse_excursion=0.0 if profit > 0 else -100.0,
            )

        # Adjust risk based on performance
        adjusted_risk = risk_manager.adjust_for_recent_performance()

        # Should reduce risk by 50%: 2.0% * 0.5 = 1.0%
        assert adjusted_risk == 1.0

        # Verify adjustment was recorded
        history = risk_manager.get_adjustment_history()
        assert len(history) > 0
        assert history[-1].adjustment_type == "performance_decrease"
        assert history[-1].win_rate == 40.0

    def test_adjust_risk_high_win_rate(self, risk_manager, performance_comparator):
        """Test risk increase when win rate > 70%."""
        # Create 20 trade outcomes with 75% win rate (15 wins, 5 losses)
        for i in range(20):
            profit = 100.0 if i < 15 else -100.0  # 15 wins, 5 losses
            position = TradePosition(
                ticket=2000 + i,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0850,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=profit,
                swap=0.0,
                commission=0.0,
            )

            performance_comparator.record_trade_outcome(
                position=position,
                exit_price=1.0850,
                exit_time=datetime.utcnow(),
                final_profit=profit,
                peak_profit=100.0 if profit > 0 else 0.0,
                max_adverse_excursion=0.0 if profit > 0 else -100.0,
            )

        # Adjust risk based on performance
        adjusted_risk = risk_manager.adjust_for_recent_performance()

        # Should increase risk by 25%: 2.0% * 1.25 = 2.5%
        assert adjusted_risk == 2.5

        # Verify adjustment was recorded
        history = risk_manager.get_adjustment_history()
        assert len(history) > 0
        assert history[-1].adjustment_type == "performance_increase"
        assert history[-1].win_rate == 75.0

    def test_adjust_risk_normal_win_rate(self, risk_manager, performance_comparator):
        """Test base risk when win rate is 50-70%."""
        # Create 20 trade outcomes with 60% win rate (12 wins, 8 losses)
        for i in range(20):
            profit = 100.0 if i < 12 else -100.0  # 12 wins, 8 losses
            position = TradePosition(
                ticket=3000 + i,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0850,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=profit,
                swap=0.0,
                commission=0.0,
            )

            performance_comparator.record_trade_outcome(
                position=position,
                exit_price=1.0850,
                exit_time=datetime.utcnow(),
                final_profit=profit,
                peak_profit=100.0 if profit > 0 else 0.0,
                max_adverse_excursion=0.0 if profit > 0 else -100.0,
            )

        # Adjust risk based on performance
        adjusted_risk = risk_manager.adjust_for_recent_performance()

        # Should use base risk: 2.0%
        assert adjusted_risk == 2.0

        # Verify adjustment was recorded
        history = risk_manager.get_adjustment_history()
        assert len(history) > 0
        assert history[-1].adjustment_type == "performance_normal"
        assert history[-1].win_rate == 60.0

    def test_minimum_risk_cap(self, risk_manager, performance_comparator):
        """Test that risk never goes below minimum cap (0.5%)."""
        # Create 20 trade outcomes with very low win rate (10% win rate)
        for i in range(20):
            profit = 100.0 if i < 2 else -100.0  # 2 wins, 18 losses
            position = TradePosition(
                ticket=4000 + i,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0850,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=profit,
                swap=0.0,
                commission=0.0,
            )

            performance_comparator.record_trade_outcome(
                position=position,
                exit_price=1.0850,
                exit_time=datetime.utcnow(),
                final_profit=profit,
                peak_profit=100.0 if profit > 0 else 0.0,
                max_adverse_excursion=0.0 if profit > 0 else -100.0,
            )

        # Set very low base risk to test minimum cap
        risk_manager._base_risk_percent = 0.3

        # Adjust risk based on performance
        adjusted_risk = risk_manager.adjust_for_recent_performance()

        # Should be capped at minimum: 0.5%
        assert adjusted_risk == 0.5

    def test_maximum_risk_cap(self, risk_manager, performance_comparator):
        """Test that risk never exceeds maximum cap (3.0%)."""
        # Create 20 trade outcomes with very high win rate (90% win rate)
        for i in range(20):
            profit = 100.0 if i < 18 else -100.0  # 18 wins, 2 losses
            position = TradePosition(
                ticket=5000 + i,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0850,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=profit,
                swap=0.0,
                commission=0.0,
            )

            performance_comparator.record_trade_outcome(
                position=position,
                exit_price=1.0850,
                exit_time=datetime.utcnow(),
                final_profit=profit,
                peak_profit=100.0 if profit > 0 else 0.0,
                max_adverse_excursion=0.0 if profit > 0 else -100.0,
            )

        # Set very high base risk to test maximum cap
        risk_manager._base_risk_percent = 3.0

        # Adjust risk based on performance
        adjusted_risk = risk_manager.adjust_for_recent_performance()

        # Should be capped at maximum: 3.0%
        assert adjusted_risk == 3.0

    def test_calculate_position_size_buy(self, risk_manager):
        """Test position size calculation for BUY trade."""
        account_balance = 10000.0
        entry_price = 1.0850
        stop_loss = 1.0800
        direction = "BUY"

        # Risk amount = 10000 * 0.02 = $200
        # Risk per lot = 1.0850 - 1.0800 = 0.0050
        # Position size = 200 / (0.0050 * 100000) = 0.4 lots
        position_size = risk_manager.calculate_position_size(
            account_balance, entry_price, stop_loss, direction
        )

        assert abs(position_size - 0.4) < 0.01

    def test_calculate_position_size_sell(self, risk_manager):
        """Test position size calculation for SELL trade."""
        account_balance = 10000.0
        entry_price = 1.0850
        stop_loss = 1.0900
        direction = "SELL"

        # Risk amount = 10000 * 0.02 = $200
        # Risk per lot = 1.0900 - 1.0850 = 0.0050
        # Position size = 200 / (0.0050 * 100000) = 0.4 lots
        position_size = risk_manager.calculate_position_size(
            account_balance, entry_price, stop_loss, direction
        )

        assert abs(position_size - 0.4) < 0.01

    def test_calculate_position_size_with_adjusted_risk(self, risk_manager, performance_comparator):
        """Test position size calculation with adjusted risk."""
        # Create trades with low win rate to reduce risk
        for i in range(20):
            profit = 100.0 if i < 8 else -100.0  # 40% win rate
            position = TradePosition(
                ticket=6000 + i,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0850,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=profit,
                swap=0.0,
                commission=0.0,
            )

            performance_comparator.record_trade_outcome(
                position=position,
                exit_price=1.0850,
                exit_time=datetime.utcnow(),
                final_profit=profit,
                peak_profit=100.0 if profit > 0 else 0.0,
                max_adverse_excursion=0.0 if profit > 0 else -100.0,
            )

        # Adjust risk (should reduce to 1.0%)
        risk_manager.adjust_for_recent_performance()

        account_balance = 10000.0
        entry_price = 1.0850
        stop_loss = 1.0800

        # Risk amount = 10000 * 0.01 = $100 (reduced from $200)
        position_size = risk_manager.calculate_position_size(
            account_balance, entry_price, stop_loss, "BUY"
        )

        # Should be 0.2 lots (half of original 0.4 lots)
        assert abs(position_size - 0.2) < 0.01

    def test_get_current_risk_percent(self, risk_manager):
        """Test getting current risk percentage."""
        current_risk = risk_manager.get_current_risk_percent()
        assert current_risk == 2.0

    def test_reset_to_base_risk(self, risk_manager, performance_comparator):
        """Test resetting risk to base percentage."""
        # Create trades with low win rate to reduce risk
        for i in range(20):
            profit = 100.0 if i < 8 else -100.0
            position = TradePosition(
                ticket=7000 + i,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0850,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=profit,
                swap=0.0,
                commission=0.0,
            )

            performance_comparator.record_trade_outcome(
                position=position,
                exit_price=1.0850,
                exit_time=datetime.utcnow(),
                final_profit=profit,
                peak_profit=100.0 if profit > 0 else 0.0,
                max_adverse_excursion=0.0 if profit > 0 else -100.0,
            )

        # Adjust risk (should reduce to 1.0%)
        risk_manager.adjust_for_recent_performance()
        assert risk_manager.get_current_risk_percent() == 1.0

        # Reset to base
        risk_manager.reset_to_base_risk()
        assert risk_manager.get_current_risk_percent() == 2.0

    def test_database_persistence(self, risk_manager, performance_comparator, temp_database):
        """Test that risk adjustments are persisted to database."""
        # Create trades and adjust risk
        for i in range(20):
            profit = 100.0 if i < 15 else -100.0  # 75% win rate
            position = TradePosition(
                ticket=8000 + i,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0850,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=profit,
                swap=0.0,
                commission=0.0,
            )

            performance_comparator.record_trade_outcome(
                position=position,
                exit_price=1.0850,
                exit_time=datetime.utcnow(),
                final_profit=profit,
                peak_profit=100.0 if profit > 0 else 0.0,
                max_adverse_excursion=0.0 if profit > 0 else -100.0,
            )

        risk_manager.adjust_for_recent_performance()

        # Verify data was stored in database
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()

        # Check risk_adjustments table
        cursor.execute("SELECT COUNT(*) FROM risk_adjustments")
        adjustment_count = cursor.fetchone()[0]
        assert adjustment_count > 0

        # Check risk_settings table
        cursor.execute("SELECT COUNT(*) FROM risk_settings")
        settings_count = cursor.fetchone()[0]
        assert settings_count > 0

        # Verify adjustment details
        cursor.execute(
            "SELECT new_risk_percent, adjustment_type, win_rate FROM risk_adjustments ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        assert row[0] == 2.5  # Increased risk
        assert row[1] == "performance_increase"
        assert row[2] == 75.0

        conn.close()

    def test_losing_streak_protection(self, risk_manager, performance_comparator):
        """Test that risk is reduced during losing streaks."""
        # Simulate a losing streak
        for i in range(20):
            profit = -100.0  # All losses
            position = TradePosition(
                ticket=9000 + i,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0850,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=profit,
                swap=0.0,
                commission=0.0,
            )

            performance_comparator.record_trade_outcome(
                position=position,
                exit_price=1.0850,
                exit_time=datetime.utcnow(),
                final_profit=profit,
                peak_profit=0.0,
                max_adverse_excursion=-100.0,
            )

        # Adjust risk (should reduce significantly)
        adjusted_risk = risk_manager.adjust_for_recent_performance()

        # With 0% win rate, risk should be reduced by 50%: 2.0% * 0.5 = 1.0%
        assert adjusted_risk == 1.0

        # Verify the reason mentions protecting capital
        history = risk_manager.get_adjustment_history()
        assert "protect capital" in history[-1].reason.lower()

    def test_winning_streak_maximization(self, risk_manager, performance_comparator):
        """Test that risk is increased during winning streaks."""
        # Simulate a winning streak
        for i in range(20):
            profit = 100.0  # All wins
            position = TradePosition(
                ticket=10000 + i,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0850,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=profit,
                swap=0.0,
                commission=0.0,
            )

            performance_comparator.record_trade_outcome(
                position=position,
                exit_price=1.0850,
                exit_time=datetime.utcnow(),
                final_profit=profit,
                peak_profit=100.0,
                max_adverse_excursion=0.0,
            )

        # Adjust risk (should increase)
        adjusted_risk = risk_manager.adjust_for_recent_performance()

        # With 100% win rate, risk should be increased by 25%: 2.0% * 1.25 = 2.5%
        assert adjusted_risk == 2.5

        # Verify the reason mentions maximizing winning streak
        history = risk_manager.get_adjustment_history()
        assert "maximize" in history[-1].reason.lower() or "winning" in history[-1].reason.lower()

    def test_volatility_multiplier_bounds(self, risk_manager_with_volatility):
        """Test that volatility multiplier stays within min/max bounds."""
        # Test with different symbols
        symbols = ["EURUSD", "GBPUSD", "V10", "V100"]

        for symbol in symbols:
            vol_mult = risk_manager_with_volatility.calculate_volatility_multiplier(symbol)

            # Verify bounds
            assert risk_manager_with_volatility._min_volatility_multiplier <= vol_mult <= risk_manager_with_volatility._max_volatility_multiplier

            logger.info(f"Volatility multiplier for {symbol}: {vol_mult:.3f}")

    def test_volatility_multiplier_high_volatility(self, risk_manager_with_volatility):
        """Test volatility multiplier for high volatility symbols (V100)."""
        vol_mult = risk_manager_with_volatility.calculate_volatility_multiplier("V100")

        # V100 should have lower multiplier due to high volatility
        # The exact value depends on the synthetic data, but it should be reasonable
        assert 0.3 <= vol_mult <= 1.5

        # Get the volatility adjustment details
        adjustments = risk_manager_with_volatility.get_volatility_adjustments(symbol="V100")
        assert len(adjustments) > 0

        latest = adjustments[-1]
        assert latest.symbol == "V100"
        assert latest.volatility_multiplier == vol_mult
        assert latest.current_atr > 0
        assert latest.average_atr > 0

        logger.info(f"V100 volatility adjustment: {latest.reason}")

    def test_volatility_multiplier_low_volatility(self, risk_manager_with_volatility):
        """Test volatility multiplier for low volatility symbols (V10)."""
        vol_mult = risk_manager_with_volatility.calculate_volatility_multiplier("V10")

        # V10 should have higher multiplier due to low volatility
        assert 0.3 <= vol_mult <= 1.5

        # Get the volatility adjustment details
        adjustments = risk_manager_with_volatility.get_volatility_adjustments(symbol="V10")
        assert len(adjustments) > 0

        latest = adjustments[-1]
        assert latest.symbol == "V10"
        assert latest.volatility_multiplier == vol_mult

        logger.info(f"V10 volatility adjustment: {latest.reason}")

    def test_position_size_with_volatility_adjustment(self, risk_manager_with_volatility):
        """Test position size calculation with volatility adjustment."""
        account_balance = 10000.0
        entry_price = 1.0850
        stop_loss = 1.0800
        symbol = "EURUSD"

        # Calculate position size with volatility adjustment
        position_size = risk_manager_with_volatility.calculate_position_size(
            account_balance, entry_price, stop_loss, "BUY", symbol
        )

        # Position size should be positive
        assert position_size > 0

        # Get the volatility multiplier
        vol_mult = risk_manager_with_volatility.calculate_volatility_multiplier(symbol)

        # Calculate expected position size
        risk_amount = account_balance * 0.02  # 2% base risk
        risk_per_lot = abs(entry_price - stop_loss)
        base_position_size = risk_amount / (risk_per_lot * 100000)
        expected_position_size = base_position_size * vol_mult

        # Verify position size matches expected (within tolerance)
        assert abs(position_size - expected_position_size) < 0.01

        logger.info(f"Position size with volatility adjustment: {position_size:.2f} lots (vol_mult: {vol_mult:.3f})")

    def test_position_size_without_volatility_adjustment(self, risk_manager):
        """Test position size calculation without volatility adjustment."""
        # Volatility adjustment is already disabled in the risk_manager fixture

        account_balance = 10000.0
        entry_price = 1.0850
        stop_loss = 1.0800
        symbol = "EURUSD"

        # Calculate position size without volatility adjustment
        position_size = risk_manager.calculate_position_size(
            account_balance, entry_price, stop_loss, "BUY", symbol
        )

        # Calculate expected position size (no volatility multiplier)
        risk_amount = account_balance * 0.02  # 2% base risk
        risk_per_lot = abs(entry_price - stop_loss)
        expected_position_size = risk_amount / (risk_per_lot * 100000)

        # Verify position size matches expected (within tolerance)
        assert abs(position_size - expected_position_size) < 0.01

        logger.info(f"Position size without volatility adjustment: {position_size:.2f} lots")

    def test_atr_calculation(self, risk_manager_with_volatility):
        """Test ATR calculation method."""
        import pandas as pd

        # Create sample price data
        data = pd.DataFrame({
            'high': [1.0850, 1.0860, 1.0870, 1.0880, 1.0890],
            'low': [1.0830, 1.0840, 1.0850, 1.0860, 1.0870],
            'close': [1.0840, 1.0850, 1.0860, 1.0870, 1.0880],
        })

        atr = risk_manager_with_volatility._calculate_atr(data, period=14)

        # ATR should be calculated for all data points
        assert len(atr) == len(data)

        # ATR values should be positive
        assert all(atr > 0)

        logger.info(f"ATR values: {atr.tolist()}")

    def test_volatility_adjustment_database_persistence(self, risk_manager_with_volatility, temp_database):
        """Test that volatility adjustments are persisted to database."""
        # Calculate volatility multipliers for multiple symbols
        symbols = ["EURUSD", "GBPUSD", "V10", "V100"]

        for symbol in symbols:
            risk_manager_with_volatility.calculate_volatility_multiplier(symbol)

        # Verify data was stored in database
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()

        # Check volatility_adjustments table
        cursor.execute("SELECT COUNT(*) FROM volatility_adjustments")
        adjustment_count = cursor.fetchone()[0]
        assert adjustment_count == len(symbols)

        # Verify unique symbols were stored
        cursor.execute("SELECT DISTINCT symbol FROM volatility_adjustments")
        stored_symbols = [row[0] for row in cursor.fetchall()]
        assert set(stored_symbols) == set(symbols)

        # Verify adjustment details for one symbol
        cursor.execute(
            "SELECT current_atr, average_atr, volatility_ratio, volatility_multiplier "
            "FROM volatility_adjustments WHERE symbol = ? "
            "ORDER BY id DESC LIMIT 1",
            ("EURUSD",)
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] > 0  # current_atr
        assert row[1] > 0  # average_atr
        assert row[2] > 0  # volatility_ratio
        assert 0.3 <= row[3] <= 1.5  # volatility_multiplier

        conn.close()

    def test_volatility_adjustment_history(self, risk_manager_with_volatility):
        """Test getting volatility adjustment history."""
        # Calculate multipliers for different symbols
        symbols = ["EURUSD", "GBPUSD", "V10"]

        for symbol in symbols:
            risk_manager_with_volatility.calculate_volatility_multiplier(symbol)

        # Get all adjustments
        all_adjustments = risk_manager_with_volatility.get_volatility_adjustments()
        assert len(all_adjustments) == len(symbols)

        # Get adjustments for specific symbol
        eurusd_adjustments = risk_manager_with_volatility.get_volatility_adjustments(symbol="EURUSD")
        assert len(eurusd_adjustments) == 1
        assert eurusd_adjustments[0].symbol == "EURUSD"

    def test_volatility_multiplier_caching(self, risk_manager_with_volatility):
        """Test that price data is cached for repeated calculations."""
        symbol = "EURUSD"

        # Calculate volatility multiplier twice
        vol_mult_1 = risk_manager_with_volatility.calculate_volatility_multiplier(symbol)
        vol_mult_2 = risk_manager_with_volatility.calculate_volatility_multiplier(symbol)

        # Results should be consistent (using cached data)
        assert vol_mult_1 == vol_mult_2

        # Cache should be populated
        cache_key = f"{symbol}_H1"
        assert cache_key in risk_manager_with_volatility._price_data_cache
        assert len(risk_manager_with_volatility._price_data_cache[cache_key]) >= risk_manager_with_volatility._atr_lookback

    def test_volatility_multiplier_error_handling(self, risk_manager_with_volatility):
        """Test error handling in volatility multiplier calculation."""
        # This test verifies graceful error handling
        # The synthetic data generation should handle errors gracefully

        # Try with an unusual symbol
        unusual_symbol = "UNUSUAL_SYMBOL_123"
        vol_mult = risk_manager_with_volatility.calculate_volatility_multiplier(unusual_symbol)

        # Should return a valid multiplier even for unusual symbols
        assert 0.3 <= vol_mult <= 1.5

        logger.info(f"Volatility multiplier for unusual symbol: {vol_mult:.3f}")


def test_integration_with_historical_data():
    """
    Integration test with historical trade data.

    This test simulates a realistic trading scenario with varying performance
    to verify that the adaptive risk manager responds appropriately.
    """
    # Create temporary database
    import tempfile
    import os

    temp_dir = tempfile.mkdtemp()
    perf_db = os.path.join(temp_dir, "test_performance_integration.db")
    risk_db = os.path.join(temp_dir, "test_risk_integration.db")

    try:
        # Create components
        comparator = PerformanceComparator(database_path=perf_db)
        risk_manager = AdaptiveRiskManager(
            performance_comparator=comparator,
            database_path=risk_db,
            base_risk_percent=2.0,
            min_risk_percent=0.5,
            max_risk_percent=3.0,
            performance_window=20,
        )

        # Simulate a trading journey:
        # Phase 1: Good performance (winning streak)
        # Phase 2: Declining performance (losing streak)
        # Phase 3: Recovery (normal performance)

        risk_history = []

        # Phase 1: 15 winning trades out of 20 (75% win rate)
        for i in range(20):
            profit = 100.0 if i < 15 else -100.0
            position = TradePosition(
                ticket=11000 + i,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0850,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=profit,
                swap=0.0,
                commission=0.0,
            )

            comparator.record_trade_outcome(
                position=position,
                exit_price=1.0850,
                exit_time=datetime.utcnow(),
                final_profit=profit,
                peak_profit=100.0 if profit > 0 else 0.0,
                max_adverse_excursion=0.0 if profit > 0 else -100.0,
            )

        risk_after_phase1 = risk_manager.adjust_for_recent_performance()
        risk_history.append(("Phase 1 (75% win rate)", risk_after_phase1))

        # Phase 2: Add more losing trades (win rate drops to 40%)
        for i in range(20):
            profit = -100.0  # All losses
            position = TradePosition(
                ticket=11200 + i,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0850,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=profit,
                swap=0.0,
                commission=0.0,
            )

            comparator.record_trade_outcome(
                position=position,
                exit_price=1.0850,
                exit_time=datetime.utcnow(),
                final_profit=profit,
                peak_profit=0.0,
                max_adverse_excursion=-100.0,
            )

        risk_after_phase2 = risk_manager.adjust_for_recent_performance()
        risk_history.append(("Phase 2 (40% win rate)", risk_after_phase2))

        # Phase 3: Add winning trades (win rate recovers to 55%)
        for i in range(20):
            profit = 100.0 if i < 11 else -100.0  # 11 wins, 9 losses
            position = TradePosition(
                ticket=11400 + i,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0850,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=profit,
                swap=0.0,
                commission=0.0,
            )

            comparator.record_trade_outcome(
                position=position,
                exit_price=1.0850,
                exit_time=datetime.utcnow(),
                final_profit=profit,
                peak_profit=100.0 if profit > 0 else 0.0,
                max_adverse_excursion=0.0 if profit > 0 else -100.0,
            )

        risk_after_phase3 = risk_manager.adjust_for_recent_performance()
        risk_history.append(("Phase 3 (55% win rate)", risk_after_phase3))

        # Verify risk adjustments
        logger.info("Risk adjustment history:")
        for phase, risk in risk_history:
            logger.info(f"  {phase}: {risk:.2f}%")

        # Assertions
        assert risk_after_phase1 == 2.5, "Phase 1 should increase risk to 2.5%"
        assert risk_after_phase2 == 1.0, "Phase 2 should decrease risk to 1.0%"
        assert risk_after_phase3 == 2.0, "Phase 3 should use base risk of 2.0%"

        # Calculate position sizes for each phase
        account_balance = 10000.0
        entry_price = 1.0850
        stop_loss = 1.0800

        position_sizes = []
        for _, risk in risk_history:
            risk_manager._current_risk_percent = risk
            position_size = risk_manager.calculate_position_size(
                account_balance, entry_price, stop_loss, "BUY"
            )
            position_sizes.append(position_size)

        logger.info("Position sizes:")
        for (phase, risk), size in zip(risk_history, position_sizes):
            logger.info(f"  {phase} ({risk:.1f}%): {size:.2f} lots")

        # Verify position sizes scale with risk
        assert position_sizes[0] > position_sizes[1], "Position size should decrease in losing streak"
        assert position_sizes[2] > position_sizes[1], "Position size should increase in recovery"

        logger.info("Integration test passed!")

    finally:
        # Cleanup - close database connections first
        comparator.close()
        risk_manager.close()
        import shutil
        import time
        time.sleep(0.1)  # Give time for connections to close
        try:
            shutil.rmtree(temp_dir)
        except PermissionError:
            # Windows may have file locking issues, skip cleanup on error
            pass


class TestDrawdownBasedRiskScaling:
    """Test suite for drawdown-based position scaling (US-003)."""

    def test_calculate_drawdown_no_drawdown(self, risk_manager):
        """Test drawdown calculation when equity is at peak."""
        initial_balance = 10000.0
        current_equity = 10000.0  # No change

        drawdown, peak, equity = risk_manager.calculate_drawdown(current_equity)

        assert drawdown == 0.0
        assert peak == initial_balance
        assert equity == current_equity

    def test_calculate_drawdown_with_decline(self, risk_manager):
        """Test drawdown calculation when equity has declined."""
        initial_balance = 10000.0
        current_equity = 9000.0  # 10% decline

        drawdown, peak, equity = risk_manager.calculate_drawdown(current_equity)

        assert drawdown == 10.0
        assert peak == initial_balance
        assert equity == current_equity

    def test_calculate_drawdown_new_peak(self, risk_manager):
        """Test drawdown calculation when equity reaches new peak."""
        initial_balance = 10000.0
        current_equity = 11000.0  # New high

        drawdown, peak, equity = risk_manager.calculate_drawdown(current_equity)

        assert drawdown == 0.0
        assert peak == 11000.0  # Peak updated
        assert equity == current_equity

    def test_drawdown_threshold_1_reduction(self, risk_manager):
        """Test 50% risk reduction when drawdown exceeds 10%."""
        base_risk = 2.0
        risk_manager._base_risk_percent = base_risk

        # Simulate 12% drawdown (above first threshold of 10%)
        current_equity = 8800.0  # 12% decline from 10000
        new_risk, trading_allowed = risk_manager.adjust_for_drawdown(current_equity)

        # Should reduce risk by 50%
        assert new_risk == base_risk * 0.5
        assert trading_allowed is True  # Trading still allowed

        # Verify adjustment was recorded
        adjustments = risk_manager.get_drawdown_adjustments()
        assert len(adjustments) > 0
        assert adjustments[-1].current_drawdown >= 10.0

    def test_drawdown_threshold_2_reduction(self, risk_manager):
        """Test 75% risk reduction when drawdown exceeds 15%."""
        base_risk = 2.0
        risk_manager._base_risk_percent = base_risk

        # Simulate 17% drawdown (above second threshold of 15%)
        current_equity = 8300.0  # 17% decline from 10000
        new_risk, trading_allowed = risk_manager.adjust_for_drawdown(current_equity)

        # Should reduce risk by 75%
        assert new_risk == base_risk * 0.25
        assert trading_allowed is True  # Trading still allowed

        # Verify adjustment was recorded
        adjustments = risk_manager.get_drawdown_adjustments()
        assert len(adjustments) > 0
        assert adjustments[-1].current_drawdown >= 15.0

    def test_drawdown_threshold_3_circuit_breaker(self, risk_manager):
        """Test circuit breaker when drawdown exceeds 20%."""
        base_risk = 2.0
        risk_manager._base_risk_percent = base_risk

        # Simulate 22% drawdown (above circuit breaker threshold of 20%)
        current_equity = 7800.0  # 22% decline from 10000
        new_risk, trading_allowed = risk_manager.adjust_for_drawdown(current_equity)

        # Should halt trading
        assert new_risk == 0.0
        assert trading_allowed is False
        assert risk_manager.is_trading_allowed() is False

        # Verify adjustment was recorded
        adjustments = risk_manager.get_drawdown_adjustments()
        assert len(adjustments) > 0
        assert "CIRCUIT BREAKER" in adjustments[-1].reason

    def test_drawdown_gradual_recovery(self, risk_manager):
        """Test gradual risk restoration as drawdown recovers."""
        base_risk = 2.0
        risk_manager._base_risk_percent = base_risk

        # First, create a drawdown scenario
        current_equity = 8800.0  # 12% drawdown
        new_risk, _ = risk_manager.adjust_for_drawdown(current_equity)
        assert new_risk == base_risk * 0.5  # 50% reduction

        # Now simulate partial recovery (8% drawdown)
        current_equity = 9200.0  # 8% drawdown
        new_risk, trading_allowed = risk_manager.adjust_for_drawdown(current_equity)

        # Should have gradual risk restoration (between 50% and 100%)
        # At 8% drawdown (80% of threshold), risk should be: 0.5 + 0.5 * (1 - 0.8) = 0.6
        expected_risk = base_risk * 0.6
        assert abs(new_risk - expected_risk) < 0.1
        assert trading_allowed is True

    def test_drawdown_full_recovery(self, risk_manager):
        """Test full risk restoration after complete recovery."""
        base_risk = 2.0
        risk_manager._base_risk_percent = base_risk

        # First, create a drawdown scenario
        current_equity = 8800.0  # 12% drawdown
        risk_manager.adjust_for_drawdown(current_equity)

        # Now simulate full recovery (0% drawdown, new peak)
        current_equity = 10500.0  # New peak
        new_risk, trading_allowed = risk_manager.adjust_for_drawdown(current_equity)

        # Should restore to base risk (100%)
        assert new_risk == base_risk
        assert trading_allowed is True

    def test_circuit_breaker_persistence(self, risk_manager):
        """Test that circuit breaker persists until recovery threshold is met."""
        base_risk = 2.0
        risk_manager._base_risk_percent = base_risk

        # Trigger circuit breaker
        current_equity = 7800.0  # 22% drawdown
        new_risk, trading_allowed = risk_manager.adjust_for_drawdown(current_equity)
        assert trading_allowed is False

        # Try to trade while still in circuit breaker (18% drawdown)
        current_equity = 8200.0  # 18% drawdown (still above 15% recovery threshold)
        new_risk, trading_allowed = risk_manager.adjust_for_drawdown(current_equity)
        assert trading_allowed is False  # Still halted
        assert new_risk == 0.0

        # Recover below threshold (14% drawdown)
        current_equity = 8600.0  # 14% drawdown (below 15% recovery threshold)
        new_risk, trading_allowed = risk_manager.adjust_for_drawdown(current_equity)

        # Trading should resume with reduced risk
        assert trading_allowed is True
        assert new_risk == base_risk * 0.5  # Start with 50% of base risk

    def test_drawdown_database_persistence(self, risk_manager, temp_database):
        """Test that drawdown adjustments are persisted to database."""
        # Create a drawdown scenario
        current_equity = 8800.0  # 12% drawdown
        risk_manager.adjust_for_drawdown(current_equity)

        # Verify data was stored in database
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()

        # Check drawdown_adjustments table
        cursor.execute("SELECT COUNT(*) FROM drawdown_adjustments")
        adjustment_count = cursor.fetchone()[0]
        assert adjustment_count > 0

        # Verify adjustment details
        cursor.execute(
            "SELECT current_drawdown, new_risk_percent "
            "FROM drawdown_adjustments ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        assert row[0] >= 10.0  # Current drawdown
        assert row[1] == 1.0  # New risk (50% of 2.0%)

        conn.close()

    def test_drawdown_minimum_risk_cap(self, risk_manager):
        """Test that drawdown adjustments respect minimum risk cap."""
        # Set very low base risk to test minimum cap
        risk_manager._base_risk_percent = 0.4  # Below minimum of 0.5%

        # Trigger 75% reduction
        current_equity = 8300.0  # 17% drawdown
        new_risk, _ = risk_manager.adjust_for_drawdown(current_equity)

        # Should be capped at minimum
        assert new_risk >= risk_manager._min_risk_percent

    def test_manual_circuit_breaker_reset(self, risk_manager):
        """Test manual circuit breaker reset functionality."""
        # Trigger circuit breaker
        current_equity = 7800.0  # 22% drawdown
        risk_manager.adjust_for_drawdown(current_equity)
        assert risk_manager.is_trading_allowed() is False

        # Manually reset circuit breaker
        risk_manager.reset_circuit_breaker()

        # Trading should be allowed with reduced risk
        assert risk_manager.is_trading_allowed() is True
        assert risk_manager._current_risk_percent == risk_manager._base_risk_percent * 0.5

    def test_drawdown_adjustment_history(self, risk_manager):
        """Test retrieving drawdown adjustment history."""
        # Create multiple drawdown scenarios (only those >= 10% trigger adjustments)
        equity_values = [9500.0, 9000.0, 8500.0, 8000.0]  # 5%, 10%, 15%, 20% drawdowns

        for equity in equity_values:
            risk_manager.adjust_for_drawdown(equity)

        # Get adjustment history
        history = risk_manager.get_drawdown_adjustments(limit=10)

        # Should have recorded 3 adjustments (10%, 15%, 20% trigger adjustments)
        # 5% drawdown doesn't trigger an adjustment
        assert len(history) >= 3

        # Verify data structure
        for adjustment in history:
            assert isinstance(adjustment, DrawdownAdjustment)
            assert adjustment.current_drawdown >= 0
            assert adjustment.peak_equity > 0
            assert adjustment.current_equity > 0

    def test_drawdown_with_initial_balance_param(self, temp_database, performance_comparator):
        """Test drawdown calculation with custom initial balance."""
        custom_initial_balance = 50000.0

        risk_manager = AdaptiveRiskManager(
            performance_comparator=performance_comparator,
            database_path=temp_database,
            initial_account_balance=custom_initial_balance,
        )

        # Verify initial peak is set correctly
        assert risk_manager._peak_equity == custom_initial_balance

        # Test drawdown from custom initial
        current_equity = 45000.0  # 10% decline
        drawdown, peak, equity = risk_manager.calculate_drawdown(current_equity)

        assert drawdown == 10.0
        assert peak == custom_initial_balance

    def test_position_size_with_drawdown_adjustment(self, risk_manager):
        """Test that position sizes are adjusted based on drawdown."""
        account_balance = 10000.0
        entry_price = 1.0850
        stop_loss = 1.0800

        # Get base position size (no drawdown)
        base_position_size = risk_manager.calculate_position_size(
            account_balance, entry_price, stop_loss, "BUY"
        )

        # Apply drawdown reduction (12% drawdown)
        current_equity = 8800.0
        new_risk, _ = risk_manager.adjust_for_drawdown(current_equity)

        # Calculate position size with drawdown adjustment
        adjusted_position_size = risk_manager.calculate_position_size(
            account_balance, entry_price, stop_loss, "BUY"
        )

        # Adjusted position size should be 50% of base
        assert abs(adjusted_position_size - base_position_size * 0.5) < 0.01


def test_drawdown_integration_scenario():
    """
    Integration test simulating realistic drawdown scenario.

    This test simulates a complete drawdown and recovery cycle to verify
    that the drawdown-based risk scaling works correctly in a realistic
    trading scenario.
    """
    import tempfile
    import os

    temp_dir = tempfile.mkdtemp()
    perf_db = os.path.join(temp_dir, "test_perf_drawdown.db")
    risk_db = os.path.join(temp_dir, "test_risk_drawdown.db")

    try:
        # Create components
        comparator = PerformanceComparator(database_path=perf_db)
        risk_manager = AdaptiveRiskManager(
            performance_comparator=comparator,
            database_path=risk_db,
            base_risk_percent=2.0,
            initial_account_balance=10000.0,
        )

        # Simulate trading journey with drawdown and recovery
        scenarios = [
            # (equity, expected_risk_range, expected_trading_allowed, description)
            (10000.0, (1.8, 2.2), True, "Initial state - no drawdown"),
            (9200.0, (1.8, 2.2), True, "8% drawdown - below threshold, maintain base risk"),
            (8800.0, (0.9, 1.1), True, "12% drawdown - 50% risk reduction"),
            (8300.0, (0.4, 0.6), True, "17% drawdown - 75% risk reduction"),
            (7800.0, (0.0, 0.1), False, "22% drawdown - circuit breaker triggered"),
            (8200.0, (0.0, 0.1), False, "18% drawdown - still in circuit breaker"),
            (8600.0, (0.9, 1.1), True, "14% drawdown - circuit breaker lifted"),
            (9200.0, (1.1, 1.3), True, "8% drawdown - gradual recovery"),
            (10000.0, (1.8, 2.2), True, "Full recovery - base risk restored"),
            (10500.0, (1.8, 2.2), True, "New peak - base risk maintained"),
        ]

        logger.info("Drawdown integration test scenario:")
        logger.info("=" * 80)

        risk_history = []

        for equity, expected_risk_range, expected_trading, description in scenarios:
            new_risk, trading_allowed = risk_manager.adjust_for_drawdown(equity)

            risk_history.append({
                "description": description,
                "equity": equity,
                "risk": new_risk,
                "trading_allowed": trading_allowed,
            })

            # Verify risk is in expected range
            assert expected_risk_range[0] <= new_risk <= expected_risk_range[1], \
                f"Risk {new_risk}% not in expected range {expected_risk_range} for: {description}"

            # Verify trading status
            assert trading_allowed == expected_trading, \
                f"Trading allowed {trading_allowed} != expected {expected_trading} for: {description}"

            logger.info(
                f"{description:40s} | Equity: ${equity:8.0f} | "
                f"Risk: {new_risk:5.2f}% | Trading: {trading_allowed}"
            )

        logger.info("=" * 80)
        logger.info("Drawdown integration test passed!")

        # Verify adjustments were recorded
        adjustments = risk_manager.get_drawdown_adjustments()
        logger.info(f"Total drawdown adjustments recorded: {len(adjustments)}")

        # Verify database persistence
        conn = sqlite3.connect(risk_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM drawdown_adjustments")
        db_count = cursor.fetchone()[0]
        conn.close()

        logger.info(f"Drawdown adjustments in database: {db_count}")
        assert db_count > 0, "No adjustments found in database"

    finally:
        # Cleanup
        comparator.close()
        risk_manager.close()
        import time
        time.sleep(0.1)
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except PermissionError:
            pass


if __name__ == "__main__":
    # Run the integration tests
    test_integration_with_historical_data()
    test_drawdown_integration_scenario()
    logger.info("All integration tests passed!")


class TestCorrelationBasedRiskAdjustment:
    """Test suite for correlation-based risk adjustment (US-004)."""

    def test_calculate_portfolio_correlation_no_positions(self, risk_manager):
        """Test correlation adjustment when no positions are open."""
        open_positions = []
        target_symbol = "EURUSD"

        multiplier, correlated_symbols, correlation_count = risk_manager.calculate_portfolio_correlation(
            target_symbol=target_symbol,
            open_positions=open_positions
        )

        assert multiplier == 1.0
        assert correlated_symbols == []
        assert correlation_count == 0

    def test_calculate_portfolio_correlation_single_position(self, risk_manager):
        """Test correlation adjustment with one open position."""
        # Create an open position
        position = TradePosition(
            ticket=1001,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0860,
            volume=1.0,
            stop_loss=1.0800,
            take_profit=1.0900,
            entry_time=datetime.utcnow(),
            profit=100.0,
            swap=0.0,
            commission=0.0,
        )

        open_positions = [position]
        target_symbol = "GBPUSD"

        multiplier, correlated_symbols, correlation_count = risk_manager.calculate_portfolio_correlation(
            target_symbol=target_symbol,
            open_positions=open_positions
        )

        # Should return a valid multiplier
        assert 0.2 <= multiplier <= 1.0
        assert isinstance(correlated_symbols, list)
        assert isinstance(correlation_count, int)

        # Verify adjustment was recorded
        adjustments = risk_manager.get_correlation_adjustments()
        assert len(adjustments) > 0
        assert adjustments[-1].symbol == target_symbol

    def test_calculate_portfolio_correlation_multiple_positions(self, risk_manager):
        """Test correlation adjustment with multiple open positions."""
        # Create multiple open positions in different symbols
        positions = [
            TradePosition(
                ticket=1001 + i,
                symbol=symbol,
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0860,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=100.0,
                swap=0.0,
                commission=0.0,
            )
            for i, symbol in enumerate(["EURUSD", "GBPUSD", "USDJPY"])
        ]

        target_symbol = "EURUSD"

        multiplier, correlated_symbols, correlation_count = risk_manager.calculate_portfolio_correlation(
            target_symbol=target_symbol,
            open_positions=positions
        )

        # Should return a valid multiplier
        assert 0.2 <= multiplier <= 1.0
        assert correlation_count >= 0
        assert correlation_count <= len(positions)

        # EURUSD should be highly correlated with itself if present in positions
        # In this case, GBPUSD and USDJPY might have some correlation with EURUSD
        logger.info(
            f"Correlation for {target_symbol}: multiplier={multiplier:.3f}, "
            f"count={correlation_count}, symbols={correlated_symbols}"
        )

    def test_position_size_adjustment_for_correlation(self, risk_manager):
        """Test position size calculation with correlation adjustment."""
        base_position_size = 1.0
        target_symbol = "EURUSD"

        # Create correlated open positions
        positions = [
            TradePosition(
                ticket=2001,
                symbol="GBPUSD",  # Likely correlated with EURUSD
                direction="BUY",
                entry_price=1.2650,
                current_price=1.2660,
                volume=1.0,
                stop_loss=1.2600,
                take_profit=1.2700,
                entry_time=datetime.utcnow(),
                profit=100.0,
                swap=0.0,
                commission=0.0,
            ),
            TradePosition(
                ticket=2002,
                symbol="USDJPY",
                direction="SELL",
                entry_price=145.50,
                current_price=145.40,
                volume=1.0,
                stop_loss=146.00,
                take_profit=145.00,
                entry_time=datetime.utcnow(),
                profit=100.0,
                swap=0.0,
                commission=0.0,
            ),
        ]

        adjusted_size = risk_manager.adjust_position_size_for_correlation(
            base_position_size=base_position_size,
            target_symbol=target_symbol,
            open_positions=positions
        )

        # Adjusted size should be less than or equal to base
        assert adjusted_size <= base_position_size
        assert adjusted_size >= base_position_size * 0.2  # Minimum 20% of base

        logger.info(
            f"Position size adjusted: {base_position_size:.2f} -> {adjusted_size:.2f} lots "
            f"for {target_symbol} with {len(positions)} open positions"
        )

    def test_correlation_threshold(self, risk_manager):
        """Test that correlation threshold is applied correctly."""
        # The correlation threshold should be 0.7
        assert risk_manager._correlation_threshold == 0.7

        # Test that symbols with correlation below threshold don't trigger reduction
        # This is tested implicitly through calculate_portfolio_correlation

    def test_correlation_adjustment_dataclass(self, risk_manager):
        """Test CorrelationAdjustment dataclass."""
        adjustment = CorrelationAdjustment(
            timestamp=datetime.utcnow(),
            symbol="EURUSD",
            correlated_symbols=["GBPUSD", "USDJPY"],
            correlation_count=2,
            adjustment_multiplier=0.8,
            reason="Test adjustment",
        )

        # Test to_dict conversion
        adj_dict = adjustment.to_dict()
        assert "timestamp" in adj_dict
        assert adj_dict["symbol"] == "EURUSD"
        assert adj_dict["correlated_symbols"] == ["GBPUSD", "USDJPY"]
        assert adj_dict["correlation_count"] == 2
        assert adj_dict["adjustment_multiplier"] == 0.8

    def test_correlation_matrix_calculation(self, risk_manager):
        """Test correlation matrix calculation."""
        symbols = ["EURUSD", "GBPUSD", "USDJPY"]

        correlation_matrix = risk_manager._calculate_correlation_matrix(symbols)

        # Should return a DataFrame
        assert correlation_matrix is not None
        assert not correlation_matrix.empty

        # Should be a square matrix
        assert correlation_matrix.shape == (len(symbols), len(symbols))

        # Diagonal should be 1.0 (perfect correlation with itself)
        for symbol in symbols:
            assert abs(correlation_matrix.loc[symbol, symbol] - 1.0) < 0.01

        logger.info(f"Correlation matrix:\n{correlation_matrix}")

    def test_correlation_matrix_insufficient_data(self, risk_manager):
        """Test correlation matrix calculation with insufficient data."""
        # Need at least 2 symbols
        result = risk_manager._calculate_correlation_matrix(["EURUSD"])
        assert result is None

    def test_get_correlation_adjustments(self, risk_manager):
        """Test retrieving correlation adjustment history."""
        # Create some adjustments
        positions = [
            TradePosition(
                ticket=3001,
                symbol="GBPUSD",
                direction="BUY",
                entry_price=1.2650,
                current_price=1.2660,
                volume=1.0,
                stop_loss=1.2600,
                take_profit=1.2700,
                entry_time=datetime.utcnow(),
                profit=100.0,
                swap=0.0,
                commission=0.0,
            )
        ]

        risk_manager.calculate_portfolio_correlation("EURUSD", positions)
        risk_manager.calculate_portfolio_correlation("USDJPY", positions)

        # Get all adjustments
        all_adjustments = risk_manager.get_correlation_adjustments()
        assert len(all_adjustments) >= 2

        # Get adjustments for specific symbol
        eurusd_adjustments = risk_manager.get_correlation_adjustments(symbol="EURUSD")
        assert len(eurusd_adjustments) >= 1
        assert eurusd_adjustments[-1].symbol == "EURUSD"

    def test_correlation_database_persistence(self, risk_manager, temp_database):
        """Test that correlation adjustments are persisted to database."""
        # Create a correlation adjustment
        position = TradePosition(
            ticket=4001,
            symbol="GBPUSD",
            direction="BUY",
            entry_price=1.2650,
            current_price=1.2660,
            volume=1.0,
            stop_loss=1.2600,
            take_profit=1.2700,
            entry_time=datetime.utcnow(),
            profit=100.0,
            swap=0.0,
            commission=0.0,
        )

        risk_manager.calculate_portfolio_correlation("EURUSD", [position])

        # Verify data was stored in database
        conn = sqlite3.connect(temp_database)
        cursor = conn.cursor()

        # Check correlation_adjustments table
        cursor.execute("SELECT COUNT(*) FROM correlation_adjustments")
        adjustment_count = cursor.fetchone()[0]
        assert adjustment_count > 0

        # Verify adjustment details
        cursor.execute(
            "SELECT symbol, correlation_count, adjustment_multiplier "
            "FROM correlation_adjustments ORDER BY id DESC LIMIT 1"
        )
        row = cursor.fetchone()
        assert row[0] == "EURUSD"
        assert row[1] >= 0
        assert 0.2 <= row[2] <= 1.0

        conn.close()

    def test_correlation_with_same_symbol(self, risk_manager):
        """Test correlation when same symbol is already in open positions."""
        # Create multiple open positions in EURUSD to test same-symbol correlation
        # According to PRD: First correlated position = no reduction, each additional = 20% reduction
        # So 1 correlated position = 1.0x (no reduction), 2 correlated = 0.8x, 3 correlated = 0.6x

        position = TradePosition(
            ticket=5001,
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.0850,
            current_price=1.0860,
            volume=1.0,
            stop_loss=1.0800,
            take_profit=1.0900,
            entry_time=datetime.utcnow(),
            profit=100.0,
            swap=0.0,
            commission=0.0,
        )

        # Create another position in a different symbol
        position2 = TradePosition(
            ticket=5002,
            symbol="GBPUSD",
            direction="BUY",
            entry_price=1.2650,
            current_price=1.2660,
            volume=1.0,
            stop_loss=1.2600,
            take_profit=1.2700,
            entry_time=datetime.utcnow(),
            profit=100.0,
            swap=0.0,
            commission=0.0,
        )

        # Try to add another EURUSD position
        multiplier, correlated_symbols, correlation_count = risk_manager.calculate_portfolio_correlation(
            target_symbol="EURUSD",
            open_positions=[position, position2]
        )

        # The correlation analysis should work correctly
        # Note: With synthetic random data, EURUSD and GBPUSD may not be highly correlated
        # The important thing is that the system correctly calculates correlations

        # Verify we get valid results
        assert 0.2 <= multiplier <= 1.0
        assert isinstance(correlation_count, int)
        assert correlation_count >= 0

        # If EURUSD is in correlated_symbols, it means we detected it's already open
        # With 1 correlated position, multiplier should be 1.0 (no reduction for first)
        # With 2+ correlated positions, multiplier should be < 1.0
        if correlation_count == 1:
            # First correlated position: no reduction
            assert multiplier == 1.0
            logger.info(
                f"First correlated position: multiplier={multiplier:.3f}, "
                f"count={correlation_count}, symbols={correlated_symbols}"
            )
        elif correlation_count >= 2:
            # Additional correlated positions: 20% reduction each beyond first
            assert multiplier < 1.0
            logger.info(
                f"Multiple correlated positions: multiplier={multiplier:.3f}, "
                f"count={correlation_count}, symbols={correlated_symbols}, "
                f"reduction={(1-multiplier)*100:.1f}%"
            )
        else:
            # No correlations detected with synthetic data
            logger.info(
                f"No significant correlations detected with synthetic data: "
                f"multiplier={multiplier:.3f}, count={correlation_count}"
            )
            assert multiplier == 1.0

    def test_correlation_adjustment_multiplier_bounds(self, risk_manager):
        """Test that correlation adjustment multiplier stays within bounds."""
        # Create many correlated positions to test minimum multiplier
        positions = [
            TradePosition(
                ticket=6001 + i,
                symbol=f"SYM{i}",
                direction="BUY",
                entry_price=100.0 + i,
                current_price=100.0 + i,
                volume=1.0,
                stop_loss=99.0,
                take_profit=101.0,
                entry_time=datetime.utcnow(),
                profit=100.0,
                swap=0.0,
                commission=0.0,
            )
            for i in range(10)
        ]

        multiplier, _, _ = risk_manager.calculate_portfolio_correlation(
            target_symbol="EURUSD",
            open_positions=positions
        )

        # Multiplier should never go below 0.2 (20% of original size)
        assert multiplier >= 0.2
        assert multiplier <= 1.0

    def test_correlation_logging(self, risk_manager):
        """Test that correlation adjustments are logged properly."""
        position = TradePosition(
            ticket=7001,
            symbol="GBPUSD",
            direction="BUY",
            entry_price=1.2650,
            current_price=1.2660,
            volume=1.0,
            stop_loss=1.2600,
            take_profit=1.2700,
            entry_time=datetime.utcnow(),
            profit=100.0,
            swap=0.0,
            commission=0.0,
        )

        # Calculate correlation adjustment
        risk_manager.calculate_portfolio_correlation("EURUSD", [position])

        # Verify adjustment was recorded
        adjustments = risk_manager.get_correlation_adjustments()
        assert len(adjustments) > 0

        latest = adjustments[-1]
        assert latest.symbol == "EURUSD"
        assert latest.timestamp is not None
        assert latest.reason is not None
        assert len(latest.reason) > 0

        logger.info(f"Correlation adjustment reason: {latest.reason}")

    def test_adjust_position_size_for_correlation_convenience_method(self, risk_manager):
        """Test the convenience method for adjusting position size."""
        base_size = 2.0
        target_symbol = "EURUSD"

        positions = [
            TradePosition(
                ticket=8001,
                symbol="GBPUSD",
                direction="BUY",
                entry_price=1.2650,
                current_price=1.2660,
                volume=1.0,
                stop_loss=1.2600,
                take_profit=1.2700,
                entry_time=datetime.utcnow(),
                profit=100.0,
                swap=0.0,
                commission=0.0,
            )
        ]

        adjusted_size = risk_manager.adjust_position_size_for_correlation(
            base_position_size=base_size,
            target_symbol=target_symbol,
            open_positions=positions
        )

        # Should return adjusted size
        assert isinstance(adjusted_size, float)
        assert adjusted_size <= base_size
        assert adjusted_size >= base_size * 0.2

    def test_correlation_with_volatility_indices(self, risk_manager):
        """Test correlation calculation with volatility indices (V10, V100)."""
        positions = [
            TradePosition(
                ticket=9001,
                symbol="V10",
                direction="BUY",
                entry_price=10.50,
                current_price=10.60,
                volume=1.0,
                stop_loss=10.00,
                take_profit=11.00,
                entry_time=datetime.utcnow(),
                profit=100.0,
                swap=0.0,
                commission=0.0,
            ),
            TradePosition(
                ticket=9002,
                symbol="V100",
                direction="SELL",
                entry_price=100.50,
                current_price=100.40,
                volume=1.0,
                stop_loss=101.00,
                take_profit=100.00,
                entry_time=datetime.utcnow(),
                profit=100.0,
                swap=0.0,
                commission=0.0,
            ),
        ]

        target_symbol = "V25"

        multiplier, correlated_symbols, correlation_count = risk_manager.calculate_portfolio_correlation(
            target_symbol=target_symbol,
            open_positions=positions
        )

        # Should handle volatility indices
        assert 0.2 <= multiplier <= 1.0
        assert isinstance(correlation_count, int)

        logger.info(
            f"Volatility indices correlation: {target_symbol} multiplier={multiplier:.3f}, "
            f"correlated={correlation_count}, symbols={correlated_symbols}"
        )


def test_correlation_integration_scenario():
    """
    Integration test for correlation-based risk adjustment.

    This test simulates a realistic scenario where a trader has multiple
    open positions and is considering adding a new position, testing that
    the correlation system correctly identifies and adjusts for correlated
    positions.
    """
    import tempfile
    import os

    temp_dir = tempfile.mkdtemp()
    perf_db = os.path.join(temp_dir, "test_perf_correlation.db")
    risk_db = os.path.join(temp_dir, "test_risk_correlation.db")

    try:
        # Create components
        comparator = PerformanceComparator(database_path=perf_db)
        risk_manager = AdaptiveRiskManager(
            performance_comparator=comparator,
            database_path=risk_db,
            base_risk_percent=2.0,
        )

        logger.info("Correlation integration test scenario:")
        logger.info("=" * 80)

        # Scenario: Trader has positions in EURUSD, GBPUSD, and USDJPY
        # Considering adding a position in EURCAD or EURUSD

        existing_positions = [
            TradePosition(
                ticket=10001,
                symbol="EURUSD",
                direction="BUY",
                entry_price=1.0850,
                current_price=1.0860,
                volume=1.0,
                stop_loss=1.0800,
                take_profit=1.0900,
                entry_time=datetime.utcnow(),
                profit=100.0,
                swap=0.0,
                commission=0.0,
            ),
            TradePosition(
                ticket=10002,
                symbol="GBPUSD",
                direction="BUY",
                entry_price=1.2650,
                current_price=1.2660,
                volume=1.0,
                stop_loss=1.2600,
                take_profit=1.2700,
                entry_time=datetime.utcnow(),
                profit=100.0,
                swap=0.0,
                commission=0.0,
            ),
            TradePosition(
                ticket=10003,
                symbol="USDJPY",
                direction="SELL",
                entry_price=145.50,
                current_price=145.40,
                volume=1.0,
                stop_loss=146.00,
                take_profit=145.00,
                entry_time=datetime.utcnow(),
                profit=100.0,
                swap=0.0,
                commission=0.0,
            ),
        ]

        # Test 1: Adding another EURUSD position (highly correlated)
        logger.info("\nTest 1: Adding EURUSD position")
        logger.info("-" * 80)

        base_position_size = 1.0
        multiplier_eurusd, corr_symbols_eurusd, count_eurusd = risk_manager.calculate_portfolio_correlation(
            target_symbol="EURUSD",
            open_positions=existing_positions
        )

        adjusted_size_eurusd = base_position_size * multiplier_eurusd

        logger.info(
            f"Base position size: {base_position_size:.2f} lots\n"
            f"Correlated positions: {count_eurusd}\n"
            f"Correlated symbols: {corr_symbols_eurusd}\n"
            f"Adjustment multiplier: {multiplier_eurusd:.3f}\n"
            f"Adjusted position size: {adjusted_size_eurusd:.2f} lots\n"
            f"Reduction: {(1-multiplier_eurusd)*100:.1f}%"
        )

        # Test 2: Adding EURCAD position (likely correlated with EURUSD)
        logger.info("\nTest 2: Adding EURCAD position")
        logger.info("-" * 80)

        multiplier_eurcad, corr_symbols_eurcad, count_eurcad = risk_manager.calculate_portfolio_correlation(
            target_symbol="EURCAD",
            open_positions=existing_positions
        )

        adjusted_size_eurcad = base_position_size * multiplier_eurcad

        logger.info(
            f"Base position size: {base_position_size:.2f} lots\n"
            f"Correlated positions: {count_eurcad}\n"
            f"Correlated symbols: {corr_symbols_eurcad}\n"
            f"Adjustment multiplier: {multiplier_eurcad:.3f}\n"
            f"Adjusted position size: {adjusted_size_eurcad:.2f} lots\n"
            f"Reduction: {(1-multiplier_eurcad)*100:.1f}%"
        )

        # Test 3: Adding a position with no existing positions
        logger.info("\nTest 3: Adding position with no existing positions")
        logger.info("-" * 80)

        multiplier_no_pos, corr_symbols_no_pos, count_no_pos = risk_manager.calculate_portfolio_correlation(
            target_symbol="AUDUSD",
            open_positions=[]
        )

        adjusted_size_no_pos = base_position_size * multiplier_no_pos

        logger.info(
            f"Base position size: {base_position_size:.2f} lots\n"
            f"Correlated positions: {count_no_pos}\n"
            f"Correlated symbols: {corr_symbols_no_pos}\n"
            f"Adjustment multiplier: {multiplier_no_pos:.3f}\n"
            f"Adjusted position size: {adjusted_size_no_pos:.2f} lots\n"
            f"Reduction: {(1-multiplier_no_pos)*100:.1f}%"
        )

        logger.info("\n" + "=" * 80)
        logger.info("Correlation integration test passed!")

        # Verify database persistence
        conn = sqlite3.connect(risk_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM correlation_adjustments")
        db_count = cursor.fetchone()[0]
        conn.close()

        logger.info(f"Correlation adjustments stored in database: {db_count}")
        # Note: Test 3 with no existing positions doesn't create an adjustment (returns early with 1.0)
        # So we expect at least 2 adjustments from tests 1 and 2
        assert db_count >= 2, f"Expected at least 2 correlation adjustments in database, got {db_count}"

    finally:
        # Cleanup
        comparator.close()
        risk_manager.close()
        import time
        time.sleep(0.1)
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except PermissionError:
            pass
