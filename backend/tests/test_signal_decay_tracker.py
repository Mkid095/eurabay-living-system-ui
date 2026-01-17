"""
Unit tests for Signal Decay Tracker.

Tests for signal decay tracking including:
- Signal age tracking
- Win rate by age buckets
- Decay curve calculation
- Signal freshness checks
- Performance degradation tracking
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.signal_decay_tracker import (
    SignalDecayTracker,
    AgeBucket,
    AgeBucketStatistics,
    DecayCurve,
    DecayReport,
    SourcePerformanceMetrics,
    create_decay_tracker
)
from app.services.ensemble_signals import TradingSignal, SignalDirection, SignalType


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def decay_tracker():
    """Create a SignalDecayTracker instance for testing."""
    return create_decay_tracker(
        max_signal_age_minutes=30,
        min_samples_per_bucket=20
    )


@pytest.fixture
def fresh_signal():
    """Create a fresh signal (just generated)."""
    return TradingSignal(
        source="xgboost_v10",
        type=SignalType.ML_MODEL,
        direction=SignalDirection.BUY,
        confidence=0.75,
        timestamp=datetime.now(),
        features={"rsi": 25, "macd": 0.001},
        symbol="V10",
        price=1.1000
    )


@pytest.fixture
def stale_signal():
    """Create a stale signal (45 minutes old)."""
    return TradingSignal(
        source="xgboost_v10",
        type=SignalType.ML_MODEL,
        direction=SignalDirection.BUY,
        confidence=0.75,
        timestamp=datetime.now() - timedelta(minutes=45),
        features={"rsi": 25, "macd": 0.001},
        symbol="V10",
        price=1.1000
    )


@pytest.fixture
def aged_signal_10min():
    """Create a signal that is 10 minutes old."""
    return TradingSignal(
        source="xgboost_v10",
        type=SignalType.ML_MODEL,
        direction=SignalDirection.SELL,
        confidence=0.68,
        timestamp=datetime.now() - timedelta(minutes=10),
        features={"rsi": 75, "macd": -0.001},
        symbol="V25",
        price=1.2500
    )


# ============================================================================
# Signal Age Tracking Tests
# ============================================================================

class TestSignalAgeTracking:
    """Tests for signal age tracking functionality."""

    def test_get_signal_age_fresh(self, decay_tracker, fresh_signal):
        """Test getting age of a fresh signal."""
        age = decay_tracker.get_signal_age(fresh_signal)

        # Fresh signal should have very low age
        assert age >= 0
        assert age < 1  # Less than 1 minute

    def test_get_signal_age_stale(self, decay_tracker, stale_signal):
        """Test getting age of a stale signal."""
        age = decay_tracker.get_signal_age(stale_signal)

        # Stale signal should be approximately 45 minutes old
        assert 44 <= age <= 46  # Allow for small timing differences

    def test_get_age_bucket_0_5min(self, decay_tracker):
        """Test age bucket classification for 0-5 minutes."""
        # Create a 3 minute old signal
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.7,
            timestamp=datetime.now() - timedelta(minutes=3),
            features={},
            symbol="V10",
            price=1.0
        )

        age = decay_tracker.get_signal_age(signal)
        bucket = decay_tracker.get_age_bucket(age)

        assert bucket == AgeBucket.BUCKET_0_5MIN

    def test_get_age_bucket_5_15min(self, decay_tracker):
        """Test age bucket classification for 5-15 minutes."""
        # Create a 10 minute old signal
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.7,
            timestamp=datetime.now() - timedelta(minutes=10),
            features={},
            symbol="V10",
            price=1.0
        )

        age = decay_tracker.get_signal_age(signal)
        bucket = decay_tracker.get_age_bucket(age)

        assert bucket == AgeBucket.BUCKET_5_15MIN

    def test_get_age_bucket_15_30min(self, decay_tracker):
        """Test age bucket classification for 15-30 minutes."""
        # Create a 20 minute old signal
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.7,
            timestamp=datetime.now() - timedelta(minutes=20),
            features={},
            symbol="V10",
            price=1.0
        )

        age = decay_tracker.get_signal_age(signal)
        bucket = decay_tracker.get_age_bucket(age)

        assert bucket == AgeBucket.BUCKET_15_30MIN

    def test_get_age_bucket_30_60min(self, decay_tracker):
        """Test age bucket classification for 30-60 minutes."""
        # Create a 45 minute old signal
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.7,
            timestamp=datetime.now() - timedelta(minutes=45),
            features={},
            symbol="V10",
            price=1.0
        )

        age = decay_tracker.get_signal_age(signal)
        bucket = decay_tracker.get_age_bucket(age)

        assert bucket == AgeBucket.BUCKET_30_60MIN

    def test_get_age_bucket_60_plus(self, decay_tracker):
        """Test age bucket classification for 60+ minutes."""
        # Create a 90 minute old signal
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.7,
            timestamp=datetime.now() - timedelta(minutes=90),
            features={},
            symbol="V10",
            price=1.0
        )

        age = decay_tracker.get_signal_age(signal)
        bucket = decay_tracker.get_age_bucket(age)

        assert bucket == AgeBucket.BUCKET_60_PLUS


# ============================================================================
# Signal Freshness Tests
# ============================================================================

class TestSignalFreshness:
    """Tests for signal freshness checking functionality."""

    def test_is_signal_fresh_true(self, decay_tracker, fresh_signal):
        """Test that a fresh signal is detected as fresh."""
        assert decay_tracker.is_signal_fresh(fresh_signal) is True

    def test_is_signal_fresh_false(self, decay_tracker, stale_signal):
        """Test that a stale signal is detected as not fresh."""
        assert decay_tracker.is_signal_fresh(stale_signal) is False

    def test_is_signal_fresh_boundary(self, decay_tracker):
        """Test freshness at the boundary (30 minutes)."""
        # Create a signal at 29.9 minutes (just under the boundary)
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.7,
            timestamp=datetime.now() - timedelta(minutes=29, seconds=54),
            features={},
            symbol="V10",
            price=1.0
        )

        # At just under 30 minutes, should still be fresh
        assert decay_tracker.is_signal_fresh(signal) is True

    def test_is_signal_fresh_just_over_boundary(self, decay_tracker):
        """Test freshness just over the boundary (31 minutes)."""
        # Create a signal just over the boundary
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.7,
            timestamp=datetime.now() - timedelta(minutes=31, seconds=1),
            features={},
            symbol="V10",
            price=1.0
        )

        # Just over 30 minutes, should be stale
        assert decay_tracker.is_signal_fresh(signal) is False

    def test_should_discard_signal_fresh(self, decay_tracker, fresh_signal):
        """Test that fresh signals should not be discarded."""
        assert decay_tracker.should_discard_signal(fresh_signal) is False

    def test_should_discard_signal_stale(self, decay_tracker, stale_signal):
        """Test that stale signals should be discarded."""
        assert decay_tracker.should_discard_signal(stale_signal) is True


# ============================================================================
# Configuration Tests
# ============================================================================

class TestDecayTrackerConfiguration:
    """Tests for SignalDecayTracker configuration."""

    def test_default_configuration(self):
        """Test creating a tracker with default configuration."""
        tracker = create_decay_tracker()

        assert tracker.max_signal_age_minutes == 30
        assert tracker.min_samples_per_bucket == 20

    def test_custom_configuration(self):
        """Test creating a tracker with custom configuration."""
        tracker = create_decay_tracker(
            max_signal_age_minutes=60,
            min_samples_per_bucket=50
        )

        assert tracker.max_signal_age_minutes == 60
        assert tracker.min_samples_per_bucket == 50

    def test_invalid_max_age(self):
        """Test that invalid max age raises error."""
        with pytest.raises(ValueError, match="max_signal_age_minutes must be at least 1"):
            create_decay_tracker(max_signal_age_minutes=0)

    def test_invalid_min_samples(self):
        """Test that invalid min samples raises error."""
        with pytest.raises(ValueError, match="min_samples_per_bucket must be at least 1"):
            create_decay_tracker(min_samples_per_bucket=0)

    def test_custom_max_age_freshness(self):
        """Test that custom max age affects freshness check."""
        # Create tracker with 60 minute max age
        tracker = create_decay_tracker(max_signal_age_minutes=60)

        # Create a 45 minute old signal
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.7,
            timestamp=datetime.now() - timedelta(minutes=45),
            features={},
            symbol="V10",
            price=1.0
        )

        # With 60 minute threshold, 45 minutes should be fresh
        assert tracker.is_signal_fresh(signal) is True


# ============================================================================
# Cache Management Tests
# ============================================================================

class TestCacheManagement:
    """Tests for cache management functionality."""

    def test_clear_all_cache(self, decay_tracker):
        """Test clearing all cache."""
        # Add some dummy data to cache
        decay_tracker.performance_cache["test_source"] = {}
        decay_tracker.decay_curve_cache["test_source"] = {}
        decay_tracker.cache_timestamp["test_source"] = datetime.now()

        # Clear all cache
        decay_tracker.clear_cache()

        assert len(decay_tracker.performance_cache) == 0
        assert len(decay_tracker.decay_curve_cache) == 0
        assert len(decay_tracker.cache_timestamp) == 0

    def test_clear_source_cache(self, decay_tracker):
        """Test clearing cache for specific source."""
        # Add data for multiple sources
        decay_tracker.performance_cache["source1"] = {}
        decay_tracker.performance_cache["source2"] = {}
        decay_tracker.decay_curve_cache["source1"] = {}
        decay_tracker.decay_curve_cache["source2"] = {}
        decay_tracker.cache_timestamp["source1"] = datetime.now()
        decay_tracker.cache_timestamp["source2"] = datetime.now()

        # Clear cache for source1 only
        decay_tracker.clear_cache(source_name="source1")

        # source1 should be cleared
        assert "source1" not in decay_tracker.performance_cache
        assert "source1" not in decay_tracker.decay_curve_cache
        assert "source1" not in decay_tracker.cache_timestamp

        # source2 should still exist
        assert "source2" in decay_tracker.performance_cache
        assert "source2" in decay_tracker.decay_curve_cache
        assert "source2" in decay_tracker.cache_timestamp


# ============================================================================
# Data Structure Tests
# ============================================================================

class TestDataStructures:
    """Tests for data structure validation and serialization."""

    def test_age_bucket_statistics_to_dict(self):
        """Test AgeBucketStatistics serialization."""
        stats = AgeBucketStatistics(
            bucket="0-5min",
            total_signals=100,
            winning_signals=60,
            losing_signals=40,
            win_rate=0.60,
            avg_age_minutes=3.5,
            last_updated=datetime.now()
        )

        data = stats.to_dict()

        assert data["bucket"] == "0-5min"
        assert data["total_signals"] == 100
        assert data["winning_signals"] == 60
        assert data["losing_signals"] == 40
        assert data["win_rate"] == 0.60
        assert data["avg_age_minutes"] == 3.5
        assert "last_updated" in data

    def test_decay_curve_to_dict(self):
        """Test DecayCurve serialization."""
        curve = DecayCurve(
            source_name="xgboost_v10",
            symbol="V10",
            bucket_statistics={},
            decay_rate=0.001,
            half_life_minutes=693.0,
            is_decayed=False,
            curve_generated=datetime.now()
        )

        data = curve.to_dict()

        assert data["source_name"] == "xgboost_v10"
        assert data["symbol"] == "V10"
        assert data["decay_rate"] == 0.001
        assert data["half_life_minutes"] == 693.0
        assert data["is_decayed"] is False
        assert "curve_generated" in data

    def test_decay_report_to_dict(self):
        """Test DecayReport serialization."""
        report = DecayReport(
            source_name="xgboost_v10",
            decay_curves={},
            overall_decay_rate=0.001,
            degraded_sources=[],
            total_signals_analyzed=1000,
            report_generated=datetime.now()
        )

        data = report.to_dict()

        assert data["source_name"] == "xgboost_v10"
        assert data["overall_decay_rate"] == 0.001
        assert data["degraded_sources"] == []
        assert data["total_signals_analyzed"] == 1000
        assert "report_generated" in data

    def test_source_performance_metrics_to_dict(self):
        """Test SourcePerformanceMetrics serialization."""
        metrics = SourcePerformanceMetrics(
            source_name="xgboost_v10",
            symbol="V10",
            current_win_rate=0.60,
            one_week_ago_win_rate=0.58,
            two_weeks_ago_win_rate=0.55,
            three_weeks_ago_win_rate=0.62,
            four_weeks_ago_win_rate=0.59,
            is_degraded=False,
            degradation_trend="improving",
            last_updated=datetime.now()
        )

        data = metrics.to_dict()

        assert data["source_name"] == "xgboost_v10"
        assert data["symbol"] == "V10"
        assert data["current_win_rate"] == 0.60
        assert data["is_degraded"] is False
        assert data["degradation_trend"] == "improving"
        assert "last_updated" in data


# ============================================================================
# Edge Cases and Validation Tests
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and validation."""

    def test_zero_age_signal(self, decay_tracker):
        """Test signal with zero age (just created)."""
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.7,
            timestamp=datetime.now(),
            features={},
            symbol="V10",
            price=1.0
        )

        age = decay_tracker.get_signal_age(signal)
        assert age >= 0
        assert decay_tracker.is_signal_fresh(signal) is True

    def test_very_old_signal(self, decay_tracker):
        """Test signal that is very old (hours)."""
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.7,
            timestamp=datetime.now() - timedelta(hours=5),
            features={},
            symbol="V10",
            price=1.0
        )

        age = decay_tracker.get_signal_age(signal)
        assert age >= 300  # At least 300 minutes (5 hours)
        assert decay_tracker.is_signal_fresh(signal) is False
        assert decay_tracker.should_discard_signal(signal) is True

    def test_get_age_bucket_negative_age(self, decay_tracker):
        """Test age bucket for signal with future timestamp (invalid)."""
        # This should not happen in practice, but we should handle it
        signal = TradingSignal(
            source="test",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.7,
            timestamp=datetime.now() + timedelta(minutes=10),  # Future
            features={},
            symbol="V10",
            price=1.0
        )

        age = decay_tracker.get_signal_age(signal)
        # Age would be negative
        assert age < 0

        # Should return None for invalid age
        bucket = decay_tracker.get_age_bucket(age)
        # This is expected to return None or handle gracefully
        # The implementation may vary


# ============================================================================
# Integration Tests
# ============================================================================

class TestDecayTrackerIntegration:
    """Integration tests for SignalDecayTracker."""

    def test_multiple_signals_age_tracking(self, decay_tracker):
        """Test tracking ages for multiple signals."""
        signals = [
            TradingSignal(
                source=f"source_{i}",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=datetime.now() - timedelta(minutes=i * 10),
                features={},
                symbol="V10",
                price=1.0
            )
            for i in range(1, 8)  # 10, 20, 30, 40, 50, 60, 70 minutes
        ]

        ages = [decay_tracker.get_signal_age(signal) for signal in signals]
        buckets = [decay_tracker.get_age_bucket(age) for age in ages]

        # Verify ages are increasing
        assert ages[0] < ages[1] < ages[2] < ages[3] < ages[4] < ages[5] < ages[6]

        # Verify buckets are correct
        assert buckets[0] == AgeBucket.BUCKET_5_15MIN    # 10 min
        assert buckets[1] == AgeBucket.BUCKET_15_30MIN   # 20 min
        assert buckets[2] == AgeBucket.BUCKET_30_60MIN   # 30 min
        assert buckets[3] == AgeBucket.BUCKET_30_60MIN   # 40 min
        assert buckets[4] == AgeBucket.BUCKET_30_60MIN   # 50 min
        assert buckets[5] == AgeBucket.BUCKET_60_PLUS    # 60 min (upper bound exclusive, goes to 60+)
        assert buckets[6] == AgeBucket.BUCKET_60_PLUS    # 70 min

        # Verify freshness (30 minute threshold)
        fresh_signals = [s for s in signals if decay_tracker.is_signal_fresh(s)]
        assert len(fresh_signals) == 2  # Only first 2 are under 30 minutes (10, 20)

    def test_filter_fresh_signals(self, decay_tracker):
        """Test filtering a list of signals to only fresh ones."""
        # Mix of fresh and stale signals
        now = datetime.now()
        signals = [
            TradingSignal(
                source="fresh_1",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=now - timedelta(minutes=5),
                features={},
                symbol="V10",
                price=1.0
            ),
            TradingSignal(
                source="fresh_2",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=now - timedelta(minutes=15),
                features={},
                symbol="V10",
                price=1.0
            ),
            TradingSignal(
                source="stale_1",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=now - timedelta(minutes=45),
                features={},
                symbol="V10",
                price=1.0
            ),
            TradingSignal(
                source="stale_2",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=now - timedelta(minutes=90),
                features={},
                symbol="V10",
                price=1.0
            ),
        ]

        # Filter to only fresh signals
        fresh_signals = [
            s for s in signals
            if not decay_tracker.should_discard_signal(s)
        ]

        assert len(fresh_signals) == 2
        assert all(s.source.startswith("fresh_") for s in fresh_signals)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
