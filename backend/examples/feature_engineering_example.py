"""
Feature Engineering Usage Example

This example demonstrates how to use the FeatureEngineering service
to transform raw OHLCV data into ML features.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.feature_engineering import (
    FeatureEngineering,
    FeatureConfig,
    create_feature_engine,
    generate_features_from_dict
)


def generate_sample_data(n_periods=100):
    """Generate sample OHLCV data."""
    np.random.seed(42)

    dates = pd.date_range(
        start=datetime.now() - timedelta(days=n_periods),
        periods=n_periods,
        freq="h"
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


def example_basic_usage():
    """Example 1: Basic usage with default settings."""
    print("="*60)
    print("Example 1: Basic Feature Generation")
    print("="*60)

    # Create feature engineering instance
    fe = FeatureEngineering()

    # Generate sample data
    df = generate_sample_data(100)
    print(f"\nInput data shape: {df.shape}")
    print(f"Input columns: {list(df.columns)}")

    # Generate all features
    df_with_features = fe.generate_features(df, symbol="V10")

    print(f"\nOutput data shape: {df_with_features.shape}")
    print(f"Output columns ({len(df_with_features.columns)} total):")
    print(f"  {', '.join(df_with_features.columns[:20])}...")
    print(f"\nFeatures generated: {len(df_with_features.columns) - len(df.columns)}")


def example_selective_features():
    """Example 2: Generate specific feature types."""
    print("\n" + "="*60)
    print("Example 2: Selective Feature Generation")
    print("="*60)

    fe = FeatureEngineering()
    df = generate_sample_data(100)

    # Generate only specific feature types
    feature_types = ["returns", "rsi", "macd", "bollinger"]
    df_features = fe.generate_features(df, "V10", feature_types=feature_types)

    print(f"\nRequested features: {', '.join(feature_types)}")
    print(f"Generated columns: {list(df_features.columns)}")


def example_custom_config():
    """Example 3: Custom configuration."""
    print("\n" + "="*60)
    print("Example 3: Custom Configuration")
    print("="*60)

    # Create custom config
    config = FeatureConfig(
        SHORT_WINDOW=3,
        MEDIUM_WINDOW=7,
        LONG_WINDOW=14,
        RSI_PERIOD=10,
        CACHE_TTL=30
    )

    fe = FeatureEngineering(config=config)
    df = generate_sample_data(100)

    df_features = fe.generate_features(df, "V10", feature_types=["sma", "ema"])

    print(f"\nCustom SMA/EMA windows: {config.SHORT_WINDOW}, {config.MEDIUM_WINDOW}, {config.LONG_WINDOW}")
    print(f"Generated SMA columns: {[col for col in df_features.columns if 'sma' in col]}")


def example_get_latest_features():
    """Example 4: Get latest feature set."""
    print("\n" + "="*60)
    print("Example 4: Get Latest Feature Set")
    print("="*60)

    fe = FeatureEngineering()
    df = generate_sample_data(100)

    # Get the latest feature set
    feature_set = fe.get_latest_features(df, "V10")

    print(f"\nSymbol: {feature_set.symbol}")
    print(f"Timestamp: {feature_set.timestamp}")
    print(f"Feature count: {feature_set.feature_count}")
    print(f"\nSample features (first 10):")
    for i, (name, value) in enumerate(list(feature_set.features.items())[:10]):
        print(f"  {name}: {value:.4f}")


def example_feature_caching():
    """Example 5: Feature caching."""
    print("\n" + "="*60)
    print("Example 5: Feature Caching")
    print("="*60)

    fe = FeatureEngineering()
    df = generate_sample_data(100)

    # First call - generates features
    df1 = fe.generate_features(df, "V10", feature_types=["returns", "rsi"])

    # Check cache stats
    stats = fe.get_cache_stats()
    print(f"\nCache size after first call: {stats['cache_size']}")

    # Second call - uses cache
    df2 = fe.generate_features(df, "V10", feature_types=["returns", "rsi"])

    print(f"Cache size after second call: {stats['cache_size']}")
    print(f"Results identical: {df1.equals(df2)}")

    # Clear cache
    fe.clear_cache()
    print(f"Cache size after clear: {len(fe._cache)}")


def example_from_dict():
    """Example 6: Generate features from list of dicts."""
    print("\n" + "="*60)
    print("Example 6: Generate Features from Dict")
    print("="*60)

    # Data as list of dictionaries (e.g., from API)
    data = [
        {"open": 10000, "high": 10020, "low": 9990, "close": 10010, "volume": 5000},
        {"open": 10010, "high": 10030, "low": 10000, "close": 10025, "volume": 5500},
        {"open": 10025, "high": 10040, "low": 10015, "close": 10035, "volume": 6000},
    ]

    # Generate features
    df = generate_features_from_dict(data, "V10")

    print(f"\nInput: {len(data)} data points")
    print(f"Output shape: {df.shape}")
    print(f"Generated features: {len(df.columns) - 5} (excluding OHLCV)")


def example_available_features():
    """Example 7: List available feature types."""
    print("\n" + "="*60)
    print("Example 7: Available Feature Types")
    print("="*60)

    fe = FeatureEngineering()
    feature_names = fe.get_feature_names()

    print(f"\nAvailable feature types ({len(feature_names)}):")
    for name in feature_names:
        print(f"  - {name}")


def main():
    """Run all examples."""
    examples = [
        example_basic_usage,
        example_selective_features,
        example_custom_config,
        example_get_latest_features,
        example_feature_caching,
        example_from_dict,
        example_available_features,
    ]

    for example in examples:
        try:
            example()
        except Exception as e:
            print(f"\nError in {example.__name__}: {e}")

    print("\n" + "="*60)
    print("Examples completed!")
    print("="*60)


if __name__ == "__main__":
    main()
