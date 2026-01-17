"""
Signal Quality Scoring System for EURABAY Living System.

This module provides quality scoring for trading signals to filter out
low-quality predictions and improve overall system performance.

Key Components:
- SignalQualityScorer class
- Multi-factor quality calculation
- Database persistence for quality scores
- Historical analysis capabilities
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.models import Signal, Trade, Configuration
from app.services.ensemble_signals import TradingSignal, SignalDirection


# ============================================================================
# Quality Score Thresholds
# ============================================================================

class QualityThreshold(str, Enum):
    """Quality score thresholds for signal filtering."""
    EXCELLENT = "excellent"  # 90-100
    HIGH = "high"  # 80-89
    MEDIUM = "medium"  # 60-79
    LOW = "low"  # 40-59
    POOR = "poor"  # 0-39


# ============================================================================
# Quality Score Data Structures
# ============================================================================

@dataclass
class QualityScoreBreakdown:
    """
    Detailed breakdown of quality score components.

    Attributes:
        ensemble_agreement: Score based on agreement between signal sources (0-100)
        confidence_calibration: Score based on calibration accuracy (0-100)
        recent_performance: Score based on recent signal source performance (0-100)
        regime_alignment: Score based on market regime alignment (0-100)
        feature_strength: Score based on indicator strength (0-100)
        overall_score: Weighted overall quality score (0-100)
        threshold: Quality threshold category
        calculated_at: When the score was calculated
    """
    ensemble_agreement: float
    confidence_calibration: float
    recent_performance: float
    regime_alignment: float
    feature_strength: float
    overall_score: float
    threshold: str
    calculated_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ensemble_agreement": round(self.ensemble_agreement, 2),
            "confidence_calibration": round(self.confidence_calibration, 2),
            "recent_performance": round(self.recent_performance, 2),
            "regime_alignment": round(self.regime_alignment, 2),
            "feature_strength": round(self.feature_strength, 2),
            "overall_score": round(self.overall_score, 2),
            "threshold": self.threshold,
            "calculated_at": self.calculated_at.isoformat(),
            "weights": QUALITY_WEIGHTS
        }


# Weights for each component (must sum to 1.0)
QUALITY_WEIGHTS: Dict[str, float] = {
    "ensemble_agreement": 0.30,
    "confidence_calibration": 0.25,
    "recent_performance": 0.25,
    "regime_alignment": 0.10,
    "feature_strength": 0.10
}


@dataclass
class QualityScoreResult:
    """
    Result of quality scoring for a signal.

    Attributes:
        signal_id: ID of the signal being scored
        source: Signal source name
        symbol: Trading symbol
        direction: Signal direction
        breakdown: Detailed quality score breakdown
        should_trade: Whether signal meets minimum quality threshold
        reason: Explanation of quality decision
        scored_at: When the score was computed
    """
    signal_id: int
    source: str
    symbol: str
    direction: str
    breakdown: QualityScoreBreakdown
    should_trade: bool
    reason: str
    scored_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "signal_id": self.signal_id,
            "source": self.source,
            "symbol": self.symbol,
            "direction": self.direction,
            "breakdown": self.breakdown.to_dict(),
            "should_trade": self.should_trade,
            "reason": self.reason,
            "scored_at": self.scored_at.isoformat()
        }


# ============================================================================
# Signal Quality Scorer Class
# ============================================================================

class SignalQualityScorer:
    """
    Signal quality scoring system for filtering low-quality predictions.

    This class calculates a quality score (0-100) for trading signals based on:
    1. Ensemble agreement (30%): Higher agreement = better quality
    2. Confidence calibration (25%): Closer to actual = better
    3. Recent performance (25%): Recent win rate of signal source
    4. Market regime alignment (10%): Signal matches current regime
    5. Feature strength (10%): How strong are the indicators?

    High quality signals (80+) should win > 60% of time.

    Example:
        scorer = SignalQualityScorer()

        # Score a signal
        result = await scorer.score_signal(
            db_session=session,
            signals=[signal1, signal2, signal3],
            symbol="V10"
        )

        if result.should_trade:
            print(f"High quality signal: {result.breakdown.overall_score}")
        else:
            print(f"Low quality signal: {result.reason}")

    Attributes:
        min_quality_threshold: Minimum quality score for trading (default: 60)
        lookback_days: Days to look back for performance data (default: 30)
        performance_cache: Cache of recent performance metrics
    """

    # Minimum quality score for trading
    DEFAULT_MIN_QUALITY_THRESHOLD = 60.0

    # High quality threshold (signals above this should win > 60%)
    HIGH_QUALITY_THRESHOLD = 80.0

    # Lookback period for performance calculation
    DEFAULT_LOOKBACK_DAYS = 30

    def __init__(
        self,
        min_quality_threshold: float = DEFAULT_MIN_QUALITY_THRESHOLD,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS
    ):
        """
        Initialize the signal quality scorer.

        Args:
            min_quality_threshold: Minimum quality score (0-100) for trading
            lookback_days: Days to look back for performance data
        """
        if not 0.0 <= min_quality_threshold <= 100.0:
            raise ValueError(
                f"min_quality_threshold must be between 0 and 100, "
                f"got {min_quality_threshold}"
            )

        if lookback_days < 1:
            raise ValueError(
                f"lookback_days must be at least 1, got {lookback_days}"
            )

        self.min_quality_threshold = min_quality_threshold
        self.lookback_days = lookback_days

        # Performance cache: {source_name: {symbol: win_rate}}
        self.performance_cache: Dict[str, Dict[str, float]] = {}

        # Cache timestamp: {source_name: last_update}
        self.performance_cache_time: Dict[str, datetime] = {}

        logger.info(
            f"SignalQualityScorer initialized: min_quality={min_quality_threshold}, "
            f"lookback={lookback_days} days"
        )

    # ========================================================================
    # Main Quality Scoring Method
    # ========================================================================

    async def score_signal(
        self,
        db_session: AsyncSession,
        signals: List[TradingSignal],
        symbol: str,
        current_regime: Optional[str] = None
    ) -> QualityScoreResult:
        """
        Calculate quality score for ensemble signals.

        This is the main entry point for quality scoring. It calculates
        all component scores and combines them into an overall quality score.

        Args:
            db_session: Database session
            signals: List of signals from different sources (ensemble)
            symbol: Trading symbol
            current_regime: Current market regime (optional)

        Returns:
            QualityScoreResult containing the quality score and decision

        Raises:
            ValueError: If signals list is empty
        """
        if not signals:
            raise ValueError("Cannot score empty signals list")

        logger.debug(
            f"Scoring quality for {len(signals)} signals for {symbol}"
        )

        # Calculate component scores
        agreement_score = await self._calculate_ensemble_agreement(signals)
        calibration_score = await self._calculate_confidence_calibration(
            db_session, signals
        )
        performance_score = await self._calculate_recent_performance(
            db_session, signals, symbol
        )
        regime_score = await self._calculate_regime_alignment(
            signals, current_regime
        )
        feature_score = await self._calculate_feature_strength(signals)

        # Calculate overall weighted score
        weights = QUALITY_WEIGHTS
        overall_score = (
            agreement_score * weights["ensemble_agreement"] +
            calibration_score * weights["confidence_calibration"] +
            performance_score * weights["recent_performance"] +
            regime_score * weights["regime_alignment"] +
            feature_score * weights["feature_strength"]
        )

        # Create breakdown
        breakdown = QualityScoreBreakdown(
            ensemble_agreement=agreement_score,
            confidence_calibration=calibration_score,
            recent_performance=performance_score,
            regime_alignment=regime_score,
            feature_strength=feature_score,
            overall_score=overall_score,
            threshold=self._get_quality_threshold(overall_score),
            calculated_at=datetime.now()
        )

        # Determine if signal should be traded
        should_trade = overall_score >= self.min_quality_threshold

        # Generate reason
        if should_trade:
            reason = (
                f"Quality score {overall_score:.1f} meets threshold "
                f"({self.min_quality_threshold})"
            )
        else:
            # Find which component(s) dragged down the score
            weak_components = []
            if agreement_score < 60:
                weak_components.append("low ensemble agreement")
            if calibration_score < 60:
                weak_components.append("poor confidence calibration")
            if performance_score < 60:
                weak_components.append("weak recent performance")
            if regime_score < 60:
                weak_components.append("regime misalignment")
            if feature_score < 60:
                weak_components.append("weak feature strength")

            reason = (
                f"Quality score {overall_score:.1f} below threshold. "
                f"Contributing factors: {', '.join(weak_components)}"
            )

        # Get primary signal info (use first signal for metadata)
        primary_signal = signals[0]

        result = QualityScoreResult(
            signal_id=id(primary_signal),  # Use object id as proxy
            source=primary_signal.source,
            symbol=symbol,
            direction=primary_signal.direction.value,
            breakdown=breakdown,
            should_trade=should_trade,
            reason=reason,
            scored_at=datetime.now()
        )

        logger.info(
            f"Quality score for {symbol}: {overall_score:.1f} | "
            f"Trade: {should_trade} | "
            f"Agreement={agreement_score:.0f}, "
            f"Calibration={calibration_score:.0f}, "
            f"Performance={performance_score:.0f}, "
            f"Regime={regime_score:.0f}, "
            f"Feature={feature_score:.0f}"
        )

        return result

    # ========================================================================
    # Component Score Calculations
    # ========================================================================

    async def _calculate_ensemble_agreement(
        self,
        signals: List[TradingSignal]
    ) -> float:
        """
        Calculate ensemble agreement score (0-100).

        Higher agreement between sources = better quality.
        - 100% agreement = 100 points
        - 67% agreement (2/3) = 80 points
        - 50% agreement = 50 points
        - 0% agreement = 0 points

        Args:
            signals: List of signals from different sources

        Returns:
            Agreement score (0-100)
        """
        if not signals:
            return 0.0

        # Count votes for each direction
        vote_count: Dict[str, int] = {"BUY": 0, "SELL": 0, "HOLD": 0}
        for signal in signals:
            vote_count[signal.direction.value] += 1

        # Find maximum agreement
        max_votes = max(vote_count.values())
        total_votes = len(signals)

        # Calculate agreement ratio
        agreement_ratio = max_votes / total_votes if total_votes > 0 else 0.0

        # Convert to score (non-linear to penalize low agreement)
        # Using quadratic scaling: agreement^2 * 100
        score = agreement_ratio ** 2 * 100

        logger.debug(
            f"Ensemble agreement: {max_votes}/{total_votes} ({agreement_ratio:.2%}) = {score:.1f}"
        )

        return min(score, 100.0)

    async def _calculate_confidence_calibration(
        self,
        db_session: AsyncSession,
        signals: List[TradingSignal]
    ) -> float:
        """
        Calculate confidence calibration score (0-100).

        Checks if predicted confidence matches actual performance.
        Uses existing confidence calibration data.

        Args:
            db_session: Database session
            signals: List of signals to evaluate

        Returns:
            Calibration score (0-100)
        """
        if not signals:
            return 0.0

        # Try to load calibration data from database
        from app.services.confidence_calibration import ConfidenceCalibrator

        calibrator = ConfidenceCalibrator()

        # Get average confidence
        avg_confidence = sum(s.confidence for s in signals) / len(signals)

        # Try to get calibrated confidence for first source
        # In production, you'd calibrate each source individually
        try:
            source_name = signals[0].source
            calibrated_conf = await calibrator.get_calibrated_confidence(
                db_session,
                avg_confidence,
                source_name
            )

            # Calculate calibration error
            calibration_error = abs(avg_confidence - calibrated_conf)

            # Convert to score: lower error = higher score
            # Error of 0 = 100 points, Error of 0.5 = 0 points
            score = max(0, (1 - calibration_error * 2) * 100)

            logger.debug(
                f"Confidence calibration: predicted={avg_confidence:.2%}, "
                f"calibrated={calibrated_conf:.2%}, error={calibration_error:.2%} = {score:.1f}"
            )

            return score

        except Exception as e:
            logger.warning(f"Could not load calibration data: {e}, using neutral score")
            # Return neutral score if calibration not available
            return 70.0

    async def _calculate_recent_performance(
        self,
        db_session: AsyncSession,
        signals: List[TradingSignal],
        symbol: str
    ) -> float:
        """
        Calculate recent performance score (0-100).

        Based on recent win rate of signal sources.

        Args:
            db_session: Database session
            signals: List of signals to evaluate
            symbol: Trading symbol

        Returns:
            Performance score (0-100)
        """
        if not signals:
            return 0.0

        # Get unique sources
        sources = list(set(s.source for s in signals))

        # Calculate win rate for each source
        win_rates = []

        cutoff_date = datetime.now() - timedelta(days=self.lookback_days)

        for source in sources:
            # Check cache first
            cached_win_rate = self.performance_cache.get(source, {}).get(symbol)
            cached_time = self.performance_cache_time.get(source)

            if cached_win_rate is not None and cached_time:
                cache_age = (datetime.now() - cached_time).total_seconds()
                # Use cache if less than 5 minutes old
                if cache_age < 300:
                    win_rates.append(cached_win_rate)
                    continue

            # Query database for recent trades
            query = (
                select(Trade)
                .join(Signal, Signal.trade_id == Trade.id)
                .where(
                    and_(
                        Signal.strategy == source,
                        Signal.symbol == symbol,
                        Signal.timestamp >= cutoff_date,
                        Trade.status == "CLOSED"
                    )
                )
            )

            result = await db_session.execute(query)
            trades = result.scalars().all()

            if not trades:
                # No recent trades, use neutral score
                win_rate = 0.50  # 50% baseline
            else:
                winning_trades = sum(1 for t in trades if t.profit_loss and t.profit_loss > 0)
                win_rate = winning_trades / len(trades)

            # Update cache
            if source not in self.performance_cache:
                self.performance_cache[source] = {}
            self.performance_cache[source][symbol] = win_rate
            self.performance_cache_time[source] = datetime.now()

            win_rates.append(win_rate)

        # Calculate average win rate
        avg_win_rate = sum(win_rates) / len(win_rates) if win_rates else 0.50

        # Convert to score: win_rate * 100
        # But cap at reasonable ranges (30% to 90%)
        capped_win_rate = max(0.30, min(0.90, avg_win_rate))
        score = capped_win_rate * 100

        logger.debug(
            f"Recent performance: win_rate={avg_win_rate:.2%} = {score:.1f}"
        )

        return score

    async def _calculate_regime_alignment(
        self,
        signals: List[TradingSignal],
        current_regime: Optional[str]
    ) -> float:
        """
        Calculate market regime alignment score (0-100).

        Checks if signal direction aligns with current market regime.
        - Trending up + BUY signal = high score
        - Trending down + SELL signal = high score
        - Ranging + signal in either direction = medium score
        - Opposing trend = low score

        Args:
            signals: List of signals to evaluate
            current_regime: Current market regime (optional)

        Returns:
            Regime alignment score (0-100)
        """
        if not signals:
            return 0.0

        # If no regime data, return neutral score
        if current_regime is None:
            logger.debug("No regime data available, using neutral score")
            return 70.0

        # Get primary signal direction
        primary_direction = signals[0].direction

        # Calculate alignment based on regime
        if "trending_up" in current_regime:
            # Bullish trend
            if primary_direction == SignalDirection.BUY:
                score = 95.0  # Excellent alignment
            elif primary_direction == SignalDirection.SELL:
                score = 30.0  # Poor alignment (fighting the trend)
            else:  # HOLD
                score = 50.0

        elif "trending_down" in current_regime:
            # Bearish trend
            if primary_direction == SignalDirection.SELL:
                score = 95.0  # Excellent alignment
            elif primary_direction == SignalDirection.BUY:
                score = 30.0  # Poor alignment (fighting the trend)
            else:  # HOLD
                score = 50.0

        elif "ranging" in current_regime:
            # Ranging market - both directions are okay
            if primary_direction in [SignalDirection.BUY, SignalDirection.SELL]:
                score = 70.0  # Medium alignment (mean reversion works)
            else:  # HOLD
                score = 50.0

        else:
            # Unknown regime
            score = 60.0  # Neutral

        logger.debug(
            f"Regime alignment: regime={current_regime}, "
            f"direction={primary_direction.value} = {score:.1f}"
        )

        return score

    async def _calculate_feature_strength(
        self,
        signals: List[TradingSignal]
    ) -> float:
        """
        Calculate feature strength score (0-100).

        Evaluates how strong the technical indicators are.
        Looks at signal features like RSI, MACD, moving averages, etc.

        Args:
            signals: List of signals to evaluate

        Returns:
            Feature strength score (0-100)
        """
        if not signals:
            return 0.0

        # Aggregate all features from all signals
        all_features = {}
        for signal in signals:
            all_features.update(signal.features)

        if not all_features:
            # No features available, return neutral score
            return 60.0

        strength_scores = []

        # RSI strength (oversold/overbought is strong)
        if "rsi" in all_features:
            rsi = all_features["rsi"]
            if rsi < 30 or rsi > 70:
                strength_scores.append(90.0)  # Strong signal
            elif rsi < 40 or rsi > 60:
                strength_scores.append(70.0)  # Medium signal
            else:
                strength_scores.append(40.0)  # Weak signal (neutral zone)

        # MACD strength (large divergence is strong)
        if "macd" in all_features and "macd_signal" in all_features:
            macd = all_features["macd"]
            signal = all_features["macd_signal"]
            divergence = abs(macd - signal)

            if divergence > 0.001:  # Strong divergence
                strength_scores.append(90.0)
            elif divergence > 0.0005:
                strength_scores.append(70.0)
            else:
                strength_scores.append(40.0)

        # Moving average crossover strength
        if "sma_20" in all_features and "sma_50" in all_features:
            sma_20 = all_features["sma_20"]
            sma_50 = all_features["sma_50"]
            ma_diff = abs(sma_20 - sma_50) / sma_50

            if ma_diff > 0.02:  # 2%+ difference = strong trend
                strength_scores.append(90.0)
            elif ma_diff > 0.01:
                strength_scores.append(70.0)
            else:
                strength_scores.append(40.0)

        # Bollinger Bands strength
        if "bb_upper" in all_features and "bb_lower" in all_features:
            bb_width = all_features["bb_upper"] - all_features["bb_lower"]
            # Wider bands = more volatility = potentially stronger signal
            # This is a heuristic - adjust based on your strategy
            strength_scores.append(60.0)  # Neutral for now

        # If we have feature scores, average them
        if strength_scores:
            avg_score = sum(strength_scores) / len(strength_scores)
        else:
            # No recognizable features, use neutral score
            avg_score = 60.0

        logger.debug(
            f"Feature strength: {len(strength_scores)} features evaluated = {avg_score:.1f}"
        )

        return avg_score

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _get_quality_threshold(self, score: float) -> str:
        """
        Get quality threshold category for a score.

        Args:
            score: Quality score (0-100)

        Returns:
            Quality threshold category
        """
        if score >= 90:
            return QualityThreshold.EXCELLENT
        elif score >= 80:
            return QualityThreshold.HIGH
        elif score >= 60:
            return QualityThreshold.MEDIUM
        elif score >= 40:
            return QualityThreshold.LOW
        else:
            return QualityThreshold.POOR

    async def store_quality_score(
        self,
        db_session: AsyncSession,
        result: QualityScoreResult
    ) -> None:
        """
        Store quality score in database for persistence.

        Args:
            db_session: Database session
            result: Quality score result to store
        """
        # Store as configuration for now
        # In production, you might want a dedicated quality_scores table
        config_key = f"quality_score_{result.source}_{result.symbol}_{result.scored_at.timestamp()}"

        config_data = {
            "source": result.source,
            "symbol": result.symbol,
            "direction": result.direction,
            "breakdown": result.breakdown.to_dict(),
            "should_trade": result.should_trade,
            "reason": result.reason,
            "scored_at": result.scored_at.isoformat()
        }

        config = Configuration(
            config_key=config_key,
            config_value=json.dumps(config_data),
            description=f"Quality score for {result.source} on {result.symbol}",
            category="quality_scores",
            is_active=True
        )

        db_session.add(config)
        await db_session.commit()

        logger.debug(f"Stored quality score for {result.source} on {result.symbol}")

    async def get_quality_distribution(
        self,
        db_session: AsyncSession,
        source_name: str,
        symbol: str,
        days: int = 7
    ) -> Dict[str, int]:
        """
        Get distribution of quality scores over time.

        Args:
            db_session: Database session
            source_name: Signal source name
            symbol: Trading symbol
            days: Number of days to look back

        Returns:
            Dictionary with count of scores in each threshold category
        """
        cutoff_date = datetime.now() - timedelta(days=days)

        # Query quality score configurations
        query = select(Configuration).where(
            and_(
                Configuration.category == "quality_scores",
                Configuration.created_at >= cutoff_date
            )
        )

        result = await db_session.execute(query)
        configs = result.scalars().all()

        # Count by threshold
        distribution = {
            QualityThreshold.EXCELLENT: 0,
            QualityThreshold.HIGH: 0,
            QualityThreshold.MEDIUM: 0,
            QualityThreshold.LOW: 0,
            QualityThreshold.POOR: 0
        }

        for config in configs:
            try:
                data = json.loads(config.config_value)
                if data.get("source") == source_name and data.get("symbol") == symbol:
                    threshold = data.get("breakdown", {}).get("threshold")
                    if threshold in distribution:
                        distribution[threshold] += 1
            except (json.JSONDecodeError, KeyError):
                continue

        logger.info(
            f"Quality distribution for {source_name} on {symbol}: {distribution}"
        )

        return distribution

    def clear_performance_cache(self) -> None:
        """Clear the performance cache."""
        self.performance_cache.clear()
        self.performance_cache_time.clear()
        logger.debug("Cleared performance cache")


# ============================================================================
# Convenience Functions
# ============================================================================

def create_quality_scorer(
    min_quality_threshold: float = SignalQualityScorer.DEFAULT_MIN_QUALITY_THRESHOLD,
    lookback_days: int = SignalQualityScorer.DEFAULT_LOOKBACK_DAYS
) -> SignalQualityScorer:
    """
    Create and configure a signal quality scorer.

    Args:
        min_quality_threshold: Minimum quality score for trading (0-100)
        lookback_days: Days to look back for performance data

    Returns:
        Configured SignalQualityScorer instance
    """
    scorer = SignalQualityScorer(
        min_quality_threshold=min_quality_threshold,
        lookback_days=lookback_days
    )
    logger.info("Created new SignalQualityScorer")
    return scorer


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "QualityThreshold",
    "QualityScoreBreakdown",
    "QualityScoreResult",
    "SignalQualityScorer",
    "create_quality_scorer"
]
