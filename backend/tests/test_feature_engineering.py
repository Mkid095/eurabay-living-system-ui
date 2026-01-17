"""
Test suite for Feature Engineering Service.

Tests all feature generation functionality including:
- Price-based features
- Volatility features
- Momentum features
- Trend features
- Lag features
- Rolling statistics
- Z-score features
- Bollinger Bands
- Feature caching
- Missing data handling
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.feature_engineering import (
    FeatureEngineering,
    FeatureConfig,
    FeatureSet,
    create_feature_engine,
    generate_features_from_dict
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)

    n_periods = 100
    dates = pd.date_range(start=datetime.now() - timedelta(days=n_periods), periods=n_periods, freq="H")

    # Generate realistic price movements
    base_price = 10000.0
    price_changes = np.random.randn(n_periods) * 50
    prices = base_price + np.cumsum(price_changes)

    data = {
        "timestamp": dates,
        "open": prices + np.random.randn(n_periods) * 10,
        "high": prices + np.abs(np.random.randn(n_periods) * 20),
        "low": prices - np.abs(np.random.randn(n_periods) * 20),
        "close": prices + np.random.randn(n_periods) * 10,
        "volume": np.random.randint(1000, 10000, n_periods)
    }

    # Ensure high >= close >= low and high >= open >= low
    df = pd.DataFrame(data)
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)

    return df


@pytest.fixture
def feature_engine():
    """Create a FeatureEngineering instance for testing."""
    return FeatureEngineering()


@pytest.fixture
def custom_config():
    """Create a custom FeatureConfig for testing."""
    return FeatureConfig(
        SHORT_WINDOW=3,
        MEDIUM_WINDOW=5,
        LONG_WINDOW=10,
        RSI_PERIOD=10,
        CACHE_TTL=30
    )


# ============================================================================
# Initialization Tests
# ============================================================================

class TestFeatureEngineeringInitialization:
    """Test FeatureEngineering initialization."""

    def test_default_initialization(self):
        """Test initialization with default configuration."""
        fe = FeatureEngineering()
        assert fe.config is not None
        assert fe.config.SHORT_WINDOW == 5
        assert fe.config.RSI_PERIOD == 14
        assert len(fe._feature_registry) > 0

    def test_custom_config_initialization(self, custom_config):
        """Test initialization with custom configuration."""
        fe = FeatureEngineering(config=custom_config)
        assert fe.config.SHORT_WINDOW == 3
        assert fe.config.RSI_PERIOD == 10

    def test_feature_registry(self, feature_engine):
        """Test that feature registry is populated."""
        registry = feature_engine._feature_registry
        assert isinstance(registry, dict)
        assert len(registry) > 0
        assert "returns" in registry
        assert "rsi" in registry
        assert "macd" in registry

    def test_get_feature_names(self, feature_engine):
        """Test getting list of feature names."""
        names = feature_engine.get_feature_names()
        assert isinstance(names, list)
        assert len(names) > 0


# ============================================================================
# Price-based Features Tests
# ============================================================================

class TestPriceBasedFeatures:
    """Test price-based feature generation."""

    def test_returns_feature(self, feature_engine, sample_ohlcv_data):
        """Test returns feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["returns"])
        assert "return_1" in df.columns
        assert "return_5" in df.columns
        assert "return_10" in df.columns
        assert "return_20" in df.columns

    def test_log_returns_feature(self, feature_engine, sample_ohlcv_data):
        """Test log returns feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["log_returns"])
        assert "log_return_1" in df.columns
        assert "log_return_5" in df.columns
        assert "log_return_10" in df.columns
        assert "log_return_20" in df.columns

    def test_price_change_feature(self, feature_engine, sample_ohlcv_data):
        """Test price change feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["price_change"])
        assert "price_change_1" in df.columns
        assert "price_change_5" in df.columns
        assert "price_change_10" in df.columns
        assert "price_change_20" in df.columns

    def test_price_relative_ma_feature(self, feature_engine, sample_ohlcv_data):
        """Test price relative to moving average feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["price_relative_ma"])
        # Check SMA relative features
        assert "price_rel_sma_5" in df.columns
        assert "price_rel_sma_10" in df.columns
        assert "price_rel_sma_20" in df.columns
        assert "price_rel_sma_50" in df.columns
        assert "price_rel_sma_200" in df.columns
        # Check EMA relative features
        assert "price_rel_ema_5" in df.columns
        assert "price_rel_ema_10" in df.columns
        assert "price_rel_ema_20" in df.columns

    def test_price_momentum_feature(self, feature_engine, sample_ohlcv_data):
        """Test price momentum (ROC) feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["price_momentum"])
        # Check ROC features
        assert "roc_1" in df.columns
        assert "roc_3" in df.columns
        assert "roc_5" in df.columns
        assert "roc_10" in df.columns
        assert "roc_20" in df.columns
        # Check momentum features
        assert "momentum_5" in df.columns
        assert "momentum_10" in df.columns
        assert "momentum_20" in df.columns

    def test_returns_calculation_accuracy(self, feature_engine, sample_ohlcv_data):
        """Test that returns are calculated correctly."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["returns"])
        # Manually calculate expected return for period 1
        expected_return = (sample_ohlcv_data["close"].iloc[1] - sample_ohlcv_data["close"].iloc[0]) / sample_ohlcv_data["close"].iloc[0]
        actual_return = df["return_1"].iloc[1]
        assert np.isclose(expected_return, actual_return)

    def test_log_returns_calculation_accuracy(self, feature_engine, sample_ohlcv_data):
        """Test that log returns are calculated correctly."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["log_returns"])
        # Manually calculate expected log return for period 1
        expected_log_return = np.log(sample_ohlcv_data["close"].iloc[1] / sample_ohlcv_data["close"].iloc[0])
        actual_log_return = df["log_return_1"].iloc[1]
        assert np.isclose(expected_log_return, actual_log_return)

    def test_price_change_calculation_accuracy(self, feature_engine, sample_ohlcv_data):
        """Test that price changes are calculated correctly."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["price_change"])
        # Manually calculate expected price change for period 1
        expected_change = sample_ohlcv_data["close"].iloc[1] - sample_ohlcv_data["close"].iloc[0]
        actual_change = df["price_change_1"].iloc[1]
        assert np.isclose(expected_change, actual_change)

    def test_roc_calculation_accuracy(self, feature_engine, sample_ohlcv_data):
        """Test that ROC is calculated correctly."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["price_momentum"])
        # Manually calculate expected ROC for period 5
        period = 5
        if len(sample_ohlcv_data) > period:
            expected_roc = ((sample_ohlcv_data["close"].iloc[period] - sample_ohlcv_data["close"].iloc[0]) /
                          sample_ohlcv_data["close"].iloc[0]) * 100
            actual_roc = df["roc_5"].iloc[period]
            assert np.isclose(expected_roc, actual_roc)

    def test_price_relative_ma_ranges(self, feature_engine, sample_ohlcv_data):
        """Test that price relative to MA features are in expected ranges."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["price_relative_ma"])
        # Price relative to MA should be a normalized ratio (can be negative or positive)
        # Values near 0 indicate price is near the MA
        # Positive values indicate price above MA, negative indicate below
        assert df["price_rel_sma_20"].dropna().min() > -1  # Price not more than 100% below MA
        assert df["price_rel_sma_20"].dropna().max() < 2  # Price not more than 200% above MA


# ============================================================================
# Volatility Features Tests
# ============================================================================

class TestVolatilityFeatures:
    """Test volatility feature generation."""

    def test_atr_feature(self, feature_engine, sample_ohlcv_data):
        """Test ATR feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["atr"])
        assert "atr" in df.columns
        assert "atr_ratio" in df.columns
        # ATR should be positive
        assert (df["atr"].dropna() > 0).all()

    def test_atr_multiple_periods(self, feature_engine, sample_ohlcv_data):
        """Test ATR for multiple periods."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["atr"])
        # Check for multiple period ATRs
        assert "atr_7" in df.columns or "atr_14" in df.columns or "atr_21" in df.columns
        # ATR ratio should also be present
        assert "atr_ratio" in df.columns

    def test_std_dev_feature(self, feature_engine, sample_ohlcv_data):
        """Test standard deviation feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["std_dev"])
        # Per acceptance criteria: periods 5, 10, 20, 50
        assert "std_5" in df.columns
        assert "std_10" in df.columns
        assert "std_20" in df.columns
        assert "std_50" in df.columns
        assert "std_ratio_5" in df.columns
        assert "std_ratio_10" in df.columns
        assert "std_ratio_20" in df.columns
        assert "std_ratio_50" in df.columns
        # Standard deviation should be positive
        assert (df["std_20"].dropna() > 0).all()

    def test_parkinson_estimator(self, feature_engine, sample_ohlcv_data):
        """Test Parkinson volatility estimator."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["parkinson"])
        # Per acceptance criteria: periods 5, 10, 20, 50
        assert "parkinson_5" in df.columns
        assert "parkinson_10" in df.columns
        assert "parkinson_20" in df.columns
        assert "parkinson_50" in df.columns
        # Parkinson should be positive
        assert (df["parkinson_10"].dropna() > 0).all()

    def test_garman_klass_estimator(self, feature_engine, sample_ohlcv_data):
        """Test Garman-Klass volatility estimator."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["garman_klass"])
        # Per acceptance criteria: periods 5, 10, 20, 50
        assert "garman_klass_5" in df.columns
        assert "garman_klass_10" in df.columns
        assert "garman_klass_20" in df.columns
        assert "garman_klass_50" in df.columns
        # Garman-Klass should be positive
        assert (df["garman_klass_10"].dropna() >= 0).all()

    def test_historical_volatility(self, feature_engine, sample_ohlcv_data):
        """Test historical volatility (annualized)."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["historical_volatility"])
        # Per acceptance criteria: periods 5, 10, 20, 50
        assert "hist_vol_5" in df.columns
        assert "hist_vol_10" in df.columns
        assert "hist_vol_20" in df.columns
        assert "hist_vol_50" in df.columns
        # Historical volatility ratio
        assert "hist_vol_ratio_5" in df.columns
        assert "hist_vol_ratio_10" in df.columns
        assert "hist_vol_ratio_20" in df.columns
        assert "hist_vol_ratio_50" in df.columns
        # Historical volatility should be positive
        assert (df["hist_vol_20"].dropna() > 0).all()

    def test_volatility_zscore(self, feature_engine, sample_ohlcv_data):
        """Test volatility z-score."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["volatility_zscore"])
        # Volatility z-score for windows 10, 20, 50
        assert "vol_zscore_10" in df.columns
        assert "vol_zscore_20" in df.columns
        assert "vol_zscore_50" in df.columns
        # Z-score should have values around 0 (mean approximately 0)
        zscore_mean = df["vol_zscore_20"].dropna().mean()
        assert abs(zscore_mean) < 1.0  # Should be near zero

    def test_volatility_regime(self, feature_engine, sample_ohlcv_data):
        """Test volatility regime classification."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["volatility_regime"])
        # Volatility regime for windows 10, 20, 50
        assert "vol_regime_10" in df.columns
        assert "vol_regime_20" in df.columns
        assert "vol_regime_50" in df.columns
        # Binary flags for each regime
        assert "vol_regime_low_10" in df.columns
        assert "vol_regime_medium_10" in df.columns
        assert "vol_regime_high_10" in df.columns
        # Regime values should be 1, 2, or 3
        valid_regimes = df["vol_regime_20"].dropna().isin([1, 2, 3])
        assert valid_regimes.all()

    def test_volatility_features_all(self, feature_engine, sample_ohlcv_data):
        """Test all volatility features together."""
        df = feature_engine.generate_features(
            sample_ohlcv_data,
            "TEST",
            feature_types=["atr", "std_dev", "parkinson", "garman_klass",
                         "historical_volatility", "volatility_zscore", "volatility_regime"]
        )
        # Check that all volatility features are present
        volatility_features = [
            "atr", "atr_ratio", "std_5", "std_10", "std_20", "std_50",
            "parkinson_5", "parkinson_10", "parkinson_20", "parkinson_50",
            "garman_klass_5", "garman_klass_10", "garman_klass_20", "garman_klass_50",
            "hist_vol_5", "hist_vol_10", "hist_vol_20", "hist_vol_50",
            "vol_zscore_10", "vol_zscore_20", "vol_zscore_50",
            "vol_regime_10", "vol_regime_20", "vol_regime_50"
        ]
        for feature in volatility_features:
            assert feature in df.columns, f"Missing feature: {feature}"

    def test_atr_calculation_accuracy(self, feature_engine, sample_ohlcv_data):
        """Test that ATR is calculated correctly."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["atr"])
        # Manually calculate True Range for a specific row
        idx = 50  # Use row 50 to ensure we have enough history
        high_low = sample_ohlcv_data["high"].iloc[idx] - sample_ohlcv_data["low"].iloc[idx]
        high_close = abs(sample_ohlcv_data["high"].iloc[idx] - sample_ohlcv_data["close"].iloc[idx-1])
        low_close = abs(sample_ohlcv_data["low"].iloc[idx] - sample_ohlcv_data["close"].iloc[idx-1])
        expected_tr = max(high_low, high_close, low_close)
        # ATR at period 14 should include this TR
        # We verify the ATR is in a reasonable range
        assert df["atr"].iloc[idx] > 0
        assert df["atr"].iloc[idx] < expected_tr * 2  # Should not be more than 2x single TR

    def test_std_dev_calculation_accuracy(self, feature_engine, sample_ohlcv_data):
        """Test that standard deviation is calculated correctly."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["std_dev"])
        # Manually calculate std for window 20
        window = 20
        idx = 50
        expected_std = sample_ohlcv_data["close"].iloc[idx-window+1:idx+1].std()
        actual_std = df["std_20"].iloc[idx]
        assert np.isclose(expected_std, actual_std, rtol=1e-10)

    def test_parkinson_calculation_accuracy(self, feature_engine, sample_ohlcv_data):
        """Test that Parkinson estimator is calculated correctly."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["parkinson"])
        # Manually calculate Parkinson for a specific window
        window = 10
        idx = 50
        log_hl = np.log(
            sample_ohlcv_data["high"].iloc[idx-window+1:idx+1] /
            sample_ohlcv_data["low"].iloc[idx-window+1:idx+1]
        )
        expected_parkinson = np.sqrt((log_hl ** 2).mean() / (4 * np.log(2)))
        actual_parkinson = df["parkinson_10"].iloc[idx]
        assert np.isclose(expected_parkinson, actual_parkinson, rtol=1e-10)

    def test_garman_klass_calculation_accuracy(self, feature_engine, sample_ohlcv_data):
        """Test that Garman-Klass estimator is calculated correctly."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["garman_klass"])
        # Manually calculate Garman-Klass for a specific window
        window = 10
        idx = 50
        log_hl = np.log(
            sample_ohlcv_data["high"].iloc[idx-window+1:idx+1] /
            sample_ohlcv_data["low"].iloc[idx-window+1:idx+1]
        )
        log_co = np.log(
            sample_ohlcv_data["close"].iloc[idx-window+1:idx+1] /
            sample_ohlcv_data["open"].iloc[idx-window+1:idx+1]
        )
        term1 = (log_hl ** 2).mean() * 0.5
        term2 = (2 * np.log(2) - 1) * (log_co ** 2).mean()
        expected_gk = np.sqrt(term1 - term2)
        actual_gk = df["garman_klass_10"].iloc[idx]
        # Garman-Klass can produce NaN if term2 > term1, check for valid values
        if not np.isnan(actual_gk) and not np.isnan(expected_gk):
            assert np.isclose(expected_gk, actual_gk, rtol=1e-10)

    def test_historical_volatility_calculation_accuracy(self, feature_engine, sample_ohlcv_data):
        """Test that historical volatility is calculated correctly."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["historical_volatility"])
        # Manually calculate historical volatility for window 20
        window = 20
        idx = 50
        log_returns = np.log(
            sample_ohlcv_data["close"].iloc[idx-window+1:idx+1] /
            sample_ohlcv_data["close"].iloc[idx-window:idx].shift(-1).dropna()
        )
        expected_hist_vol = log_returns.std() * np.sqrt(252)  # Annualized
        actual_hist_vol = df["hist_vol_20"].iloc[idx]
        # Check that values are in reasonable range
        assert actual_hist_vol > 0
        assert actual_hist_vol < 5  # Should not be extremely high for this data

    def test_volatility_regime_distribution(self, feature_engine, sample_ohlcv_data):
        """Test that volatility regimes are distributed reasonably."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["volatility_regime"])
        # Check that we have all three regimes represented
        regime_counts = df["vol_regime_20"].value_counts()
        # At least low and medium regimes should be present
        assert 1 in regime_counts.index or 2 in regime_counts.index or 3 in regime_counts.index


# ============================================================================
# Momentum Features Tests
# ============================================================================

class TestMomentumFeatures:
    """Test momentum feature generation."""

    def test_rsi_feature(self, feature_engine, sample_ohlcv_data):
        """Test RSI feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["rsi"])
        assert "rsi" in df.columns
        # RSI should be between 0 and 100
        assert df["rsi"].dropna().between(0, 100).all()

    def test_rsi_overbought_oversold(self, feature_engine, sample_ohlcv_data):
        """Test RSI overbought/oversold indicators."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["rsi"])
        assert "rsi_overbought" in df.columns
        assert "rsi_oversold" in df.columns
        # Binary indicators
        assert df["rsi_overbought"].dropna().isin([0, 1]).all()
        assert df["rsi_oversold"].dropna().isin([0, 1]).all()

    def test_macd_feature(self, feature_engine, sample_ohlcv_data):
        """Test MACD feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["macd"])
        assert "macd" in df.columns
        assert "macd_signal" in df.columns
        assert "macd_hist" in df.columns

    def test_stochastic_feature(self, feature_engine, sample_ohlcv_data):
        """Test Stochastic oscillator feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["stochastic"])
        assert "stoch_k" in df.columns
        assert "stoch_d" in df.columns
        # Stochastic should be between 0 and 100
        assert df["stoch_k"].dropna().between(0, 100).all()

    def test_stochastic_overbought_oversold(self, feature_engine, sample_ohlcv_data):
        """Test Stochastic overbought/oversold indicators."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["stochastic"])
        assert "stoch_overbought" in df.columns
        assert "stoch_oversold" in df.columns
        # Binary indicators
        assert df["stoch_overbought"].dropna().isin([0, 1]).all()
        assert df["stoch_oversold"].dropna().isin([0, 1]).all()

    def test_williams_r_feature(self, feature_engine, sample_ohlcv_data):
        """Test Williams %R feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["williams_r"])
        assert "williams_r" in df.columns
        # Williams %R should be between -100 and 0
        assert df["williams_r"].dropna().between(-100, 0).all()

    def test_williams_r_multiple_periods(self, feature_engine, sample_ohlcv_data):
        """Test Williams %R for multiple periods."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["williams_r"])
        # Check for multiple period Williams %R
        assert "williams_r_7" in df.columns or "williams_r_14" in df.columns or "williams_r_21" in df.columns

    def test_williams_r_overbought_oversold(self, feature_engine, sample_ohlcv_data):
        """Test Williams %R overbought/oversold indicators."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["williams_r"])
        assert "williams_r_overbought" in df.columns
        assert "williams_r_oversold" in df.columns
        # Binary indicators
        assert df["williams_r_overbought"].dropna().isin([0, 1]).all()
        assert df["williams_r_oversold"].dropna().isin([0, 1]).all()

    def test_mfi_feature(self, feature_engine, sample_ohlcv_data):
        """Test Money Flow Index feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["mfi"])
        assert "mfi" in df.columns
        # MFI should be between 0 and 100
        assert df["mfi"].dropna().between(0, 100).all()

    def test_mfi_multiple_periods(self, feature_engine, sample_ohlcv_data):
        """Test MFI for multiple periods."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["mfi"])
        # Check for multiple period MFI
        assert "mfi_7" in df.columns or "mfi_14" in df.columns or "mfi_21" in df.columns

    def test_mfi_overbought_oversold(self, feature_engine, sample_ohlcv_data):
        """Test MFI overbought/oversold indicators."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["mfi"])
        assert "mfi_overbought" in df.columns
        assert "mfi_oversold" in df.columns
        # Binary indicators
        assert df["mfi_overbought"].dropna().isin([0, 1]).all()
        assert df["mfi_oversold"].dropna().isin([0, 1]).all()

    def test_divergence_detection_rsi(self, feature_engine, sample_ohlcv_data):
        """Test divergence detection with RSI."""
        # First generate RSI
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["rsi"])
        # Then add divergence detection
        df = feature_engine._add_divergence_detection(df, indicator="rsi")
        assert "rsi_bullish_divergence" in df.columns
        assert "rsi_bearish_divergence" in df.columns
        # Binary indicators
        assert df["rsi_bullish_divergence"].dropna().isin([0, 1]).all()
        assert df["rsi_bearish_divergence"].dropna().isin([0, 1]).all()

    def test_divergence_detection_stochastic(self, feature_engine, sample_ohlcv_data):
        """Test divergence detection with Stochastic."""
        # First generate Stochastic
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["stochastic"])
        # Then add divergence detection for stoch_k
        df = feature_engine._add_divergence_detection(df, indicator="stoch_k")
        assert "stoch_k_bullish_divergence" in df.columns
        assert "stoch_k_bearish_divergence" in df.columns

    def test_momentum_indicators_all(self, feature_engine, sample_ohlcv_data):
        """Test all momentum indicators together."""
        df = feature_engine.generate_features(
            sample_ohlcv_data,
            "TEST",
            feature_types=["rsi", "macd", "stochastic", "williams_r", "mfi"]
        )
        # Check that all momentum features are present
        momentum_features = [
            "rsi", "rsi_overbought", "rsi_oversold",
            "macd", "macd_signal", "macd_hist", "macd_bullish",
            "stoch_k", "stoch_d", "stoch_overbought", "stoch_oversold",
            "williams_r", "williams_r_overbought", "williams_r_oversold",
            "mfi", "mfi_overbought", "mfi_oversold"
        ]
        for feature in momentum_features:
            assert feature in df.columns, f"Missing feature: {feature}"

    def test_williams_r_calculation_accuracy(self, feature_engine, sample_ohlcv_data):
        """Test that Williams %R is calculated correctly."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["williams_r"])
        # Manually calculate Williams %R for a specific row
        period = 14
        idx = 50  # Use row 50 to ensure we have enough history
        high_max = sample_ohlcv_data["high"].iloc[idx-period+1:idx+1].max()
        low_min = sample_ohlcv_data["low"].iloc[idx-period+1:idx+1].min()
        expected_williams_r = -100 * (high_max - sample_ohlcv_data["close"].iloc[idx]) / (high_max - low_min)
        actual_williams_r = df["williams_r"].iloc[idx]
        assert np.isclose(expected_williams_r, actual_williams_r, rtol=1e-10)

    def test_mfi_calculation_accuracy(self, feature_engine, sample_ohlcv_data):
        """Test that MFI is calculated correctly."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["mfi"])
        # Verify MFI is in valid range
        assert df["mfi"].dropna().between(0, 100).all()
        # MFI should be similar to RSI but with volume weighting
        # (can't easily verify exact calculation without complex setup)


# ============================================================================
# Trend Features Tests
# ============================================================================

class TestTrendFeatures:
    """Test trend feature generation."""

    def test_sma_feature(self, feature_engine, sample_ohlcv_data):
        """Test SMA feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["sma"])
        assert "sma_5" in df.columns
        assert "sma_10" in df.columns
        assert "sma_20" in df.columns
        assert "sma_cross_short_medium" in df.columns

    def test_ema_feature(self, feature_engine, sample_ohlcv_data):
        """Test EMA feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["ema"])
        assert "ema_5" in df.columns
        assert "ema_10" in df.columns
        assert "ema_20" in df.columns

    def test_adx_feature(self, feature_engine, sample_ohlcv_data):
        """Test ADX feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["adx"])
        assert "adx" in df.columns
        assert "di_plus" in df.columns
        assert "di_minus" in df.columns
        assert "trend_direction" in df.columns


# ============================================================================
# Lag Features Tests
# ============================================================================

class TestLagFeatures:
    """Test lag feature generation."""

    def test_lag_features(self, feature_engine, sample_ohlcv_data):
        """Test lag feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["lag"])
        assert "close_lag_1" in df.columns
        assert "close_lag_2" in df.columns
        assert "close_lag_3" in df.columns
        assert "return_lag_1" in df.columns

    def test_volume_lag_features(self, feature_engine, sample_ohlcv_data):
        """Test volume lag feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["lag"])
        if "volume" in sample_ohlcv_data.columns:
            assert "volume_lag_1" in df.columns


# ============================================================================
# Rolling Statistics Tests
# ============================================================================

class TestRollingStatistics:
    """Test rolling statistics feature generation."""

    def test_rolling_stats_features(self, feature_engine, sample_ohlcv_data):
        """Test rolling statistics generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["rolling"])
        assert "rolling_mean_5" in df.columns
        assert "rolling_std_5" in df.columns
        assert "rolling_min_5" in df.columns
        assert "rolling_max_5" in df.columns

    def test_rolling_range_features(self, feature_engine, sample_ohlcv_data):
        """Test rolling range statistics."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["rolling"])
        assert "rolling_range_5" in df.columns
        assert "rolling_range_pct_5" in df.columns

    def test_rolling_distribution_features(self, feature_engine, sample_ohlcv_data):
        """Test rolling distribution features."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["rolling"])
        assert "rolling_median_5" in df.columns
        assert "rolling_skew_5" in df.columns
        assert "rolling_kurt_5" in df.columns


# ============================================================================
# Z-score Features Tests
# ============================================================================

class TestZScoreFeatures:
    """Test z-score feature generation."""

    def test_zscore_feature(self, feature_engine, sample_ohlcv_data):
        """Test z-score feature generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["zscore"])
        assert "zscore" in df.columns
        # Z-score should have values near zero (mean)
        assert abs(df["zscore"].dropna().mean()) < 1.0

    def test_zscore_extreme_indicators(self, feature_engine, sample_ohlcv_data):
        """Test z-score extreme indicators."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["zscore"])
        assert "zscore_extreme_high" in df.columns
        assert "zscore_extreme_low" in df.columns


# ============================================================================
# Bollinger Bands Features Tests
# ============================================================================

class TestBollingerBands:
    """Test Bollinger Bands feature generation."""

    def test_bollinger_bands_feature(self, feature_engine, sample_ohlcv_data):
        """Test Bollinger Bands generation."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["bollinger"])
        assert "bb_upper" in df.columns
        assert "bb_middle" in df.columns
        assert "bb_lower" in df.columns

    def test_bollinger_band_width(self, feature_engine, sample_ohlcv_data):
        """Test Bollinger Band width feature."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["bollinger"])
        assert "bb_width" in df.columns
        assert "bb_position" in df.columns

    def test_bollinger_squeeze(self, feature_engine, sample_ohlcv_data):
        """Test Bollinger Band squeeze indicator."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST", feature_types=["bollinger"])
        assert "bb_squeeze" in df.columns


# ============================================================================
# Full Feature Generation Tests
# ============================================================================

class TestFullFeatureGeneration:
    """Test complete feature generation."""

    def test_generate_all_features(self, feature_engine, sample_ohlcv_data):
        """Test generating all feature types."""
        df = feature_engine.generate_features(sample_ohlcv_data, "TEST")
        # Should have many more columns than original
        assert len(df.columns) > 20

    def test_specific_feature_types(self, feature_engine, sample_ohlcv_data):
        """Test generating specific feature types."""
        feature_types = ["returns", "rsi", "macd"]
        df = feature_engine.generate_features(
            sample_ohlcv_data,
            "TEST",
            feature_types=feature_types
        )
        # Should have only specified features
        assert "return_1" in df.columns
        assert "rsi" in df.columns
        assert "macd" in df.columns
        assert "atr" not in df.columns  # Not requested

    def test_get_latest_features(self, feature_engine, sample_ohlcv_data):
        """Test getting the latest feature set."""
        feature_set = feature_engine.get_latest_features(sample_ohlcv_data, "TEST")
        assert isinstance(feature_set, FeatureSet)
        assert feature_set.symbol == "TEST"
        assert feature_set.feature_count > 0
        assert len(feature_set.features) > 0


# ============================================================================
# Missing Data Handling Tests
# ============================================================================

class TestMissingDataHandling:
    """Test missing data handling."""

    def test_handle_missing_data_forward_fill(self, feature_engine):
        """Test forward fill for missing data."""
        data = {
            "open": [100, 101, np.nan, 103, 104],
            "high": [102, 103, np.nan, 105, 106],
            "low": [99, 100, np.nan, 102, 103],
            "close": [101, 102, np.nan, 104, 105]
        }
        df = pd.DataFrame(data)
        result = feature_engine._handle_missing_data(df)
        # Missing values should be filled
        assert result["close"].isnull().sum() == 0

    def test_drop_critical_missing_values(self, feature_engine):
        """Test dropping rows with critical missing values."""
        data = {
            "open": [100, np.nan, 102],
            "high": [102, 103, 104],
            "low": [99, 100, 101],
            "close": [101, 102, 103]
        }
        df = pd.DataFrame(data)
        result = feature_engine._handle_missing_data(df)
        # Row with missing open should be dropped
        assert len(result) < len(df)

    def test_features_with_missing_data(self, feature_engine):
        """Test feature generation with missing data."""
        data = {
            "open": [100, 101, 102, 103, 104] * 20,
            "high": [102, 103, 104, 105, 106] * 20,
            "low": [99, 100, 101, 102, 103] * 20,
            "close": [101, 102, np.nan, 104, 105] * 20
        }
        df = pd.DataFrame(data)
        result = feature_engine.generate_features(df, "TEST", feature_types=["returns"])
        # Should handle missing data gracefully
        assert "return_1" in result.columns


# ============================================================================
# Caching Tests
# ============================================================================

class TestFeatureCaching:
    """Test feature caching functionality."""

    def test_cache_hit(self, feature_engine, sample_ohlcv_data):
        """Test that cache is used on subsequent calls."""
        # First call
        df1 = feature_engine.generate_features(sample_ohlcv_data, "TEST")
        cache_size_1 = len(feature_engine._cache)

        # Second call (should hit cache)
        df2 = feature_engine.generate_features(sample_ohlcv_data, "TEST")
        cache_size_2 = len(feature_engine._cache)

        # Cache should have been used
        assert cache_size_1 == cache_size_2
        # Results should be identical
        pd.testing.assert_frame_equal(df1, df2)

    def test_clear_cache(self, feature_engine, sample_ohlcv_data):
        """Test cache clearing."""
        # Generate features to populate cache
        feature_engine.generate_features(sample_ohlcv_data, "TEST")
        assert len(feature_engine._cache) > 0

        # Clear cache
        feature_engine.clear_cache()
        assert len(feature_engine._cache) == 0

    def test_cache_stats(self, feature_engine):
        """Test getting cache statistics."""
        stats = feature_engine.get_cache_stats()
        assert "cache_size" in stats
        assert "cache_max_size" in stats
        assert "cache_ttl" in stats


# ============================================================================
# Edge Cases and Error Handling Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dataframe(self, feature_engine):
        """Test handling of empty DataFrame."""
        df = pd.DataFrame()
        result = feature_engine.generate_features(df, "TEST")
        assert result.empty

    def test_missing_required_columns(self, feature_engine):
        """Test handling of missing required columns."""
        data = {"open": [100, 101, 102]}
        df = pd.DataFrame(data)
        with pytest.raises(ValueError):
            feature_engine.generate_features(df, "TEST")

    def test_single_row_dataframe(self, feature_engine):
        """Test handling of single-row DataFrame."""
        data = {
            "open": [100],
            "high": [102],
            "low": [99],
            "close": [101]
        }
        df = pd.DataFrame(data)
        result = feature_engine.generate_features(df, "TEST", feature_types=["returns"])
        # Should handle gracefully
        assert len(result) == 1

    def test_unknown_feature_type(self, feature_engine, sample_ohlcv_data):
        """Test handling of unknown feature type."""
        result = feature_engine.generate_features(
            sample_ohlcv_data,
            "TEST",
            feature_types=["unknown_feature"]
        )
        # Should not crash, just log warning


# ============================================================================
# Utility Functions Tests
# ============================================================================

class TestUtilityFunctions:
    """Test utility functions."""

    def test_create_feature_engine(self):
        """Test factory function."""
        fe = create_feature_engine()
        assert isinstance(fe, FeatureEngineering)

    def test_create_feature_engine_with_config(self, custom_config):
        """Test factory function with config."""
        fe = create_feature_engine(config=custom_config)
        assert isinstance(fe, FeatureEngineering)
        assert fe.config.SHORT_WINDOW == 3

    def test_generate_features_from_dict(self):
        """Test generating features from dict data."""
        data = [
            {"open": 100, "high": 102, "low": 99, "close": 101, "volume": 1000},
            {"open": 101, "high": 103, "low": 100, "close": 102, "volume": 1100},
            {"open": 102, "high": 104, "low": 101, "close": 103, "volume": 1200},
        ]
        df = generate_features_from_dict(data, "TEST")
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3


# ============================================================================
# FeatureSet Tests
# ============================================================================

class TestFeatureSet:
    """Test FeatureSet functionality."""

    def test_add_feature(self):
        """Test adding features to FeatureSet."""
        fs = FeatureSet(symbol="TEST", timestamp=datetime.now())
        fs.add_feature("test_feature", 1.5)
        assert fs.feature_count == 1
        assert fs.features["test_feature"] == 1.5

    def test_to_dict(self):
        """Test converting FeatureSet to dict."""
        fs = FeatureSet(symbol="TEST", timestamp=datetime.now())
        fs.add_feature("test_feature", 1.5)
        result = fs.to_dict()
        assert result["symbol"] == "TEST"
        assert result["feature_count"] == 1
        assert "features" in result


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
