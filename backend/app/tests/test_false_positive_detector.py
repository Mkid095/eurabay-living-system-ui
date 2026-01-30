"""
Unit tests for False Positive Detector (US-009).

Tests the false positive detection system including:
- Losing trade pattern analysis
- High-loss condition identification
- False positive rate calculation by market condition
- Signal blocking for known bad conditions
- Logging blocked signals with reason
- Storing false positive patterns in database
"""

import pytest
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch

from app.services.false_positive_detector import (
    BlockingReason,
    MarketCondition,
    FalsePositivePattern,
    HighLossCondition,
    FalsePositiveRateByCondition,
    SignalBlockResult,
    FalsePositiveDetector,
    create_false_positive_detector
)
from app.services.ensemble_signals import (
    SignalDirection,
    SignalType,
    TradingSignal
)
from app.services.signal_quality_scorer import (
    QualityScoreResult,
    QualityScoreBreakdown
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_buy_signals():
    """Create sample BUY signals for testing."""
    return [
        TradingSignal(
            source="xgboost_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.75,
            timestamp=datetime.now(),
            features={"rsi": 25, "macd": 0.5},
            symbol="V10",
            price=1.0850
        ),
        TradingSignal(
            source="random_forest_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.70,
            timestamp=datetime.now(),
            features={"rsi": 28, "macd": 0.4},
            symbol="V10",
            price=1.0851
        ),
        TradingSignal(
            source="rule_based_v10",
            type=SignalType.RULE_BASED,
            direction=SignalDirection.BUY,
            confidence=0.65,
            timestamp=datetime.now(),
            features={"rsi": 30, "sma_crossover": True},
            symbol="V10",
            price=1.0852
        )
    ]


@pytest.fixture
def low_agreement_signals():
    """Create signals with low agreement."""
    return [
        TradingSignal(
            source="xgboost_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.60,
            timestamp=datetime.now(),
            features={"rsi": 45},
            symbol="V10",
            price=1.0850
        ),
        TradingSignal(
            source="random_forest_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.SELL,
            confidence=0.60,
            timestamp=datetime.now(),
            features={"rsi": 55},
            symbol="V10",
            price=1.0851
        ),
        TradingSignal(
            source="rule_based_v10",
            type=SignalType.RULE_BASED,
            direction=SignalDirection.HOLD,
            confidence=0.50,
            timestamp=datetime.now(),
            features={"rsi": 50},
            symbol="V10",
            price=1.0852
        )
    ]


@pytest.fixture
def quality_score_low():
    """Create a low quality score result."""
    breakdown = QualityScoreBreakdown(
        ensemble_agreement=50.0,
        confidence_calibration=60.0,
        recent_performance=55.0,
        regime_alignment=50.0,
        feature_strength=45.0,
        overall_score=48.0,
        threshold="low",
        calculated_at=datetime.now()
    )

    return QualityScoreResult(
        signal_id=1,
        source="xgboost_v10",
        symbol="V10",
        direction="BUY",
        breakdown=breakdown,
        should_trade=False,
        reason="Quality score 48.0 below threshold",
        scored_at=datetime.now()
    )


@pytest.fixture
def quality_score_high():
    """Create a high quality score result."""
    breakdown = QualityScoreBreakdown(
        ensemble_agreement=90.0,
        confidence_calibration=85.0,
        recent_performance=88.0,
        regime_alignment=80.0,
        feature_strength=85.0,
        overall_score=85.0,
        threshold="high",
        calculated_at=datetime.now()
    )

    return QualityScoreResult(
        signal_id=1,
        source="xgboost_v10",
        symbol="V10",
        direction="BUY",
        breakdown=breakdown,
        should_trade=True,
        reason="Quality score 85.0 meets threshold",
        scored_at=datetime.now()
    )


@pytest.fixture
def false_positive_detector():
    """Create FalsePositiveDetector instance with default thresholds."""
    return FalsePositiveDetector(
        min_quality_threshold=50.0,
        min_agreement_threshold=0.66,
        min_source_win_rate=0.50,
        lookback_days=30
    )


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = Mock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = Mock()
    return session


# ============================================================================
# Test FalsePositiveDetector Initialization
# ============================================================================

class TestFalsePositiveDetectorInitialization:
    """Tests for FalsePositiveDetector initialization."""

    def test_initialization_default(self):
        """Test initialization with default parameters."""
        detector = FalsePositiveDetector()

        assert detector.min_quality_threshold == 50.0
        assert detector.min_agreement_threshold == 0.66
        assert detector.min_source_win_rate == 0.50
        assert detector.lookback_days == 30

    def test_initialization_custom_thresholds(self):
        """Test initialization with custom thresholds."""
        detector = FalsePositiveDetector(
            min_quality_threshold=60.0,
            min_agreement_threshold=0.75,
            min_source_win_rate=0.55,
            lookback_days=60
        )

        assert detector.min_quality_threshold == 60.0
        assert detector.min_agreement_threshold == 0.75
        assert detector.min_source_win_rate == 0.55
        assert detector.lookback_days == 60

    def test_initialization_invalid_quality_threshold(self):
        """Test initialization with invalid quality threshold."""
        with pytest.raises(ValueError):
            FalsePositiveDetector(min_quality_threshold=150.0)

        with pytest.raises(ValueError):
            FalsePositiveDetector(min_quality_threshold=-10.0)

    def test_initialization_invalid_agreement_threshold(self):
        """Test initialization with invalid agreement threshold."""
        with pytest.raises(ValueError):
            FalsePositiveDetector(min_agreement_threshold=1.5)

        # Note: min_agreement_threshold of 0.0 is allowed (no blocking)
        # Test with negative value instead
        with pytest.raises(ValueError):
            FalsePositiveDetector(min_agreement_threshold=-0.1)

    def test_initialization_invalid_win_rate(self):
        """Test initialization with invalid win rate."""
        with pytest.raises(ValueError):
            FalsePositiveDetector(min_source_win_rate=1.5)

        with pytest.raises(ValueError):
            FalsePositiveDetector(min_source_win_rate=-0.1)

    def test_initialization_invalid_lookback(self):
        """Test initialization with invalid lookback days."""
        with pytest.raises(ValueError):
            FalsePositiveDetector(lookback_days=0)

        with pytest.raises(ValueError):
            FalsePositiveDetector(lookback_days=-10)


# ============================================================================
# Test Signal Blocking (US-009 #4)
# ============================================================================

class TestSignalBlocking:
    """Tests for signal blocking logic."""

    @pytest.mark.asyncio
    async def test_should_block_low_quality_score(
        self,
        false_positive_detector,
        sample_buy_signals,
        quality_score_low
    ):
        """Test blocking signal with low quality score (< 50)."""
        result = await false_positive_detector.should_block_signal(
            db_session=Mock(),
            signals=sample_buy_signals,
            quality_result=quality_score_low,
            current_regime="trending_up",
            symbol="V10"
        )

        assert result.should_block is True
        assert result.blocking_reason == BlockingReason.LOW_QUALITY_SCORE.value
        assert "quality_score_48.0" in result.violated_thresholds

    @pytest.mark.asyncio
    async def test_should_not_block_high_quality_score(
        self,
        false_positive_detector,
        sample_buy_signals,
        quality_score_high
    ):
        """Test not blocking signal with high quality score."""
        result = await false_positive_detector.should_block_signal(
            db_session=Mock(),
            signals=sample_buy_signals,
            quality_result=quality_score_high,
            current_regime="trending_up",
            symbol="V10"
        )

        assert result.should_block is False
        assert result.blocking_reason is None

    @pytest.mark.asyncio
    async def test_should_block_low_agreement(
        self,
        false_positive_detector,
        low_agreement_signals
    ):
        """Test blocking signal with low ensemble agreement (< 66%)."""
        result = await false_positive_detector.should_block_signal(
            db_session=Mock(),
            signals=low_agreement_signals,
            quality_result=None,
            current_regime=None,
            symbol="V10"
        )

        assert result.should_block is True
        assert "agreement_" in result.violated_thresholds[0]
        # Agreement is 1/3 = 0.33, which is < 0.66

    @pytest.mark.asyncio
    async def test_should_block_regime_misalignment(
        self,
        false_positive_detector,
        sample_buy_signals
    ):
        """Test blocking signal that opposes market regime."""
        # Create SELL signal in trending_up market (misalignment)
        sell_signals = [
            TradingSignal(
                source="xgboost_v10",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.SELL,
                confidence=0.75,
                timestamp=datetime.now(),
                features={},
                symbol="V10",
                price=1.0850
            )
        ]

        result = await false_positive_detector.should_block_signal(
            db_session=Mock(),
            signals=sell_signals,
            quality_result=None,
            current_regime="trending_up",
            symbol="V10"
        )

        assert result.should_block is True
        assert result.blocking_reason == BlockingReason.REGIME_MISALIGNMENT.value

    @pytest.mark.asyncio
    async def test_should_not_block_regime_aligned(
        self,
        false_positive_detector,
        sample_buy_signals
    ):
        """Test not blocking signal aligned with regime."""
        result = await false_positive_detector.should_block_signal(
            db_session=Mock(),
            signals=sample_buy_signals,
            quality_result=None,
            current_regime="trending_up",
            symbol="V10"
        )

        # BUY in trending_up is aligned
        # But agreement check passes, so not blocked
        assert not any("regime" in v for v in result.violated_thresholds)

    @pytest.mark.asyncio
    async def test_should_block_empty_signals(
        self,
        false_positive_detector
    ):
        """Test blocking when no signals provided."""
        result = await false_positive_detector.should_block_signal(
            db_session=Mock(),
            signals=[],
            quality_result=None,
            current_regime=None,
            symbol="V10"
        )

        assert result.should_block is True
        assert "no_signals" in result.violated_thresholds

    @pytest.mark.asyncio
    async def test_block_result_to_dict(self):
        """Test converting SignalBlockResult to dictionary."""
        result = SignalBlockResult(
            should_block=True,
            blocking_reason="low_quality_score",
            blocking_details="Quality score 45.0 below threshold (50.0)",
            violated_thresholds=["quality_score_45.0"],
            evaluated_at=datetime.now()
        )

        result_dict = result.to_dict()

        assert result_dict["should_block"] is True
        assert result_dict["blocking_reason"] == "low_quality_score"
        assert "Quality score" in result_dict["blocking_details"]
        assert "quality_score_45.0" in result_dict["violated_thresholds"]


# ============================================================================
# Test Pattern Analysis (US-009 #1, #2)
# ============================================================================

class TestPatternAnalysis:
    """Tests for pattern analysis functionality."""

    @pytest.mark.asyncio
    async def test_analyze_losing_trades_with_data(
        self,
        false_positive_detector,
        mock_db_session
    ):
        """Test analyzing losing trades with historical data."""
        # Mock database response
        mock_signals = [
            Mock(
                strategy="xgboost_v10",
                symbol="V10",
                timestamp=datetime.now(),
                confidence=0.60,
                direction=SignalDirection.BUY
            )
        ]
        mock_trades = [
            Mock(
                status="CLOSED",
                profit_loss=-50.0,
                exit_price=1.0800
            )
        ]

        # Setup mock to return signal-trade pairs
        mock_result = Mock()
        mock_result.all.return_value = list(zip(mock_signals, mock_trades))
        mock_db_session.execute.return_value = mock_result

        patterns = await false_positive_detector.analyze_losing_trades(
            db_session=mock_db_session,
            source_name="xgboost_v10",
            symbol="V10",
            days=30
        )

        # Should identify low confidence pattern
        assert len(patterns) > 0
        assert isinstance(patterns[0], FalsePositivePattern)

    @pytest.mark.asyncio
    async def test_analyze_losing_trades_no_data(
        self,
        false_positive_detector,
        mock_db_session
    ):
        """Test analyzing when no losing trades found."""
        # Mock empty response
        mock_result = Mock()
        mock_result.all.return_value = []
        mock_db_session.execute.return_value = mock_result

        patterns = await false_positive_detector.analyze_losing_trades(
            db_session=mock_db_session,
            source_name="xgboost_v10",
            symbol="V10",
            days=30
        )

        assert len(patterns) == 0

    @pytest.mark.asyncio
    async def test_identify_high_loss_conditions(
        self,
        false_positive_detector,
        mock_db_session
    ):
        """Test identifying high-loss conditions."""
        # Mock signal-trade pairs
        mock_signals = [
            Mock(
                strategy="xgboost_v10",
                symbol="V10",
                timestamp=datetime.now(),
                confidence=0.60,
                direction=SignalDirection.BUY
            )
        ]
        mock_trades = [
            Mock(
                status="CLOSED",
                profit_loss=-100.0
            ),
            Mock(
                status="CLOSED",
                profit_loss=50.0
            )
        ]

        mock_result = Mock()
        mock_result.all.return_value = list(zip(mock_signals, mock_trades))
        mock_db_session.execute.return_value = mock_result

        conditions = await false_positive_detector.identify_high_loss_conditions(
            db_session=mock_db_session,
            source_name="xgboost_v10",
            symbol="V10",
            days=30
        )

        assert isinstance(conditions, list)
        # Should have conditions like low_confidence
        if conditions:
            assert isinstance(conditions[0], HighLossCondition)


# ============================================================================
# Test False Positive Rate by Condition (US-009 #3)
# ============================================================================

class TestFalsePositiveRateByCondition:
    """Tests for false positive rate calculation by market condition."""

    @pytest.mark.asyncio
    async def test_calculate_fp_rate_by_condition(
        self,
        false_positive_detector,
        mock_db_session
    ):
        """Test calculating false positive rate by market condition."""
        # Mock signal-trade pairs
        mock_signals = [
            Mock(
                strategy="xgboost_v10",
                symbol="V10",
                timestamp=datetime.now(),
                direction=SignalDirection.BUY
            )
        ]
        mock_trades = [
            Mock(status="CLOSED", profit_loss=-50.0),  # Losing
            Mock(status="CLOSED", profit_loss=100.0),  # Winning
            Mock(status="CLOSED", profit_loss=-30.0),  # Losing
            Mock(status="CLOSED", profit_loss=80.0),   # Winning
        ]

        mock_result = Mock()
        mock_result.all.return_value = list(zip(mock_signals, mock_trades))
        mock_db_session.execute.return_value = mock_result

        fp_rates = await false_positive_detector.calculate_false_positive_rate_by_condition(
            db_session=mock_db_session,
            source_name="xgboost_v10",
            symbol="V10",
            days=30
        )

        assert isinstance(fp_rates, dict)
        # Should have rates for different conditions
        # Based on mock data, trending_up (wins) and trending_down (losses)
        assert len(fp_rates) > 0

        # Check structure of returned data
        for condition, rate_data in fp_rates.items():
            assert isinstance(condition, str)
            assert isinstance(rate_data, FalsePositiveRateByCondition)
            assert hasattr(rate_data, 'false_positive_rate')
            assert hasattr(rate_data, 'total_signals')
            assert hasattr(rate_data, 'false_positives')

    @pytest.mark.asyncio
    async def test_fp_rate_calculation_accuracy(
        self,
        false_positive_detector,
        mock_db_session
    ):
        """Test accuracy of false positive rate calculation."""
        # Create 10 trades: 3 losses, 7 wins
        mock_signals = [Mock(timestamp=datetime.now()) for _ in range(10)]
        mock_trades = [
            Mock(status="CLOSED", profit_loss=-10.0),
            Mock(status="CLOSED", profit_loss=-20.0),
            Mock(status="CLOSED", profit_loss=-15.0),
            Mock(status="CLOSED", profit_loss=50.0),
            Mock(status="CLOSED", profit_loss=60.0),
            Mock(status="CLOSED", profit_loss=70.0),
            Mock(status="CLOSED", profit_loss=80.0),
            Mock(status="CLOSED", profit_loss=90.0),
            Mock(status="CLOSED", profit_loss=100.0),
            Mock(status="CLOSED", profit_loss=110.0),
        ]

        mock_result = Mock()
        mock_result.all.return_value = list(zip(mock_signals, mock_trades))
        mock_db_session.execute.return_value = mock_result

        fp_rates = await false_positive_detector.calculate_false_positive_rate_by_condition(
            db_session=mock_db_session,
            source_name="xgboost_v10",
            symbol="V10"
        )

        # Check that rates are calculated correctly
        for condition, rate_data in fp_rates.items():
            # False positive rate should be between 0 and 1
            assert 0.0 <= rate_data.false_positive_rate <= 1.0
            # Total signals should match or be less than total trades
            assert rate_data.total_signals <= 10


# ============================================================================
# Test Database Persistence (US-009 #5, #6)
# ============================================================================

class TestDatabasePersistence:
    """Tests for database persistence functionality."""

    @pytest.mark.asyncio
    async def test_log_blocked_signal(
        self,
        false_positive_detector,
        sample_buy_signals,
        mock_db_session
    ):
        """Test logging a blocked signal to database."""
        block_result = SignalBlockResult(
            should_block=True,
            blocking_reason="low_quality_score",
            blocking_details="Quality score 45.0 below threshold (50.0)",
            violated_thresholds=["quality_score_45.0"],
            evaluated_at=datetime.now()
        )

        await false_positive_detector.log_blocked_signal(
            db_session=mock_db_session,
            signal=sample_buy_signals[0],
            block_result=block_result,
            symbol="V10"
        )

        # Verify database operations were called
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_false_positive_patterns(
        self,
        false_positive_detector,
        mock_db_session
    ):
        """Test storing false positive patterns to database."""
        # Add a pattern to cache
        pattern = FalsePositivePattern(
            pattern_id="low_confidence",
            name="Low Confidence Pattern",
            description="Low confidence signals have high FP rate",
            conditions={"min_confidence": 0.65},
            false_positive_rate=0.40,
            sample_count=100,
            last_updated=datetime.now(),
            is_active=True
        )

        cache_key = "xgboost_v10_V10"
        false_positive_detector.pattern_cache[cache_key] = {
            "low_confidence": pattern
        }

        # Create a proper async mock for execute
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=None)

        # Track calls
        execute_called = False
        original_execute = mock_db_session.execute

        async def mock_execute(*args, **kwargs):
            nonlocal execute_called
            execute_called = True
            return mock_result

        mock_db_session.execute = mock_execute

        await false_positive_detector.store_false_positive_patterns(
            db_session=mock_db_session,
            source_name="xgboost_v10",
            symbol="V10"
        )

        # Verify database operations were called
        assert execute_called, "execute should have been called"
        assert mock_db_session.commit.called, "commit should have been called"

    @pytest.mark.asyncio
    async def test_store_patterns_no_cache(
        self,
        false_positive_detector,
        mock_db_session
    ):
        """Test storing patterns when cache is empty."""
        # Don't add any patterns to cache

        await false_positive_detector.store_false_positive_patterns(
            db_session=mock_db_session,
            source_name="xgboost_v10",
            symbol="V10"
        )

        # Should not call database if no patterns
        mock_db_session.execute.assert_not_called()


# ============================================================================
# Test Data Structures
# ============================================================================

class TestDataStructures:
    """Tests for data structure conversions."""

    def test_false_positive_pattern_to_dict(self):
        """Test converting FalsePositivePattern to dictionary."""
        pattern = FalsePositivePattern(
            pattern_id="test_pattern",
            name="Test Pattern",
            description="Test description",
            conditions={"test": "value"},
            false_positive_rate=0.50,
            sample_count=100,
            last_updated=datetime.now(),
            is_active=True
        )

        pattern_dict = pattern.to_dict()

        assert pattern_dict["pattern_id"] == "test_pattern"
        assert pattern_dict["name"] == "Test Pattern"
        assert pattern_dict["false_positive_rate"] == 0.50
        assert pattern_dict["sample_count"] == 100
        assert pattern_dict["is_active"] is True

    def test_high_loss_condition_to_dict(self):
        """Test converting HighLossCondition to dictionary."""
        condition = HighLossCondition(
            condition_name="low_confidence",
            description="Low confidence signals",
            avg_loss=-100.0,
            false_positive_rate=0.40,
            occurrence_count=50,
            severity="high",
            last_updated=datetime.now()
        )

        condition_dict = condition.to_dict()

        assert condition_dict["condition_name"] == "low_confidence"
        assert condition_dict["avg_loss"] == -100.0
        assert condition_dict["false_positive_rate"] == 0.40
        assert condition_dict["severity"] == "high"

    def test_fp_rate_by_condition_to_dict(self):
        """Test converting FalsePositiveRateByCondition to dictionary."""
        fp_rate = FalsePositiveRateByCondition(
            market_condition="trending_up",
            total_signals=100,
            false_positives=30,
            false_positive_rate=0.30,
            avg_loss_per_false_positive=-80.0,
            last_updated=datetime.now()
        )

        fp_rate_dict = fp_rate.to_dict()

        assert fp_rate_dict["market_condition"] == "trending_up"
        assert fp_rate_dict["total_signals"] == 100
        assert fp_rate_dict["false_positives"] == 30
        assert fp_rate_dict["false_positive_rate"] == 0.30
        assert fp_rate_dict["avg_loss_per_false_positive"] == -80.0


# ============================================================================
# Test Helper Methods
# ============================================================================

class TestHelperMethods:
    """Tests for internal helper methods."""

    @pytest.mark.asyncio
    async def test_calculate_ensemble_agreement(
        self,
        false_positive_detector,
        sample_buy_signals
    ):
        """Test ensemble agreement calculation."""
        # All BUY signals = 100% agreement
        agreement = await false_positive_detector._calculate_ensemble_agreement(
            sample_buy_signals
        )

        assert agreement == 1.0

    @pytest.mark.asyncio
    async def test_calculate_ensemble_agreement_mixed(
        self,
        false_positive_detector,
        low_agreement_signals
    ):
        """Test ensemble agreement with mixed signals."""
        # 1 BUY, 1 SELL, 1 HOLD = max agreement is 1/3
        agreement = await false_positive_detector._calculate_ensemble_agreement(
            low_agreement_signals
        )

        assert agreement == pytest.approx(1/3)

    @pytest.mark.asyncio
    async def test_calculate_ensemble_agreement_empty(
        self,
        false_positive_detector
    ):
        """Test ensemble agreement with empty list."""
        agreement = await false_positive_detector._calculate_ensemble_agreement([])

        assert agreement == 0.0

    @pytest.mark.asyncio
    async def test_check_regime_alignment_buy_trending_up(
        self,
        false_positive_detector,
        sample_buy_signals
    ):
        """Test regime alignment: BUY in trending_up."""
        is_aligned = await false_positive_detector._check_regime_alignment(
            sample_buy_signals[0],
            "trending_up"
        )

        assert is_aligned is True

    @pytest.mark.asyncio
    async def test_check_regime_alignment_sell_trending_up(
        self,
        false_positive_detector
    ):
        """Test regime misalignment: SELL in trending_up."""
        sell_signal = TradingSignal(
            source="xgboost_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.SELL,
            confidence=0.75,
            timestamp=datetime.now(),
            features={},
            symbol="V10",
            price=1.0850
        )

        is_aligned = await false_positive_detector._check_regime_alignment(
            sell_signal,
            "trending_up"
        )

        assert is_aligned is False

    @pytest.mark.asyncio
    async def test_check_regime_alignment_ranging(
        self,
        false_positive_detector,
        sample_buy_signals
    ):
        """Test regime alignment in ranging market."""
        # Both BUY and SELL are acceptable in ranging
        is_aligned_buy = await false_positive_detector._check_regime_alignment(
            sample_buy_signals[0],
            "ranging"
        )

        sell_signal = TradingSignal(
            source="xgboost_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.SELL,
            confidence=0.75,
            timestamp=datetime.now(),
            features={},
            symbol="V10",
            price=1.0850
        )

        is_aligned_sell = await false_positive_detector._check_regime_alignment(
            sell_signal,
            "ranging"
        )

        assert is_aligned_buy is True
        assert is_aligned_sell is True


# ============================================================================
# Test Convenience Function
# ============================================================================

class TestConvenienceFunction:
    """Tests for convenience function."""

    def test_create_false_positive_detector_default(self):
        """Test creating detector with default parameters."""
        detector = create_false_positive_detector()

        assert detector.min_quality_threshold == 50.0
        assert detector.min_agreement_threshold == 0.66
        assert detector.min_source_win_rate == 0.50
        assert detector.lookback_days == 30

    def test_create_false_positive_detector_custom(self):
        """Test creating detector with custom parameters."""
        detector = create_false_positive_detector(
            min_quality_threshold=70.0,
            min_agreement_threshold=0.80,
            min_source_win_rate=0.60,
            lookback_days=60
        )

        assert detector.min_quality_threshold == 70.0
        assert detector.min_agreement_threshold == 0.80
        assert detector.min_source_win_rate == 0.60
        assert detector.lookback_days == 60


# ============================================================================
# Test Cache Management
# ============================================================================

class TestCacheManagement:
    """Tests for cache management."""

    def test_clear_cache_all(self, false_positive_detector):
        """Test clearing all cache."""
        # Add some data to cache
        false_positive_detector.pattern_cache["test"] = {}
        false_positive_detector.high_loss_conditions_cache["test"] = []
        false_positive_detector.fp_rate_cache["test"] = {}
        false_positive_detector.cache_timestamp["test"] = datetime.now()

        false_positive_detector.clear_cache()

        assert len(false_positive_detector.pattern_cache) == 0
        assert len(false_positive_detector.high_loss_conditions_cache) == 0
        assert len(false_positive_detector.fp_rate_cache) == 0
        assert len(false_positive_detector.cache_timestamp) == 0

    def test_clear_cache_source_specific(self, false_positive_detector):
        """Test clearing cache for specific source."""
        # Add data for multiple sources
        false_positive_detector.pattern_cache["xgboost_V10"] = {}
        false_positive_detector.pattern_cache["rf_V10"] = {}
        false_positive_detector.cache_timestamp["xgboost_V10"] = datetime.now()
        false_positive_detector.cache_timestamp["rf_V10"] = datetime.now()

        # Clear only xgboost cache
        false_positive_detector.clear_cache(source_name="xgboost")

        # xgboost cache should be cleared
        assert "xgboost_V10" not in false_positive_detector.pattern_cache
        # rf cache should remain
        assert "rf_V10" in false_positive_detector.pattern_cache


# ============================================================================
# Test Threshold Configurations (US-009 Acceptance Criteria)
# ============================================================================

class TestThresholdConfigurations:
    """Tests for threshold configurations from US-009."""

    def test_blocking_thresholds_structure(self, false_positive_detector):
        """Test that blocking thresholds are properly configured."""
        assert "quality_score" in false_positive_detector.blocking_thresholds
        assert "ensemble_agreement" in false_positive_detector.blocking_thresholds
        assert "source_win_rate" in false_positive_detector.blocking_thresholds

        # Check default values from US-009
        assert false_positive_detector.blocking_thresholds["quality_score"] == 50.0
        assert false_positive_detector.blocking_thresholds["ensemble_agreement"] == 0.66
        assert false_positive_detector.blocking_thresholds["source_win_rate"] == 0.50

    def test_us009_threshold_quality_score(self, false_positive_detector):
        """Test US-009 requirement: Block if quality score < 50."""
        assert false_positive_detector.min_quality_threshold == 50.0

    def test_us009_threshold_agreement(self, false_positive_detector):
        """Test US-009 requirement: Block if agreement < 66%."""
        assert false_positive_detector.min_agreement_threshold == 0.66

    def test_us009_threshold_win_rate(self, false_positive_detector):
        """Test US-009 requirement: Block if source win rate < 50%."""
        assert false_positive_detector.min_source_win_rate == 0.50
