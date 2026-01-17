"""
Unit tests for Ensemble Signal System.

Tests the foundation classes for ensemble signal management including:
- Signal schema validation
- Signal source registration
- Signal generation and aggregation
- Ensemble manager functionality
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from app.services.ensemble_signals import (
    SignalDirection,
    SignalType,
    TradingSignal,
    SignalSource,
    EnsembleSignalManager,
    create_ensemble_manager
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def sample_signal():
    """Create a sample trading signal."""
    return TradingSignal(
        source="test_source",
        type=SignalType.ML_MODEL,
        direction=SignalDirection.BUY,
        confidence=0.85,
        timestamp=datetime.now(),
        features={"rsi": 30, "macd": 0.5},
        symbol="V10",
        price=10000.0,
        metadata={"model_version": "1.0"}
    )


@pytest.fixture
def ensemble_manager():
    """Create a fresh ensemble manager for each test."""
    return EnsembleSignalManager()


@pytest.fixture
def mock_signal_sources():
    """Create mock signal sources for testing."""
    sources = []

    # XGBoost source
    xgb_source = SignalSource(
        name="xgboost_v10",
        description="XGBoost model for V10",
        priority=3,
        enabled=True
    )
    sources.append(xgb_source)

    # Random Forest source
    rf_source = SignalSource(
        name="random_forest_v10",
        description="Random Forest model for V10",
        priority=2,
        enabled=True
    )
    sources.append(rf_source)

    # Rule-based source
    rule_source = SignalSource(
        name="rule_based_v10",
        description="Rule-based technical analysis",
        priority=1,
        enabled=True
    )
    sources.append(rule_source)

    return sources


# ============================================================================
# TradingSignal Tests
# ============================================================================

class TestTradingSignal:
    """Test TradingSignal dataclass."""

    def test_signal_creation(self, sample_signal):
        """Test creating a valid trading signal."""
        assert sample_signal.source == "test_source"
        assert sample_signal.type == SignalType.ML_MODEL
        assert sample_signal.direction == SignalDirection.BUY
        assert sample_signal.confidence == 0.85
        assert sample_signal.symbol == "V10"
        assert sample_signal.price == 10000.0
        assert "rsi" in sample_signal.features

    def test_signal_confidence_validation(self):
        """Test that confidence must be between 0 and 1."""
        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            TradingSignal(
                source="test",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=1.5,  # Invalid: > 1
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=10000.0
            )

        with pytest.raises(ValueError, match="Confidence must be between 0 and 1"):
            TradingSignal(
                source="test",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=-0.1,  # Invalid: < 0
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=10000.0
            )

    def test_signal_price_validation(self):
        """Test that price must be positive."""
        with pytest.raises(ValueError, match="Price must be positive"):
            TradingSignal(
                source="test",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.8,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=0.0  # Invalid: <= 0
            )

    def test_signal_to_dict(self, sample_signal):
        """Test converting signal to dictionary."""
        signal_dict = sample_signal.to_dict()

        assert signal_dict["source"] == "test_source"
        assert signal_dict["type"] == "ML_MODEL"
        assert signal_dict["direction"] == "BUY"
        assert signal_dict["confidence"] == 0.85
        assert signal_dict["symbol"] == "V10"
        assert signal_dict["price"] == 10000.0
        assert "rsi" in signal_dict["features"]

    def test_signal_from_dict(self, sample_signal):
        """Test creating signal from dictionary."""
        signal_dict = sample_signal.to_dict()
        restored_signal = TradingSignal.from_dict(signal_dict)

        assert restored_signal.source == sample_signal.source
        assert restored_signal.type == sample_signal.type
        assert restored_signal.direction == sample_signal.direction
        assert restored_signal.confidence == sample_signal.confidence
        assert restored_signal.symbol == sample_signal.symbol
        assert restored_signal.price == sample_signal.price

    def test_signal_direction_enum(self):
        """Test signal direction enum values."""
        assert SignalDirection.BUY.value == "BUY"
        assert SignalDirection.SELL.value == "SELL"
        assert SignalDirection.HOLD.value == "HOLD"

    def test_signal_type_enum(self):
        """Test signal type enum values."""
        assert SignalType.ML_MODEL.value == "ML_MODEL"
        assert SignalType.RULE_BASED.value == "RULE_BASED"
        assert SignalType.ENSEMBLE.value == "ENSEMBLE"


# ============================================================================
# SignalSource Tests
# ============================================================================

class TestSignalSource:
    """Test SignalSource dataclass."""

    def test_signal_source_creation(self):
        """Test creating a signal source."""
        source = SignalSource(
            name="xgboost_v10",
            description="XGBoost for V10",
            priority=3,
            enabled=True
        )

        assert source.name == "xgboost_v10"
        assert source.description == "XGBoost for V10"
        assert source.priority == 3
        assert source.enabled is True

    def test_signal_source_hash(self):
        """Test that signal source is hashable."""
        source1 = SignalSource(name="test", description="Test")
        source2 = SignalSource(name="test", description="Test")

        # Should be able to create a set
        source_set = {source1, source2}
        assert len(source_set) == 1  # Same hash, so only one


# ============================================================================
# EnsembleSignalManager Tests
# ============================================================================

class TestEnsembleSignalManager:
    """Test EnsembleSignalManager class."""

    def test_manager_initialization(self, ensemble_manager):
        """Test manager initialization."""
        assert ensemble_manager is not None
        assert len(ensemble_manager._signal_sources) == 0
        assert len(ensemble_manager._signal_cache) == 0

    def test_register_signal_source(self, ensemble_manager):
        """Test registering a signal source."""
        source = SignalSource(
            name="xgboost_v10",
            description="XGBoost for V10"
        )

        ensemble_manager.register_signal_source(source)

        assert "xgboost_v10" in ensemble_manager._signal_sources
        assert ensemble_manager.get_signal_source("xgboost_v10") == source

    def test_register_duplicate_source(self, ensemble_manager):
        """Test that registering duplicate source raises error."""
        source = SignalSource(name="test", description="Test")
        ensemble_manager.register_signal_source(source)

        with pytest.raises(ValueError, match="already registered"):
            ensemble_manager.register_signal_source(source)

    def test_unregister_signal_source(self, ensemble_manager):
        """Test unregistering a signal source."""
        source = SignalSource(name="test", description="Test")
        ensemble_manager.register_signal_source(source)

        ensemble_manager.unregister_signal_source("test")

        assert "test" not in ensemble_manager._signal_sources
        assert ensemble_manager.get_signal_source("test") is None

    def test_unregister_nonexistent_source(self, ensemble_manager):
        """Test that unregistering nonexistent source raises error."""
        with pytest.raises(KeyError, match="not found"):
            ensemble_manager.unregister_signal_source("nonexistent")

    def test_list_signal_sources(self, ensemble_manager, mock_signal_sources):
        """Test listing all signal sources."""
        for source in mock_signal_sources:
            ensemble_manager.register_signal_source(source)

        all_sources = ensemble_manager.list_signal_sources()
        enabled_sources = ensemble_manager.list_signal_sources(enabled_only=True)

        assert len(all_sources) == 3
        assert len(enabled_sources) == 3

    def test_list_signal_sources_sorted_by_priority(self, ensemble_manager, mock_signal_sources):
        """Test that sources are sorted by priority (descending)."""
        for source in mock_signal_sources:
            ensemble_manager.register_signal_source(source)

        sources = ensemble_manager.list_signal_sources()

        # Should be sorted by priority descending
        assert sources[0].name == "xgboost_v10"  # priority 3
        assert sources[1].name == "random_forest_v10"  # priority 2
        assert sources[2].name == "rule_based_v10"  # priority 1

    def test_enable_disable_signal_source(self, ensemble_manager):
        """Test enabling and disabling signal sources."""
        source = SignalSource(name="test", description="Test", enabled=True)
        ensemble_manager.register_signal_source(source)

        # Disable
        ensemble_manager.disable_signal_source("test")
        assert ensemble_manager.get_signal_source("test").enabled is False

        # Enable
        ensemble_manager.enable_signal_source("test")
        assert ensemble_manager.get_signal_source("test").enabled is True

    def test_enable_disable_nonexistent_source(self, ensemble_manager):
        """Test enabling/disabling nonexistent source raises error."""
        with pytest.raises(KeyError, match="not found"):
            ensemble_manager.enable_signal_source("nonexistent")

        with pytest.raises(KeyError, match="not found"):
            ensemble_manager.disable_signal_source("nonexistent")


# ============================================================================
# Signal Validation Tests
# ============================================================================

class TestSignalValidation:
    """Test signal validation functionality."""

    def test_validate_valid_signal(self, ensemble_manager, sample_signal):
        """Test validating a valid signal."""
        assert ensemble_manager.validate_signal(sample_signal) is True

    def test_validate_signal_wrong_type(self, ensemble_manager):
        """Test that non-TradingSignal objects fail validation."""
        assert ensemble_manager.validate_signal("not a signal") is False
        assert ensemble_manager.validate_signal({"direction": "BUY"}) is False

    def test_validate_signal_missing_source(self, ensemble_manager):
        """Test that signal without source fails validation."""
        signal = TradingSignal(
            source="",  # Empty source
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.8,
            timestamp=datetime.now(),
            features={},
            symbol="V10",
            price=10000.0
        )

        assert ensemble_manager.validate_signal(signal) is False

    def test_validate_signal_missing_symbol(self, ensemble_manager):
        """Test that signal without symbol fails validation."""
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.8,
            timestamp=datetime.now(),
            features={},
            symbol="",  # Empty symbol
            price=10000.0
        )

        assert ensemble_manager.validate_signal(signal) is False

    def test_validate_signal_invalid_direction(self, ensemble_manager):
        """Test that signal with invalid direction fails validation."""
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.8,
            timestamp=datetime.now(),
            features={},
            symbol="V10",
            price=10000.0
        )

        # Manually corrupt the direction for testing
        signal.direction = "INVALID"  # type: ignore

        assert ensemble_manager.validate_signal(signal) is False

    def test_validate_signal_confidence_out_of_range(self, ensemble_manager):
        """Test that signal with invalid confidence fails validation."""
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.8,
            timestamp=datetime.now(),
            features={},
            symbol="V10",
            price=10000.0
        )

        # Manually corrupt the confidence for testing
        signal.confidence = 1.5

        assert ensemble_manager.validate_signal(signal) is False

    def test_validate_signal_invalid_price(self, ensemble_manager):
        """Test that signal with invalid price fails validation."""
        # Create valid signal first, then corrupt for testing
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.8,
            timestamp=datetime.now(),
            features={},
            symbol="V10",
            price=10000.0  # Valid price
        )

        # Manually corrupt the price for testing validation
        signal.price = 0.0  # type: ignore

        assert ensemble_manager.validate_signal(signal) is False

    def test_validate_signal_future_timestamp(self, ensemble_manager):
        """Test that signal with future timestamp fails validation."""
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.8,
            timestamp=datetime.now() + timedelta(hours=1),  # Future
            features={},
            symbol="V10",
            price=10000.0
        )

        assert ensemble_manager.validate_signal(signal) is False

    def test_validate_signal_old_timestamp(self, ensemble_manager):
        """Test that old signal fails validation."""
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.8,
            timestamp=datetime.now() - timedelta(hours=2),  # Too old (> 1 hour)
            features={},
            symbol="V10",
            price=10000.0
        )

        assert ensemble_manager.validate_signal(signal) is False

    def test_validate_signal_recent_timestamp(self, ensemble_manager):
        """Test that recent signal passes validation."""
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.8,
            timestamp=datetime.now() - timedelta(minutes=30),  # Recent enough
            features={},
            symbol="V10",
            price=10000.0
        )

        assert ensemble_manager.validate_signal(signal) is True


# ============================================================================
# Signal Aggregation Tests
# ============================================================================

class TestSignalAggregation:
    """Test signal aggregation functionality."""

    def test_aggregate_empty_signals(self, ensemble_manager):
        """Test aggregating empty signal list."""
        result = ensemble_manager.aggregate_signals([])

        assert result["direction"] == SignalDirection.HOLD
        assert result["confidence"] == 0.0
        assert result["agreement"] == 0.0
        assert result["num_signals"] == 0

    def test_aggregate_single_signal(self, ensemble_manager, sample_signal):
        """Test aggregating single signal."""
        result = ensemble_manager.aggregate_signals([sample_signal])

        assert result["direction"] == SignalDirection.BUY
        assert result["confidence"] == 0.85
        assert result["agreement"] == 1.0
        assert result["num_signals"] == 1

    def test_aggregate_majority_vote_buy(self, ensemble_manager):
        """Test majority vote with BUY consensus."""
        signals = [
            TradingSignal(
                source="source1",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.8,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=10000.0
            ),
            TradingSignal(
                source="source2",
                type=SignalType.RULE_BASED,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=10000.0
            ),
            TradingSignal(
                source="source3",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.SELL,
                confidence=0.6,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=10000.0
            )
        ]

        result = ensemble_manager.aggregate_signals(signals, method="majority_vote")

        assert result["direction"] == SignalDirection.BUY
        assert result["vote_count"]["BUY"] == 2
        assert result["vote_count"]["SELL"] == 1
        assert result["agreement"] == 2/3

    def test_aggregate_majority_vote_sell(self, ensemble_manager):
        """Test majority vote with SELL consensus."""
        signals = [
            TradingSignal(
                source="source1",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.SELL,
                confidence=0.9,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=10000.0
            ),
            TradingSignal(
                source="source2",
                type=SignalType.RULE_BASED,
                direction=SignalDirection.SELL,
                confidence=0.8,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=10000.0
            ),
            TradingSignal(
                source="source3",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.HOLD,
                confidence=0.5,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=10000.0
            )
        ]

        result = ensemble_manager.aggregate_signals(signals, method="majority_vote")

        assert result["direction"] == SignalDirection.SELL
        assert result["vote_count"]["SELL"] == 2
        assert result["vote_count"]["HOLD"] == 1

    def test_aggregate_unanimous_agreement(self, ensemble_manager):
        """Test unanimous agreement."""
        signals = [
            TradingSignal(
                source="source1",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.8,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=10000.0
            ),
            TradingSignal(
                source="source2",
                type=SignalType.RULE_BASED,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=10000.0
            ),
            TradingSignal(
                source="source3",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.9,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=10000.0
            )
        ]

        result = ensemble_manager.aggregate_signals(signals, method="unanimous")

        assert result["direction"] == SignalDirection.BUY
        assert result["agreement"] == 1.0

    def test_aggregate_no_unanimous_agreement(self, ensemble_manager):
        """Test unanimous method without full agreement."""
        signals = [
            TradingSignal(
                source="source1",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.8,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=10000.0
            ),
            TradingSignal(
                source="source2",
                type=SignalType.RULE_BASED,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=10000.0
            ),
            TradingSignal(
                source="source3",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.SELL,
                confidence=0.6,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=10000.0
            )
        ]

        result = ensemble_manager.aggregate_signals(signals, method="unanimous")

        assert result["direction"] == SignalDirection.HOLD
        assert result["agreement"] == 0.0

    def test_aggregate_invalid_method(self, ensemble_manager, sample_signal):
        """Test that invalid aggregation method raises error."""
        with pytest.raises(ValueError, match="Unknown aggregation method"):
            ensemble_manager.aggregate_signals([sample_signal], method="invalid")


# ============================================================================
# Statistics Tests
# ============================================================================

class TestStatistics:
    """Test statistics and monitoring functionality."""

    def test_get_statistics_empty_manager(self, ensemble_manager):
        """Test getting statistics from empty manager."""
        stats = ensemble_manager.get_statistics()

        assert stats["total_sources"] == 0
        assert stats["enabled_sources"] == 0
        assert stats["disabled_sources"] == 0
        assert stats["cached_signals"] == 0
        assert len(stats["sources"]) == 0

    def test_get_statistics_with_sources(self, ensemble_manager, mock_signal_sources):
        """Test getting statistics with registered sources."""
        for source in mock_signal_sources:
            ensemble_manager.register_signal_source(source)

        # Disable one source
        ensemble_manager.disable_signal_source("rule_based_v10")

        stats = ensemble_manager.get_statistics()

        assert stats["total_sources"] == 3
        assert stats["enabled_sources"] == 2
        assert stats["disabled_sources"] == 1
        assert len(stats["sources"]) == 3


# ============================================================================
# Cache Tests
# ============================================================================

class TestCache:
    """Test signal caching functionality."""

    def test_clear_all_cache(self, ensemble_manager):
        """Test clearing all signal cache."""
        ensemble_manager._signal_cache["V10_signals"] = []
        ensemble_manager._signal_cache["V25_signals"] = []

        ensemble_manager.clear_signal_cache()

        assert len(ensemble_manager._signal_cache) == 0

    def test_clear_symbol_cache(self, ensemble_manager):
        """Test clearing cache for specific symbol."""
        ensemble_manager._signal_cache["V10_signals"] = []
        ensemble_manager._signal_cache["V25_signals"] = []

        ensemble_manager.clear_signal_cache(symbol="V10")

        assert "V10_signals" not in ensemble_manager._signal_cache
        assert "V25_signals" in ensemble_manager._signal_cache


# ============================================================================
# Mock Signal Source Tests
# ============================================================================

class TestMockSignalSources:
    """Test ensemble manager with mock signal sources."""

    def test_get_all_signals_with_mock_sources(self, ensemble_manager):
        """Test fetching signals from mock sources."""
        # Create mock signal generator
        def mock_generator(symbol: str):
            return TradingSignal(
                source="mock",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.8,
                timestamp=datetime.now(),
                features={},
                symbol=symbol,
                price=10000.0
            )

        # Register mock source
        source = SignalSource(
            name="mock_source",
            description="Mock signal source",
            signal_generator=mock_generator
        )
        ensemble_manager.register_signal_source(source)

        # Fetch signals
        import asyncio
        signals = asyncio.run(ensemble_manager.get_all_signals("V10"))

        assert len(signals) == 1
        assert signals[0].source == "mock"
        assert signals[0].direction == SignalDirection.BUY

    def test_get_all_signals_disabled_source(self, ensemble_manager):
        """Test that disabled sources are not called."""
        call_count = 0

        def mock_generator(symbol: str):
            nonlocal call_count
            call_count += 1
            return TradingSignal(
                source="mock",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.8,
                timestamp=datetime.now(),
                features={},
                symbol=symbol,
                price=10000.0
            )

        # Register and disable source
        source = SignalSource(
            name="mock_source",
            description="Mock signal source",
            enabled=False,
            signal_generator=mock_generator
        )
        ensemble_manager.register_signal_source(source)

        # Fetch signals
        import asyncio
        signals = asyncio.run(ensemble_manager.get_all_signals("V10"))

        assert len(signals) == 0
        assert call_count == 0  # Should not be called

    def test_get_all_signals_with_cache(self, ensemble_manager):
        """Test signal caching."""
        call_count = 0

        def mock_generator(symbol: str):
            nonlocal call_count
            call_count += 1
            return TradingSignal(
                source="mock",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.8,
                timestamp=datetime.now(),
                features={},
                symbol=symbol,
                price=10000.0
            )

        # Register mock source
        source = SignalSource(
            name="mock_source",
            description="Mock signal source",
            signal_generator=mock_generator
        )
        ensemble_manager.register_signal_source(source)

        # Fetch signals twice
        import asyncio
        signals1 = asyncio.run(ensemble_manager.get_all_signals("V10", use_cache=True))
        signals2 = asyncio.run(ensemble_manager.get_all_signals("V10", use_cache=True))

        # Should only call generator once due to cache
        assert call_count == 1
        assert len(signals1) == 1
        assert len(signals2) == 1


# ============================================================================
# Convenience Functions Tests
# ============================================================================

class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_ensemble_manager(self):
        """Test creating ensemble manager."""
        manager = create_ensemble_manager()

        assert isinstance(manager, EnsembleSignalManager)
        assert manager is not None
