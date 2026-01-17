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
    - Volatility: ATR, standard deviation, Parkinson estimator, Garman-Klass estimator,
                  historical volatility, volatility z-score, volatility regime classification
    - Momentum: RSI, MACD, Stochastic oscillator, Williams %R, Money Flow Index (MFI)
    - Trend: SMA, EMA, WMA, ADX with +DI/-DI, Ichimoku Cloud, Parabolic SAR, trend strength classification
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
            "garman_klass": self._add_garman_klass,
            "historical_volatility": self._add_historical_volatility,
            "volatility_zscore": self._add_volatility_zscore,
            "volatility_regime": self._add_volatility_regime,

            # Momentum features
            "rsi": self._add_rsi,
            "macd": self._add_macd,
            "stochastic": self._add_stochastic,
            "williams_r": self._add_williams_r,
            "mfi": self._add_mfi,
            "divergence": self._add_divergence_detection,

            # Trend features
            "sma": self._add_sma,
            "ema": self._add_ema,
            "wma": self._add_wma,
            "adx": self._add_adx,
            "ichimoku": self._add_ichimoku,
            "parabolic_sar": self._add_parabolic_sar,
            "trend_strength": self._add_trend_strength,

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
        """
        Add Average True Range (ATR) with configurable period.

        ATR measures market volatility by decomposing the entire range of an asset
        price for that period. True Range is the greatest of:
        - Current high minus current low
        - Absolute value of current high minus previous close
        - Absolute value of current low minus previous close

        Formula: SMA(TR, period) where TR = max(high-low, |high-close_prev|, |low-close_prev|)
        """
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

        # ATR for multiple periods per acceptance criteria
        for atr_period in [7, 14, 21]:
            if atr_period != period:
                if talib is not None:
                    df[f"atr_{atr_period}"] = talib.ATR(
                        df["high"].values,
                        df["low"].values,
                        df["close"].values,
                        timeperiod=atr_period
                    )
                else:
                    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                    df[f"atr_{atr_period}"] = tr.rolling(window=atr_period).mean()
                df[f"atr_ratio_{atr_period}"] = df[f"atr_{atr_period}"] / df["close"]

        return df

    def _add_std_dev(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add rolling standard deviation for periods: 5, 10, 20, 50.

        Standard deviation measures the amount of variation or dispersion of price values.
        A low standard deviation indicates that prices tend to be close to the mean.
        A high standard deviation indicates that prices are spread out over a wider range.
        """
        # Per acceptance criteria: periods 5, 10, 20, 50
        for window in [5, 10, 20, 50]:
            df[f"std_{window}"] = df["close"].rolling(window=window).std()
            df[f"std_ratio_{window}"] = df[f"std_{window}"] / df["close"]

        return df

    def _add_parkinson_estimator(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add Parkinson volatility estimator (high-low based).

        Parkinson estimator uses high and low prices to estimate volatility,
        theoretically more efficient than close-to-close estimator as it
        uses intraday price information.

        Formula: sqrt((1/(4*n*ln(2))) * sum(ln(high_t/low_t)^2))

        Where n is the window size. This estimator assumes continuous trading
        and no jumps, making it suitable for volatility indices.
        """
        for window in [5, 10, 20, 50]:
            log_hl = np.log(df["high"] / df["low"])
            # Parkinson volatility formula
            parkinson = np.sqrt((log_hl ** 2).rolling(window=window).mean() / (4 * np.log(2)))
            df[f"parkinson_{window}"] = parkinson

        return df

    def _add_garman_klass(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add Garman-Klass volatility estimator.

        The Garman-Klass estimator extends the Parkinson estimator by incorporating
        both open and close prices, providing a more efficient volatility estimate
        that uses all available price information (open, high, low, close).

        Formula: sqrt((0.5/n) * sum(ln(high_t/low_t)^2) - (2*ln(2)-1) * sum(ln(close_t/open_t)^2))

        This estimator is theoretically more efficient than both close-to-close
        and Parkinson estimators for assets with continuous trading.
        """
        for window in [5, 10, 20, 50]:
            log_hl = np.log(df["high"] / df["low"])
            log_co = np.log(df["close"] / df["open"])

            # Garman-Klass volatility formula
            term1 = (log_hl ** 2).rolling(window=window).mean() * 0.5
            term2 = (2 * np.log(2) - 1) * (log_co ** 2).rolling(window=window).mean()
            garman_klass = np.sqrt(term1 - term2)

            df[f"garman_klass_{window}"] = garman_klass

        return df

    def _add_historical_volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add historical volatility (annualized).

        Historical volatility measures the standard deviation of logarithmic returns,
        annualized to represent volatility over a one-year period.

        Formula: std(log_returns) * sqrt(trading_periods_per_year)

        Where trading_periods_per_year is typically:
        - 252 for daily data
        - 52 for weekly data
        - 12 for monthly data

        For intraday data (minute-by-minute), we assume 252 trading days * 1440 minutes.
        """
        # Calculate log returns
        log_returns = np.log(df["close"] / df["close"].shift(1))

        # Trading periods per year (assuming daily data - 252 trading days)
        trading_periods_per_year = 252

        for window in [5, 10, 20, 50]:
            # Calculate standard deviation of log returns
            std_log_returns = log_returns.rolling(window=window).std()

            # Annualize the volatility
            hist_vol = std_log_returns * np.sqrt(trading_periods_per_year)

            df[f"hist_vol_{window}"] = hist_vol

            # Historical volatility ratio (normalized by price)
            df[f"hist_vol_ratio_{window}"] = hist_vol / df["close"]

        return df

    def _add_volatility_zscore(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add volatility z-score (current volatility relative to historical mean).

        The volatility z-score measures how many standard deviations the current
        volatility is from its historical mean. This helps identify periods of
        unusually high or low volatility.

        Formula: (current_volatility - mean_volatility) / std_volatility

        Values interpretation:
        - z-score > 2: Abnormally high volatility
        - z-score < -2: Abnormally low volatility
        - z-score around 0: Normal volatility
        """
        # Use historical volatility as the base
        log_returns = np.log(df["close"] / df["close"].shift(1))

        for window in [10, 20, 50]:
            # Calculate rolling volatility
            rolling_vol = log_returns.rolling(window=window).std()

            # Calculate mean and std of volatility over a longer period
            long_window = window * 3
            vol_mean = rolling_vol.rolling(window=long_window).mean()
            vol_std = rolling_vol.rolling(window=long_window).std()

            # Calculate z-score
            vol_zscore = (rolling_vol - vol_mean) / vol_std
            df[f"vol_zscore_{window}"] = vol_zscore

        return df

    def _add_volatility_regime(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add volatility regime classification (low/medium/high).

        Volatility regime classification categorizes market conditions into
        three states based on historical volatility levels:
        - Low volatility: Calm market conditions
        - Medium volatility: Normal market conditions
        - High volatility: Turbulent market conditions

        Classification is based on percentiles of historical volatility:
        - Low: below 33rd percentile
        - Medium: 33rd to 67th percentile
        - High: above 67th percentile
        """
        # Use historical volatility as the base
        log_returns = np.log(df["close"] / df["close"].shift(1))

        for window in [10, 20, 50]:
            # Calculate rolling volatility
            rolling_vol = log_returns.rolling(window=window).std()

            # Calculate percentiles for classification
            vol_33 = rolling_vol.rolling(window=window * 5).quantile(0.33)
            vol_67 = rolling_vol.rolling(window=window * 5).quantile(0.67)

            # Classify regime (1=low, 2=medium, 3=high)
            regime = pd.Series(2, index=df.index)  # Default to medium
            regime = regime.where(rolling_vol >= vol_33, 1)  # Low volatility
            regime = regime.where(rolling_vol <= vol_67, 3)  # High volatility

            df[f"vol_regime_{window}"] = regime

            # Binary flags for each regime
            df[f"vol_regime_low_{window}"] = (regime == 1).astype(int)
            df[f"vol_regime_medium_{window}"] = (regime == 2).astype(int)
            df[f"vol_regime_high_{window}"] = (regime == 3).astype(int)

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

    def _add_williams_r(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Add Williams %R indicator.

        Williams %R is a momentum indicator that measures overbought/oversold levels.
        It is similar to Stochastic oscillator but uses a different scale.
        Formula: -100 * (high_max - close) / (high_max - low_min)

        Range: -100 to 0 (some implementations invert to 0-100)
        Interpretation:
        - Above -20: Overbought
        - Below -80: Oversold
        """
        # Calculate highest high and lowest low over the period
        high_max = df["high"].rolling(window=period).max()
        low_min = df["low"].rolling(window=period).min()

        # Williams %R formula (returns -100 to 0)
        df["williams_r"] = -100 * (high_max - df["close"]) / (high_max - low_min)

        # Williams %R for multiple periods
        for p in [7, 14, 21]:
            if p != period:
                high_max_p = df["high"].rolling(window=p).max()
                low_min_p = df["low"].rolling(window=p).min()
                df[f"williams_r_{p}"] = -100 * (high_max_p - df["close"]) / (high_max_p - low_min_p)

        # Williams %R-based features
        df["williams_r_overbought"] = (df["williams_r"] > -20).astype(int)
        df["williams_r_oversold"] = (df["williams_r"] < -80).astype(int)

        return df

    def _add_mfi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Add Money Flow Index (MFI).

        MFI is a momentum indicator that incorporates both price and volume data.
        It is similar to RSI but uses money flow instead of just price.
        Formula: 100 - (100 / (1 + money_ratio))

        Range: 0 to 100
        Interpretation:
        - Above 80: Overbought
        - Below 20: Oversold

        Money Flow = Typical Price * Volume
        Typical Price = (High + Low + Close) / 3
        """
        if "volume" not in df.columns:
            logger.warning("Volume column not found, skipping MFI calculation")
            return df

        # Calculate typical price
        typical_price = (df["high"] + df["low"] + df["close"]) / 3

        # Calculate money flow
        money_flow = typical_price * df["volume"]

        # Calculate positive and negative money flow
        positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0)
        negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0)

        # Calculate rolling sums
        positive_mf = positive_flow.rolling(window=period).sum()
        negative_mf = negative_flow.rolling(window=period).sum()

        # Calculate money ratio and MFI
        money_ratio = positive_mf / negative_mf
        df["mfi"] = 100 - (100 / (1 + money_ratio))

        # MFI for multiple periods
        for p in [7, 14, 21]:
            if p != period:
                positive_mf_p = positive_flow.rolling(window=p).sum()
                negative_mf_p = negative_flow.rolling(window=p).sum()
                money_ratio_p = positive_mf_p / negative_mf_p
                df[f"mfi_{p}"] = 100 - (100 / (1 + money_ratio_p))

        # MFI-based features
        df["mfi_overbought"] = (df["mfi"] > 80).astype(int)
        df["mfi_oversold"] = (df["mfi"] < 20).astype(int)

        return df

    def _add_divergence_detection(self, df: pd.DataFrame, indicator: str = "rsi", period: int = 14) -> pd.DataFrame:
        """
        Add indicator divergence detection (price vs indicator).

        Divergence occurs when the price of an asset is moving in the opposite direction
        of a technical indicator, such as an oscillator. This can signal potential trend reversals.

        Types of divergence:
        - Bullish divergence: Price makes lower low, indicator makes higher low
        - Bearish divergence: Price makes higher high, indicator makes lower high

        This implementation uses a simplified approach based on trend direction comparison.

        Args:
            df: Input DataFrame
            indicator: Name of the indicator column to check for divergence
            period: Lookback period for detecting divergence

        Returns:
            DataFrame with divergence flags added
        """
        # Ensure indicator exists
        if indicator not in df.columns:
            logger.warning(f"Indicator {indicator} not found in DataFrame, skipping divergence detection")
            return df

        # Initialize divergence columns
        df[f"{indicator}_bullish_divergence"] = 0
        df[f"{indicator}_bearish_divergence"] = 0

        # Calculate price momentum (direction) over the period
        price_change = df["close"].diff(period)

        # Calculate indicator momentum (direction) over the period
        indicator_change = df[indicator].diff(period)

        # Detect divergence based on opposite trends
        # Bullish divergence: price down, indicator up
        bullish_div = (price_change < 0) & (indicator_change > 0)
        df.loc[bullish_div, f"{indicator}_bullish_divergence"] = 1

        # Bearish divergence: price up, indicator down
        bearish_div = (price_change > 0) & (indicator_change < 0)
        df.loc[bearish_div, f"{indicator}_bearish_divergence"] = 1

        # Additional: Compare recent highs/lows for more robust divergence detection
        # Using a shorter window for recent pivots
        short_window = period // 2

        # Recent price highs/lows
        recent_price_high = df["high"].rolling(window=short_window).max()
        recent_price_low = df["low"].rolling(window=short_window).min()

        # Recent indicator highs/lows
        recent_indicator_high = df[indicator].rolling(window=short_window).max()
        recent_indicator_low = df[indicator].rolling(window=short_window).min()

        # Price making higher high but indicator not (bearish)
        price_higher_high = (df["high"] == recent_price_high) & (df["high"].shift(period) < recent_price_high.shift(period))
        indicator_not_higher_high = df[indicator] < recent_indicator_high.shift(period)
        df.loc[price_higher_high & indicator_not_higher_high, f"{indicator}_bearish_divergence"] = 1

        # Price making lower low but indicator not (bullish)
        price_lower_low = (df["low"] == recent_price_low) & (df["low"].shift(period) > recent_price_low.shift(period))
        indicator_not_lower_low = df[indicator] > recent_indicator_low.shift(period)
        df.loc[price_lower_low & indicator_not_lower_low, f"{indicator}_bullish_divergence"] = 1

        return df

    # ========================================================================
    # Trend Features
    # ========================================================================

    def _add_sma(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add Simple Moving Averages (SMA).

        Per acceptance criteria: Implement SMA for periods: 5, 10, 20, 50, 200
        """
        for window in [5, 10, 20, 50, 200]:
            df[f"sma_{window}"] = df["close"].rolling(window=window).mean()

        # SMA crossover signals
        df["sma_cross_short_medium"] = (
            (df[f"sma_5"] > df[f"sma_10"]).astype(int)
        )
        df["sma_cross_medium_long"] = (
            (df[f"sma_10"] > df[f"sma_20"]).astype(int)
        )
        df["sma_cross_long_xlong"] = (
            (df[f"sma_50"] > df[f"sma_200"]).astype(int)
        )

        # Price vs SMA
        df["price_above_sma_short"] = (
            (df["close"] > df[f"sma_5"]).astype(int)
        )
        df["price_above_sma_long"] = (
            (df["close"] > df[f"sma_200"]).astype(int)
        )

        # SMA slopes (trend direction)
        df["sma_5_slope"] = df["sma_5"].diff(5)
        df["sma_20_slope"] = df["sma_20"].diff(5)
        df["sma_200_slope"] = df["sma_200"].diff(10)

        return df

    def _add_ema(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add Exponential Moving Averages (EMA).

        Per acceptance criteria: Implement EMA for periods: 5, 10, 20, 50, 200
        """
        for window in [5, 10, 20, 50, 200]:
            df[f"ema_{window}"] = df["close"].ewm(span=window, adjust=False).mean()

        # EMA crossover signals
        df["ema_cross_short_medium"] = (
            (df["ema_5"] > df["ema_10"]).astype(int)
        )
        df["ema_cross_medium_long"] = (
            (df["ema_10"] > df["ema_20"]).astype(int)
        )
        df["ema_cross_long_xlong"] = (
            (df["ema_50"] > df["ema_200"]).astype(int)
        )

        # EMA vs SMA (trend strength) - only if SMA exists
        if "sma_5" in df.columns:
            df["ema_sma_diff_short"] = (
                df["ema_5"] - df["sma_5"]
            ) / df["sma_5"]
        else:
            df["ema_sma_diff_short"] = np.nan

        if "sma_200" in df.columns:
            df["ema_sma_diff_long"] = (
                df["ema_200"] - df["sma_200"]
            ) / df["sma_200"]
        else:
            df["ema_sma_diff_long"] = np.nan

        # EMA slopes (trend direction)
        df["ema_5_slope"] = df["ema_5"].diff(5)
        df["ema_20_slope"] = df["ema_20"].diff(5)
        df["ema_200_slope"] = df["ema_200"].diff(10)

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

    def _add_wma(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add Weighted Moving Average (WMA).

        WMA assigns greater weight to more recent data points and less weight to older data points.
        The weights decrease linearly from the most recent to the oldest data point.

        Formula: sum(price_i * weight_i) / sum(weight_i)
        Where weight_i = i (for i from 1 to n, with n being most recent)

        Per acceptance criteria: Implement WMA for periods 5, 10, 20, 50
        """
        for window in [5, 10, 20, 50]:
            # Calculate weights (linearly decreasing from recent to oldest)
            weights = np.arange(1, window + 1)

            def weighted_mean(x, w=weights):
                """Calculate weighted mean for a window."""
                if len(x) != window:
                    return np.nan
                valid = ~np.isnan(x)
                if not valid.any():
                    return np.nan
                return np.average(x[valid], weights=w[-len(x[valid]):])

            # Apply weighted moving average
            df[f"wma_{window}"] = df["close"].rolling(window=window).apply(
                weighted_mean, raw=True
            )

        # WMA crossover signals (after all WMAs are calculated)
        df["wma_cross_short_medium"] = (
            (df["wma_5"] > df["wma_10"]).astype(int)
        )

        # Price vs WMA
        df["price_above_wma_short"] = (
            (df["close"] > df["wma_5"]).astype(int)
        )

        # WMA vs SMA comparison (trend strength indicator) - only if SMA exists
        if "sma_5" in df.columns:
            df["wma_sma_diff_short"] = (
                df["wma_5"] - df["sma_5"]
            ) / df["sma_5"]
        else:
            df["wma_sma_diff_short"] = np.nan

        return df

    def _add_ichimoku(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add Ichimoku Cloud components.

        The Ichimoku Cloud is a comprehensive indicator that defines support and resistance,
        identifies trend direction, gauges momentum, and provides trading signals.

        Components:
        - Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
        - Kijun-sen (Base Line): (26-period high + 26-period low) / 2
        - Senkou Span A (Leading Span A): (Tenkan-sen + Kijun-sen) / 2, shifted 26 periods ahead
        - Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, shifted 26 periods ahead
        - Chikou Span (Lagging Span): Close, shifted 26 periods behind

        The cloud (Kumo) is formed by the area between Senkou Span A and Senkou Span B.

        Per acceptance criteria: Implement Tenkan, Kijun, Senkou components
        """
        # Tenkan-sen (Conversion Line) - 9 periods
        tenkan_period = 9
        high_9 = df["high"].rolling(window=tenkan_period).max()
        low_9 = df["low"].rolling(window=tenkan_period).min()
        df["ichimoku_tenkan"] = (high_9 + low_9) / 2

        # Kijun-sen (Base Line) - 26 periods
        kijun_period = 26
        high_26 = df["high"].rolling(window=kijun_period).max()
        low_26 = df["low"].rolling(window=kijun_period).min()
        df["ichimoku_kijun"] = (high_26 + low_26) / 2

        # Senkou Span A (Leading Span A)
        senkou_span_a = (df["ichimoku_tenkan"] + df["ichimoku_kijun"]) / 2
        df["ichimoku_senkou_a"] = senkou_span_a.shift(kijun_period)  # Shift 26 periods ahead

        # Senkou Span B (Leading Span B) - 52 periods
        senkou_period = 52
        high_52 = df["high"].rolling(window=senkou_period).max()
        low_52 = df["low"].rolling(window=senkou_period).min()
        senkou_span_b = (high_52 + low_52) / 2
        df["ichimoku_senkou_b"] = senkou_span_b.shift(kijun_period)  # Shift 26 periods ahead

        # Chikou Span (Lagging Span) - Close shifted 26 periods behind
        df["ichimoku_chikou"] = df["close"].shift(-kijun_period)

        # Ichimoku-based signals
        # Price above cloud (bullish)
        df["ichimoku_above_cloud"] = (
            (df["close"] > df["ichimoku_senkou_a"]) &
            (df["close"] > df["ichimoku_senkou_b"])
        ).astype(int)

        # Price below cloud (bearish)
        df["ichimoku_below_cloud"] = (
            (df["close"] < df["ichimoku_senkou_a"]) &
            (df["close"] < df["ichimoku_senkou_b"])
        ).astype(int)

        # Tenkan-Kijun crossover (TK Cross)
        df["ichimoku_tk_bullish"] = (
            (df["ichimoku_tenkan"] > df["ichimoku_kijun"]).astype(int)
        )

        # Cloud thickness (volatility measure)
        df["ichimoku_cloud_thickness"] = np.abs(
            df["ichimoku_senkou_a"] - df["ichimoku_senkou_b"]
        ) / df["close"]

        # Cloud color (A > B = bullish, A < B = bearish)
        df["ichimoku_cloud_bullish"] = (
            (df["ichimoku_senkou_a"] > df["ichimoku_senkou_b"]).astype(int)
        )

        return df

    def _add_parabolic_sar(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add Parabolic SAR (Stop and Reverse).

        Parabolic SAR is a trend-following indicator that sets trailing price stops
        for long or short positions. It helps identify potential trend reversals.

        The SAR is calculated as:
        - SAR_new = SAR_prev + AF * (EP - SAR_prev)
        - Where AF (Acceleration Factor) starts at 0.02 and increases by 0.02 up to 0.2
        - EP (Extreme Point) is the highest high (uptrend) or lowest low (downtrend)

        Interpretation:
        - When SAR is below price, trend is up (bullish)
        - When SAR is above price, trend is down (bearish)
        - Price crossing SAR signals potential reversal

        Per acceptance criteria: Implement Parabolic SAR
        """
        if talib is not None:
            # Use TA-Lib implementation if available
            df["sar"] = talib.SAR(
                df["high"].values,
                df["low"].values,
                acceleration=0.02,  # Starting AF
                maximum=0.2         # Maximum AF
            )
        else:
            # Fallback implementation
            sar = np.zeros(len(df))
            is_up_trend = True
            af = 0.02
            ep = df["high"].iloc[0]
            sar[0] = df["low"].iloc[0]

            for i in range(1, len(df)):
                if is_up_trend:
                    # Uptrend: SAR is below price
                    sar[i] = sar[i-1] + af * (ep - sar[i-1])

                    # Update EP if new high
                    if df["high"].iloc[i] > ep:
                        ep = df["high"].iloc[i]
                        af = min(af + 0.02, 0.2)

                    # Check for trend reversal
                    if df["low"].iloc[i] < sar[i]:
                        is_up_trend = False
                        sar[i] = ep
                        ep = df["low"].iloc[i]
                        af = 0.02
                else:
                    # Downtrend: SAR is above price
                    sar[i] = sar[i-1] + af * (ep - sar[i-1])

                    # Update EP if new low
                    if df["low"].iloc[i] < ep:
                        ep = df["low"].iloc[i]
                        af = min(af + 0.02, 0.2)

                    # Check for trend reversal
                    if df["high"].iloc[i] > sar[i]:
                        is_up_trend = True
                        sar[i] = ep
                        ep = df["high"].iloc[i]
                        af = 0.02

            df["sar"] = sar

        # Parabolic SAR-based signals
        # Price above SAR = uptrend
        df["sar_uptrend"] = (df["close"] > df["sar"]).astype(int)

        # Price below SAR = downtrend
        df["sar_downtrend"] = (df["close"] < df["sar"]).astype(int)

        # SAR reversal signal (when price crosses SAR)
        df["sar_reversal"] = (
            ((df["close"].shift(1) > df["sar"].shift(1)) & (df["close"] < df["sar"])) |
            ((df["close"].shift(1) < df["sar"].shift(1)) & (df["close"] > df["sar"]))
        ).astype(int)

        # Distance from SAR (trend strength indicator)
        df["sar_distance"] = np.abs(df["close"] - df["sar"]) / df["close"]

        return df

    def _add_trend_strength(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add trend strength classification (strong/weak/no trend).

        Trend strength is determined using multiple indicators:
        - ADX: Measures trend strength (regardless of direction)
        - MACD histogram: Shows momentum strength
        - Price distance from moving averages
        - Slope of moving averages

        Classification:
        - Strong trend: ADX > 25 AND price far from MA AND consistent slope
        - Weak trend: ADX between 20 and 25 OR moderate distance from MA
        - No trend: ADX < 20 AND price near MA

        Per acceptance criteria: Implement trend strength classification (strong/weak/no trend)
        """
        # Ensure we have the required indicators
        if "adx" not in df.columns:
            self._add_adx(df)
        if "macd_hist" not in df.columns:
            self._add_macd(df)
        if "sma_20" not in df.columns:
            self._add_sma(df)

        # Calculate price distance from SMA (normalized)
        price_sma_distance = np.abs(df["close"] - df["sma_20"]) / df["sma_20"]

        # Calculate slope of SMA (rate of change)
        sma_slope = df["sma_20"].diff(5)  # 5-period slope

        # Calculate MACD histogram strength
        macd_strength = np.abs(df["macd_hist"])

        # Classify trend strength
        # Initialize with "no trend" (0)
        df["trend_strength"] = 0

        # Strong trend (1) conditions:
        # - ADX > 25 (strong trend)
        # - Price more than 1% from SMA
        # - Consistent SMA slope (positive or negative)
        strong_trend = (
            (df["adx"] > 25) &
            (price_sma_distance > 0.01) &
            (np.abs(sma_slope) > 0)
        )
        df.loc[strong_trend, "trend_strength"] = 1

        # Weak trend (2) conditions:
        # - ADX between 20 and 25 (developing trend)
        # - OR price 0.5-1% from SMA with moderate ADX
        weak_trend = (
            ((df["adx"] >= 20) & (df["adx"] <= 25)) |
            ((price_sma_distance >= 0.005) & (price_sma_distance <= 0.01) & (df["adx"] > 15))
        ) & (~strong_trend)
        df.loc[weak_trend, "trend_strength"] = 2

        # No trend remains 0 for:
        # - ADX < 20 (sideways/ranging)
        # - Price within 0.5% of SMA
        # (already initialized as 0)

        # Binary flags for each trend strength
        df["trend_strong"] = (df["trend_strength"] == 1).astype(int)
        df["trend_weak"] = (df["trend_strength"] == 2).astype(int)
        df["trend_none"] = (df["trend_strength"] == 0).astype(int)

        # Trend strength score (0-100)
        # Combines ADX, price distance, and MACD strength
        adx_normalized = np.clip(df["adx"] / 50, 0, 1)  # ADX 0-50 scaled to 0-1
        distance_normalized = np.clip(price_sma_distance * 100, 0, 1)  # 0-1% distance scaled
        macd_normalized = np.clip(macd_strength / (df["close"].std()), 0, 1)

        df["trend_strength_score"] = (
            adx_normalized * 0.5 +
            distance_normalized * 0.3 +
            macd_normalized * 0.2
        ) * 100

        # Trend direction combined with strength
        # +1 = strong uptrend, -1 = strong downtrend, 0.5 = weak uptrend, -0.5 = weak downtrend, 0 = no trend
        df["trend_direction_strength"] = df["trend_direction"] * (
            df["trend_strong"] * 1.0 +
            df["trend_weak"] * 0.5
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
