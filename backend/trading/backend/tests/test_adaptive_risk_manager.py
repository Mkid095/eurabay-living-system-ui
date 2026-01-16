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


if __name__ == "__main__":
    # Run the integration test
    test_integration_with_historical_data()
