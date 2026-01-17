"""
Feature Engineering Service - Transform raw market data into ML features.

This module provides comprehensive feature engineering capabilities for trading systems,
transforming raw OHLCV data into meaningful features for machine learning models.
Implements price-based, volatility, momentum, trend, and statistical features.
"""

import pandas as pd
import numpy as np
from typing import Optional, List, Dict, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime
from functools import lru_cache
from cachetools import TTLCache
from loguru import logger

try:
    import talib
except ImportError:
    logger.warning("TA-Lib not installed. Some features will use pandas-ta or fallback implementations.")
    talib = None

try:
    import pandas_ta as ta
except ImportError:
    logger.warning("pandas-ta not installed. Using fallback implementations.")
    ta = None


@dataclass
class FeatureConfig:
    """Configuration for feature engineering."""

    # Price-based feature windows
    SHORT_WINDOW: int = 5
    MEDIUM_WINDOW: int = 10
    LONG_WINDOW: int = 20

    # RSI period
    RSI_PERIOD: int = 14

    # MACD settings
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9

    # Bollinger Bands
    BB_PERIOD: int = 20
    BB_STD: float = 2.0

    # ATR period
    ATR_PERIOD: int = 14

    # Stochastic settings
    STOCH_K: int = 14
    STOCH_D: int = 3

    # ADX period
    ADX_PERIOD: int = 14

    # Lag periods
    LAG_PERIODS: List[int] = field(default_factory=lambda: [1, 2, 3, 5, 10])

    # Z-score window
    ZSCORE_WINDOW: int = 20

    # Feature cache TTL (seconds)
    CACHE_TTL: int = 60


@dataclass
class FeatureSet:
    """Container for generated features."""

    symbol: str
    timestamp: datetime
    features: Dict[str, float] = field(default_factory=dict)
    feature_count: int = 0

    def add_feature(self, name: str, value: float) -> None:
        """Add a feature to the set."""
        self.features[name] = value
        self.feature_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "symbol": self.symbol,
            "timestamp": self.timestamp,
            "features": self.features,
            "feature_count": self.feature_count
        }


class FeatureEngineering:
    """
    Comprehensive feature engineering for trading systems.

    Features:
    - Price-based: Returns, log returns, price changes, price relative to MA, price momentum (ROC)
    - Volatility: ATR, standard deviation, Parkinson estimator
    - Momentum: RSI, MACD, Stochastic oscillator
    - Trend: SMA, EMA, ADX
    - Lag features: Multiple period lags
    - Rolling statistics: Mean, std, min, max
    - Z-score features
    - Bollinger Bands

    Usage:
        fe = FeatureEngineering()
        features = fe.generate_features(df, symbol="V10")
    """

    def __init__(self, config: Optional[FeatureConfig] = None):
        """
        Initialize FeatureEngineering service.

        Args:
            config: Feature configuration (uses defaults if not provided)
        """
        self.config = config or FeatureConfig()

        # Feature cache with TTL
        self._cache = TTLCache(maxsize=1000, ttl=self.config.CACHE_TTL)

        # Feature registry for tracking available features
        self._feature_registry = self._build_feature_registry()

        logger.info(
            f"FeatureEngineering initialized with {len(self._feature_registry)} feature types"
        )

    def _build_feature_registry(self) -> Dict[str, Callable]:
        """Build registry of available feature functions."""
        return {
            # Price-based features
            "returns": self._add_returns,
            "log_returns": self._add_log_returns,
            "price_change": self._add_price_change,
            "price_relative_ma": self._add_price_relative_ma,
            "price_momentum": self._add_price_momentum,

            # Volatility features
            "atr": self._add_atr,
            "std_dev": self._add_std_dev,
            "parkinson": self._add_parkinson_estimator,

            # Momentum features
            "rsi": self._add_rsi,
            "macd": self._add_macd,
            "stochastic": self._add_stochastic,

            # Trend features
            "sma": self._add_sma,
            "ema": self._add_ema,
            "adx": self._add_adx,

            # Lag features
            "lag": self._add_lag_features,

            # Rolling statistics
            "rolling": self._add_rolling_stats,

            # Z-score
            "zscore": self._add_zscore,

            # Bollinger Bands
            "bollinger": self._add_bollinger_bands,
        }

    def generate_features(
        self,
        df: pd.DataFrame,
        symbol: str,
        feature_types: Optional[List[str]] = None
    ) -> pd.DataFrame:
        """
        Generate all features for the given DataFrame.

        Args:
            df: Input DataFrame with OHLCV data (columns: timestamp, open, high, low, close, volume)
            symbol: Trading symbol
            feature_types: List of feature types to generate (None = all)

        Returns:
            DataFrame with all generated features added
        """
        if df.empty:
            logger.warning(f"Empty DataFrame provided for {symbol}")
            return df

        # Validate input columns
        required_cols = ["open", "high", "low", "close"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        # Make a copy to avoid modifying the original
        df = df.copy()

        # Ensure timestamp is datetime
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Handle missing data before feature generation
        df = self._handle_missing_data(df)

        # Determine which features to generate
        if feature_types is None:
            feature_types = list(self._feature_registry.keys())

        # Check cache first
        cache_key = self._get_cache_key(df, symbol, feature_types)
        if cache_key in self._cache:
            logger.debug(f"Using cached features for {symbol}")
            return self._cache[cache_key].copy()

        # Generate features
        generated_count = 0
        for feature_type in feature_types:
            if feature_type in self._feature_registry:
                try:
                    feature_func = self._feature_registry[feature_type]
                    df = feature_func(df)
                    generated_count += 1
                except Exception as e:
                    logger.error(f"Error generating {feature_type} features: {e}")
                    continue
            else:
                logger.warning(f"Unknown feature type: {feature_type}")

        logger.info(
            f"Generated {generated_count} feature types for {symbol} "
            f"({len(df.columns)} total columns)"
        )

        # Cache the result
        self._cache[cache_key] = df.copy()

        return df

    def _get_cache_key(self, df: pd.DataFrame, symbol: str, feature_types: List[str]) -> str:
        """Generate cache key for features."""
        # Use shape, last timestamp hash, and feature types for cache key
        last_ts = df["timestamp"].iloc[-1] if "timestamp" in df.columns else datetime.now()
        key = f"{symbol}_{df.shape}_{last_ts.timestamp()}_{'-'.join(sorted(feature_types))}"
        return key

    def _handle_missing_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Handle missing data in the DataFrame.

        Strategy:
        - Forward fill for small gaps (< 3 consecutive missing values)
        - Backward fill for remaining gaps
        - Drop rows with critical missing values (OHLC)

        Args:
            df: Input DataFrame

        Returns:
            DataFrame with handled missing data
        """
        initial_rows = len(df)

        # Check for critical missing values (OHLC)
        critical_cols = ["open", "high", "low", "close"]
        critical_missing = df[critical_cols].isnull().any(axis=1)

        if critical_missing.sum() > 0:
            logger.warning(
                f"Dropping {critical_missing.sum()} rows with critical missing values"
            )
            df = df[~critical_missing].reset_index(drop=True)

        # Forward fill for small gaps
        df = df.fillna(method="ffill", limit=3)

        # Backward fill for remaining gaps
        df = df.fillna(method="bfill")

        # If still have missing values, drop them
        df = df.dropna()

        final_rows = len(df)
        if initial_rows != final_rows:
            logger.info(
                f"Handled missing data: {initial_rows} -> {final_rows} rows "
                f"({initial_rows - final_rows} rows removed)"
            )

        return df

    # ========================================================================
    # Price-based Features
    # ========================================================================

    def _add_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add simple returns: (price_t - price_t-1) / price_t-1.

        Simple returns represent the percentage change in price over a given period.
        Formula: (price_t - price_t-1) / price_t-1
        """
        # Single period returns
        df["return_1"] = df["close"].pct_change()

        # Multi-period returns for periods 1, 5, 10, 20 (per acceptance criteria)
        for period in [1, 5, 10, 20]:
            if period != 1:  # Avoid duplicate for period 1
                df[f"return_{period}"] = df["close"].pct_change(period)

        return df

    def _add_log_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add logarithmic returns: log(price_t / price_t-1).

        Log returns are useful for time-series analysis as they are additive
        over time and approximately normally distributed.
        Formula: log(price_t / price_t-1)
        """
        # Single period log returns
        df["log_return_1"] = np.log(df["close"] / df["close"].shift(1))

        # Multi-period log returns for periods 1, 5, 10, 20
        for period in [1, 5, 10, 20]:
            if period != 1:  # Avoid duplicate for period 1
                df[f"log_return_{period}"] = np.log(df["close"] / df["close"].shift(period))

        return df

    def _add_price_change(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add absolute price changes: price_t - price_t-1.

        Absolute price changes represent the nominal difference in price.
        Formula: price_t - price_t-1
        """
        # Single period price change
        df["price_change_1"] = df["close"].diff()

        # Multi-period price changes for periods 5, 10, 20
        for period in [5, 10, 20]:
            df[f"price_change_{period}"] = df["close"].diff(period)

        return df

    def _add_price_relative_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add price relative to moving average.

        This feature indicates whether the current price is above or below
        its moving average, useful for trend identification.
        Formula: price_t / SMA(period) - 1
        """
        # Calculate SMAs for different periods
        for window in [self.config.SHORT_WINDOW, self.config.MEDIUM_WINDOW,
                       self.config.LONG_WINDOW, 50, 200]:
            sma = df["close"].rolling(window=window).mean()
            # Price relative to MA (normalized)
            df[f"price_rel_sma_{window}"] = (df["close"] / sma) - 1

        # Calculate EMAs for different periods
        for window in [self.config.SHORT_WINDOW, self.config.MEDIUM_WINDOW,
                       self.config.LONG_WINDOW]:
            ema = df["close"].ewm(span=window, adjust=False).mean()
            df[f"price_rel_ema_{window}"] = (df["close"] / ema) - 1

        return df

    def _add_price_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add price momentum (Rate of Change - ROC).

        ROC measures the percentage change in price over n periods.
        Formula: ((price_t - price_t-n) / price_t-n) * 100
        """
        # ROC for different periods
        for period in [1, 3, 5, 10, 20]:
            df[f"roc_{period}"] = (
                (df["close"] - df["close"].shift(period)) /
                df["close"].shift(period)
            ) * 100

        # Momentum indicators (absolute price difference)
        for period in [5, 10, 20]:
            df[f"momentum_{period}"] = df["close"] - df["close"].shift(period)

        return df

    # ========================================================================
    # Volatility Features
    # ========================================================================

    def _add_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Average True Range (ATR)."""
        period = self.config.ATR_PERIOD

        if talib is not None:
            df["atr"] = talib.ATR(
                df["high"].values,
                df["low"].values,
                df["close"].values,
                timeperiod=period
            )
        else:
            # Fallback implementation
            high_low = df["high"] - df["low"]
            high_close = np.abs(df["high"] - df["close"].shift())
            low_close = np.abs(df["low"] - df["close"].shift())
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            df["atr"] = tr.rolling(window=period).mean()

        # ATR ratio (normalized by price)
        df["atr_ratio"] = df["atr"] / df["close"]

        return df

    def _add_std_dev(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add rolling standard deviation."""
        for window in [self.config.SHORT_WINDOW, self.config.MEDIUM_WINDOW, self.config.LONG_WINDOW]:
            df[f"std_{window}"] = df["close"].rolling(window=window).std()
            df[f"std_ratio_{window}"] = df[f"std_{window}"] / df["close"]

        return df

    def _add_parkinson_estimator(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add Parkinson volatility estimator.

        Parkinson estimator uses high and low prices to estimate volatility,
        theoretically more efficient than close-to-close estimator.
        """
        for window in [self.config.MEDIUM_WINDOW, self.config.LONG_WINDOW]:
            log_hl = np.log(df["high"] / df["low"])
            parkinson = np.sqrt((log_hl ** 2).rolling(window=window).mean() / (4 * np.log(2)))
            df[f"parkinson_{window}"] = parkinson

        return df

    # ========================================================================
    # Momentum Features
    # ========================================================================

    def _add_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Relative Strength Index (RSI)."""
        period = self.config.RSI_PERIOD

        if talib is not None:
            df["rsi"] = talib.RSI(df["close"].values, timeperiod=period)
        else:
            # Fallback implementation
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            df["rsi"] = 100 - (100 / (1 + rs))

        # RSI-based features
        df["rsi_overbought"] = (df["rsi"] > 70).astype(int)
        df["rsi_oversold"] = (df["rsi"] < 30).astype(int)

        return df

    def _add_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Moving Average Convergence Divergence (MACD)."""
        fast = self.config.MACD_FAST
        slow = self.config.MACD_SLOW
        signal = self.config.MACD_SIGNAL

        if talib is not None:
            macd, macdsignal, macdhist = talib.MACD(
                df["close"].values,
                fastperiod=fast,
                slowperiod=slow,
                signalperiod=signal
            )
            df["macd"] = macd
            df["macd_signal"] = macdsignal
            df["macd_hist"] = macdhist
        else:
            # Fallback implementation
            ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
            ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
            df["macd"] = ema_fast - ema_slow
            df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
            df["macd_hist"] = df["macd"] - df["macd_signal"]

        # MACD-based features
        df["macd_bullish"] = (df["macd_hist"] > 0).astype(int)

        return df

    def _add_stochastic(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Stochastic oscillator."""
        k_period = self.config.STOCH_K
        d_period = self.config.STOCH_D

        if talib is not None:
            slowk, slowd = talib.STOCH(
                df["high"].values,
                df["low"].values,
                df["close"].values,
                fastk_period=k_period,
                slowk_period=d_period,
                slowd_period=d_period
            )
            df["stoch_k"] = slowk
            df["stoch_d"] = slowd
        else:
            # Fallback implementation
            low_min = df["low"].rolling(window=k_period).min()
            high_max = df["high"].rolling(window=k_period).max()
            df["stoch_k"] = 100 * (df["close"] - low_min) / (high_max - low_min)
            df["stoch_d"] = df["stoch_k"].rolling(window=d_period).mean()

        # Stochastic-based features
        df["stoch_overbought"] = (df["stoch_k"] > 80).astype(int)
        df["stoch_oversold"] = (df["stoch_k"] < 20).astype(int)

        return df

    # ========================================================================
    # Trend Features
    # ========================================================================

    def _add_sma(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Simple Moving Averages (SMA)."""
        for window in [self.config.SHORT_WINDOW, self.config.MEDIUM_WINDOW, self.config.LONG_WINDOW]:
            df[f"sma_{window}"] = df["close"].rolling(window=window).mean()

        # SMA crossover signals
        df["sma_cross_short_medium"] = (
            (df[f"sma_{self.config.SHORT_WINDOW}"] > df[f"sma_{self.config.MEDIUM_WINDOW}"]).astype(int)
        )
        df["sma_cross_medium_long"] = (
            (df[f"sma_{self.config.MEDIUM_WINDOW}"] > df[f"sma_{self.config.LONG_WINDOW}"]).astype(int)
        )

        # Price vs SMA
        df["price_above_sma_short"] = (
            (df["close"] > df[f"sma_{self.config.SHORT_WINDOW}"]).astype(int)
        )

        return df

    def _add_ema(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Exponential Moving Averages (EMA)."""
        for window in [self.config.SHORT_WINDOW, self.config.MEDIUM_WINDOW, self.config.LONG_WINDOW]:
            df[f"ema_{window}"] = df["close"].ewm(span=window, adjust=False).mean()

        # EMA crossover signals
        df["ema_cross_short_medium"] = (
            (df[f"ema_{self.config.SHORT_WINDOW}"] > df[f"ema_{self.config.MEDIUM_WINDOW}"]).astype(int)
        )

        # EMA vs SMA (trend strength)
        df["ema_sma_diff_short"] = (
            df[f"ema_{self.config.SHORT_WINDOW}"] - df[f"sma_{self.config.SHORT_WINDOW}"]
        ) / df[f"sma_{self.config.SHORT_WINDOW}"]

        return df

    def _add_adx(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Average Directional Index (ADX)."""
        period = self.config.ADX_PERIOD

        if talib is not None:
            df["adx"] = talib.ADX(
                df["high"].values,
                df["low"].values,
                df["close"].values,
                timeperiod=period
            )
            df["di_plus"] = talib.PLUS_DI(
                df["high"].values,
                df["low"].values,
                df["close"].values,
                timeperiod=period
            )
            df["di_minus"] = talib.MINUS_DI(
                df["high"].values,
                df["low"].values,
                df["close"].values,
                timeperiod=period
            )
        else:
            # Fallback implementation (simplified)
            high_diff = df["high"].diff()
            low_diff = -df["low"].diff()

            plus_dm = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0)
            minus_dm = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0)

            tr = pd.concat([
                df["high"] - df["low"],
                np.abs(df["high"] - df["close"].shift()),
                np.abs(df["low"] - df["close"].shift())
            ], axis=1).max(axis=1)

            plus_di = 100 * (pd.Series(plus_dm).rolling(window=period).mean() /
                            tr.rolling(window=period).mean())
            minus_di = 100 * (pd.Series(minus_dm).rolling(window=period).mean() /
                             tr.rolling(window=period).mean())

            dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
            df["adx"] = dx.rolling(window=period).mean()
            df["di_plus"] = plus_di
            df["di_minus"] = minus_di

        # ADX-based trend strength
        df["adx_strong_trend"] = (df["adx"] > 25).astype(int)
        df["trend_direction"] = np.where(
            df["di_plus"] > df["di_minus"], 1, -1
        )

        return df

    # ========================================================================
    # Lag Features
    # ========================================================================

    def _add_lag_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add lagged values of key columns."""
        lag_periods = self.config.LAG_PERIODS

        # Lag returns
        for period in lag_periods:
            df[f"close_lag_{period}"] = df["close"].shift(period)
            df[f"return_lag_{period}"] = df["close"].pct_change(period)

        # Lag volume
        if "volume" in df.columns:
            for period in lag_periods[:3]:  # Fewer lags for volume
                df[f"volume_lag_{period}"] = df["volume"].shift(period)

        return df

    # ========================================================================
    # Rolling Statistics
    # ========================================================================

    def _add_rolling_stats(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add rolling statistical features."""
        windows = [self.config.SHORT_WINDOW, self.config.MEDIUM_WINDOW, self.config.LONG_WINDOW]

        for window in windows:
            # Basic statistics
            df[f"rolling_mean_{window}"] = df["close"].rolling(window=window).mean()
            df[f"rolling_std_{window}"] = df["close"].rolling(window=window).std()
            df[f"rolling_min_{window}"] = df["close"].rolling(window=window).min()
            df[f"rolling_max_{window}"] = df["close"].rolling(window=window).max()

            # Range statistics
            df[f"rolling_range_{window}"] = (
                df[f"rolling_max_{window}"] - df[f"rolling_min_{window}"]
            )
            df[f"rolling_range_pct_{window}"] = (
                df[f"rolling_range_{window}"] / df[f"rolling_mean_{window}"]
            )

            # Percentiles
            df[f"rolling_median_{window}"] = df["close"].rolling(window=window).median()

            # Skewness and kurtosis
            df[f"rolling_skew_{window}"] = df["close"].rolling(window=window).skew()
            df[f"rolling_kurt_{window}"] = df["close"].rolling(window=window).kurt()

        return df

    # ========================================================================
    # Z-score Features
    # ========================================================================

    def _add_zscore(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Z-score (standardization) features."""
        window = self.config.ZSCORE_WINDOW

        rolling_mean = df["close"].rolling(window=window).mean()
        rolling_std = df["close"].rolling(window=window).std()

        df["zscore"] = (df["close"] - rolling_mean) / rolling_std

        # Z-score-based features
        df["zscore_extreme_high"] = (df["zscore"] > 2).astype(int)
        df["zscore_extreme_low"] = (df["zscore"] < -2).astype(int)

        # Multi-period Z-scores
        for w in [self.config.SHORT_WINDOW, self.config.LONG_WINDOW]:
            mean_w = df["close"].rolling(window=w).mean()
            std_w = df["close"].rolling(window=w).std()
            df[f"zscore_{w}"] = (df["close"] - mean_w) / std_w

        return df

    # ========================================================================
    # Bollinger Bands Features
    # ========================================================================

    def _add_bollinger_bands(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add Bollinger Bands features."""
        period = self.config.BB_PERIOD
        num_std = self.config.BB_STD

        # Calculate bands
        sma = df["close"].rolling(window=period).mean()
        std = df["close"].rolling(window=period).std()

        df["bb_upper"] = sma + (num_std * std)
        df["bb_middle"] = sma
        df["bb_lower"] = sma - (num_std * std)

        # Bollinger Band features
        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"]
        df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

        # Bollinger Band squeeze/narrow bands (potential breakout indicator)
        df["bb_squeeze"] = (df["bb_width"] < df["bb_width"].rolling(window=50).mean()).astype(int)

        # Price relative to bands
        df["price_above_bb_upper"] = (df["close"] > df["bb_upper"]).astype(int)
        df["price_below_bb_lower"] = (df["close"] < df["bb_lower"]).astype(int)

        return df

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_latest_features(
        self,
        df: pd.DataFrame,
        symbol: str
    ) -> FeatureSet:
        """
        Get the latest feature set for a symbol.

        Args:
            df: Input DataFrame with OHLCV data
            symbol: Trading symbol

        Returns:
            FeatureSet object with latest features
        """
        # Generate all features
        df_with_features = self.generate_features(df, symbol)

        # Get the latest row
        latest = df_with_features.iloc[-1]
        timestamp = latest.get("timestamp", datetime.now())

        # Create feature set
        feature_set = FeatureSet(symbol=symbol, timestamp=timestamp)

        # Add all feature columns (exclude OHLCV columns)
        exclude_cols = {"timestamp", "open", "high", "low", "close", "volume"}
        feature_cols = [col for col in df_with_features.columns if col not in exclude_cols]

        for col in feature_cols:
            value = latest[col]
            if pd.notna(value):
                feature_set.add_feature(col, float(value))

        logger.info(
            f"Retrieved {feature_set.feature_count} features for {symbol} "
            f"at {timestamp}"
        )

        return feature_set

    def get_feature_names(self) -> List[str]:
        """
        Get list of all available feature names.

        Returns:
            List of feature names
        """
        return list(self._feature_registry.keys())

    def clear_cache(self) -> None:
        """Clear the feature cache."""
        self._cache.clear()
        logger.info("Feature cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        return {
            "cache_size": len(self._cache),
            "cache_max_size": self._cache.maxsize,
            "cache_ttl": self._cache.ttl
        }


# ============================================================================
# Convenience Functions
# ============================================================================

def create_feature_engine(
    config: Optional[FeatureConfig] = None
) -> FeatureEngineering:
    """
    Factory function to create a FeatureEngineering instance.

    Args:
        config: Optional feature configuration

    Returns:
        FeatureEngineering instance
    """
    return FeatureEngineering(config=config)


def generate_features_from_dict(
    data: List[Dict[str, Any]],
    symbol: str
) -> pd.DataFrame:
    """
    Generate features from a list of OHLCV dictionaries.

    Args:
        data: List of dictionaries with OHLCV data
        symbol: Trading symbol

    Returns:
        DataFrame with features
    """
    df = pd.DataFrame(data)
    fe = FeatureEngineering()
    return fe.generate_features(df, symbol)
