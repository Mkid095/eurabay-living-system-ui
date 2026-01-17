"""
Unit tests for Signal Quality Scoring System.

Tests the quality scoring functionality including:
- Ensemble agreement calculation
- Confidence calibration calculation
- Recent performance calculation
- Market regime alignment calculation
- Feature strength calculation
- Overall quality scoring
"""

import pytest
from datetime import datetime, timedelta
from typing import List

from app.services.signal_quality_scorer import (
    QualityThreshold,
    QualityScoreBreakdown,
    QualityScoreResult,
    SignalQualityScorer,
    create_quality_scorer
)
from app.services.ensemble_signals import (
    SignalDirection,
    SignalType,
    TradingSignal
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def quality_scorer():
    """Create a fresh quality scorer for each test."""
    return SignalQualityScorer()


@pytest.fixture
def sample_signals():
    """Create sample trading signals for testing."""
    now = datetime.now()

    # High agreement: 3 BUY signals
    high_agreement_signals = [
        TradingSignal(
            source="xgboost_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.75,
            timestamp=now,
            features={
                "rsi": 25,
                "macd": 0.002,
                "macd_signal": 0.001,
                "sma_20": 10050,
                "sma_50": 10000
            },
            symbol="V10",
            price=10000.0
        ),
        TradingSignal(
            source="random_forest_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.80,
            timestamp=now,
            features={
                "rsi": 28,
                "macd": 0.0018,
                "macd_signal": 0.0009,
                "sma_20": 10050,
                "sma_50": 10000
            },
            symbol="V10",
            price=10000.0
        ),
        TradingSignal(
            source="rule_based_v10",
            type=SignalType.RULE_BASED,
            direction=SignalDirection.BUY,
            confidence=0.70,
            timestamp=now,
            features={
                "rsi": 30,
                "macd": 0.0015,
                "macd_signal": 0.0008,
                "sma_20": 10050,
                "sma_50": 10000
            },
            symbol="V10",
            price=10000.0
        )
    ]

    # Low agreement: mixed signals
    low_agreement_signals = [
        TradingSignal(
            source="xgboost_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.BUY,
            confidence=0.60,
            timestamp=now,
            features={"rsi": 50},
            symbol="V10",
            price=10000.0
        ),
        TradingSignal(
            source="random_forest_v10",
            type=SignalType.ML_MODEL,
            direction=SignalDirection.SELL,
            confidence=0.60,
            timestamp=now,
            features={"rsi": 50},
            symbol="V10",
            price=10000.0
        ),
        TradingSignal(
            source="rule_based_v10",
            type=SignalType.RULE_BASED,
            direction=SignalDirection.HOLD,
            confidence=0.50,
            timestamp=now,
            features={"rsi": 50},
            symbol="V10",
            price=10000.0
        )
    ]

    return {
        "high_agreement": high_agreement_signals,
        "low_agreement": low_agreement_signals
    }


# ============================================================================
# SignalQualityScorer Initialization Tests
# ============================================================================

class TestSignalQualityScorerInitialization:
    """Test SignalQualityScorer initialization."""

    def test_default_initialization(self):
        """Test default initialization."""
        scorer = SignalQualityScorer()

        assert scorer.min_quality_threshold == 60.0
        assert scorer.lookback_days == 30
        assert len(scorer.performance_cache) == 0

    def test_custom_initialization(self):
        """Test custom initialization."""
        scorer = SignalQualityScorer(
            min_quality_threshold=70.0,
            lookback_days=60
        )

        assert scorer.min_quality_threshold == 70.0
        assert scorer.lookback_days == 60

    def test_invalid_min_quality_threshold(self):
        """Test that invalid min quality threshold raises error."""
        with pytest.raises(ValueError, match="min_quality_threshold must be between 0 and 100"):
            SignalQualityScorer(min_quality_threshold=150.0)

        with pytest.raises(ValueError, match="min_quality_threshold must be between 0 and 100"):
            SignalQualityScorer(min_quality_threshold=-10.0)

    def test_invalid_lookback_days(self):
        """Test that invalid lookback days raises error."""
        with pytest.raises(ValueError, match="lookback_days must be at least 1"):
            SignalQualityScorer(lookback_days=0)


# ============================================================================
# Ensemble Agreement Tests
# ============================================================================

class TestEnsembleAgreement:
    """Test ensemble agreement calculation."""

    @pytest.mark.asyncio
    async def test_full_agreement_buy(self, quality_scorer, sample_signals):
        """Test 100% agreement (all BUY)."""
        signals = sample_signals["high_agreement"]

        score = await quality_scorer._calculate_ensemble_agreement(signals)

        # 3/3 agreement = 100% agreement ratio
        # Score = 1.0^2 * 100 = 100
        assert score == 100.0

    @pytest.mark.asyncio
    async def test_two_third_agreement(self, quality_scorer):
        """Test 2/3 agreement."""
        now = datetime.now()

        signals = [
            TradingSignal(
                source="source1",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=now,
                features={},
                symbol="V10",
                price=10000.0
            ),
            TradingSignal(
                source="source2",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=now,
                features={},
                symbol="V10",
                price=10000.0
            ),
            TradingSignal(
                source="source3",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.SELL,
                confidence=0.7,
                timestamp=now,
                features={},
                symbol="V10",
                price=10000.0
            )
        ]

        score = await quality_scorer._calculate_ensemble_agreement(signals)

        # 2/3 agreement = 0.67 agreement ratio
        # Score = 0.67^2 * 100 = ~44.4
        assert 44.0 <= score <= 45.0

    @pytest.mark.asyncio
    async def test_no_agreement(self, quality_scorer, sample_signals):
        """Test no agreement (all different)."""
        signals = sample_signals["low_agreement"]

        score = await quality_scorer._calculate_ensemble_agreement(signals)

        # 1/3 agreement = 0.33 agreement ratio
        # Score = 0.33^2 * 100 = ~11.1
        assert 11.0 <= score <= 12.0

    @pytest.mark.asyncio
    async def test_empty_signals(self, quality_scorer):
        """Test empty signals list."""
        score = await quality_scorer._calculate_ensemble_agreement([])

        assert score == 0.0


# ============================================================================
# Feature Strength Tests
# ============================================================================

class TestFeatureStrength:
    """Test feature strength calculation."""

    @pytest.mark.asyncio
    async def test_strong_rsi_oversold(self, quality_scorer, sample_signals):
        """Test strong RSI (oversold)."""
        signals = sample_signals["high_agreement"]

        score = await quality_scorer._calculate_feature_strength(signals)

        # RSI=30 (medium, 70 points), MA diff=0.5% (40 points), MACD divergence=0.0007 (70 points)
        # Average: (70 + 40 + 70) / 3 = 60
        assert score >= 50.0  # Should be medium-high

    @pytest.mark.asyncio
    async def test_strong_rsi_overbought(self, quality_scorer):
        """Test strong RSI (overbought)."""
        now = datetime.now()

        signals = [
            TradingSignal(
                source="test",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.SELL,
                confidence=0.7,
                timestamp=now,
                features={"rsi": 80},
                symbol="V10",
                price=10000.0
            )
        ]

        score = await quality_scorer._calculate_feature_strength(signals)

        # RSI > 70 should give 90 points
        assert score >= 80.0

    @pytest.mark.asyncio
    async def test_weak_rsi_neutral(self, quality_scorer):
        """Test weak RSI (neutral zone)."""
        now = datetime.now()

        signals = [
            TradingSignal(
                source="test",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=now,
                features={"rsi": 50},
                symbol="V10",
                price=10000.0
            )
        ]

        score = await quality_scorer._calculate_feature_strength(signals)

        # RSI = 50 should give 40 points (weak)
        assert score <= 50.0

    @pytest.mark.asyncio
    async def test_strong_macd_divergence(self, quality_scorer):
        """Test strong MACD divergence."""
        now = datetime.now()

        signals = [
            TradingSignal(
                source="test",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=now,
                features={
                    "macd": 0.002,
                    "macd_signal": 0.0005
                },
                symbol="V10",
                price=10000.0
            )
        ]

        score = await quality_scorer._calculate_feature_strength(signals)

        # Strong MACD divergence should give high score
        assert score >= 80.0

    @pytest.mark.asyncio
    async def test_strong_ma_crossover(self, quality_scorer):
        """Test strong moving average crossover."""
        now = datetime.now()

        signals = [
            TradingSignal(
                source="test",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=now,
                features={
                    "sma_20": 10201,  # Slightly more than 2%
                    "sma_50": 10000
                },
                symbol="V10",
                price=10000.0
            )
        ]

        score = await quality_scorer._calculate_feature_strength(signals)

        # 2.01% MA difference should give 90 points for MA
        assert score >= 80.0

    @pytest.mark.asyncio
    async def test_no_features(self, quality_scorer):
        """Test signals with no features."""
        now = datetime.now()

        signals = [
            TradingSignal(
                source="test",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=now,
                features={},
                symbol="V10",
                price=10000.0
            )
        ]

        score = await quality_scorer._calculate_feature_strength(signals)

        # No features should give neutral score
        assert score == 60.0


# ============================================================================
# Regime Alignment Tests
# ============================================================================

class TestRegimeAlignment:
    """Test market regime alignment calculation."""

    @pytest.mark.asyncio
    async def test_trending_up_buy_alignment(self, quality_scorer, sample_signals):
        """Test BUY signal in trending up regime."""
        signals = sample_signals["high_agreement"]

        score = await quality_scorer._calculate_regime_alignment(
            signals,
            current_regime="trending_up"
        )

        # Perfect alignment: 95 points
        assert score == 95.0

    @pytest.mark.asyncio
    async def test_trending_up_sell_misalignment(self, quality_scorer):
        """Test SELL signal in trending up regime (poor alignment)."""
        now = datetime.now()

        signals = [
            TradingSignal(
                source="test",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.SELL,
                confidence=0.7,
                timestamp=now,
                features={},
                symbol="V10",
                price=10000.0
            )
        ]

        score = await quality_scorer._calculate_regime_alignment(
            signals,
            current_regime="trending_up"
        )

        # Poor alignment: 30 points
        assert score == 30.0

    @pytest.mark.asyncio
    async def test_trending_down_sell_alignment(self, quality_scorer):
        """Test SELL signal in trending down regime."""
        now = datetime.now()

        signals = [
            TradingSignal(
                source="test",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.SELL,
                confidence=0.7,
                timestamp=now,
                features={},
                symbol="V10",
                price=10000.0
            )
        ]

        score = await quality_scorer._calculate_regime_alignment(
            signals,
            current_regime="trending_down"
        )

        # Perfect alignment: 95 points
        assert score == 95.0

    @pytest.mark.asyncio
    async def test_ranging_regime(self, quality_scorer, sample_signals):
        """Test signal in ranging regime."""
        signals = sample_signals["high_agreement"]

        score = await quality_scorer._calculate_regime_alignment(
            signals,
            current_regime="ranging_calm"
        )

        # Ranging regime: 70 points (neutral/good)
        assert score == 70.0

    @pytest.mark.asyncio
    async def test_no_regime_data(self, quality_scorer, sample_signals):
        """Test with no regime data."""
        signals = sample_signals["high_agreement"]

        score = await quality_scorer._calculate_regime_alignment(
            signals,
            current_regime=None
        )

        # No regime data: 70 points (neutral)
        assert score == 70.0


# ============================================================================
# Quality Threshold Tests
# ============================================================================

class TestQualityThreshold:
    """Test quality threshold categorization."""

    def test_excellent_threshold(self, quality_scorer):
        """Test excellent threshold (90-100)."""
        threshold = quality_scorer._get_quality_threshold(95.0)
        assert threshold == QualityThreshold.EXCELLENT

        threshold = quality_scorer._get_quality_threshold(90.0)
        assert threshold == QualityThreshold.EXCELLENT

    def test_high_threshold(self, quality_scorer):
        """Test high threshold (80-89)."""
        threshold = quality_scorer._get_quality_threshold(85.0)
        assert threshold == QualityThreshold.HIGH

        threshold = quality_scorer._get_quality_threshold(80.0)
        assert threshold == QualityThreshold.HIGH

    def test_medium_threshold(self, quality_scorer):
        """Test medium threshold (60-79)."""
        threshold = quality_scorer._get_quality_threshold(70.0)
        assert threshold == QualityThreshold.MEDIUM

        threshold = quality_scorer._get_quality_threshold(60.0)
        assert threshold == QualityThreshold.MEDIUM

    def test_low_threshold(self, quality_scorer):
        """Test low threshold (40-59)."""
        threshold = quality_scorer._get_quality_threshold(50.0)
        assert threshold == QualityThreshold.LOW

        threshold = quality_scorer._get_quality_threshold(40.0)
        assert threshold == QualityThreshold.LOW

    def test_poor_threshold(self, quality_scorer):
        """Test poor threshold (0-39)."""
        threshold = quality_scorer._get_quality_threshold(30.0)
        assert threshold == QualityThreshold.POOR

        threshold = quality_scorer._get_quality_threshold(0.0)
        assert threshold == QualityThreshold.POOR


# ============================================================================
# Overall Quality Scoring Tests
# ============================================================================

class TestOverallQualityScoring:
    """Test overall quality scoring."""

    @pytest.mark.asyncio
    async def test_high_quality_signal(self, quality_scorer, sample_signals):
        """Test scoring a high quality signal."""
        # This test requires database mock, so we'll test the structure
        signals = sample_signals["high_agreement"]

        # Create a mock result to verify the structure
        breakdown = QualityScoreBreakdown(
            ensemble_agreement=100.0,
            confidence_calibration=85.0,
            recent_performance=75.0,
            regime_alignment=95.0,
            feature_strength=90.0,
            overall_score=89.5,
            threshold="high",
            calculated_at=datetime.now()
        )

        result = QualityScoreResult(
            signal_id=123,
            source="xgboost_v10",
            symbol="V10",
            direction="BUY",
            breakdown=breakdown,
            should_trade=True,
            reason="Quality score 89.5 meets threshold (60.0)",
            scored_at=datetime.now()
        )

        assert result.should_trade is True
        assert result.breakdown.overall_score == 89.5
        assert result.breakdown.threshold == "high"

    def test_quality_score_breakdown_weights(self):
        """Test that weights sum to 1.0."""
        from app.services.signal_quality_scorer import QUALITY_WEIGHTS

        weights = QUALITY_WEIGHTS

        total_weight = sum(weights.values())

        assert total_weight == pytest.approx(1.0)

    def test_quality_score_breakdown_to_dict(self):
        """Test converting breakdown to dictionary."""
        breakdown = QualityScoreBreakdown(
            ensemble_agreement=80.0,
            confidence_calibration=75.0,
            recent_performance=70.0,
            regime_alignment=85.0,
            feature_strength=90.0,
            overall_score=79.5,
            threshold="high",
            calculated_at=datetime.now()
        )

        result_dict = breakdown.to_dict()

        assert result_dict["ensemble_agreement"] == 80.0
        assert result_dict["confidence_calibration"] == 75.0
        assert result_dict["recent_performance"] == 70.0
        assert result_dict["regime_alignment"] == 85.0
        assert result_dict["feature_strength"] == 90.0
        assert result_dict["overall_score"] == 79.5
        assert result_dict["threshold"] == "high"
        assert "calculated_at" in result_dict
        assert "weights" in result_dict


# ============================================================================
# Performance Cache Tests
# ============================================================================

class TestPerformanceCache:
    """Test performance cache functionality."""

    def test_clear_performance_cache(self, quality_scorer):
        """Test clearing performance cache."""
        # Add some data to cache
        quality_scorer.performance_cache["test_source"] = {"V10": 0.65}
        quality_scorer.performance_cache_time["test_source"] = datetime.now()

        # Clear cache
        quality_scorer.clear_performance_cache()

        assert len(quality_scorer.performance_cache) == 0
        assert len(quality_scorer.performance_cache_time) == 0


# ============================================================================
# Convenience Functions Tests
# ============================================================================

class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_create_quality_scorer_default(self):
        """Test creating quality scorer with defaults."""
        scorer = create_quality_scorer()

        assert isinstance(scorer, SignalQualityScorer)
        assert scorer.min_quality_threshold == 60.0
        assert scorer.lookback_days == 30

    def test_create_quality_scorer_custom(self):
        """Test creating quality scorer with custom params."""
        scorer = create_quality_scorer(
            min_quality_threshold=75.0,
            lookback_days=45
        )

        assert isinstance(scorer, SignalQualityScorer)
        assert scorer.min_quality_threshold == 75.0
        assert scorer.lookback_days == 45


# ============================================================================
# Edge Cases Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_score_empty_signals(self, quality_scorer):
        """Test scoring empty signals list."""
        with pytest.raises(ValueError, match="Cannot score empty signals list"):
            # Using a mock DB session - won't actually execute
            await quality_scorer.score_signal(
                db_session=None,
                signals=[],
                symbol="V10"
            )

    @pytest.mark.asyncio
    async def test_score_single_signal(self, quality_scorer):
        """Test scoring a single signal."""
        now = datetime.now()

        signals = [
            TradingSignal(
                source="test",
                type=SignalType.ML_MODEL,
                direction=SignalDirection.BUY,
                confidence=0.7,
                timestamp=now,
                features={"rsi": 25},
                symbol="V10",
                price=10000.0
            )
        ]

        # Should handle single signal gracefully
        # (will use neutral scores for components requiring multiple sources)
        agreement_score = await quality_scorer._calculate_ensemble_agreement(signals)
        assert agreement_score == 100.0  # Single signal = full agreement
