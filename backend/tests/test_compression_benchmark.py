"""
Compression benchmark for TimeSeriesStorage.

This script tests the compression ratio with realistic market data volumes.
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime, date
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from storage.time_series_storage import TimeSeriesStorage


def create_large_dataset(num_rows: int = 10000) -> pd.DataFrame:
    """Create a large realistic market dataset."""
    print(f"Creating dataset with {num_rows} rows...")

    timestamps = [
        datetime(2024, 1, 15, 0, 0, 0) + pd.Timedelta(minutes=i)
        for i in range(num_rows)
    ]

    # Simulate realistic price movement
    import random
    random.seed(42)

    base_price = 1.0850
    prices = []
    for _ in range(num_rows):
        change = random.uniform(-0.0010, 0.0010)
        base_price += change
        prices.append(base_price)

    data = {
        "timestamp": timestamps,
        "open": [p - random.uniform(0.0001, 0.0003) for p in prices],
        "high": [p + random.uniform(0.0001, 0.0003) for p in prices],
        "low": [p - random.uniform(0.0002, 0.0005) for p in prices],
        "close": prices,
        "volume": [random.randint(1000, 5000) for _ in range(num_rows)],
    }

    df = pd.DataFrame(data)
    return df


def benchmark_compression():
    """Run compression benchmark with realistic data volumes."""
    temp_dir = tempfile.mkdtemp()

    try:
        print("=" * 60)
        print("TimeSeriesStorage Compression Benchmark")
        print("=" * 60)

        storage = TimeSeriesStorage(
            base_path=os.path.join(temp_dir, "market"),
            compression="zstd",
            compression_level=10,
        )

        # Test different data volumes
        test_sizes = [1000, 10000, 100000]

        for size in test_sizes:
            print(f"\n--- Testing with {size:,} rows ---")

            df = create_large_dataset(size)

            # Calculate CSV size
            csv_size = len(df.to_csv(index=False).encode("utf-8"))
            print(f"CSV size: {csv_size:,} bytes ({csv_size / 1024:.1f} KB)")

            # Save as Parquet
            result = storage.save_market_data(df, symbol="EURUSD")

            parquet_size = result["total_size_bytes"]
            compression_ratio = result["compression_ratio"]

            print(f"Parquet size: {parquet_size:,} bytes ({parquet_size / 1024:.1f} KB)")
            print(f"Compression ratio: {compression_ratio:.2f}x")
            print(f"Space saved: {(1 - 1/compression_ratio) * 100:.1f}%")

            # Clean up for next test
            shutil.rmtree(os.path.join(temp_dir, "market"), ignore_errors=True)
            storage.base_path.mkdir(parents=True, exist_ok=True)
            storage.metadata_path.mkdir(parents=True, exist_ok=True)

        print("\n" + "=" * 60)
        print("Benchmark complete!")
        print("=" * 60)

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    benchmark_compression()
