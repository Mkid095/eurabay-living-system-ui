"""
Standalone test runner for Feature Engineering Service.

This script runs tests for the feature engineering module without requiring pytest.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.services.feature_engineering import (
    FeatureEngineering,
    FeatureConfig,
    FeatureSet,
    create_feature_engine,
    generate_features_from_dict
)


def generate_sample_data(n_periods=100):
    """Generate sample OHLCV data for testing."""
    np.random.seed(42)

    dates = pd.date_range(
        start=datetime.now() - timedelta(days=n_periods),
        periods=n_periods,
        freq="H"
    )

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

    df = pd.DataFrame(data)
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)

    return df


class TestRunner:
    """Simple test runner."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def run_test(self, name, test_func):
        """Run a single test."""
        try:
            test_func()
            self.passed += 1
            print(f"[PASS] {name}")
            return True
        except AssertionError as e:
            self.failed += 1
            self.errors.append((name, str(e)))
            print(f"[FAIL] {name}: {e}")
            return False
        except Exception as e:
            self.failed += 1
            self.errors.append((name, str(e)))
            print(f"[ERROR] {name}: {e}")
            return False

    def summary(self):
        """Print test summary."""
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Tests run: {total}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Success rate: {self.passed/total*100:.1f}%")
        print(f"{'='*60}")

        if self.errors:
            print("\nFailed tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")

        return self.failed == 0


def test_initialization():
    """Test FeatureEngineering initialization."""
    fe = FeatureEngineering()
    assert fe.config is not None
    assert fe.config.SHORT_WINDOW == 5
    assert len(fe._feature_registry) > 0


def test_custom_config():
    """Test custom configuration."""
    config = FeatureConfig(SHORT_WINDOW=3, RSI_PERIOD=10)
    fe = FeatureEngineering(config=config)
    assert fe.config.SHORT_WINDOW == 3
    assert fe.config.RSI_PERIOD == 10


def test_price_features():
    """Test price-based features."""
    fe = FeatureEngineering()
    df = generate_sample_data()
    result = fe.generate_features(df, "TEST", feature_types=["returns"])

    assert "return_1" in result.columns
    assert "return_5" in result.columns
    assert "return_10" in result.columns


def test_volatility_features():
    """Test volatility features."""
    fe = FeatureEngineering()
    df = generate_sample_data()
    result = fe.generate_features(df, "TEST", feature_types=["atr", "std_dev"])

    assert "atr" in result.columns
    assert "atr_ratio" in result.columns
    assert "std_5" in result.columns
    assert (result["atr"].dropna() > 0).all()


def test_momentum_features():
    """Test momentum features."""
    fe = FeatureEngineering()
    df = generate_sample_data()
    result = fe.generate_features(df, "TEST", feature_types=["rsi", "macd"])

    assert "rsi" in result.columns
    assert result["rsi"].dropna().between(0, 100).all()
    assert "macd" in result.columns
    assert "macd_signal" in result.columns


def test_trend_features():
    """Test trend features."""
    fe = FeatureEngineering()
    df = generate_sample_data()
    result = fe.generate_features(df, "TEST", feature_types=["sma", "ema", "adx"])

    assert "sma_5" in result.columns
    assert "ema_5" in result.columns
    assert "adx" in result.columns


def test_lag_features():
    """Test lag features."""
    fe = FeatureEngineering()
    df = generate_sample_data()
    result = fe.generate_features(df, "TEST", feature_types=["lag"])

    assert "close_lag_1" in result.columns
    assert "return_lag_1" in result.columns


def test_rolling_stats():
    """Test rolling statistics."""
    fe = FeatureEngineering()
    df = generate_sample_data()
    result = fe.generate_features(df, "TEST", feature_types=["rolling"])

    assert "rolling_mean_5" in result.columns
    assert "rolling_std_5" in result.columns
    assert "rolling_min_5" in result.columns
    assert "rolling_max_5" in result.columns


def test_zscore_features():
    """Test z-score features."""
    fe = FeatureEngineering()
    df = generate_sample_data()
    result = fe.generate_features(df, "TEST", feature_types=["zscore"])

    assert "zscore" in result.columns
    assert abs(result["zscore"].dropna().mean()) < 1.0


def test_bollinger_bands():
    """Test Bollinger Bands."""
    fe = FeatureEngineering()
    df = generate_sample_data()
    result = fe.generate_features(df, "TEST", feature_types=["bollinger"])

    assert "bb_upper" in result.columns
    assert "bb_middle" in result.columns
    assert "bb_lower" in result.columns
    assert "bb_width" in result.columns


def test_full_feature_generation():
    """Test generating all features."""
    fe = FeatureEngineering()
    df = generate_sample_data()
    result = fe.generate_features(df, "TEST")

    assert len(result.columns) > 20
    assert "return_1" in result.columns
    assert "rsi" in result.columns
    assert "macd" in result.columns


def test_get_latest_features():
    """Test getting latest feature set."""
    fe = FeatureEngineering()
    df = generate_sample_data()
    feature_set = fe.get_latest_features(df, "TEST")

    assert isinstance(feature_set, FeatureSet)
    assert feature_set.symbol == "TEST"
    assert feature_set.feature_count > 0
    assert len(feature_set.features) > 0


def test_missing_data_handling():
    """Test missing data handling."""
    fe = FeatureEngineering()
    data = {
        "open": [100, 101, np.nan, 103, 104],
        "high": [102, 103, np.nan, 105, 106],
        "low": [99, 100, np.nan, 102, 103],
        "close": [101, 102, np.nan, 104, 105]
    }
    df = pd.DataFrame(data)
    result = fe._handle_missing_data(df)

    assert result["close"].isnull().sum() == 0


def test_caching():
    """Test feature caching."""
    fe = FeatureEngineering()
    df = generate_sample_data()

    # First call
    df1 = fe.generate_features(df, "TEST")
    cache_size_1 = len(fe._cache)

    # Second call (should hit cache)
    df2 = fe.generate_features(df, "TEST")
    cache_size_2 = len(fe._cache)

    assert cache_size_1 == cache_size_2
    pd.testing.assert_frame_equal(df1, df2)


def test_clear_cache():
    """Test cache clearing."""
    fe = FeatureEngineering()
    df = generate_sample_data()

    fe.generate_features(df, "TEST")
    assert len(fe._cache) > 0

    fe.clear_cache()
    assert len(fe._cache) == 0


def test_cache_stats():
    """Test cache statistics."""
    fe = FeatureEngineering()
    stats = fe.get_cache_stats()

    assert "cache_size" in stats
    assert "cache_max_size" in stats
    assert "cache_ttl" in stats


def test_empty_dataframe():
    """Test empty DataFrame handling."""
    fe = FeatureEngineering()
    df = pd.DataFrame()
    result = fe.generate_features(df, "TEST")

    assert result.empty


def test_missing_columns():
    """Test missing required columns."""
    fe = FeatureEngineering()
    df = pd.DataFrame({"open": [100, 101, 102]})

    try:
        fe.generate_features(df, "TEST")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected


def test_factory_function():
    """Test factory function."""
    fe = create_feature_engine()
    assert isinstance(fe, FeatureEngineering)


def test_generate_from_dict():
    """Test generating features from dict."""
    data = [
        {"open": 100, "high": 102, "low": 99, "close": 101, "volume": 1000},
        {"open": 101, "high": 103, "low": 100, "close": 102, "volume": 1100},
        {"open": 102, "high": 104, "low": 101, "close": 103, "volume": 1200},
    ]
    df = generate_features_from_dict(data, "TEST")

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3


def test_feature_set():
    """Test FeatureSet class."""
    fs = FeatureSet(symbol="TEST", timestamp=datetime.now())
    fs.add_feature("test_feature", 1.5)

    assert fs.feature_count == 1
    assert fs.features["test_feature"] == 1.5

    result = fs.to_dict()
    assert result["symbol"] == "TEST"
    assert result["feature_count"] == 1


def main():
    """Run all tests."""
    print("Running Feature Engineering Tests...")
    print("="*60)

    tests = [
        ("Initialization", test_initialization),
        ("Custom Configuration", test_custom_config),
        ("Price Features", test_price_features),
        ("Volatility Features", test_volatility_features),
        ("Momentum Features", test_momentum_features),
        ("Trend Features", test_trend_features),
        ("Lag Features", test_lag_features),
        ("Rolling Statistics", test_rolling_stats),
        ("Z-score Features", test_zscore_features),
        ("Bollinger Bands", test_bollinger_bands),
        ("Full Feature Generation", test_full_feature_generation),
        ("Get Latest Features", test_get_latest_features),
        ("Missing Data Handling", test_missing_data_handling),
        ("Caching", test_caching),
        ("Clear Cache", test_clear_cache),
        ("Cache Stats", test_cache_stats),
        ("Empty DataFrame", test_empty_dataframe),
        ("Missing Columns", test_missing_columns),
        ("Factory Function", test_factory_function),
        ("Generate From Dict", test_generate_from_dict),
        ("FeatureSet Class", test_feature_set),
    ]

    runner = TestRunner()

    for name, test_func in tests:
        runner.run_test(name, test_func)

    success = runner.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
