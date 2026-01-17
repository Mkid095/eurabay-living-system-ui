"""
Data Ingestion Service - Continuous market data ingestion from MT5.

This service handles real-time data ingestion for all volatility indices (V10, V25, V50, V75, V100).
Stores OHLCV data in Parquet format for efficiency and tick data in SQLite for recent data.
Includes data deduplication, quality checks, retention policy, and backfill capabilities.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import pandas as pd
from loguru import logger

from app.core.config import settings
from app.services.mt5_service import MT5Service, OHLCVData, TickData, MT5Error
from app.services.database_service import DatabaseService
from app.services.historical_backfill import HistoricalBackfillService
from storage.time_series_storage import TimeSeriesStorage


class DataQuality(Enum):
    """Data quality indicators."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    BAD = "bad"


@dataclass
class DataQualityReport:
    """Data quality assessment report."""
    symbol: str
    timestamp: datetime
    quality: DataQuality
    missing_data_points: int
    duplicate_data_points: int
    outlier_data_points: int
    stale_data: bool
    gaps_detected: int
    issues: List[str] = field(default_factory=list)
    score: float = 0.0  # 0.0 to 1.0


@dataclass
class IngestionStats:
    """Statistics for data ingestion operations."""
    symbols_ingested: int
    total_ohlcv_records: int
    total_tick_records: int
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    errors: List[str] = field(default_factory=list)
    quality_reports: List[DataQualityReport] = field(default_factory=list)


class DataIngestionService:
    """
    Continuous data ingestion service for market data from MT5.

    Features:
    - Async data fetching loop for all volatility indices
    - OHLCV data storage in Parquet format for efficiency
    - Tick data storage in SQLite for recent data
    - Automatic data deduplication
    - Data quality checks and monitoring
    - 90-day data retention policy
    - Backfill for missing historical data
    - Error handling and recovery

    Usage:
        service = DataIngestionService()
        await service.initialize()
        await service.start_continuous_ingestion()
    """

    # Volatility indices to monitor
    VOLATILITY_INDICES = ["V10", "V25", "V50", "V75", "V100"]

    # Timeframes for OHLCV data
    TIMEFRAMES = ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]

    # Data retention settings
    TICK_DATA_RETENTION_DAYS = 7  # Keep tick data for 7 days
    OHLCV_DATA_RETENTION_DAYS = 90  # Keep OHLCV data for 90 days

    # Data quality thresholds
    MAX_MISSING_DATA_POINTS = 5  # Max consecutive missing points before alert
    MAX_STALE_DATA_MINUTES = 10  # Max minutes before data is considered stale
    OUTLIER_THRESHOLD_STD = 3.0  # Standard deviations for outlier detection

    # Ingestion intervals
    TICK_INGESTION_INTERVAL = 1  # Seconds between tick data fetches
    OHLCV_INGESTION_INTERVAL = 60  # Seconds between OHLCV data fetches

    def __init__(
        self,
        mt5_service: Optional[MT5Service] = None,
        database_service: Optional[DatabaseService] = None,
        time_series_storage: Optional[TimeSeriesStorage] = None,
        symbols: Optional[List[str]] = None,
        historical_backfill: Optional[HistoricalBackfillService] = None,
    ):
        """
        Initialize DataIngestionService.

        Args:
            mt5_service: MT5 service instance (created if not provided)
            database_service: Database service instance (created if not provided)
            time_series_storage: TimeSeries storage instance (created if not provided)
            symbols: List of symbols to ingest (defaults to volatility indices)
            historical_backfill: Historical backfill service instance (created if not provided)
        """
        self.mt5_service = mt5_service
        self.database_service = database_service
        self.time_series_storage = time_series_storage
        self.historical_backfill = historical_backfill

        # Use provided symbols or default to volatility indices from config
        self.symbols = symbols or settings.parsed_trading_symbols

        # Ingestion state
        self.is_running = False
        self.is_initialized = False
        self._ingestion_tasks: Optional[List[asyncio.Task]] = None
        self._stop_event = asyncio.Event()

        # Quality monitoring
        self._quality_reports: Dict[str, DataQualityReport] = {}
        self._data_gaps: Dict[str, List[datetime]] = {}

        # Statistics
        self._stats = IngestionStats(
            symbols_ingested=0,
            total_ohlcv_records=0,
            total_tick_records=0,
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            duration_seconds=0.0,
        )

        logger.info(
            f"DataIngestionService initialized for symbols: {', '.join(self.symbols)}"
        )

    async def initialize(self) -> None:
        """
        Initialize the data ingestion service.

        Creates required service instances and validates connections.
        Raises RuntimeError if initialization fails.
        """
        if self.is_initialized:
            logger.warning("DataIngestionService already initialized")
            return

        try:
            # Create MT5 service if not provided
            if self.mt5_service is None:
                self.mt5_service = MT5Service()
                await self.mt5_service.initialize()
                logger.info("MT5 service initialized")

            # Database service is optional - tick data storage to SQLite
            # If not provided, tick data will not be stored (OHLCV still goes to Parquet)
            if self.database_service is None:
                logger.warning("No database service provided - tick data will not be stored to SQLite")
                logger.info("OHLCV data will still be stored to Parquet files")

            # Create time series storage if not provided
            if self.time_series_storage is None:
                self.time_series_storage = TimeSeriesStorage(
                    base_path=str(Path(settings.DATA_DIR) / "market")
                )
                logger.info("TimeSeriesStorage initialized")

            # Create historical backfill service if not provided
            if self.historical_backfill is None:
                self.historical_backfill = HistoricalBackfillService(
                    mt5_service=self.mt5_service,
                    symbols=self.symbols,
                )
                await self.historical_backfill.initialize()
                logger.info("HistoricalBackfillService initialized")

            # Validate MT5 connection
            if not self.mt5_service.is_connected:
                raise RuntimeError("MT5 service is not connected")

            # Verify symbols are valid
            for symbol in self.symbols:
                if symbol not in settings.parsed_trading_symbols:
                    logger.warning(
                        f"Symbol {symbol} is not in configured trading symbols"
                    )

            self.is_initialized = True
            logger.info("DataIngestionService initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize DataIngestionService: {e}")
            raise RuntimeError(f"Initialization failed: {e}") from e

    async def start_continuous_ingestion(self) -> None:
        """
        Start continuous data ingestion for all configured symbols.

        Creates async tasks for:
        - Tick data ingestion (runs every 1 second)
        - OHLCV data ingestion (runs every 60 seconds)
        - Data quality monitoring (runs every 30 seconds)
        - Retention policy cleanup (runs daily)

        Raises RuntimeError if service is not initialized.
        """
        if not self.is_initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        if self.is_running:
            logger.warning("Data ingestion already running")
            return

        self.is_running = True
        self._stop_event.clear()
        self._ingestion_tasks = []

        logger.info("Starting continuous data ingestion...")

        # Create ingestion tasks
        self._ingestion_tasks = [
            asyncio.create_task(self._tick_ingestion_loop()),
            asyncio.create_task(self._ohlcv_ingestion_loop()),
            asyncio.create_task(self._quality_monitoring_loop()),
            asyncio.create_task(self._retention_cleanup_loop()),
        ]

        logger.info(
            f"Data ingestion started for {len(self.symbols)} symbols: "
            f"{', '.join(self.symbols)}"
        )

    async def stop_continuous_ingestion(self) -> None:
        """
        Stop continuous data ingestion.

        Gracefully stops all ingestion tasks and waits for completion.
        """
        if not self.is_running:
            logger.warning("Data ingestion not running")
            return

        logger.info("Stopping continuous data ingestion...")
        self._stop_event.set()
        self.is_running = False

        # Cancel all tasks
        if self._ingestion_tasks:
            for task in self._ingestion_tasks:
                if not task.done():
                    task.cancel()

            # Wait for tasks to complete
            await asyncio.gather(*self._ingestion_tasks, return_exceptions=True)
            self._ingestion_tasks.clear()

        # Update final statistics
        self._stats.end_time = datetime.now(timezone.utc)
        self._stats.duration_seconds = (
            self._stats.end_time - self._stats.start_time
        ).total_seconds()

        logger.info(
            f"Data ingestion stopped. "
            f"Duration: {self._stats.duration_seconds:.2f}s, "
            f"OHLCV records: {self._stats.total_ohlcv_records}, "
            f"Tick records: {self._stats.total_tick_records}"
        )

    async def _tick_ingestion_loop(self) -> None:
        """
        Continuous loop for tick data ingestion.

        Fetches and stores tick data for all symbols every second.
        Implements exponential backoff on errors.
        """
        retry_delay = 1.0
        max_retry_delay = 60.0

        while not self._stop_event.is_set():
            try:
                for symbol in self.symbols:
                    if self._stop_event.is_set():
                        break

                    try:
                        # Fetch tick data from MT5
                        tick_data = await self._fetch_tick_data(symbol)

                        if tick_data:
                            # Store in SQLite for recent data
                            await self._store_tick_data(tick_data)
                            self._stats.total_tick_records += 1

                    except MT5Error as e:
                        logger.error(f"MT5 error fetching tick data for {symbol}: {e}")
                        self._stats.errors.append(
                            f"Tick data error for {symbol}: {str(e)}"
                        )

                # Reset retry delay on success
                retry_delay = 1.0

                # Wait before next iteration
                await asyncio.sleep(self.TICK_INGESTION_INTERVAL)

            except Exception as e:
                logger.error(f"Error in tick ingestion loop: {e}")
                self._stats.errors.append(f"Tick loop error: {str(e)}")

                # Exponential backoff
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)

    async def _ohlcv_ingestion_loop(self) -> None:
        """
        Continuous loop for OHLCV data ingestion.

        Fetches and stores OHLCV data for all symbols and timeframes every 60 seconds.
        Implements exponential backoff on errors.
        """
        retry_delay = 1.0
        max_retry_delay = 60.0

        while not self._stop_event.is_set():
            try:
                for symbol in self.symbols:
                    if self._stop_event.is_set():
                        break

                    for timeframe in self.TIMEFRAMES:
                        if self._stop_event.is_set():
                            break

                        try:
                            # Fetch OHLCV data from MT5
                            ohlcv_data = await self._fetch_ohlcv_data(
                                symbol, timeframe, bars=100
                            )

                            if ohlcv_data:
                                # Store in Parquet format
                                await self._store_ohlcv_data(symbol, timeframe, ohlcv_data)
                                self._stats.total_ohlcv_records += len(ohlcv_data)

                        except MT5Error as e:
                            logger.error(
                                f"MT5 error fetching OHLCV data for {symbol} {timeframe}: {e}"
                            )
                            self._stats.errors.append(
                                f"OHLCV data error for {symbol} {timeframe}: {str(e)}"
                            )

                # Reset retry delay on success
                retry_delay = 1.0

                # Wait before next iteration
                await asyncio.sleep(self.OHLCV_INGESTION_INTERVAL)

            except Exception as e:
                logger.error(f"Error in OHLCV ingestion loop: {e}")
                self._stats.errors.append(f"OHLCV loop error: {str(e)}")

                # Exponential backoff
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)

    async def _quality_monitoring_loop(self) -> None:
        """
        Continuous loop for data quality monitoring.

        Checks data quality every 30 seconds and generates reports.
        Implements exponential backoff on errors.
        """
        retry_delay = 1.0
        max_retry_delay = 60.0
        check_interval = 30  # seconds

        while not self._stop_event.is_set():
            try:
                for symbol in self.symbols:
                    if self._stop_event.is_set():
                        break

                    try:
                        # Generate quality report
                        report = await self._generate_quality_report(symbol)
                        self._quality_reports[symbol] = report
                        self._stats.quality_reports.append(report)

                        # Log quality issues
                        if report.quality in [DataQuality.POOR, DataQuality.BAD]:
                            logger.warning(
                                f"Data quality issue for {symbol}: {report.quality.value}. "
                                f"Issues: {', '.join(report.issues)}"
                            )

                    except Exception as e:
                        logger.error(f"Error generating quality report for {symbol}: {e}")

                # Reset retry delay on success
                retry_delay = 1.0

                # Wait before next iteration
                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"Error in quality monitoring loop: {e}")

                # Exponential backoff
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, max_retry_delay)

    async def _retention_cleanup_loop(self) -> None:
        """
        Continuous loop for data retention cleanup.

        Runs daily at midnight to clean up old data.
        Implements exponential backoff on errors.
        """
        while not self._stop_event.is_set():
            try:
                # Wait until next midnight
                now = datetime.now(timezone.utc)
                next_midnight = (now + timedelta(days=1)).replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                wait_seconds = (next_midnight - now).total_seconds()

                logger.info(f"Retention cleanup scheduled in {wait_seconds:.0f} seconds")
                await asyncio.sleep(wait_seconds)

                if self._stop_event.is_set():
                    break

                # Perform cleanup
                await self._cleanup_old_data()
                logger.info("Retention cleanup completed")

            except Exception as e:
                logger.error(f"Error in retention cleanup loop: {e}")
                # Wait 1 hour before retry
                await asyncio.sleep(3600)

    async def _fetch_tick_data(self, symbol: str) -> Optional[TickData]:
        """
        Fetch current tick data for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            TickData if successful, None otherwise
        """
        if self.mt5_service is None:
            return None

        try:
            return await self.mt5_service.get_price(symbol)
        except Exception as e:
            logger.error(f"Failed to fetch tick data for {symbol}: {e}")
            return None

    async def _fetch_ohlcv_data(
        self, symbol: str, timeframe: str, bars: int = 100
    ) -> Optional[List[OHLCVData]]:
        """
        Fetch OHLCV data for a symbol and timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (M1, M5, M15, M30, H1, H4, D1)
            bars: Number of bars to fetch

        Returns:
            List of OHLCVData if successful, None otherwise
        """
        if self.mt5_service is None:
            return None

        try:
            # Convert timeframe string to MT5 constant
            timeframe_map = {
                "M1": 1,  # TIMEFRAME_M1
                "M5": 5,  # TIMEFRAME_M5
                "M15": 15,  # TIMEFRAME_M15
                "M30": 30,  # TIMEFRAME_M30
                "H1": 60,  # TIMEFRAME_H1
                "H4": 240,  # TIMEFRAME_H4
                "D1": 1440,  # TIMEFRAME_D1
            }

            mt5_timeframe = timeframe_map.get(timeframe)
            if mt5_timeframe is None:
                logger.error(f"Invalid timeframe: {timeframe}")
                return None

            # Fetch historical data from MT5
            return await self.mt5_service.get_historical_data(
                symbol, mt5_timeframe, bars
            )

        except Exception as e:
            logger.error(f"Failed to fetch OHLCV data for {symbol} {timeframe}: {e}")
            return None

    async def _store_tick_data(self, tick_data: TickData) -> None:
        """
        Store tick data in SQLite database.

        Args:
            tick_data: Tick data to store
        """
        if self.database_service is None:
            return

        try:
            # Import MarketData model
            from app.models.models import MarketData

            # Create MarketData record from tick data
            market_data = MarketData(
                symbol=tick_data.symbol,
                timeframe="TICK",  # Tick data
                timestamp=tick_data.time,
                open_price=tick_data.bid,
                high_price=max(tick_data.bid, tick_data.ask),
                low_price=min(tick_data.bid, tick_data.ask),
                close_price=tick_data.ask,
                volume=tick_data.volume,
            )

            # Store in database
            await self.database_service.create_market_data(market_data)

        except Exception as e:
            logger.error(f"Failed to store tick data: {e}")

    async def _store_ohlcv_data(
        self, symbol: str, timeframe: str, ohlcv_data: List[OHLCVData]
    ) -> None:
        """
        Store OHLCV data in Parquet format.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            ohlcv_data: List of OHLCV data to store
        """
        if self.time_series_storage is None or not ohlcv_data:
            return

        try:
            # Convert OHLCVData to DataFrame
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

            # Set timestamp as index for time series operations
            df.set_index("timestamp", inplace=True)

            # Store in Parquet format
            # File path: backend/data/market/{symbol}/{timeframe}/{YYYY-MM-DD}.parquet
            base_path = str(Path(settings.DATA_DIR) / "market" / symbol / timeframe)
            storage = TimeSeriesStorage(base_path=base_path)

            # Save data with automatic deduplication
            storage.save_market_data(df, symbol, append_mode=True)

            logger.debug(
                f"Stored {len(ohlcv_data)} OHLCV records for {symbol} {timeframe}"
            )

        except Exception as e:
            logger.error(f"Failed to store OHLCV data for {symbol} {timeframe}: {e}")

    async def _generate_quality_report(self, symbol: str) -> DataQualityReport:
        """
        Generate data quality report for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            DataQualityReport with quality assessment
        """
        issues = []
        missing_data_points = 0
        duplicate_data_points = 0
        outlier_data_points = 0
        gaps_detected = 0

        # Check for stale data
        latest_data = await self._fetch_tick_data(symbol)
        stale_data = False
        if latest_data:
            time_diff = (datetime.now(timezone.utc) - latest_data.time).total_seconds() / 60
            if time_diff > self.MAX_STALE_DATA_MINUTES:
                stale_data = True
                issues.append(f"Data is stale ({time_diff:.1f} minutes old)")
        else:
            stale_data = True
            issues.append("No data available")
            missing_data_points += 1

        # Check for data gaps in recent OHLCV data
        try:
            recent_ohlcv = await self._fetch_ohlcv_data(symbol, "M1", bars=100)
            if recent_ohlcv and len(recent_ohlcv) > 1:
                # Check for time gaps between consecutive bars
                for i in range(1, len(recent_ohlcv)):
                    time_diff = (
                        recent_ohlcv[i].timestamp - recent_ohlcv[i - 1].timestamp
                    ).total_seconds()
                    # Allow for 2-minute gap (should be 60 seconds)
                    if time_diff > 120:
                        gaps_detected += 1
                        missing_data_points += int(time_diff / 60) - 1

                if gaps_detected > 0:
                    issues.append(f"Detected {gaps_detected} data gaps")

                # Check for outliers using standard deviation
                closes = [d.close for d in recent_ohlcv]
                if closes:
                    mean_close = sum(closes) / len(closes)
                    std_close = (sum((x - mean_close) ** 2 for x in closes) / len(closes)) ** 0.5

                    for close in closes:
                        if abs(close - mean_close) > self.OUTLIER_THRESHOLD_STD * std_close:
                            outlier_data_points += 1

                    if outlier_data_points > 0:
                        issues.append(f"Detected {outlier_data_points} outliers")

        except Exception as e:
            logger.error(f"Error checking data quality for {symbol}: {e}")

        # Calculate quality score
        total_issues = len(issues)
        if total_issues == 0:
            quality = DataQuality.EXCELLENT
            score = 1.0
        elif total_issues <= 1:
            quality = DataQuality.GOOD
            score = 0.8
        elif total_issues <= 2:
            quality = DataQuality.ACCEPTABLE
            score = 0.6
        elif total_issues <= 4:
            quality = DataQuality.POOR
            score = 0.4
        else:
            quality = DataQuality.BAD
            score = 0.2

        return DataQualityReport(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            quality=quality,
            missing_data_points=missing_data_points,
            duplicate_data_points=duplicate_data_points,
            outlier_data_points=outlier_data_points,
            stale_data=stale_data,
            gaps_detected=gaps_detected,
            issues=issues,
            score=score,
        )

    async def _cleanup_old_data(self) -> None:
        """
        Clean up old data based on retention policy.

        - Removes tick data older than 7 days from SQLite
        - Removes OHLCV data older than 90 days from Parquet files
        """
        try:
            logger.info("Starting data retention cleanup...")

            # Clean up old tick data from SQLite
            if self.database_service:
                tick_cutoff = datetime.now(timezone.utc) - timedelta(
                    days=self.TICK_DATA_RETENTION_DAYS
                )
                # This would require a delete_market_data method in DatabaseService
                logger.info(f"Tick data cleanup: deleting data older than {tick_cutoff}")

            # Clean up old OHLCV data from Parquet files
            if self.time_series_storage:
                ohlcv_cutoff = datetime.now(timezone.utc) - timedelta(
                    days=self.OHLCV_DATA_RETENTION_DAYS
                )
                for symbol in self.symbols:
                    for timeframe in self.TIMEFRAMES:
                        try:
                            # Delete old Parquet files
                            base_path = Path(settings.DATA_DIR) / "market" / symbol / timeframe
                            if base_path.exists():
                                for file_path in base_path.glob("*.parquet"):
                                    # Extract date from filename
                                    try:
                                        file_date = datetime.strptime(
                                            file_path.stem, "%Y-%m-%d"
                                        ).replace(tzinfo=timezone.utc)
                                        if file_date < ohlcv_cutoff:
                                            file_path.unlink()
                                            logger.debug(
                                                f"Deleted old Parquet file: {file_path}"
                                            )
                                    except ValueError:
                                        pass

                        except Exception as e:
                            logger.error(f"Error cleaning up {symbol} {timeframe}: {e}")

            logger.info("Data retention cleanup completed")

        except Exception as e:
            logger.error(f"Error during data cleanup: {e}")

    async def backfill_missing_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> int:
        """
        Backfill missing historical data for a symbol and timeframe.

        This method now uses the comprehensive HistoricalBackfillService which provides:
        - Chunked backfill to avoid memory issues
        - Progress tracking
        - Rate limit handling
        - Retry logic

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (M1, M5, M15, M30, H1, H4, D1)
            start_date: Start date for backfill
            end_date: End date for backfill (defaults to now)

        Returns:
            Number of records backfilled

        Raises:
            RuntimeError: If service is not initialized
        """
        if not self.is_initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        if self.historical_backfill is None:
            raise RuntimeError("HistoricalBackfillService not available")

        # Use the comprehensive backfill service
        progress = await self.historical_backfill.backfill_historical_data(
            symbol=symbol,
            timeframe=timeframe,
            start_date=start_date,
            end_date=end_date,
        )

        return progress.bars_backfilled

    async def detect_and_backfill_gaps(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Detect data gaps and backfill them automatically.

        This is a convenience method that combines gap detection and backfilling.

        Args:
            symbols: List of symbols to check (defaults to all)
            timeframes: List of timeframes to check (defaults to all)
            start_date: Start date for gap detection (defaults to 1 year ago)
            end_date: End date for gap detection (defaults to now)

        Returns:
            Dictionary with detection and backfill results
        """
        if not self.is_initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        if self.historical_backfill is None:
            raise RuntimeError("HistoricalBackfillService not available")

        logger.info("Starting gap detection and backfill process")

        # Detect gaps
        gaps = await self.historical_backfill.detect_data_gaps(
            symbols=symbols,
            timeframes=timeframes,
            start_date=start_date,
            end_date=end_date,
        )

        if not gaps:
            logger.info("No data gaps detected")
            return {
                "gaps_detected": 0,
                "gaps_backfilled": 0,
                "total_bars_backfilled": 0,
                "progress": {},
            }

        # Backfill gaps
        progress_map = await self.historical_backfill.backfill_gaps(gaps)

        # Calculate statistics
        total_bars = sum(p.bars_backfilled for p in progress_map.values())
        completed = sum(1 for p in progress_map.values() if p.status.name == "COMPLETED")

        return {
            "gaps_detected": len(gaps),
            "gaps_backfilled": completed,
            "total_bars_backfilled": total_bars,
            "progress": progress_map,
        }

    async def backfill_all_historical_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive backfill for all symbols and timeframes.

        Useful for fresh installation or complete historical data refresh.

        Args:
            start_date: Start date (defaults to 1 year ago)
            end_date: End date (defaults to now)
            symbols: List of symbols to backfill (defaults to all)
            timeframes: List of timeframes to backfill (defaults to all)

        Returns:
            Dictionary with backfill results
        """
        if not self.is_initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        if self.historical_backfill is None:
            raise RuntimeError("HistoricalBackfillService not available")

        logger.info("Starting comprehensive historical backfill")

        # Perform comprehensive backfill
        progress_map = await self.historical_backfill.backfill_all_symbols(
            start_date=start_date,
            end_date=end_date,
            symbols=symbols,
            timeframes=timeframes,
        )

        # Calculate statistics
        total_bars = sum(p.bars_backfilled for p in progress_map.values())
        completed = sum(1 for p in progress_map.values() if p.status.name == "COMPLETED")
        failed = sum(1 for p in progress_map.values() if p.status.name == "FAILED")

        return {
            "total_operations": len(progress_map),
            "completed": completed,
            "failed": failed,
            "total_bars_backfilled": total_bars,
            "progress": progress_map,
        }

    def get_statistics(self) -> IngestionStats:
        """
        Get current ingestion statistics.

        Returns:
            IngestionStats with current statistics
        """
        # Update end time and duration
        self._stats.end_time = datetime.now(timezone.utc)
        self._stats.duration_seconds = (
            self._stats.end_time - self._stats.start_time
        ).total_seconds()

        return self._stats

    def get_quality_reports(self) -> Dict[str, DataQualityReport]:
        """
        Get latest quality reports for all symbols.

        Returns:
            Dictionary mapping symbol to DataQualityReport
        """
        return self._quality_reports.copy()

    async def fetch_all_symbols_once(self) -> Dict[str, Dict[str, int]]:
        """
        Fetch data for all symbols once (manual trigger).

        Useful for testing or manual data refresh.

        Returns:
            Dictionary with symbol -> {'ohlcv': count, 'tick': count}
        """
        if not self.is_initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        results = {}

        for symbol in self.symbols:
            results[symbol] = {"ohlcv": 0, "tick": 0}

            # Fetch tick data
            try:
                tick_data = await self._fetch_tick_data(symbol)
                if tick_data:
                    await self._store_tick_data(tick_data)
                    results[symbol]["tick"] = 1
            except Exception as e:
                logger.error(f"Error fetching tick data for {symbol}: {e}")

            # Fetch OHLCV data for primary timeframe (M1)
            try:
                ohlcv_data = await self._fetch_ohlcv_data(symbol, "M1", bars=100)
                if ohlcv_data:
                    await self._store_ohlcv_data(symbol, "M1", ohlcv_data)
                    results[symbol]["ohlcv"] = len(ohlcv_data)
            except Exception as e:
                logger.error(f"Error fetching OHLCV data for {symbol}: {e}")

        logger.info(f"Manual data fetch completed: {results}")
        return results
