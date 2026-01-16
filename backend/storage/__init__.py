"""
Storage module for time-series data using Parquet format.

This module provides efficient storage and retrieval of market data
with compression and partitioning support.
"""

from .time_series_storage import TimeSeriesStorage

__all__ = ["TimeSeriesStorage"]
