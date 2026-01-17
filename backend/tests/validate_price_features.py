"""
Validation script for price-based features distribution.

This script validates that price-based features have reasonable distributions
and statistical properties when applied to realistic market data.
"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.feature_engineering import FeatureEngineering


def generate_realistic_data(n_periods: int = 1000) -> pd.DataFrame:
    """Generate realistic OHLCV data for validation."""
    np.random.seed(42)

    dates = pd.date_range(start=datetime.now() - timedelta(days=n_periods), periods=n_periods, freq="h")

    # Generate realistic price movements with trend and volatility
    base_price = 10000.0
    trend = np.linspace(0, 500, n_periods)  # Slight upward trend
    price_changes = np.random.randn(n_periods) * 50  # Random walk
    prices = base_price + trend + np.cumsum(price_changes)

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


def validate_feature_distributions(df: pd.DataFrame, features_df: pd.DataFrame) -> dict:
    """
    Validate that features have reasonable distributions.

    Returns:
        Dictionary with validation results
    """
    results = {
        "passed": [],
        "failed": [],
        "warnings": []
    }

    # Validate returns (should be small, mostly between -0.05 and 0.05)
    for period in [1, 5, 10, 20]:
        col = f"return_{period}"
        if col in features_df.columns:
            returns = features_df[col].dropna()
            extreme_count = ((returns < -0.1) | (returns > 0.1)).sum()
            extreme_pct = (extreme_count / len(returns)) * 100

            if extreme_pct < 5:  # Less than 5% extreme returns
                results["passed"].append(f"{col}: reasonable distribution ({extreme_pct:.2f}% extreme)")
            else:
                results["warnings"].append(f"{col}: {extreme_pct:.2f}% extreme values")

    # Validate log returns (should be roughly symmetric around 0)
    for period in [1, 5, 10, 20]:
        col = f"log_return_{period}"
        if col in features_df.columns:
            log_returns = features_df[col].dropna()
            mean = log_returns.mean()
            std = log_returns.std()

            if abs(mean) < 0.01:  # Mean should be close to 0
                results["passed"].append(f"{col}: mean centered ({mean:.6f})")
            else:
                results["warnings"].append(f"{col}: mean = {mean:.6f} (expected near 0)")

    # Validate price changes (should vary with period)
    for period in [1, 5, 10, 20]:
        col = f"price_change_{period}"
        if col in features_df.columns:
            changes = features_df[col].dropna()
            std = changes.std()

            if std > 0:  # Should have some variation
                results["passed"].append(f"{col}: has variation (std={std:.2f})")
            else:
                results["failed"].append(f"{col}: no variation detected")

    # Validate ROC (should be percentage-based)
    for period in [1, 3, 5, 10, 20]:
        col = f"roc_{period}"
        if col in features_df.columns:
            roc = features_df[col].dropna()
            # ROC values should be reasonable percentages
            extreme_count = ((roc < -50) | (roc > 50)).sum()
            extreme_pct = (extreme_count / len(roc)) * 100

            if extreme_pct < 10:
                results["passed"].append(f"{col}: reasonable percentage range")
            else:
                results["warnings"].append(f"{col}: {extreme_pct:.2f}% extreme values")

    # Validate price relative to MA
    for window in [5, 10, 20, 50, 200]:
        if len(features_df) > window:
            col = f"price_rel_sma_{window}"
            if col in features_df.columns:
                rel_ma = features_df[col].dropna()
                # Price relative to MA should typically be within +/- 0.5 (50%)
                extreme_count = ((rel_ma < -0.5) | (rel_ma > 0.5)).sum()
                extreme_pct = (extreme_count / len(rel_ma)) * 100

                if extreme_pct < 20:
                    results["passed"].append(f"{col}: reasonable MA relationship")
                else:
                    results["warnings"].append(f"{col}: {extreme_pct:.2f}% far from MA")

    # Check for missing values in critical features
    critical_features = ["return_1", "log_return_1", "price_change_1", "roc_5"]
    for feature in critical_features:
        if feature in features_df.columns:
            missing_pct = (features_df[feature].isnull().sum() / len(features_df)) * 100
            if missing_pct < 10:  # Less than 10% missing
                results["passed"].append(f"{feature}: low missing data ({missing_pct:.1f}%)")
            else:
                results["warnings"].append(f"{feature}: {missing_pct:.1f}% missing data")

    return results


def print_validation_results(results: dict):
    """Print validation results in a formatted way."""
    print("\n" + "=" * 80)
    print("PRICE-BASED FEATURES VALIDATION RESULTS")
    print("=" * 80)

    print(f"\n[PASSED] ({len(results['passed'])} checks):")
    for check in results['passed']:
        print(f"  - {check}")

    if results['warnings']:
        print(f"\n[WARNINGS] ({len(results['warnings'])} items):")
        for warning in results['warnings']:
            print(f"  - {warning}")

    if results['failed']:
        print(f"\n[FAILED] ({len(results['failed'])} items):")
        for failure in results['failed']:
            print(f"  - {failure}")

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total Checks: {len(results['passed']) + len(results['warnings']) + len(results['failed'])}")
    print(f"Passed: {len(results['passed'])}")
    print(f"Warnings: {len(results['warnings'])}")
    print(f"Failed: {len(results['failed'])}")

    if not results['failed'] and len(results['warnings']) <= 2:
        print("\n[VALIDATION PASSED]: Features have reasonable distributions")
    else:
        print("\n[VALIDATION COMPLETE]: Review warnings and failures")


def main():
    """Main validation function."""
    print("Generating realistic market data...")
    df = generate_realistic_data(1000)

    print("Generating price-based features...")
    fe = FeatureEngineering()

    price_features = [
        "returns",
        "log_returns",
        "price_change",
        "price_relative_ma",
        "price_momentum"
    ]

    features_df = fe.generate_features(df, "V10", feature_types=price_features)

    print(f"Generated {len(features_df.columns)} total columns")
    print(f"Original data: {len(df.columns)} columns")
    print(f"New features: {len(features_df.columns) - len(df.columns)} columns")

    # List all new price-based features
    feature_cols = set(features_df.columns) - set(df.columns)
    print(f"\nPrice-based features created ({len(feature_cols)}):")
    for col in sorted(feature_cols):
        print(f"  • {col}")

    # Validate distributions
    print("\nValidating feature distributions...")
    results = validate_feature_distributions(df, features_df)

    # Print results
    print_validation_results(results)

    # Print some statistics
    print("\n" + "=" * 80)
    print("FEATURE STATISTICS (Sample)")
    print("=" * 80)

    sample_features = ["return_1", "return_5", "log_return_1", "price_change_1", "roc_5", "price_rel_sma_20"]
    for feature in sample_features:
        if feature in features_df.columns:
            data = features_df[feature].dropna()
            print(f"\n{feature}:")
            print(f"  Mean:     {data.mean():.6f}")
            print(f"  Std Dev:  {data.std():.6f}")
            print(f"  Min:      {data.min():.6f}")
            print(f"  Max:      {data.max():.6f}")
            print(f"  Median:   {data.median():.6f}")


if __name__ == "__main__":
    main()
