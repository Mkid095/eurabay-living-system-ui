"""
OHLCV Data Collector - Specialized service for OHLCV data collection and Parquet storage.

This service handles:
- OHLCV data collection from MT5 for all volatility indices across multiple timeframes
- Parquet format storage with snappy compression for efficiency
- Data validation (OHLC relationships, volume checks)
- Data deduplication based on timestamp
- Data retention policy (90 days for detailed, 1 year for daily)
- Monitoring for data gaps and missing candles
- Comprehensive quality monitoring and alerting
"""

import asyncio
from datetime import datetime, timedelta, timezone, date
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import pandas as pd
from loguru import logger

from app.core.config import settings
from app.services.mt5_service import MT5Service, OHLCVData, MT5Error


class OHLCVQuality(Enum):
    """OHLCV data quality indicators."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    BAD = "bad"


@dataclass
class OHLCVQualityReport:
    """Quality assessment report for OHLCV data."""
    symbol: str
    timeframe: str
    timestamp: datetime
    quality: OHLCVQuality
    total_candles: int
    missing_candles: int
    duplicate_candles: int
    invalid_ohlc_count: int
    invalid_volume_count: int
    data_gaps: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    score: float = 0.0  # 0.0 to 1.0


@dataclass
class OHLCVCollectionStats:
    """Statistics for OHLCV collection operations."""
    symbol: str
    timeframe: str
    total_collected: int
    total_stored: int
    duplicate_count: int
    invalid_count: int
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    errors: List[str] = field(default_factory=list)


@dataclass
class OHLCVDataRecord:
    """OHLCV data record for storage and validation."""
    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


class OHLCVDataCollector:
    """
    Specialized OHLCV data collector for multi-timeframe market data.

    Features:
    - Multi-timeframe data fetching (M1, M5, M15, H1, H4, D1)
    - Parquet storage with snappy compression
    - Organized by symbol and timeframe for efficient querying
    - Comprehensive OHLC validation (high >= open/close/low, low <= open/close/high)
    - Volume validation (non-negative, reasonable ranges)
    - Timestamp-based deduplication
    - Data retention policy (90 days detailed, 1 year daily)
    - Data gap detection and monitoring
    - Missing candle alerting
    - Batch insert optimization for high throughput

    Usage:
        collector = OHLCVDataCollector()
        await collector.initialize()
        await collector.start_continuous_collection()
    """

    # Timeframes to collect
    TIMEFRAMES = ["M1", "M5", "M15", "H1", "H4", "D1"]

    # MT5 timeframe mapping
    MT5_TIMEFRAMES = {
        "M1": 1,    # TIMEFRAME_M1
        "M5": 5,    # TIMEFRAME_M5
        "M15": 15,  # TIMEFRAME_M15
        "H1": 60,   # TIMEFRAME_H1
        "H4": 240,  # TIMEFRAME_H4
        "D1": 1440, # TIMEFRAME_D1
    }

    # Data retention settings
    DETAILED_RETENTION_DAYS = 90   # For M1-H4 timeframes
    DAILY_RETENTION_DAYS = 365     # For D1 timeframe (1 year)

    # Collection settings
    COLLECTION_INTERVAL = 60        # Seconds between collection cycles
    BATCH_INSERT_SIZE = 100        # Process candles in batches
    DEFAULT_BARS_TO_FETCH = 100    # Default number of bars to fetch

    # Data quality thresholds
    MAX_MISSING_CANDLES = 5        # Alert threshold for missing candles
    MAX_PRICE_CHANGE_PERCENT = 50  # Max reasonable price change in one candle
    MIN_VOLUME = 0                 # Minimum valid volume
    MAX_VOLUME = 1000000           # Maximum valid volume (prevents data errors)

    # Gap detection settings (in timeframe units)
    GAP_THRESHOLDS = {
        "M1": 120,     # 2 minutes
        "M5": 600,     # 10 minutes
        "M15": 1800,   # 30 minutes
        "H1": 7200,    # 2 hours
        "H4": 28800,   # 8 hours
        "D1": 172800,  # 2 days
    }

    def __init__(
        self,
        mt5_service: Optional[MT5Service] = None,
        symbols: Optional[List[str]] = None,
        base_path: Optional[str] = None,
    ):
        """
        Initialize OHLCVDataCollector.

        Args:
            mt5_service: MT5 service instance (created if not provided)
            symbols: List of symbols to collect (defaults to volatility indices)
            base_path: Base path for Parquet storage (defaults to backend/data/parquet/)
        """
        self.mt5_service = mt5_service
        self.symbols = symbols or settings.parsed_trading_symbols

        # Storage setup
        if base_path is None:
            self.base_path = Path(settings.DATA_DIR) / "parquet"
        else:
            self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Collection state
        self.is_running = False
        self.is_initialized = False
        self._collection_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        # Quality monitoring
        self._quality_reports: Dict[str, OHLCVQualityReport] = {}
        self._last_collection_time: Dict[str, datetime] = {}

        # Statistics
        self._stats: Dict[str, OHLCVCollectionStats] = {}

        logger.info(
            f"OHLCVDataCollector initialized for symbols: {', '.join(self.symbols)}, "
            f"timeframes: {', '.join(self.TIMEFRAMES)}"
        )

    async def initialize(self) -> None:
        """
        Initialize the OHLCV data collector.

        Creates required service instances and validates connections.
        Raises RuntimeError if initialization fails.
        """
        if self.is_initialized:
            logger.warning("OHLCVDataCollector already initialized")
            return

        try:
            # Create MT5 service if not provided
            if self.mt5_service is None:
                self.mt5_service = MT5Service()
                await self.mt5_service.initialize()
                logger.info("MT5 service initialized")

            # Validate MT5 connection
            if not self.mt5_service.is_connected:
                raise RuntimeError("MT5 service is not connected")

            # Initialize statistics for each symbol/timeframe combination
            for symbol in self.symbols:
                for timeframe in self.TIMEFRAMES:
                    key = f"{symbol}_{timeframe}"
                    self._stats[key] = OHLCVCollectionStats(
                        symbol=symbol,
                        timeframe=timeframe,
                        total_collected=0,
                        total_stored=0,
                        duplicate_count=0,
                        invalid_count=0,
                        start_time=datetime.now(timezone.utc),
                        end_time=datetime.now(timezone.utc),
                        duration_seconds=0.0,
                    )
                    self._last_collection_time[key] = datetime.now(timezone.utc)

            self.is_initialized = True
            logger.info("OHLCVDataCollector initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize OHLCVDataCollector: {e}")
            raise RuntimeError(f"Initialization failed: {e}") from e

    async def start_continuous_collection(self) -> None:
        """
        Start continuous OHLCV data collection for all configured symbols and timeframes.

        Raises RuntimeError if service is not initialized.
        """
        if not self.is_initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        if self.is_running:
            logger.warning("OHLCV collection already running")
            return

        self.is_running = True
        self._stop_event.clear()

        logger.info("Starting continuous OHLCV data collection...")

        # Start collection task
        self._collection_task = asyncio.create_task(self._collection_loop())

        logger.info(
            f"OHLCV data collection started for {len(self.symbols)} symbols "
            f"and {len(self.TIMEFRAMES)} timeframes"
        )

    async def stop_continuous_collection(self) -> None:
        """
        Stop continuous OHLCV data collection.

        Gracefully stops the collection task and waits for completion.
        """
        if not self.is_running:
            logger.warning("OHLCV collection not running")
            return

        logger.info("Stopping continuous OHLCV data collection...")
        self._stop_event.set()
        self.is_running = False

        # Cancel task
        if self._collection_task and not self._collection_task.done():
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass

        # Update final statistics
        for key in self._stats:
            self._stats[key].end_time = datetime.now(timezone.utc)
            self._stats[key].duration_seconds = (
                self._stats[key].end_time - self._stats[key].start_time
            ).total_seconds()

        logger.info("OHLCV data collection stopped")

    async def _collection_loop(self) -> None:
        """
        Continuous loop for OHLCV data collection.

        Fetches and stores OHLCV data for all symbols and timeframes.
        Implements exponential backoff on errors.
        """
        retry_delay = 1.0
        max_retry_delay = 30.0

        while not self._stop_event.is_set():
            try:
                # Collect OHLCV data for all symbol/timeframe combinations
                for symbol in self.symbols:
                    if self._stop_event.is_set():
                        break

                    for timeframe in self.TIMEFRAMES:
                        if self._stop_event.is_set():
                            break

                        try:
                            await self._collect_ohlcv_data(symbol, timeframe)
                        except MT5Error as e:
                            logger.error(
                                f"MT5 error collecting OHLCV for {symbol} {timeframe}: {e}"
                            )
                            key = f"{symbol}_{timeframe}"
                            self._stats[key].errors.append(f"MT5 error: {str(e)}")
                        except Exception as e:
                            logger.error(
                                f"Error collecting OHLCV for {symbol} {timeframe}: {e}"
                            )
                            key = f"{symbol}_{timeframe}"
                            self._stats[key].errors.append(f"Collection error: {str(e)}")

                # Reset retry delay on success
                retry_delay = 1.0

                # Wait before next iteration
                await asyncio.sleep(self.COLLECTION_INTERVAL)

            except Exception as e:
                logger.error(f"Error in OHLCV collection loop: {e}")

                # Exponential backoff
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)

    async def _collect_ohlcv_data(self, symbol: str, timeframe: str) -> None:
        """
        Collect OHLCV data for a single symbol and timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (M1, M5, M15, H1, H4, D1)
        """
        if self.mt5_service is None:
            return

        key = f"{symbol}_{timeframe}"

        # Fetch OHLCV data from MT5
        ohlcv_data = await self.fetch_ohlcv_data(
            symbol, timeframe, bars=self.DEFAULT_BARS_TO_FETCH
        )

        if not ohlcv_data:
            logger.debug(f"No OHLCV data available for {symbol} {timeframe}")
            return

        # Update statistics
        self._stats[key].total_collected += len(ohlcv_data)
        self._last_collection_time[key] = datetime.now(timezone.utc)

        # Validate and filter data
        valid_data = []
        duplicate_count = 0
        invalid_count = 0

        for data in ohlcv_data:
            # Check for duplicates
            if await self._is_duplicate(symbol, timeframe, data):
                duplicate_count += 1
                continue

            # Validate OHLCV data
            validation_result = self._validate_ohlcv_data(data)
            if not validation_result["is_valid"]:
                invalid_count += 1
                logger.debug(
                    f"Invalid OHLCV for {symbol} {timeframe}: {validation_result['reason']}"
                )
                continue

            valid_data.append(data)

        self._stats[key].duplicate_count += duplicate_count
        self._stats[key].invalid_count += invalid_count

        if not valid_data:
            logger.debug(f"No valid OHLCV data for {symbol} {timeframe}")
            return

        # Store OHLCV data
        await self._store_ohlcv_data(symbol, timeframe, valid_data)
        self._stats[key].total_stored += len(valid_data)

        logger.debug(
            f"Stored {len(valid_data)} OHLCV candles for {symbol} {timeframe}"
        )

    async def fetch_ohlcv_data(
        self,
        symbol: str,
        timeframe: str,
        bars: int = 100,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[OHLCVData]:
        """
        Fetch OHLCV data from MT5 for a symbol and timeframe.

        Public method for manual OHLCV data fetching.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (M1, M5, M15, H1, H4, D1)
            bars: Number of bars to fetch (default: 100)
            start_date: Optional start date for historical data
            end_date: Optional end date for historical data

        Returns:
            List of OHLCVData

        Raises:
            RuntimeError: If service is not initialized
            ValueError: If timeframe is invalid
        """
        if not self.is_initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        if self.mt5_service is None:
            return []

        # Validate timeframe
        if timeframe not in self.MT5_TIMEFRAMES:
            raise ValueError(
                f"Invalid timeframe: {timeframe}. Must be one of {list(self.MT5_TIMEFRAMES.keys())}"
            )

        try:
            mt5_timeframe = self.MT5_TIMEFRAMES[timeframe]

            # If date range is specified, fetch historical data
            if start_date and end_date:
                ohlcv_data = await self._fetch_historical_data_by_date(
                    symbol, mt5_timeframe, start_date, end_date
                )
            else:
                # Fetch recent data using MT5 service
                ohlcv_data = await self.mt5_service.get_historical_data(
                    symbol, mt5_timeframe, bars
                )

            logger.debug(
                f"Fetched {len(ohlcv_data)} OHLCV bars for {symbol} {timeframe}"
            )
            return ohlcv_data

        except MT5Error as e:
            logger.error(f"MT5 error fetching OHLCV for {symbol} {timeframe}: {e}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch OHLCV for {symbol} {timeframe}: {e}")
            return []

    async def _fetch_historical_data_by_date(
        self,
        symbol: str,
        timeframe: int,
        start_date: datetime,
        end_date: datetime,
    ) -> List[OHLCVData]:
        """
        Fetch historical OHLCV data for a specific date range.

        Args:
            symbol: Trading symbol
            timeframe: MT5 timeframe constant
            start_date: Start date
            end_date: End date

        Returns:
            List of OHLCVData
        """
        try:
            import MetaTrader5 as mt5

            # Fetch rates for the date range
            rates = mt5.copy_rates_range(symbol, timeframe, start_date, end_date)

            if rates is None or len(rates) == 0:
                logger.warning(f"No historical data for {symbol} in date range")
                return []

            # Convert to OHLCVData
            ohlcv_data = []
            for rate in rates:
                ohlcv_data.append(OHLCVData(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(rate['time']),
                    open=float(rate['open']),
                    high=float(rate['high']),
                    low=float(rate['low']),
                    close=float(rate['close']),
                    volume=int(rate['tick_volume'])
                ))

            return ohlcv_data

        except Exception as e:
            logger.error(f"Error fetching historical data by date: {e}")
            return []

    async def _is_duplicate(self, symbol: str, timeframe: str, data: OHLCVData) -> bool:
        """
        Check if OHLCV data is a duplicate based on timestamp.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            data: OHLCV data to check

        Returns:
            True if duplicate exists, False otherwise
        """
        # Load existing data and check for timestamp
        file_path = self._get_file_path(symbol, timeframe)

        if not file_path.exists():
            return False

        try:
            import pyarrow.parquet as pq

            # Load existing data
            table = pq.read_table(file_path)
            existing_timestamps = table.column("timestamp").to_pylist()

            # Check if timestamp exists
            return data.timestamp in existing_timestamps

        except Exception as e:
            logger.warning(f"Error checking for duplicates: {e}")
            return False

    def _validate_ohlcv_data(self, data: OHLCVData) -> Dict[str, Any]:
        """
        Validate OHLCV data quality.

        Args:
            data: OHLCV data to validate

        Returns:
            Dictionary with 'is_valid' (bool) and 'reason' (str if invalid)
        """
        # Check OHLC relationships
        if data.high < max(data.open, data.close, data.low):
            return {
                "is_valid": False,
                "reason": f"High ({data.high}) < max of O/C/L ({max(data.open, data.close, data.low)})"
            }

        if data.low > min(data.open, data.close, data.high):
            return {
                "is_valid": False,
                "reason": f"Low ({data.low}) > min of O/C/H ({min(data.open, data.close, data.high)})"
            }

        # Check price validity
        if any(price <= 0 for price in [data.open, data.high, data.low, data.close]):
            return {"is_valid": False, "reason": "Invalid price (<= 0)"}

        # Check timestamp validity
        now = datetime.now(timezone.utc)
        if data.timestamp > now:
            return {"is_valid": False, "reason": "Timestamp in the future"}

        # Check volume validity
        if data.volume < self.MIN_VOLUME:
            return {"is_valid": False, "reason": f"Volume ({data.volume}) below minimum ({self.MIN_VOLUME})"}

        if data.volume > self.MAX_VOLUME:
            return {
                "is_valid": False,
                "reason": f"Volume ({data.volume}) exceeds maximum ({self.MAX_VOLUME})"
            }

        # Check for extreme price changes
        if data.open > 0:
            price_change_pct = abs((data.close - data.open) / data.open) * 100
            if price_change_pct > self.MAX_PRICE_CHANGE_PERCENT:
                return {
                    "is_valid": False,
                    "reason": f"Price change ({price_change_pct:.1f}%) exceeds threshold ({self.MAX_PRICE_CHANGE_PERCENT}%)"
                }

        return {"is_valid": True, "reason": None}

    def _get_file_path(self, symbol: str, timeframe: str) -> Path:
        """
        Get the file path for a specific symbol and timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe

        Returns:
            Path object for the Parquet file
        """
        # File name format: {SYMBOL}_{TIMEFRAME}.parquet
        filename = f"{symbol}_{timeframe}.parquet"
        return self.base_path / filename

    async def _store_ohlcv_data(
        self,
        symbol: str,
        timeframe: str,
        ohlcv_data: List[OHLCVData],
    ) -> None:
        """
        Store OHLCV data in Parquet format with snappy compression.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            ohlcv_data: List of OHLCV data to store
        """
        if not ohlcv_data:
            return

        try:
            import pyarrow as pa
            import pyarrow.parquet as pq

            # Convert to DataFrame
            data_records = [
                {
                    "timestamp": d.timestamp,
                    "open": d.open,
                    "high": d.high,
                    "low": d.low,
                    "close": d.close,
                    "volume": d.volume,
                }
                for d in ohlcv_data
            ]

            df = pd.DataFrame(data_records)

            # Ensure timestamp is datetime
            if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
                df["timestamp"] = pd.to_datetime(df["timestamp"])

            # Get file path
            file_path = self._get_file_path(symbol, timeframe)

            # Load existing data if file exists
            if file_path.exists():
                existing_df = pq.read_table(file_path).to_pandas()
                # Combine and deduplicate
                combined_df = pd.concat([existing_df, df], ignore_index=True)
                combined_df = combined_df.drop_duplicates(subset=["timestamp"], keep="last")
                combined_df = combined_df.sort_values("timestamp")
            else:
                combined_df = df.sort_values("timestamp")

            # Save to Parquet with snappy compression
            table = pa.Table.from_pandas(combined_df)
            pq.write_table(
                table,
                file_path,
                compression="snappy",
            )

            logger.debug(
                f"Stored {len(combined_df)} OHLCV records to {file_path}"
            )

        except Exception as e:
            logger.error(f"Failed to store OHLCV data for {symbol} {timeframe}: {e}")
            raise

    async def detect_data_gaps(
        self,
        symbol: str,
        timeframe: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[str]:
        """
        Detect data gaps for a symbol and timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            start_date: Start date (defaults to 7 days ago)
            end_date: End date (defaults to today)

        Returns:
            List of gap descriptions
        """
        gaps = []

        if end_date is None:
            end_date = datetime.now(timezone.utc).date()
        if start_date is None:
            start_date = (datetime.now(timezone.utc) - timedelta(days=7)).date()

        # Load data
        file_path = self._get_file_path(symbol, timeframe)
        if not file_path.exists():
            gaps.append(f"No data file found for {symbol} {timeframe}")
            return gaps

        try:
            import pyarrow.parquet as pq

            table = pq.read_table(file_path)
            df = table.to_pandas()

            if df.empty:
                gaps.append(f"No data found for {symbol} {timeframe}")
                return gaps

            # Filter by date range
            df["date"] = pd.to_datetime(df["timestamp"]).dt.date
            df = df[(df["date"] >= start_date) & (df["date"] <= end_date)]

            if df.empty:
                gaps.append(f"No data found for {symbol} {timeframe} in date range")
                return gaps

            # Sort by timestamp
            df = df.sort_values("timestamp")

            # Check for time gaps
            gap_threshold_seconds = self.GAP_THRESHOLDS.get(timeframe, 120)

            for i in range(1, len(df)):
                time_diff = (
                    df.iloc[i]["timestamp"] - df.iloc[i - 1]["timestamp"]
                ).total_seconds()

                if time_diff > gap_threshold_seconds:
                    gap_start = df.iloc[i - 1]["timestamp"]
                    gap_end = df.iloc[i]["timestamp"]
                    gaps.append(
                        f"Gap of {time_diff / 60:.1f} minutes from {gap_start} to {gap_end}"
                    )

        except Exception as e:
            logger.error(f"Error detecting data gaps for {symbol} {timeframe}: {e}")
            gaps.append(f"Error detecting gaps: {str(e)}")

        return gaps

    async def apply_retention_policy(self) -> int:
        """
        Apply data retention policy by deleting old data.

        - Detailed timeframes (M1-H4): Keep 90 days
        - Daily timeframe (D1): Keep 1 year (365 days)

        Returns:
            Number of files deleted
        """
        deleted_count = 0

        try:
            now = datetime.now(timezone.utc)
            detailed_cutoff = now - timedelta(days=self.DETAILED_RETENTION_DAYS)
            daily_cutoff = now - timedelta(days=self.DAILY_RETENTION_DAYS)

            for symbol in self.symbols:
                for timeframe in self.TIMEFRAMES:
                    file_path = self._get_file_path(symbol, timeframe)

                    if not file_path.exists():
                        continue

                    try:
                        import pyarrow.parquet as pq

                        # Load data
                        table = pq.read_table(file_path)
                        df = table.to_pandas()

                        if df.empty:
                            continue

                        # Determine cutoff based on timeframe
                        if timeframe == "D1":
                            cutoff = daily_cutoff
                        else:
                            cutoff = detailed_cutoff

                        # Filter out old data
                        df["timestamp"] = pd.to_datetime(df["timestamp"])
                        filtered_df = df[df["timestamp"] >= cutoff]

                        deleted_rows = len(df) - len(filtered_df)

                        if deleted_rows > 0:
                            # Save filtered data
                            import pyarrow as pa

                            table = pa.Table.from_pandas(filtered_df)
                            pq.write_table(table, file_path, compression="snappy")

                            logger.info(
                                f"Deleted {deleted_rows} old records from {file_path.name} "
                                f"(retention: {timeframe})"
                            )
                            deleted_count += 1

                    except Exception as e:
                        logger.error(f"Error applying retention to {file_path}: {e}")

            logger.info(f"Retention policy applied: {deleted_count} files processed")
            return deleted_count

        except Exception as e:
            logger.error(f"Error during retention policy application: {e}")
            return 0

    async def generate_quality_report(
        self,
        symbol: str,
        timeframe: str,
    ) -> OHLCVQualityReport:
        """
        Generate data quality report for a symbol and timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe

        Returns:
            OHLCVQualityReport with quality assessment
        """
        issues = []
        data_gaps = []
        missing_candles = 0
        invalid_ohlc_count = 0
        invalid_volume_count = 0

        # Check for data gaps
        gaps = await self.detect_data_gaps(symbol, timeframe)
        data_gaps = gaps
        if gaps:
            issues.append(f"Found {len(gaps)} data gaps")

        # Load data for quality checks
        file_path = self._get_file_path(symbol, timeframe)
        total_candles = 0
        duplicate_candles = 0

        if file_path.exists():
            try:
                import pyarrow.parquet as pq

                table = pq.read_table(file_path)
                df = table.to_pandas()
                total_candles = len(df)

                # Check for duplicates
                duplicate_count = df.duplicated(subset=["timestamp"]).sum()
                duplicate_candles = int(duplicate_count)

                if duplicate_candles > 0:
                    issues.append(f"Found {duplicate_candles} duplicate candles")

                # Validate OHLC relationships
                for _, row in df.iterrows():
                    if row["high"] < max(row["open"], row["close"], row["low"]):
                        invalid_ohlc_count += 1
                    if row["low"] > min(row["open"], row["close"], row["high"]):
                        invalid_ohlc_count += 1
                    if row["volume"] < self.MIN_VOLUME or row["volume"] > self.MAX_VOLUME:
                        invalid_volume_count += 1

                if invalid_ohlc_count > 0:
                    issues.append(f"Found {invalid_ohlc_count} invalid OHLC values")

                if invalid_volume_count > 0:
                    issues.append(f"Found {invalid_volume_count} invalid volume values")

            except Exception as e:
                logger.error(f"Error loading data for quality report: {e}")
                issues.append(f"Error loading data: {str(e)}")
        else:
            issues.append("No data file found")
            missing_candles = 1

        # Calculate quality score
        total_issues = len(issues)
        if total_issues == 0:
            quality = OHLCVQuality.EXCELLENT
            score = 1.0
        elif total_issues <= 1:
            quality = OHLCVQuality.GOOD
            score = 0.8
        elif total_issues <= 2:
            quality = OHLCVQuality.ACCEPTABLE
            score = 0.6
        elif total_issues <= 4:
            quality = OHLCVQuality.POOR
            score = 0.4
        else:
            quality = OHLCVQuality.BAD
            score = 0.2

        report = OHLCVQualityReport(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=datetime.now(timezone.utc),
            quality=quality,
            total_candles=total_candles,
            missing_candles=missing_candles,
            duplicate_candles=duplicate_candles,
            invalid_ohlc_count=invalid_ohlc_count,
            invalid_volume_count=invalid_volume_count,
            data_gaps=data_gaps,
            issues=issues,
            score=score,
        )

        self._quality_reports[f"{symbol}_{timeframe}"] = report
        return report

    def get_statistics(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> Dict[str, OHLCVCollectionStats]:
        """
        Get current collection statistics.

        Args:
            symbol: Optional symbol filter
            timeframe: Optional timeframe filter

        Returns:
            Dictionary mapping key to OHLCVCollectionStats
        """
        if symbol and timeframe:
            key = f"{symbol}_{timeframe}"
            return {key: self._stats.get(key)}
        elif symbol:
            return {
                k: v
                for k, v in self._stats.items()
                if v.symbol == symbol
            }
        elif timeframe:
            return {
                k: v
                for k, v in self._stats.items()
                if v.timeframe == timeframe
            }
        return self._stats.copy()

    def get_quality_reports(self) -> Dict[str, OHLCVQualityReport]:
        """
        Get latest quality reports for all symbol/timeframe combinations.

        Returns:
            Dictionary mapping key to OHLCVQualityReport
        """
        return self._quality_reports.copy()

    async def fetch_all_timeframes_once(
        self,
        symbol: str,
    ) -> Dict[str, int]:
        """
        Fetch OHLCV data for all timeframes once (manual trigger).

        Useful for testing or manual data refresh.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary mapping timeframe to record count
        """
        if not self.is_initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        results = {}

        for timeframe in self.TIMEFRAMES:
            try:
                ohlcv_data = await self.fetch_ohlcv_data(symbol, timeframe)
                if ohlcv_data:
                    await self._store_ohlcv_data(symbol, timeframe, ohlcv_data)
                    results[timeframe] = len(ohlcv_data)
                else:
                    results[timeframe] = 0
            except Exception as e:
                logger.error(f"Error fetching {timeframe} data for {symbol}: {e}")
                results[timeframe] = 0

        logger.info(f"Manual OHLCV fetch completed for {symbol}: {results}")
        return results
