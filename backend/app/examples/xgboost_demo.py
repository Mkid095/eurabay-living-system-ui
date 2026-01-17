"""
XGBoost Signal Source Demonstration

This script demonstrates the usage of the XGBoostSignalSource for the
EURABAY Living System ensemble signal implementation (US-002).

Usage:
    python -m app.examples.xgboost_demo
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.xgboost_signal_source import (
    XGBoostConfig,
    XGBoostSignalSource,
    create_xgboost_signal_source,
    create_and_train_source
)
from app.core.logging import logger


def generate_sample_data(symbol: str = "V10", n_samples: int = 2000) -> pd.DataFrame:
    """
    Generate synthetic OHLCV data for demonstration.

    In production, this would fetch real historical data from the database
    or MT5 connection.
    """
    np.random.seed(42)

    # Generate data
    timestamps = [datetime.now() - timedelta(hours=n_samples - i) for i in range(n_samples)]

    # Simulate price with trend, cycles, and noise
    trend = np.linspace(1.0, 1.15, n_samples)
    cycle = 0.02 * np.sin(np.linspace(0, 8 * np.pi, n_samples))
    noise = np.random.normal(0, 0.003, n_samples)
    price = 10000 * trend * (1 + cycle + noise)

    data = {
        "timestamp": timestamps,
        "open": price * (1 + np.random.uniform(-0.0005, 0.0005, n_samples)),
        "high": price * (1 + np.random.uniform(0, 0.0015, n_samples)),
        "low": price * (1 - np.random.uniform(0, 0.0015, n_samples)),
        "close": price,
        "volume": np.random.randint(100, 1000, n_samples)
    }

    df = pd.DataFrame(data)
    return df


async def main():
    """Main demonstration function."""

    print("\n" + "="*70)
    print("XGBoost Signal Source Demonstration - US-002")
    print("="*70 + "\n")

    # ========================================================================
    # Step 1: Create Configuration
    # ========================================================================

    print("Step 1: Creating XGBoost configuration")
    print("-" * 70)

    config = XGBoostConfig(
        N_ESTIMATORS=100,
        MAX_DEPTH=6,
        LEARNING_RATE=0.1,
        TRAINING_PERIOD_MONTHS=6,
        BUY_THRESHOLD=0.6,
        SELL_THRESHOLD=0.6,
        MODEL_DIR="models"
    )

    print(f"  Estimators: {config.N_ESTIMATORS}")
    print(f"  Max Depth: {config.MAX_DEPTH}")
    print(f"  Learning Rate: {config.LEARNING_RATE}")
    print(f"  Training Period: {config.TRAINING_PERIOD_MONTHS} months")
    print(f"  BUY Threshold: {config.BUY_THRESHOLD}")
    print(f"  SELL Threshold: {config.SELL_THRESHOLD}")
    print()

    # ========================================================================
    # Step 2: Generate Sample Data
    # ========================================================================

    print("Step 2: Generating sample historical data")
    print("-" * 70)

    symbol = "V10"
    historical_data = generate_sample_data(symbol=symbol, n_samples=2000)

    print(f"  Symbol: {symbol}")
    print(f"  Data Points: {len(historical_data)}")
    print(f"  Date Range: {historical_data['timestamp'].min()} to {historical_data['timestamp'].max()}")
    print(f"  Price Range: {historical_data['close'].min():.2f} - {historical_data['close'].max():.2f}")
    print()

    # ========================================================================
    # Step 3: Create and Train Signal Source
    # ========================================================================

    print("Step 3: Training XGBoost model")
    print("-" * 70)

    source = XGBoostSignalSource(symbol=symbol, config=config)

    print(f"  Initializing XGBoost signal source for {symbol}...")
    metrics = await source.train(historical_data)

    print(f"\n  Training Metrics:")
    print(f"    Accuracy: {metrics['accuracy']:.2%}")
    print(f"    Precision: {metrics['precision']:.2%}")
    print(f"    Recall: {metrics['recall']:.2%}")
    print(f"    F1 Score: {metrics['f1_score']:.2%}")
    print(f"    Training Samples: {source.training_samples}")
    print(f"    Features Used: {len(source.config.FEATURE_COLUMNS)}")
    print(f"    Model Version: {source.model_version}")
    print()

    # Check win rate acceptance criteria (>55%)
    if metrics['accuracy'] > 0.55:
        print(f"  ✓ PASS: Model accuracy ({metrics['accuracy']:.2%}) exceeds 55% threshold")
    else:
        print(f"  ✗ FAIL: Model accuracy ({metrics['accuracy']:.2%}) below 55% threshold")
    print()

    # ========================================================================
    # Step 4: Display Feature Importance
    # ========================================================================

    print("Step 4: Top 10 Feature Importance")
    print("-" * 70)

    source.print_feature_importance(top_n=10)
    print()

    # ========================================================================
    # Step 5: Generate Predictions
    # ========================================================================

    print("Step 5: Generating Trading Signals")
    print("-" * 70)

    # Generate predictions on recent data
    recent_data = historical_data.tail(500).copy()

    # Generate multiple predictions to demonstrate
    for i in range(5):
        signal = await source.predict(current_data=recent_data)

        if signal:
            print(f"\n  Signal #{i+1}:")
            print(f"    Direction: {signal.direction.value}")
            print(f"    Confidence: {signal.confidence:.2%}")
            print(f"    Timestamp: {signal.timestamp}")

            probs = signal.metadata.get("probabilities", {})
            print(f"    Probabilities:")
            print(f"      BUY:  {probs.get('BUY', 0):.2%}")
            print(f"      SELL: {probs.get('SELL', 0):.2%}")
            print(f"      HOLD: {probs.get('HOLD', 0):.2%}")
        else:
            print(f"\n  Signal #{i+1}: Failed to generate")

    print()

    # ========================================================================
    # Step 6: Model Persistence
    # ========================================================================

    print("Step 6: Model Persistence")
    print("-" * 70)

    model_file = Path(config.MODEL_DIR) / f"{config.MODEL_VERSION_PREFIX}_{symbol}.json"
    if model_file.exists():
        print(f"  ✓ Model saved to: {model_file}")
        print(f"    File size: {model_file.stat().st_size / 1024:.2f} KB")

    metadata_file = model_file.with_suffix(".metadata.json")
    if metadata_file.exists():
        print(f"  ✓ Metadata saved to: {metadata_file}")

    print()

    # ========================================================================
    # Step 7: Load Existing Model
    # ========================================================================

    print("Step 7: Loading Existing Model")
    print("-" * 70)

    # Create new instance and load
    new_source = XGBoostSignalSource(symbol=symbol, config=config)
    success = new_source._load_model()

    if success:
        print(f"  ✓ Successfully loaded existing model")
        print(f"    Model Version: {new_source.model_version}")
        print(f"    Training Samples: {new_source.training_samples}")

        # Generate prediction with loaded model
        signal = await new_source.predict(current_data=recent_data)
        if signal:
            print(f"    Generated Signal: {signal.direction.value} ({signal.confidence:.2%})")
    else:
        print(f"  ✗ Failed to load existing model")

    print()

    # ========================================================================
    # Step 8: Model Information
    # ========================================================================

    print("Step 8: Model Information Summary")
    print("-" * 70)

    info = source.get_model_info()

    print(f"  Symbol: {info['symbol']}")
    print(f"  Model Version: {info['model_version']}")
    print(f"  Is Trained: {info['is_trained']}")
    print(f"  Training Samples: {info['training_samples']}")
    print(f"  Feature Count: {info['feature_count']}")
    print(f"  Model File: {info['model_file']}")
    print(f"\n  Configuration:")
    print(f"    N Estimators: {info['config']['n_estimators']}")
    print(f"    Max Depth: {info['config']['max_depth']}")
    print(f"    Learning Rate: {info['config']['learning_rate']}")
    print(f"    BUY Threshold: {info['config']['buy_threshold']}")
    print(f"    SELL Threshold: {info['config']['sell_threshold']}")
    print(f"\n  Performance Metrics:")
    print(f"    Accuracy: {info['metrics']['accuracy']:.2%}")
    print(f"    F1 Score: {info['metrics']['f1_score']:.2%}")

    print()
    print("="*70)
    print("Demonstration Complete!")
    print("="*70)
    print()


if __name__ == "__main__":
    asyncio.run(main())
