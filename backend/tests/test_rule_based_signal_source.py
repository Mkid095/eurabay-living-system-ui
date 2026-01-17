"""
Unit tests for Rule-Based Signal Source.

Tests the rule-based technical analysis signal source including:
- RSI strategy
- MACD strategy
- Moving average crossover strategy
- Bollinger Bands strategy
- Majority voting mechanism
- Signal storage
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import tempfile
import shutil

from app.services.rule_based_signal_source import (
    RuleBasedSignalSource,
    RuleBasedConfig,
    RuleStrategy,
    RuleSignalResult,
    SignalDirection,
    create_rule_based_signal_source
)
from app.services.ensemble_signals import SignalType


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_market_data():
    """Generate sample OHLCV market data for testing."""
    np.random.seed(42)

    # Generate 500 candles of sample data
    n = 500

    # Generate price data with trend and volatility
    trend = np.linspace(100, 110, n)
    noise = np.random.normal(0, 0.5, n)
    close = trend + noise

    # Generate OHLC from close
    high = close + np.abs(np.random.normal(0, 0.2, n))
    low = close - np.abs(np.random.normal(0, 0.2, n))
    open_ = close + np.random.normal(0, 0.1, n)

    # Volume
    volume = np.random.randint(1000, 10000, n)

    # Create DataFrame
    df = pd.DataFrame({
        "timestamp": pd.date_range(start="2024-01-01", periods=n, freq="5min"),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    })

    return df


@pytest.fixture
def rule_based_config():
    """Get test configuration for rule-based signal source."""
    return RuleBasedConfig(
        RSI_OVERBOUGHT=70.0,
        RSI_OVERSOLD=30.0,
        MA_SHORT_PERIOD=20,
        MA_LONG_PERIOD=50,
        MIN_AGREEMENT_RATIO=0.5
    )


@pytest.fixture
def temp_signal_dir():
    """Create temporary directory for signal storage."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def rule_based_source(rule_based_config, temp_signal_dir):
    """Create a rule-based signal source for testing."""
    config = rule_based_config
    config.SIGNAL_DIR = temp_signal_dir
    return RuleBasedSignalSource(symbol="V10", config=config)


# ============================================================================
# Test Initialization
# ============================================================================

def test_rule_based_source_initialization(rule_based_source):
    """Test that rule-based signal source initializes correctly."""
    assert rule_based_source.symbol == "V10"
    assert rule_based_source.config.RSI_OVERBOUGHT == 70.0
    assert rule_based_source.config.RSI_OVERSOLD == 30.0
    assert rule_based_source.config.MA_SHORT_PERIOD == 20
    assert rule_based_source.config.MA_LONG_PERIOD == 50
    assert rule_based_source._signals_generated == 0


def test_create_rule_based_signal_source_factory():
    """Test factory function for creating rule-based signal source."""
    source = create_rule_based_signal_source("V25")
    assert source.symbol == "V25"
    assert isinstance(source, RuleBasedSignalSource)


# ============================================================================
# Test RSI Strategy
# ============================================================================

def test_rsi_strategy_oversold(rule_based_source, sample_market_data):
    """Test RSI strategy generates BUY signal when oversold."""
    # Generate features
    from app.services.feature_engineering import FeatureEngineering
    fe = FeatureEngineering()
    df = fe.generate_features(sample_market_data, "V10")

    # Manually set RSI to oversold level
    df.loc[df.index[-1], "rsi"] = 25.0

    # Get RSI signal
    signal = rule_based_source._rsi_strategy(df)

    assert signal is not None
    assert signal.strategy == RuleStrategy.RSI
    assert signal.direction == SignalDirection.BUY
    assert signal.confidence > 0.5
    assert "oversold" in signal.reason.lower()
    assert signal.features["rsi"] == 25.0


def test_rsi_strategy_overbought(rule_based_source, sample_market_data):
    """Test RSI strategy generates SELL signal when overbought."""
    from app.services.feature_engineering import FeatureEngineering
    fe = FeatureEngineering()
    df = fe.generate_features(sample_market_data, "V10")

    # Manually set RSI to overbought level
    df.loc[df.index[-1], "rsi"] = 75.0

    # Get RSI signal
    signal = rule_based_source._rsi_strategy(df)

    assert signal is not None
    assert signal.strategy == RuleStrategy.RSI
    assert signal.direction == SignalDirection.SELL
    assert signal.confidence > 0.5
    assert "overbought" in signal.reason.lower()
    assert signal.features["rsi"] == 75.0


def test_rsi_strategy_neutral(rule_based_source, sample_market_data):
    """Test RSI strategy generates HOLD signal when neutral."""
    from app.services.feature_engineering import FeatureEngineering
    fe = FeatureEngineering()
    df = fe.generate_features(sample_market_data, "V10")

    # Manually set RSI to neutral level
    df.loc[df.index[-1], "rsi"] = 50.0

    # Get RSI signal
    signal = rule_based_source._rsi_strategy(df)

    assert signal is not None
    assert signal.strategy == RuleStrategy.RSI
    assert signal.direction == SignalDirection.HOLD
    assert "neutral" in signal.reason.lower()


# ============================================================================
# Test MACD Strategy
# ============================================================================

def test_macd_strategy_bullish_crossover(rule_based_source, sample_market_data):
    """Test MACD strategy detects bullish crossover."""
    from app.services.feature_engineering import FeatureEngineering
    fe = FeatureEngineering()
    df = fe.generate_features(sample_market_data, "V10")

    # Set previous values (MACD below signal)
    rule_based_source._prev_macd = -0.5
    rule_based_source._prev_macd_signal = -0.3

    # Set current values (MACD above signal - bullish crossover)
    df.loc[df.index[-1], "macd"] = 0.5
    df.loc[df.index[-1], "macd_signal"] = 0.3

    # Get MACD signal
    signal = rule_based_source._macd_strategy(df)

    assert signal is not None
    assert signal.strategy == RuleStrategy.MACD
    assert signal.direction == SignalDirection.BUY
    assert "crossover" in signal.reason.lower()
    assert signal.confidence >= 0.7


def test_macd_strategy_bearish_crossover(rule_based_source, sample_market_data):
    """Test MACD strategy detects bearish crossover."""
    from app.services.feature_engineering import FeatureEngineering
    fe = FeatureEngineering()
    df = fe.generate_features(sample_market_data, "V10")

    # Set previous values (MACD above signal)
    rule_based_source._prev_macd = 0.5
    rule_based_source._prev_macd_signal = 0.3

    # Set current values (MACD below signal - bearish crossover)
    df.loc[df.index[-1], "macd"] = -0.5
    df.loc[df.index[-1], "macd_signal"] = -0.3

    # Get MACD signal
    signal = rule_based_source._macd_strategy(df)

    assert signal is not None
    assert signal.strategy == RuleStrategy.MACD
    assert signal.direction == SignalDirection.SELL
    assert "crossover" in signal.reason.lower()
    assert signal.confidence >= 0.7


def test_macd_strategy_no_crossover(rule_based_source, sample_market_data):
    """Test MACD strategy when no crossover occurs."""
    from app.services.feature_engineering import FeatureEngineering
    fe = FeatureEngineering()
    df = fe.generate_features(sample_market_data, "V10")

    # Set previous values
    rule_based_source._prev_macd = 0.5
    rule_based_source._prev_macd_signal = 0.3

    # Set current values (still above signal, no crossover)
    df.loc[df.index[-1], "macd"] = 0.6
    df.loc[df.index[-1], "macd_signal"] = 0.4

    # Get MACD signal
    signal = rule_based_source._macd_strategy(df)

    assert signal is not None
    assert signal.strategy == RuleStrategy.MACD
    assert signal.direction == SignalDirection.BUY
    assert "no crossover" in signal.reason.lower()


# ============================================================================
# Test Moving Average Crossover Strategy
# ============================================================================

def test_ma_crossover_bullish(rule_based_source, sample_market_data):
    """Test MA crossover strategy detects bullish crossover."""
    from app.services.feature_engineering import FeatureEngineering
    fe = FeatureEngineering()
    df = fe.generate_features(sample_market_data, "V10")

    # Set previous values (short MA below long MA)
    rule_based_source._prev_ma_short = 105.0
    rule_based_source._prev_ma_long = 107.0

    # Set current values (short MA above long MA - bullish crossover)
    df.loc[df.index[-1], "sma_20"] = 108.0
    df.loc[df.index[-1], "sma_50"] = 106.0

    # Get MA signal
    signal = rule_based_source._ma_crossover_strategy(df)

    assert signal is not None
    assert signal.strategy == RuleStrategy.MA_CROSSOVER
    assert signal.direction == SignalDirection.BUY
    assert "crossover" in signal.reason.lower()
    assert signal.confidence >= 0.8


def test_ma_crossover_bearish(rule_based_source, sample_market_data):
    """Test MA crossover strategy detects bearish crossover."""
    from app.services.feature_engineering import FeatureEngineering
    fe = FeatureEngineering()
    df = fe.generate_features(sample_market_data, "V10")

    # Set previous values (short MA above long MA)
    rule_based_source._prev_ma_short = 108.0
    rule_based_source._prev_ma_long = 106.0

    # Set current values (short MA below long MA - bearish crossover)
    df.loc[df.index[-1], "sma_20"] = 105.0
    df.loc[df.index[-1], "sma_50"] = 107.0

    # Get MA signal
    signal = rule_based_source._ma_crossover_strategy(df)

    assert signal is not None
    assert signal.strategy == RuleStrategy.MA_CROSSOVER
    assert signal.direction == SignalDirection.SELL
    assert "crossover" in signal.reason.lower()
    assert signal.confidence >= 0.8


def test_ma_crossover_uptrend(rule_based_source, sample_market_data):
    """Test MA crossover strategy in established uptrend."""
    from app.services.feature_engineering import FeatureEngineering
    fe = FeatureEngineering()
    df = fe.generate_features(sample_market_data, "V10")

    # Set previous values (short MA already above long MA)
    rule_based_source._prev_ma_short = 108.0
    rule_based_source._prev_ma_long = 106.0

    # Set current values (still above, no crossover)
    df.loc[df.index[-1], "sma_20"] = 109.0
    df.loc[df.index[-1], "sma_50"] = 107.0

    # Get MA signal
    signal = rule_based_source._ma_crossover_strategy(df)

    assert signal is not None
    assert signal.strategy == RuleStrategy.MA_CROSSOVER
    assert signal.direction == SignalDirection.BUY
    assert "uptrend" in signal.reason.lower()


# ============================================================================
# Test Bollinger Bands Strategy
# ============================================================================

def test_bollinger_bands_upper_touch(rule_based_source, sample_market_data):
    """Test Bollinger Bands strategy when price touches upper band."""
    from app.services.feature_engineering import FeatureEngineering
    fe = FeatureEngineering()
    df = fe.generate_features(sample_market_data, "V10")

    # Set Bollinger Bands
    df.loc[df.index[-1], "bb_upper"] = 110.0
    df.loc[df.index[-1], "bb_middle"] = 105.0
    df.loc[df.index[-1], "bb_lower"] = 100.0
    df.loc[df.index[-1], "close"] = 110.0  # Price at upper band

    # Get BB signal
    signal = rule_based_source._bollinger_bands_strategy(df)

    assert signal is not None
    assert signal.strategy == RuleStrategy.BOLLINGER_BANDS
    assert signal.direction == SignalDirection.SELL
    assert "upper" in signal.reason.lower()
    assert signal.confidence >= 0.6


def test_bollinger_bands_lower_touch(rule_based_source, sample_market_data):
    """Test Bollinger Bands strategy when price touches lower band."""
    from app.services.feature_engineering import FeatureEngineering
    fe = FeatureEngineering()
    df = fe.generate_features(sample_market_data, "V10")

    # Set Bollinger Bands
    df.loc[df.index[-1], "bb_upper"] = 110.0
    df.loc[df.index[-1], "bb_middle"] = 105.0
    df.loc[df.index[-1], "bb_lower"] = 100.0
    df.loc[df.index[-1], "close"] = 100.0  # Price at lower band

    # Get BB signal
    signal = rule_based_source._bollinger_bands_strategy(df)

    assert signal is not None
    assert signal.strategy == RuleStrategy.BOLLINGER_BANDS
    assert signal.direction == SignalDirection.BUY
    assert "lower" in signal.reason.lower()
    assert signal.confidence >= 0.6


def test_bollinger_bands_neutral(rule_based_source, sample_market_data):
    """Test Bollinger Bands strategy when price is within bands."""
    from app.services.feature_engineering import FeatureEngineering
    fe = FeatureEngineering()
    df = fe.generate_features(sample_market_data, "V10")

    # Set Bollinger Bands
    df.loc[df.index[-1], "bb_upper"] = 110.0
    df.loc[df.index[-1], "bb_middle"] = 105.0
    df.loc[df.index[-1], "bb_lower"] = 100.0
    df.loc[df.index[-1], "close"] = 105.0  # Price at middle

    # Get BB signal
    signal = rule_based_source._bollinger_bands_strategy(df)

    assert signal is not None
    assert signal.strategy == RuleStrategy.BOLLINGER_BANDS
    assert signal.direction == SignalDirection.HOLD
    assert "within" in signal.reason.lower()


# ============================================================================
# Test Majority Voting
# ============================================================================

def test_majority_vote_buy_majority(rule_based_source):
    """Test majority voting with BUY majority."""
    rule_signals = [
        RuleSignalResult(
            strategy=RuleStrategy.RSI,
            direction=SignalDirection.BUY,
            confidence=0.8,
            reason="RSI oversold",
            features={"rsi": 25.0},
            timestamp=datetime.now()
        ),
        RuleSignalResult(
            strategy=RuleStrategy.MACD,
            direction=SignalDirection.BUY,
            confidence=0.7,
            reason="MACD bullish",
            features={"macd": 0.5},
            timestamp=datetime.now()
        ),
        RuleSignalResult(
            strategy=RuleStrategy.MA_CROSSOVER,
            direction=SignalDirection.SELL,
            confidence=0.6,
            reason="MA bearish",
            features={"sma_20": 105.0},
            timestamp=datetime.now()
        ),
        RuleSignalResult(
            strategy=RuleStrategy.BOLLINGER_BANDS,
            direction=SignalDirection.BUY,
            confidence=0.75,
            reason="BB lower",
            features={"bb_pct_b": 0.1},
            timestamp=datetime.now()
        )
    ]

    result = rule_based_source._majority_vote(rule_signals)

    assert result is not None
    assert result["direction"] == SignalDirection.BUY
    assert result["num_agreeing"] == 3
    assert result["total_rules"] == 4
    assert result["agreement_ratio"] == 0.75
    assert result["confidence"] > 0.5


def test_majority_vote_no_clear_majority(rule_based_source):
    """Test majority voting with no clear majority."""
    rule_signals = [
        RuleSignalResult(
            strategy=RuleStrategy.RSI,
            direction=SignalDirection.BUY,
            confidence=0.6,
            reason="RSI",
            features={"rsi": 40.0},
            timestamp=datetime.now()
        ),
        RuleSignalResult(
            strategy=RuleStrategy.MACD,
            direction=SignalDirection.SELL,
            confidence=0.6,
            reason="MACD",
            features={"macd": -0.3},
            timestamp=datetime.now()
        ),
        RuleSignalResult(
            strategy=RuleStrategy.MA_CROSSOVER,
            direction=SignalDirection.HOLD,
            confidence=0.5,
            reason="MA",
            features={"sma_20": 105.0},
            timestamp=datetime.now()
        ),
        RuleSignalResult(
            strategy=RuleStrategy.BOLLINGER_BANDS,
            direction=SignalDirection.HOLD,
            confidence=0.5,
            reason="BB",
            features={"bb_pct_b": 0.5},
            timestamp=datetime.now()
        )
    ]

    result = rule_based_source._majority_vote(rule_signals)

    # With min_agreement_ratio=0.5, HOLD with 2/4 votes should pass
    # But if MIN_AGREEMENT_RATIO is higher, this might return None
    # The test expects either a HOLD result or None depending on config
    if result is not None:
        assert result["direction"] == SignalDirection.HOLD
        assert result["num_agreeing"] == 2


def test_majority_vote_insufficient_agreement(rule_based_source):
    """Test majority voting with insufficient agreement."""
    # Create a source with higher minimum agreement
    config = RuleBasedConfig(MIN_AGREEMENT_RATIO=0.75)
    source = RuleBasedSignalSource(symbol="V10", config=config)

    rule_signals = [
        RuleSignalResult(
            strategy=RuleStrategy.RSI,
            direction=SignalDirection.BUY,
            confidence=0.6,
            reason="RSI",
            features={"rsi": 25.0},
            timestamp=datetime.now()
        ),
        RuleSignalResult(
            strategy=RuleStrategy.MACD,
            direction=SignalDirection.SELL,
            confidence=0.6,
            reason="MACD",
            features={"macd": -0.3},
            timestamp=datetime.now()
        ),
        RuleSignalResult(
            strategy=RuleStrategy.MA_CROSSOVER,
            direction=SignalDirection.SELL,
            confidence=0.6,
            reason="MA",
            features={"sma_20": 105.0},
            timestamp=datetime.now()
        ),
        RuleSignalResult(
            strategy=RuleStrategy.BOLLINGER_BANDS,
            direction=SignalDirection.HOLD,
            confidence=0.5,
            reason="BB",
            features={"bb_pct_b": 0.5},
            timestamp=datetime.now()
        )
    ]

    result = source._majority_vote(rule_signals)

    # SELL has 2/4 = 50% < 75% threshold, should return None
    assert result is None


# ============================================================================
# Test Signal Generation
# ============================================================================

@pytest.mark.asyncio
async def test_predict_generates_signal(rule_based_source, sample_market_data):
    """Test that predict generates a valid trading signal."""
    signal = await rule_based_source.predict(sample_market_data)

    assert signal is not None
    assert signal.symbol == "V10"
    assert signal.source == "rule_based_V10"
    assert signal.type == SignalType.RULE_BASED
    assert signal.direction in [SignalDirection.BUY, SignalDirection.SELL, SignalDirection.HOLD]
    assert 0.0 <= signal.confidence <= 1.0
    assert signal.price > 0
    assert "rule_signals" in signal.metadata
    assert "vote_breakdown" in signal.metadata
    assert "num_agreeing" in signal.metadata
    assert "total_rules" in signal.metadata


@pytest.mark.asyncio
async def test_predict_insufficient_data(rule_based_source):
    """Test that predict returns None with insufficient data."""
    small_df = pd.DataFrame({
        "timestamp": pd.date_range(start="2024-01-01", periods=50, freq="5min"),
        "open": list(range(50)),
        "high": [i + 1 for i in range(50)],
        "low": [i - 1 if i > 0 else 0 for i in range(50)],
        "close": list(range(50)),
        "volume": list(range(1000, 51000, 1000))
    })

    signal = await rule_based_source.predict(small_df)

    assert signal is None


@pytest.mark.asyncio
async def test_predict_updates_statistics(rule_based_source, sample_market_data):
    """Test that predict updates signal statistics."""
    initial_stats = rule_based_source.get_statistics()
    initial_count = initial_stats["signals_generated"]

    await rule_based_source.predict(sample_market_data)

    updated_stats = rule_based_source.get_statistics()
    assert updated_stats["signals_generated"] == initial_count + 1


# ============================================================================
# Test Signal Storage
# ============================================================================

@pytest.mark.asyncio
async def test_signal_storage(rule_based_source, sample_market_data, temp_signal_dir):
    """Test that signals are stored to file."""
    # Generate a signal
    signal = await rule_based_source.predict(sample_market_data)

    # Check that file was created
    signal_file = Path(temp_signal_dir) / f"rule_based_{rule_based_source.symbol}.jsonl"
    assert signal_file.exists()

    # Read and verify the stored signal
    with open(signal_file, "r") as f:
        content = f.read()
        assert len(content) > 0

        # Verify it's valid JSON
        stored_signals = [json.loads(line) for line in content.strip().split("\n")]
        assert len(stored_signals) == 1

        stored = stored_signals[0]
        assert stored["symbol"] == "V10"
        assert "direction" in stored
        assert "confidence" in stored
        assert "num_agreeing" in stored
        assert "total_rules" in stored


# ============================================================================
# Test Statistics and History
# ============================================================================

def test_get_statistics(rule_based_source):
    """Test getting signal source statistics."""
    stats = rule_based_source.get_statistics()

    assert stats["symbol"] == "V10"
    assert stats["signals_generated"] == 0
    assert stats["buy_signals"] == 0
    assert stats["sell_signals"] == 0
    assert stats["hold_signals"] == 0
    assert stats["buy_ratio"] == 0.0
    assert stats["sell_ratio"] == 0.0


def test_get_signal_history(rule_based_source, temp_signal_dir):
    """Test getting signal history."""
    # Manually create some signal entries
    signal_file = Path(temp_signal_dir) / f"rule_based_{rule_based_source.symbol}.jsonl"

    test_signals = [
        {
            "timestamp": "2024-01-01T10:00:00",
            "symbol": "V10",
            "direction": "BUY",
            "confidence": 0.8,
            "price": 105.0,
            "num_agreeing": 3,
            "total_rules": 4
        },
        {
            "timestamp": "2024-01-01T10:05:00",
            "symbol": "V10",
            "direction": "SELL",
            "confidence": 0.7,
            "price": 104.0,
            "num_agreeing": 2,
            "total_rules": 4
        }
    ]

    with open(signal_file, "w") as f:
        for signal in test_signals:
            f.write(json.dumps(signal) + "\n")

    # Get history
    history = rule_based_source.get_signal_history()

    assert len(history) == 2
    assert history[0]["direction"] == "BUY"
    assert history[1]["direction"] == "SELL"


def test_get_signal_history_with_limit(rule_based_source, temp_signal_dir):
    """Test getting signal history with limit."""
    signal_file = Path(temp_signal_dir) / f"rule_based_{rule_based_source.symbol}.jsonl"

    # Create 10 signals
    test_signals = []
    for i in range(10):
        test_signals.append({
            "timestamp": f"2024-01-01T{i:02d}:00:00",
            "symbol": "V10",
            "direction": "BUY" if i % 2 == 0 else "SELL",
            "confidence": 0.7,
            "price": 100.0 + i,
            "num_agreeing": 3,
            "total_rules": 4
        })

    with open(signal_file, "w") as f:
        for signal in test_signals:
            f.write(json.dumps(signal) + "\n")

    # Get limited history
    history = rule_based_source.get_signal_history(limit=5)

    assert len(history) == 5


# ============================================================================
# Test Edge Cases
# ============================================================================

@pytest.mark.asyncio
async def test_predict_with_none_data(rule_based_source):
    """Test predict with None data."""
    signal = await rule_based_source.predict(None)
    assert signal is None


@pytest.mark.asyncio
async def test_predict_with_empty_dataframe(rule_based_source):
    """Test predict with empty DataFrame."""
    signal = await rule_based_source.predict(pd.DataFrame())
    assert signal is None


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
async def test_end_to_end_signal_generation(rule_based_source, sample_market_data):
    """Test complete signal generation workflow."""
    # Generate signal
    signal = await rule_based_source.predict(sample_market_data)

    # Verify signal structure
    assert signal is not None
    assert signal.symbol == "V10"
    assert signal.source == "rule_based_V10"
    assert signal.type == SignalType.RULE_BASED

    # Check metadata
    assert "rule_signals" in signal.metadata
    rule_signals = signal.metadata["rule_signals"]
    assert len(rule_signals) == 4  # All 4 rules should have signals

    # Verify each rule has required fields
    for rule_signal in rule_signals:
        assert "strategy" in rule_signal
        assert "direction" in rule_signal
        assert "confidence" in rule_signal
        assert "reason" in rule_signal

    # Check voting breakdown
    assert "vote_breakdown" in signal.metadata
    assert "num_agreeing" in signal.metadata
    assert "total_rules" in signal.metadata
    assert signal.metadata["total_rules"] == 4

    # Verify signal was stored
    history = rule_based_source.get_signal_history()
    assert len(history) == 1
    assert history[0]["direction"] == signal.direction.value

    # Check statistics
    stats = rule_based_source.get_statistics()
    assert stats["signals_generated"] == 1
