"""
Historical Data Backfill Service - Comprehensive backfill system for missing historical data.

This service handles:
- Detection of data gaps in existing datasets
- Chunked backfill of historical data from MT5 (up to 1 year)
- Progress tracking for long-running backfill operations
- Backfill priority management (recent data first)
- MT5 rate limit handling during backfill
- Comprehensive logging and error handling
- Support for both fresh installation and gap detection scenarios
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import pandas as pd
from loguru import logger

from app.core.config import settings
from app.services.mt5_service import MT5Service, OHLCVData, MT5Error
from app.services.ohlcv_data_collector import OHLCVDataCollector


class BackfillStatus(Enum):
    """Backfill operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BackfillPriority(Enum):
    """Backfill priority levels."""
    CRITICAL = 1  # Most recent data (last 24 hours)
    HIGH = 2      # Recent data (last 7 days)
    MEDIUM = 3    # Last 30 days
    LOW = 4       # Older historical data (up to 1 year)


@dataclass
class DataGap:
    """Represents a detected data gap."""
    symbol: str
    timeframe: str
    gap_start: datetime
    gap_end: datetime
    missing_bars: int
    priority: BackfillPriority


@dataclass
class BackfillProgress:
    """Progress tracking for backfill operations."""
    operation_id: str
    symbol: str
    timeframe: str
    status: BackfillStatus
    start_date: datetime
    end_date: datetime
    total_bars_needed: int
    bars_backfilled: int
    start_time: datetime
    estimated_completion: Optional[datetime] = None
    error_message: Optional[str] = None
    chunks_completed: int = 0
    total_chunks: int = 0


@dataclass
class BackfillConfig:
    """Configuration for backfill operations."""
    chunk_size_bars: int = 10000  # Number of bars to fetch per chunk
    max_concurrent_requests: int = 3  # Max concurrent MT5 requests
    rate_limit_delay: float = 0.5  # Delay between requests (seconds)
    max_retries: int = 3  # Max retry attempts for failed requests
    backfill_priority: bool = True  # Use priority-based backfill (recent first)
    max_historical_years: int = 1  # Maximum years of historical data to backfill
    enable_progress_tracking: bool = True


class HistoricalBackfillService:
    """
    Comprehensive historical data backfill service.

    Features:
    - Data gap detection across all symbols and timeframes
    - Chunked backfill to avoid memory issues
    - Progress tracking with estimates
    - Priority-based backfill (recent data first)
    - MT5 rate limit handling
    - Comprehensive error handling and retries
    - Support for fresh installation (full backfill)
    - Support for gap detection (selective backfill)

    Usage:
        service = HistoricalBackfillService()
        await service.initialize()

        # Detect gaps and backfill
        gaps = await service.detect_data_gaps()
        await service.backfill_gaps(gaps)

        # Or full backfill for date range
        await service.backfill_historical_data("V10", "M1", start_date, end_date)
    """

    # Timeframes to support
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

    # Gap detection thresholds (in timeframe units)
    GAP_THRESHOLDS = {
        "M1": 120,     # 2 minutes
        "M5": 600,     # 10 minutes
        "M15": 1800,   # 30 minutes
        "H1": 7200,    # 2 hours
        "H4": 28800,   # 8 hours
        "D1": 172800,  # 2 days
    }

    # Priority thresholds
    PRIORITY_THRESHOLDS = {
        BackfillPriority.CRITICAL: timedelta(hours=24),
        BackfillPriority.HIGH: timedelta(days=7),
        BackfillPriority.MEDIUM: timedelta(days=30),
    }

    def __init__(
        self,
        mt5_service: Optional[MT5Service] = None,
        ohlcv_collector: Optional[OHLCVDataCollector] = None,
        symbols: Optional[List[str]] = None,
        config: Optional[BackfillConfig] = None,
    ):
        """
        Initialize HistoricalBackfillService.

        Args:
            mt5_service: MT5 service instance (created if not provided)
            ohlcv_collector: OHLCV collector instance (created if not provided)
            symbols: List of symbols to backfill (defaults to volatility indices)
            config: Backfill configuration (uses defaults if not provided)
        """
        self.mt5_service = mt5_service
        self.ohlcv_collector = ohlcv_collector
        self.symbols = symbols or settings.parsed_trading_symbols
        self.config = config or BackfillConfig()

        # State management
        self.is_initialized = False
        self._active_operations: Dict[str, BackfillProgress] = {}
        self._operation_counter = 0
        self._rate_limit_lock = asyncio.Lock()

        logger.info(
            f"HistoricalBackfillService initialized for {len(self.symbols)} symbols"
        )

    async def initialize(self) -> None:
        """
        Initialize the backfill service.

        Creates required service instances and validates connections.
        Raises RuntimeError if initialization fails.
        """
        if self.is_initialized:
            logger.warning("HistoricalBackfillService already initialized")
            return

        try:
            # Create MT5 service if not provided
            if self.mt5_service is None:
                self.mt5_service = MT5Service()
                await self.mt5_service.initialize()
                logger.info("MT5 service initialized")

            # Create OHLCV collector if not provided
            if self.ohlcv_collector is None:
                self.ohlcv_collector = OHLCVDataCollector(
                    mt5_service=self.mt5_service,
                    symbols=self.symbols,
                )
                await self.ohlcv_collector.initialize()
                logger.info("OHLCV collector initialized")

            # Validate MT5 connection
            if not self.mt5_service.is_connected:
                raise RuntimeError("MT5 service is not connected")

            self.is_initialized = True
            logger.info("HistoricalBackfillService initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize HistoricalBackfillService: {e}")
            raise RuntimeError(f"Initialization failed: {e}") from e

    async def detect_data_gaps(
        self,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[DataGap]:
        """
        Detect data gaps in existing datasets.

        Args:
            symbols: List of symbols to check (defaults to all)
            timeframes: List of timeframes to check (defaults to all)
            start_date: Start date for gap detection (defaults to 1 year ago)
            end_date: End date for gap detection (defaults to now)

        Returns:
            List of detected DataGap objects, sorted by priority
        """
        if not self.is_initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        symbols_to_check = symbols or self.symbols
        timeframes_to_check = timeframes or self.TIMEFRAMES

        if end_date is None:
            end_date = datetime.now(timezone.utc)
        if start_date is None:
            start_date = end_date - timedelta(days=self.config.max_historical_years * 365)

        logger.info(
            f"Detecting data gaps for {len(symbols_to_check)} symbols, "
            f"{len(timeframes_to_check)} timeframes, "
            f"from {start_date} to {end_date}"
        )

        gaps = []

        for symbol in symbols_to_check:
            for timeframe in timeframes_to_check:
                try:
                    symbol_gaps = await self._detect_gaps_for_symbol(
                        symbol, timeframe, start_date, end_date
                    )
                    gaps.extend(symbol_gaps)

                except Exception as e:
                    logger.error(f"Error detecting gaps for {symbol} {timeframe}: {e}")

        # Sort by priority (critical first)
        gaps.sort(key=lambda g: g.priority.value)

        logger.info(f"Detected {len(gaps)} data gaps total")
        for gap in gaps[:10]:  # Log first 10
            logger.info(
                f"Gap: {gap.symbol} {gap.timeframe} "
                f"({gap.gap_start} to {gap.gap_end}) "
                f"- {gap.missing_bars} bars [{gap.priority.name}]"
            )

        return gaps

    async def _detect_gaps_for_symbol(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[DataGap]:
        """
        Detect gaps for a specific symbol and timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            start_date: Start date
            end_date: End date

        Returns:
            List of DataGap objects
        """
        gaps = []

        try:
            # Get file path for existing data
            base_path = Path(settings.DATA_DIR) / "parquet"
            file_path = base_path / f"{symbol}_{timeframe}.parquet"

            # If no file exists, entire range is a gap
            if not file_path.exists():
                missing_bars = self._estimate_missing_bars(start_date, end_date, timeframe)
                priority = self._determine_priority(end_date)
                gaps.append(
                    DataGap(
                        symbol=symbol,
                        timeframe=timeframe,
                        gap_start=start_date,
                        gap_end=end_date,
                        missing_bars=missing_bars,
                        priority=priority,
                    )
                )
                logger.warning(f"No data file for {symbol} {timeframe} - treating as gap")
                return gaps

            # Load existing data and detect gaps
            try:
                import pyarrow.parquet as pq

                table = pq.read_table(file_path)
                df = table.to_pandas()

                if df.empty:
                    missing_bars = self._estimate_missing_bars(start_date, end_date, timeframe)
                    priority = self._determine_priority(end_date)
                    gaps.append(
                        DataGap(
                            symbol=symbol,
                            timeframe=timeframe,
                            gap_start=start_date,
                            gap_end=end_date,
                            missing_bars=missing_bars,
                            priority=priority,
                        )
                    )
                    return gaps

                # Ensure timestamp is datetime
                df["timestamp"] = pd.to_datetime(df["timestamp"])

                # Filter by date range
                df = df[(df["timestamp"] >= start_date) & (df["timestamp"] <= end_date)]

                if df.empty:
                    missing_bars = self._estimate_missing_bars(start_date, end_date, timeframe)
                    priority = self._determine_priority(end_date)
                    gaps.append(
                        DataGap(
                            symbol=symbol,
                            timeframe=timeframe,
                            gap_start=start_date,
                            gap_end=end_date,
                            missing_bars=missing_bars,
                            priority=priority,
                        )
                    )
                    return gaps

                # Sort by timestamp
                df = df.sort_values("timestamp")

                # Check for gaps between consecutive bars
                gap_threshold_seconds = self.GAP_THRESHOLDS.get(timeframe, 120)
                gap_start = None

                for i in range(1, len(df)):
                    time_diff = (
                        df.iloc[i]["timestamp"] - df.iloc[i - 1]["timestamp"]
                    ).total_seconds()

                    if time_diff > gap_threshold_seconds:
                        # Found a gap
                        if gap_start is None:
                            gap_start = df.iloc[i - 1]["timestamp"]

                        gap_end = df.iloc[i]["timestamp"]
                        missing_bars = int(time_diff / gap_threshold_seconds)

                        # Determine priority based on gap_end (most recent point)
                        priority = self._determine_priority(gap_end)

                        gaps.append(
                            DataGap(
                                symbol=symbol,
                                timeframe=timeframe,
                                gap_start=gap_start,
                                gap_end=gap_end,
                                missing_bars=missing_bars,
                                priority=priority,
                            )
                        )

                        gap_start = None

                # Check for gap at start
                if len(df) > 0:
                    first_timestamp = df.iloc[0]["timestamp"]
                    if first_timestamp > start_date:
                        missing_bars = int(
                            (first_timestamp - start_date).total_seconds() / gap_threshold_seconds
                        )
                        priority = self._determine_priority(first_timestamp)
                        gaps.append(
                            DataGap(
                                symbol=symbol,
                                timeframe=timeframe,
                                gap_start=start_date,
                                gap_end=first_timestamp,
                                missing_bars=missing_bars,
                                priority=priority,
                            )
                        )

                # Check for gap at end
                if len(df) > 0:
                    last_timestamp = df.iloc[-1]["timestamp"]
                    if last_timestamp < end_date:
                        missing_bars = int(
                            (end_date - last_timestamp).total_seconds() / gap_threshold_seconds
                        )
                        priority = self._determine_priority(end_date)
                        gaps.append(
                            DataGap(
                                symbol=symbol,
                                timeframe=timeframe,
                                gap_start=last_timestamp,
                                gap_end=end_date,
                                missing_bars=missing_bars,
                                priority=priority,
                            )
                        )

            except Exception as e:
                logger.error(f"Error processing data file for {symbol} {timeframe}: {e}")
                raise

        except Exception as e:
            logger.error(f"Error detecting gaps for {symbol} {timeframe}: {e}")

        return gaps

    def _estimate_missing_bars(
        self,
        start_date: datetime,
        end_date: datetime,
        timeframe: str,
    ) -> int:
        """
        Estimate the number of missing bars for a date range.

        Args:
            start_date: Start date
            end_date: End date
            timeframe: Timeframe

        Returns:
            Estimated number of bars
        """
        total_seconds = (end_date - start_date).total_seconds()
        timeframe_seconds = self.GAP_THRESHOLDS.get(timeframe, 60) // 2  # Approximate
        return int(total_seconds / timeframe_seconds)

    def _determine_priority(self, gap_date: datetime) -> BackfillPriority:
        """
        Determine backfill priority based on gap date.

        Args:
            gap_date: Date of the gap

        Returns:
            BackfillPriority
        """
        now = datetime.now(timezone.utc)
        age = now - gap_date

        if age <= self.PRIORITY_THRESHOLDS[BackfillPriority.CRITICAL]:
            return BackfillPriority.CRITICAL
        elif age <= self.PRIORITY_THRESHOLDS[BackfillPriority.HIGH]:
            return BackfillPriority.HIGH
        elif age <= self.PRIORITY_THRESHOLDS[BackfillPriority.MEDIUM]:
            return BackfillPriority.MEDIUM
        else:
            return BackfillPriority.LOW

    async def backfill_gaps(
        self,
        gaps: List[DataGap],
        max_concurrent: int = 3,
    ) -> Dict[str, BackfillProgress]:
        """
        Backfill multiple data gaps with concurrency control.

        Args:
            gaps: List of DataGap objects to backfill
            max_concurrent: Maximum number of concurrent backfill operations

        Returns:
            Dictionary mapping operation_id to BackfillProgress
        """
        if not self.is_initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        logger.info(f"Starting backfill for {len(gaps)} gaps (max concurrent: {max_concurrent})")

        # Sort gaps by priority if enabled
        if self.config.backfill_priority:
            gaps = sorted(gaps, key=lambda g: g.priority.value)
            logger.info("Gaps sorted by priority (recent data first)")

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        # Create backfill tasks
        tasks = []
        for gap in gaps:
            task = self._backfill_gap_with_semaphore(gap, semaphore)
            tasks.append(task)

        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        progress_map = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Backfill failed for gap {i}: {result}")
            elif result is not None:
                progress_map[result.operation_id] = result

        # Summary
        completed = sum(1 for p in progress_map.values() if p.status == BackfillStatus.COMPLETED)
        failed = sum(1 for p in progress_map.values() if p.status == BackfillStatus.FAILED)

        logger.info(
            f"Backfill completed: {completed} succeeded, {failed} failed out of {len(gaps)} total"
        )

        return progress_map

    async def _backfill_gap_with_semaphore(
        self,
        gap: DataGap,
        semaphore: asyncio.Semaphore,
    ) -> Optional[BackfillProgress]:
        """
        Backfill a single gap with semaphore control.

        Args:
            gap: DataGap to backfill
            semaphore: Semaphore for concurrency control

        Returns:
            BackfillProgress if successful, None otherwise
        """
        async with semaphore:
            return await self._backfill_single_gap(gap)

    async def _backfill_single_gap(
        self,
        gap: DataGap,
    ) -> Optional[BackfillProgress]:
        """
        Backfill a single data gap.

        Args:
            gap: DataGap to backfill

        Returns:
            BackfillProgress with operation details
        """
        # Create operation ID
        self._operation_counter += 1
        operation_id = f"backfill_{gap.symbol}_{gap.timeframe}_{self._operation_counter}"

        # Estimate total bars needed
        total_bars = gap.missing_bars

        # Create progress tracker
        progress = BackfillProgress(
            operation_id=operation_id,
            symbol=gap.symbol,
            timeframe=gap.timeframe,
            status=BackfillStatus.IN_PROGRESS,
            start_date=gap.gap_start,
            end_date=gap.gap_end,
            total_bars_needed=total_bars,
            bars_backfilled=0,
            start_time=datetime.now(timezone.utc),
            total_chunks=0,
        )

        self._active_operations[operation_id] = progress

        logger.info(
            f"Starting backfill {operation_id}: {gap.symbol} {gap.timeframe} "
            f"({gap.gap_start} to {gap.gap_end}) - ~{total_bars} bars"
        )

        try:
            # Perform chunked backfill
            bars_backfilled = await self._chunked_backfill(
                gap.symbol,
                gap.timeframe,
                gap.gap_start,
                gap.gap_end,
                progress,
            )

            # Update progress
            progress.bars_backfilled = bars_backfilled
            progress.status = BackfillStatus.COMPLETED

            logger.info(
                f"Backfill {operation_id} completed: {bars_backfilled} bars backfilled"
            )

        except Exception as e:
            progress.status = BackfillStatus.FAILED
            progress.error_message = str(e)
            logger.error(f"Backfill {operation_id} failed: {e}")

        return progress

    async def _chunked_backfill(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        progress: BackfillProgress,
    ) -> int:
        """
        Perform chunked backfill to avoid memory issues.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            start_date: Start date
            end_date: End date
            progress: Progress tracker to update

        Returns:
            Total number of bars backfilled
        """
        total_backfilled = 0

        # Calculate number of chunks needed
        chunk_size = self.config.chunk_size_bars
        total_seconds = (end_date - start_date).total_seconds()
        timeframe_seconds = self.GAP_THRESHOLDS.get(timeframe, 60) // 2
        estimated_bars = int(total_seconds / timeframe_seconds)
        progress.total_chunks = max(1, estimated_bars // chunk_size + 1)

        # Split date range into chunks
        current_start = start_date
        chunk_num = 0

        while current_start < end_date:
            chunk_num += 1

            # Calculate chunk end date
            chunk_duration_seconds = chunk_size * timeframe_seconds
            chunk_end = min(
                current_start + timedelta(seconds=chunk_duration_seconds),
                end_date,
            )

            logger.info(
                f"Processing chunk {chunk_num}/{progress.total_chunks} "
                f"for {symbol} {timeframe}: "
                f"{current_start} to {chunk_end}"
            )

            # Fetch and store data for this chunk
            try:
                bars_filled = await self._backfill_chunk(
                    symbol,
                    timeframe,
                    current_start,
                    chunk_end,
                )

                total_backfilled += bars_filled
                progress.bars_backfilled = total_backfilled
                progress.chunks_completed = chunk_num

                # Update estimated completion
                if chunk_num > 0:
                    elapsed = (datetime.now(timezone.utc) - progress.start_time).total_seconds()
                    avg_time_per_chunk = elapsed / chunk_num
                    remaining_chunks = progress.total_chunks - chunk_num
                    estimated_remaining = avg_time_per_chunk * remaining_chunks
                    progress.estimated_completion = (
                        datetime.now(timezone.utc) + timedelta(seconds=estimated_remaining)
                    )

                logger.info(
                    f"Chunk {chunk_num} completed: {bars_filled} bars "
                    f"(total: {total_backfilled}/{progress.total_bars_needed})"
                )

            except Exception as e:
                logger.error(f"Error processing chunk {chunk_num}: {e}")
                # Continue with next chunk

            # Move to next chunk
            current_start = chunk_end

            # Rate limiting
            await self._rate_limit_delay()

        return total_backfilled

    async def _backfill_chunk(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
    ) -> int:
        """
        Backfill a single chunk of data.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            start_date: Chunk start date
            end_date: Chunk end date

        Returns:
            Number of bars backfilled

        Raises:
            MT5Error: If MT5 request fails after retries
        """
        if self.mt5_service is None:
            raise RuntimeError("MT5 service not available")

        # Validate timeframe
        if timeframe not in self.MT5_TIMEFRAMES:
            raise ValueError(f"Invalid timeframe: {timeframe}")

        mt5_timeframe = self.MT5_TIMEFRAMES[timeframe]

        # Retry logic
        last_error = None
        for attempt in range(self.config.max_retries):
            try:
                # Fetch historical data from MT5
                import MetaTrader5 as mt5

                logger.debug(
                    f"Fetching {symbol} {timeframe} from {start_date} to {end_date} "
                    f"(attempt {attempt + 1}/{self.config.max_retries})"
                )

                rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_date, end_date)

                if rates is None or len(rates) == 0:
                    logger.warning(
                        f"No data returned for {symbol} {timeframe} "
                        f"from {start_date} to {end_date}"
                    )
                    return 0

                # Convert to OHLCVData
                ohlcv_data = []
                for rate in rates:
                    ohlcv_data.append(
                        OHLCVData(
                            symbol=symbol,
                            timestamp=datetime.fromtimestamp(rate["time"], tz=timezone.utc),
                            open=float(rate["open"]),
                            high=float(rate["high"]),
                            low=float(rate["low"]),
                            close=float(rate["close"]),
                            volume=int(rate["tick_volume"]),
                        )
                    )

                # Store data
                if self.ohlcv_collector:
                    await self.ohlcv_collector._store_ohlcv_data(
                        symbol, timeframe, ohlcv_data
                    )

                logger.debug(f"Backfilled {len(ohlcv_data)} bars for {symbol} {timeframe}")
                return len(ohlcv_data)

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Attempt {attempt + 1} failed for {symbol} {timeframe}: {e}"
                )

                if attempt < self.config.max_retries - 1:
                    # Wait before retry with exponential backoff
                    await asyncio.sleep(self.config.rate_limit_delay * (2 ** attempt))

        # All retries failed
        raise MT5Error(f"Failed to backfill chunk after {self.config.max_retries} attempts: {last_error}")

    async def _rate_limit_delay(self) -> None:
        """
        Apply rate limiting delay between requests.
        """
        async with self._rate_limit_lock:
            await asyncio.sleep(self.config.rate_limit_delay)

    async def backfill_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: Optional[datetime] = None,
    ) -> BackfillProgress:
        """
        Backfill historical data for a specific date range.

        This is the main entry point for backfill operations.
        Handles both fresh installation (full backfill) and gap filling.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (M1, M5, M15, H1, H4, D1)
            start_date: Start date for backfill
            end_date: End date for backfill (defaults to now)

        Returns:
            BackfillProgress with operation details

        Raises:
            RuntimeError: If service is not initialized
            ValueError: If timeframe is invalid
        """
        if not self.is_initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        if timeframe not in self.TIMEFRAMES:
            raise ValueError(
                f"Invalid timeframe: {timeframe}. Must be one of {self.TIMEFRAMES}"
            )

        if end_date is None:
            end_date = datetime.now(timezone.utc)

        logger.info(
            f"Starting historical backfill for {symbol} {timeframe} "
            f"from {start_date} to {end_date}"
        )

        # Create a gap object for this range
        missing_bars = self._estimate_missing_bars(start_date, end_date, timeframe)
        priority = self._determine_priority(end_date)

        gap = DataGap(
            symbol=symbol,
            timeframe=timeframe,
            gap_start=start_date,
            gap_end=end_date,
            missing_bars=missing_bars,
            priority=priority,
        )

        # Backfill the gap
        progress = await self._backfill_single_gap(gap)

        if progress is None:
            raise RuntimeError("Backfill operation returned no progress")

        return progress

    async def backfill_all_symbols(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
    ) -> Dict[str, BackfillProgress]:
        """
        Backfill all symbols and timeframes for a date range.

        Useful for fresh installation or comprehensive backfill.

        Args:
            start_date: Start date (defaults to 1 year ago)
            end_date: End date (defaults to now)
            symbols: List of symbols to backfill (defaults to all)
            timeframes: List of timeframes to backfill (defaults to all)

        Returns:
            Dictionary mapping operation_id to BackfillProgress
        """
        if not self.is_initialized:
            raise RuntimeError("Service not initialized. Call initialize() first.")

        if end_date is None:
            end_date = datetime.now(timezone.utc)
        if start_date is None:
            start_date = end_date - timedelta(days=self.config.max_historical_years * 365)

        symbols_to_backfill = symbols or self.symbols
        timeframes_to_backfill = timeframes or self.TIMEFRAMES

        logger.info(
            f"Starting comprehensive backfill for {len(symbols_to_backfill)} symbols, "
            f"{len(timeframes_to_backfill)} timeframes, "
            f"from {start_date} to {end_date}"
        )

        # Create gaps for all combinations
        gaps = []
        for symbol in symbols_to_backfill:
            for timeframe in timeframes_to_backfill:
                missing_bars = self._estimate_missing_bars(start_date, end_date, timeframe)
                priority = self._determine_priority(end_date)

                gaps.append(
                    DataGap(
                        symbol=symbol,
                        timeframe=timeframe,
                        gap_start=start_date,
                        gap_end=end_date,
                        missing_bars=missing_bars,
                        priority=priority,
                    )
                )

        # Backfill all gaps
        return await self.backfill_gaps(gaps)

    def get_active_operations(self) -> Dict[str, BackfillProgress]:
        """
        Get all active backfill operations.

        Returns:
            Dictionary mapping operation_id to BackfillProgress
        """
        return self._active_operations.copy()

    def get_operation_progress(self, operation_id: str) -> Optional[BackfillProgress]:
        """
        Get progress for a specific backfill operation.

        Args:
            operation_id: Operation ID

        Returns:
            BackfillProgress if found, None otherwise
        """
        return self._active_operations.get(operation_id)
