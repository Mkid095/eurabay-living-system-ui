"""
Rule-Based Signal Source for EURABAY Living System.

This module implements a rule-based technical analysis signal source for trading.
It generates trading signals based on interpretable technical indicators and rules.

Features:
- RSI strategy: BUY if RSI < 30, SELL if RSI > 70
- MACD strategy: BUY if MACD crosses above signal, SELL if crosses below
- Moving average crossover: BUY if SMA_20 > SMA_50, SELL if SMA_20 < SMA_50
- Bollinger Bands: BUY if price touches lower band, SELL if touches upper
- Majority voting from all rules
- Confidence score based on agreement between rules
- Database storage for signals
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.core.logging import logger
from app.services.feature_engineering import FeatureEngineering, FeatureConfig
from app.services.ensemble_signals import TradingSignal, SignalDirection, SignalType


# ============================================================================
# Rule Strategy Enum
# ============================================================================

class RuleStrategy(str, Enum):
    """Rule-based strategy types."""
    RSI = "RSI"
    MACD = "MACD"
    MA_CROSSOVER = "MA_CROSSOVER"
    BOLLINGER_BANDS = "BOLLINGER_BANDS"


# ============================================================================
# Rule Signal Result
# ============================================================================

@dataclass
class RuleSignalResult:
    """Result from a single rule strategy."""

    strategy: RuleStrategy
    direction: SignalDirection
    confidence: float
    reason: str
    features: Dict[str, float]
    timestamp: datetime


# ============================================================================
# Rule-Based Configuration
# ============================================================================

@dataclass
class RuleBasedConfig:
    """Configuration for rule-based signal source."""

    # RSI thresholds
    RSI_OVERBOUGHT: float = 70.0
    RSI_OVERSOLD: float = 30.0

    # MACD settings (must match feature engineering)
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9

    # Moving average periods
    MA_SHORT_PERIOD: int = 20
    MA_LONG_PERIOD: int = 50

    # Bollinger Bands settings
    BB_PERIOD: int = 20
    BB_STD: float = 2.0

    # Signal storage
    SIGNAL_DIR: str = "signals"

    # Minimum agreement for majority vote (e.g., 0.5 = majority)
    MIN_AGREEMENT_RATIO: float = 0.5


# ============================================================================
# Rule-Based Signal Source
# ============================================================================

class RuleBasedSignalSource:
    """
    Rule-based signal source for trading using technical analysis.

    This class implements multiple technical analysis strategies and combines
    their signals using majority voting. Each strategy is independently
    implemented and interpretable.

    Strategies:
    1. RSI (Relative Strength Index): Identifies overbought/oversold conditions
    2. MACD (Moving Average Convergence Divergence): Identifies momentum changes
    3. MA Crossover: Identifies trend changes using moving averages
    4. Bollinger Bands: Identifies price extremes relative to volatility

    Example:
        source = RuleBasedSignalSource(symbol="V10")
        signal = await source.predict(market_data)
    """

    def __init__(
        self,
        symbol: str,
        config: Optional[RuleBasedConfig] = None,
        feature_engine: Optional[FeatureEngineering] = None
    ):
        """
        Initialize rule-based signal source.

        Args:
            symbol: Trading symbol (e.g., V10, V25, V50, V75, V100)
            config: Rule-based configuration (uses defaults if not provided)
            feature_engine: Feature engineering instance (creates new if not provided)
        """
        self.symbol = symbol
        self.config = config or RuleBasedConfig()
        self.feature_engine = feature_engine or FeatureEngineering()

        # Signal storage
        self.signal_dir = Path(self.config.SIGNAL_DIR)
        self.signal_dir.mkdir(parents=True, exist_ok=True)
        self.signal_file = self.signal_dir / f"rule_based_{self.symbol}.jsonl"

        # Track previous values for crossover detection
        self._prev_macd: Optional[float] = None
        self._prev_macd_signal: Optional[float] = None
        self._prev_ma_short: Optional[float] = None
        self._prev_ma_long: Optional[float] = None

        # Statistics
        self._signals_generated: int = 0
        self._buy_signals: int = 0
        self._sell_signals: int = 0
        self._hold_signals: int = 0

        logger.info(
            f"RuleBasedSignalSource initialized for {symbol} "
            f"(strategies: RSI, MACD, MA_Crossover, Bollinger_Bands)"
        )

    # ========================================================================
    # Signal Generation
    # ========================================================================

    async def predict(
        self,
        market_data: pd.DataFrame
    ) -> Optional[TradingSignal]:
        """
        Generate trading signal based on rule-based strategies.

        Args:
            market_data: DataFrame with OHLCV data

        Returns:
            TradingSignal or None if prediction fails
        """
        if market_data is None or market_data.empty:
            logger.error(f"No market data provided for {self.symbol}")
            return None

        # Validate we have enough data
        min_required = 100  # Minimum samples for indicator calculation
        if len(market_data) < min_required:
            logger.error(
                f"Insufficient data for prediction: {len(market_data)} < {min_required}"
            )
            return None

        try:
            # Generate features
            df_with_features = self.feature_engine.generate_features(
                market_data,
                self.symbol,
                feature_types=["rsi", "macd", "sma", "bollinger"]
            )

            # Get the latest row (most recent data)
            latest = df_with_features.iloc[-1]

            # Generate signals from each rule
            rule_signals = []

            # RSI strategy
            rsi_signal = self._rsi_strategy(df_with_features)
            if rsi_signal:
                rule_signals.append(rsi_signal)

            # MACD strategy
            macd_signal = self._macd_strategy(df_with_features)
            if macd_signal:
                rule_signals.append(macd_signal)

            # Moving average crossover strategy
            ma_signal = self._ma_crossover_strategy(df_with_features)
            if ma_signal:
                rule_signals.append(ma_signal)

            # Bollinger Bands strategy
            bb_signal = self._bollinger_bands_strategy(df_with_features)
            if bb_signal:
                rule_signals.append(bb_signal)

            if not rule_signals:
                logger.warning(f"No rule signals generated for {self.symbol}")
                return None

            # Combine rules using majority vote
            ensemble_signal = self._majority_vote(rule_signals)

            if ensemble_signal is None:
                return None

            # Create trading signal
            signal = TradingSignal(
                source=f"rule_based_{self.symbol}",
                type=SignalType.RULE_BASED,
                direction=ensemble_signal["direction"],
                confidence=ensemble_signal["confidence"],
                timestamp=datetime.now(),
                features=ensemble_signal["features"],
                symbol=self.symbol,
                price=float(latest["close"]),
                metadata={
                    "rule_signals": [
                        {
                            "strategy": r.strategy.value,
                            "direction": r.direction.value,
                            "confidence": r.confidence,
                            "reason": r.reason
                        }
                        for r in rule_signals
                    ],
                    "vote_breakdown": ensemble_signal["vote_breakdown"],
                    "num_agreeing": ensemble_signal["num_agreeing"],
                    "total_rules": len(rule_signals)
                }
            )

            # Update statistics
            self._signals_generated += 1
            if signal.direction == SignalDirection.BUY:
                self._buy_signals += 1
            elif signal.direction == SignalDirection.SELL:
                self._sell_signals += 1
            else:
                self._hold_signals += 1

            # Store signal
            self._store_signal(signal, ensemble_signal)

            logger.info(
                f"Rule-based signal for {self.symbol}: {signal.direction} "
                f"(confidence={signal.confidence:.2f}, "
                f"agreeing_rules={ensemble_signal['num_agreeing']}/{len(rule_signals)})"
            )

            return signal

        except Exception as e:
            logger.error(f"Error generating prediction for {self.symbol}: {e}", exc_info=True)
            return None

    # ========================================================================
    # Individual Rule Strategies
    # ========================================================================

    def _rsi_strategy(self, df: pd.DataFrame) -> Optional[RuleSignalResult]:
        """
        RSI strategy: BUY if RSI < 30, SELL if RSI > 70.

        RSI (Relative Strength Index) measures the speed and change of price movements.
        - RSI > 70: Overbought condition (potential SELL)
        - RSI < 30: Oversold condition (potential BUY)
        - RSI 30-70: Neutral (HOLD)

        Args:
            df: DataFrame with features

        Returns:
            RuleSignalResult or None if strategy cannot be applied
        """
        if "rsi" not in df.columns:
            logger.warning("RSI not available in features")
            return None

        latest = df.iloc[-1]
        rsi = latest["rsi"]

        # Check for NaN
        if pd.isna(rsi):
            return None

        if rsi > self.config.RSI_OVERBOUGHT:
            # Overbought - sell signal
            direction = SignalDirection.SELL
            # Confidence increases as RSI moves further above 70
            # Max RSI is 100, so range is 70-100 (30 points)
            confidence = 0.6 + min((rsi - 70) / 30 * 0.4, 0.4)
            reason = f"RSI overbought ({rsi:.2f} > {self.config.RSI_OVERBOUGHT})"
        elif rsi < self.config.RSI_OVERSOLD:
            # Oversold - buy signal
            # Confidence increases as RSI moves further below 30
            # Min RSI is 0, so range is 0-30 (30 points)
            direction = SignalDirection.BUY
            confidence = 0.6 + min((30 - rsi) / 30 * 0.4, 0.4)
            reason = f"RSI oversold ({rsi:.2f} < {self.config.RSI_OVERSOLD})"
        else:
            # Neutral
            direction = SignalDirection.HOLD
            # Higher confidence near middle of range (50)
            confidence = 0.5 + (1.0 - abs(rsi - 50) / 20) * 0.5
            reason = f"RSI neutral ({rsi:.2f} in range 30-70)"

        return RuleSignalResult(
            strategy=RuleStrategy.RSI,
            direction=direction,
            confidence=float(confidence),
            reason=reason,
            features={"rsi": float(rsi)},
            timestamp=datetime.now()
        )

    def _macd_strategy(self, df: pd.DataFrame) -> Optional[RuleSignalResult]:
        """
        MACD strategy: BUY if MACD crosses above signal, SELL if crosses below.

        MACD (Moving Average Convergence Divergence) shows the relationship between
        two moving averages of price.
        - MACD crosses above signal line: Bullish momentum (BUY)
        - MACD crosses below signal line: Bearish momentum (SELL)
        - No crossover: HOLD

        Args:
            df: DataFrame with features

        Returns:
            RuleSignalResult or None if strategy cannot be applied
        """
        if "macd" not in df.columns or "macd_signal" not in df.columns:
            logger.warning("MACD not available in features")
            return None

        latest = df.iloc[-1]
        macd = latest["macd"]
        macd_signal = latest["macd_signal"]

        # Check for NaN
        if pd.isna(macd) or pd.isna(macd_signal):
            return None

        # Check for crossover (need previous values)
        if self._prev_macd is not None and self._prev_macd_signal is not None:
            # Bullish crossover: MACD crosses above signal
            if self._prev_macd <= self._prev_macd_signal and macd > macd_signal:
                direction = SignalDirection.BUY
                confidence = 0.8
                reason = f"MACD bullish crossover (MACD={macd:.4f} > Signal={macd_signal:.4f})"
            # Bearish crossover: MACD crosses below signal
            elif self._prev_macd >= self._prev_macd_signal and macd < macd_signal:
                direction = SignalDirection.SELL
                confidence = 0.8
                reason = f"MACD bearish crossover (MACD={macd:.4f} < Signal={macd_signal:.4f})"
            # Check histogram for additional confirmation
            elif macd > macd_signal:
                direction = SignalDirection.BUY
                # Confidence based on histogram strength
                hist = macd - macd_signal
                confidence = min(0.3 + abs(hist) * 10, 0.7)
                reason = f"MACD above signal (no crossover yet, hist={hist:.4f})"
            elif macd < macd_signal:
                direction = SignalDirection.SELL
                # Confidence based on histogram strength
                hist = macd - macd_signal
                confidence = min(0.3 + abs(hist) * 10, 0.7)
                reason = f"MACD below signal (no crossover yet, hist={hist:.4f})"
            else:
                direction = SignalDirection.HOLD
                confidence = 0.5
                reason = "MACD at signal level"
        else:
            # Not enough history for crossover detection
            # Use current position
            if macd > macd_signal:
                direction = SignalDirection.BUY
                confidence = 0.5
                reason = f"MACD above signal (insufficient history for crossover)"
            elif macd < macd_signal:
                direction = SignalDirection.SELL
                confidence = 0.5
                reason = f"MACD below signal (insufficient history for crossover)"
            else:
                direction = SignalDirection.HOLD
                confidence = 0.5
                reason = "MACD at signal level"

        # Store current values for next iteration
        self._prev_macd = float(macd)
        self._prev_macd_signal = float(macd_signal)

        return RuleSignalResult(
            strategy=RuleStrategy.MACD,
            direction=direction,
            confidence=float(confidence),
            reason=reason,
            features={
                "macd": float(macd),
                "macd_signal": float(macd_signal),
                "macd_hist": float(macd - macd_signal)
            },
            timestamp=datetime.now()
        )

    def _ma_crossover_strategy(self, df: pd.DataFrame) -> Optional[RuleSignalResult]:
        """
        Moving average crossover: BUY if SMA_20 > SMA_50, SELL if SMA_20 < SMA_50.

        Moving average crossovers are a popular trend-following strategy.
        - Short MA crosses above long MA: Uptrend (BUY)
        - Short MA crosses below long MA: Downtrend (SELL)

        Args:
            df: DataFrame with features

        Returns:
            RuleSignalResult or None if strategy cannot be applied
        """
        short_col = f"sma_{self.config.MA_SHORT_PERIOD}"
        long_col = f"sma_{self.config.MA_LONG_PERIOD}"

        if short_col not in df.columns or long_col not in df.columns:
            logger.warning(f"Moving averages {short_col}, {long_col} not available in features")
            return None

        latest = df.iloc[-1]
        ma_short = latest[short_col]
        ma_long = latest[long_col]

        # Check for NaN
        if pd.isna(ma_short) or pd.isna(ma_long):
            return None

        # Check for crossover (need previous values)
        if self._prev_ma_short is not None and self._prev_ma_long is not None:
            # Bullish crossover: short MA crosses above long MA
            if self._prev_ma_short <= self._prev_ma_long and ma_short > ma_long:
                direction = SignalDirection.BUY
                confidence = 0.85
                reason = (
                    f"MA bullish crossover (SMA_{self.config.MA_SHORT_PERIOD}="
                    f"{ma_short:.2f} > SMA_{self.config.MA_LONG_PERIOD}={ma_long:.2f})"
                )
            # Bearish crossover: short MA crosses below long MA
            elif self._prev_ma_short >= self._prev_ma_long and ma_short < ma_long:
                direction = SignalDirection.SELL
                confidence = 0.85
                reason = (
                    f"MA bearish crossover (SMA_{self.config.MA_SHORT_PERIOD}="
                    f"{ma_short:.2f} < SMA_{self.config.MA_LONG_PERIOD}={ma_long:.2f})"
                )
            # Check current position
            elif ma_short > ma_long:
                direction = SignalDirection.BUY
                # Confidence based on distance between MAs
                distance = (ma_short - ma_long) / ma_long
                confidence = min(0.4 + abs(distance) * 5, 0.75)
                reason = (
                    f"Price in uptrend (SMA_{self.config.MA_SHORT_PERIOD} > "
                    f"SMA_{self.config.MA_LONG_PERIOD}, no fresh crossover)"
                )
            elif ma_short < ma_long:
                direction = SignalDirection.SELL
                # Confidence based on distance between MAs
                distance = (ma_long - ma_short) / ma_long
                confidence = min(0.4 + abs(distance) * 5, 0.75)
                reason = (
                    f"Price in downtrend (SMA_{self.config.MA_SHORT_PERIOD} < "
                    f"SMA_{self.config.MA_LONG_PERIOD}, no fresh crossover)"
                )
            else:
                direction = SignalDirection.HOLD
                confidence = 0.5
                reason = "Moving averages equal"
        else:
            # Not enough history for crossover detection
            if ma_short > ma_long:
                direction = SignalDirection.BUY
                confidence = 0.5
                reason = f"SMA_{self.config.MA_SHORT_PERIOD} above SMA_{self.config.MA_LONG_PERIOD} (insufficient history)"
            elif ma_short < ma_long:
                direction = SignalDirection.SELL
                confidence = 0.5
                reason = f"SMA_{self.config.MA_SHORT_PERIOD} below SMA_{self.config.MA_LONG_PERIOD} (insufficient history)"
            else:
                direction = SignalDirection.HOLD
                confidence = 0.5
                reason = "Moving averages equal"

        # Store current values for next iteration
        self._prev_ma_short = float(ma_short)
        self._prev_ma_long = float(ma_long)

        return RuleSignalResult(
            strategy=RuleStrategy.MA_CROSSOVER,
            direction=direction,
            confidence=float(confidence),
            reason=reason,
            features={
                f"sma_{self.config.MA_SHORT_PERIOD}": float(ma_short),
                f"sma_{self.config.MA_LONG_PERIOD}": float(ma_long),
                "ma_distance": float((ma_short - ma_long) / ma_long if ma_long != 0 else 0)
            },
            timestamp=datetime.now()
        )

    def _bollinger_bands_strategy(self, df: pd.DataFrame) -> Optional[RuleSignalResult]:
        """
        Bollinger Bands: BUY if price touches lower band, SELL if touches upper.

        Bollinger Bands measure volatility and identify potential overbought/oversold
        conditions based on standard deviations from a moving average.
        - Price touches or exceeds upper band: Overbought (SELL)
        - Price touches or falls below lower band: Oversold (BUY)
        - Price within bands: HOLD (with potential for fade signals)

        Args:
            df: DataFrame with features

        Returns:
            RuleSignalResult or None if strategy cannot be applied
        """
        if "bb_upper" not in df.columns or "bb_lower" not in df.columns:
            logger.warning("Bollinger Bands not available in features")
            return None

        latest = df.iloc[-1]
        price = latest["close"]
        bb_upper = latest["bb_upper"]
        bb_lower = latest["bb_lower"]
        bb_middle = latest.get("bb_middle", (bb_upper + bb_lower) / 2)

        # Check for NaN
        if pd.isna(bb_upper) or pd.isna(bb_lower):
            return None

        # Calculate %B (position within bands)
        if bb_upper != bb_lower:
            pct_b = (price - bb_lower) / (bb_upper - bb_lower)
        else:
            pct_b = 0.5

        # Check band touches
        # Using small epsilon for floating point comparison
        epsilon = 0.001

        if price >= bb_upper * (1 - epsilon):
            # Price at or above upper band - overbought
            direction = SignalDirection.SELL
            # Higher confidence the further above the upper band
            confidence = min(0.6 + (pct_b - 1.0) * 2, 0.95)
            reason = f"Price at upper Bollinger Band ({price:.2f} >= {bb_upper:.2f}, %B={pct_b:.2f})"
        elif price <= bb_lower * (1 + epsilon):
            # Price at or below lower band - oversold
            direction = SignalDirection.BUY
            # Higher confidence the further below the lower band
            confidence = min(0.6 + (0.0 - pct_b) * 2, 0.95)
            reason = f"Price at lower Bollinger Band ({price:.2f} <= {bb_lower:.2f}, %B={pct_b:.2f})"
        elif pct_b > 0.8:
            # Price approaching upper band
            direction = SignalDirection.SELL
            confidence = 0.4 + (pct_b - 0.8) * 2
            reason = f"Price near upper Bollinger Band (%B={pct_b:.2f})"
        elif pct_b < 0.2:
            # Price approaching lower band
            direction = SignalDirection.BUY
            confidence = 0.4 + (0.2 - pct_b) * 2
            reason = f"Price near lower Bollinger Band (%B={pct_b:.2f})"
        else:
            # Price within bands - neutral
            direction = SignalDirection.HOLD
            # Higher confidence near middle
            confidence = 1.0 - abs(pct_b - 0.5) * 1.5
            reason = f"Price within Bollinger Bands (%B={pct_b:.2f})"

        return RuleSignalResult(
            strategy=RuleStrategy.BOLLINGER_BANDS,
            direction=direction,
            confidence=float(confidence),
            reason=reason,
            features={
                "bb_upper": float(bb_upper),
                "bb_middle": float(bb_middle),
                "bb_lower": float(bb_lower),
                "bb_pct_b": float(pct_b)
            },
            timestamp=datetime.now()
        )

    # ========================================================================
    # Majority Voting
    # ========================================================================

    def _majority_vote(
        self,
        rule_signals: List[RuleSignalResult]
    ) -> Optional[Dict[str, Any]]:
        """
        Combine signals from all rules using majority voting.

        The ensemble signal is determined by:
        1. Counting votes for BUY, SELL, and HOLD
        2. Selecting the direction with the most votes
        3. Calculating confidence as the ratio of agreeing rules to total rules
        4. Requiring minimum agreement threshold (default 50%)

        Args:
            rule_signals: List of signals from individual rules

        Returns:
            Dictionary with ensemble signal or None if no clear majority
        """
        if not rule_signals:
            return None

        # Count votes
        vote_count = {
            SignalDirection.BUY: 0,
            SignalDirection.SELL: 0,
            SignalDirection.HOLD: 0
        }

        total_confidence = {
            SignalDirection.BUY: 0.0,
            SignalDirection.SELL: 0.0,
            SignalDirection.HOLD: 0.0
        }

        # Aggregate features from all rules
        all_features: Dict[str, float] = {}
        vote_breakdown: List[Dict[str, str]] = []

        for signal in rule_signals:
            vote_count[signal.direction] += 1
            total_confidence[signal.direction] += signal.confidence
            all_features.update(signal.features)

            vote_breakdown.append({
                "strategy": signal.strategy.value,
                "direction": signal.direction.value,
                "confidence": f"{signal.confidence:.2f}",
                "reason": signal.reason
            })

        # Find the direction with most votes
        winning_direction = max(vote_count, key=vote_count.get)
        winning_votes = vote_count[winning_direction]
        total_votes = len(rule_signals)

        # Calculate agreement ratio
        agreement_ratio = winning_votes / total_votes if total_votes > 0 else 0.0

        # Check if we meet minimum agreement threshold
        if agreement_ratio < self.config.MIN_AGREEMENT_RATIO:
            logger.info(
                f"No clear majority for {self.symbol}: "
                f"{winning_direction.value} has {winning_votes}/{total_votes} votes "
                f"({agreement_ratio:.2f} < {self.config.MIN_AGREEMENT_RATIO})"
            )
            return None

        # Calculate average confidence for winning direction
        if winning_votes > 0:
            avg_confidence = total_confidence[winning_direction] / winning_votes
        else:
            avg_confidence = 0.5

        # Boost confidence based on agreement ratio
        # Higher agreement = higher confidence
        boosted_confidence = avg_confidence * (0.5 + agreement_ratio)
        boosted_confidence = min(boosted_confidence, 1.0)

        result = {
            "direction": winning_direction,
            "confidence": float(boosted_confidence),
            "num_agreeing": winning_votes,
            "total_rules": total_votes,
            "agreement_ratio": float(agreement_ratio),
            "features": all_features,
            "vote_breakdown": vote_breakdown
        }

        logger.info(
            f"Majority vote for {self.symbol}: {winning_direction.value} "
            f"({winning_votes}/{total_votes} votes, "
            f"confidence={boosted_confidence:.2f})"
        )

        return result

    # ========================================================================
    # Signal Storage
    # ========================================================================

    def _store_signal(
        self,
        signal: TradingSignal,
        ensemble_result: Dict[str, Any]
    ) -> None:
        """
        Store rule-based signal to file.

        Args:
            signal: TradingSignal to store
            ensemble_result: Ensemble voting result
        """
        try:
            signal_data = {
                "timestamp": signal.timestamp.isoformat(),
                "symbol": signal.symbol,
                "direction": signal.direction.value,
                "confidence": signal.confidence,
                "price": signal.price,
                "num_agreeing": ensemble_result["num_agreeing"],
                "total_rules": ensemble_result["total_rules"],
                "agreement_ratio": ensemble_result["agreement_ratio"],
                "vote_breakdown": ensemble_result["vote_breakdown"],
                "features": signal.features
            }

            # Append to file (one line per signal)
            with open(self.signal_file, "a") as f:
                f.write(json.dumps(signal_data) + "\n")

            logger.debug(f"Stored rule-based signal for {self.symbol}")

        except Exception as e:
            logger.error(f"Error storing signal: {e}", exc_info=True)

    # ========================================================================
    # Statistics and Info
    # ========================================================================

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get signal source statistics.

        Returns:
            Dictionary with statistics
        """
        return {
            "symbol": self.symbol,
            "signals_generated": self._signals_generated,
            "buy_signals": self._buy_signals,
            "sell_signals": self._sell_signals,
            "hold_signals": self._hold_signals,
            "buy_ratio": self._buy_signals / self._signals_generated if self._signals_generated > 0 else 0.0,
            "sell_ratio": self._sell_signals / self._signals_generated if self._signals_generated > 0 else 0.0
        }

    def get_signal_history(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent signal history.

        Args:
            limit: Maximum number of signals to return

        Returns:
            List of signal dictionaries
        """
        try:
            if not self.signal_file.exists():
                return []

            signals = []
            with open(self.signal_file, "r") as f:
                for line in f:
                    try:
                        signal = json.loads(line.strip())
                        signals.append(signal)
                    except json.JSONDecodeError:
                        continue

            # Return most recent signals
            return signals[-limit:]

        except Exception as e:
            logger.error(f"Error reading signal history: {e}", exc_info=True)
            return []


# ============================================================================
# Convenience Functions
# ============================================================================

def create_rule_based_signal_source(
    symbol: str,
    config: Optional[RuleBasedConfig] = None
) -> RuleBasedSignalSource:
    """
    Factory function to create a rule-based signal source.

    Args:
        symbol: Trading symbol
        config: Optional rule-based configuration

    Returns:
        RuleBasedSignalSource instance
    """
    return RuleBasedSignalSource(symbol=symbol, config=config)


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    "RuleStrategy",
    "RuleSignalResult",
    "RuleBasedConfig",
    "RuleBasedSignalSource",
    "create_rule_based_signal_source"
]
