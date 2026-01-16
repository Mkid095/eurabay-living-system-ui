"""
TimeSeriesStorage - Parquet-based storage for time-series market data.

This module provides efficient storage and retrieval of time-series data using
the Parquet format with zstd compression, providing 5-10x better performance
than CSV with significantly reduced storage requirements.
"""

import os
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Any
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from loguru import logger


class TimeSeriesStorage:
    """
    Efficient time-series data storage using Parquet format.

    Features:
    - Zstandard (zstd) compression for optimal compression ratios
    - Partitioned storage by symbol and date for efficient querying
    - Automatic deduplication based on timestamp
    - Append mode for adding new data to existing files
    - Metadata tracking for file statistics
    """

    def __init__(
        self,
        base_path: str = "backend/data/market",
        compression: str = "zstd",
        compression_level: int = 10,
    ):
        """
        Initialize TimeSeriesStorage.

        Args:
            base_path: Base directory for market data storage
            compression: Compression algorithm (default: 'zstd')
            compression_level: Compression level for zstd (1-22, default: 10)
        """
        self.base_path = Path(base_path)
        self.compression = compression
        self.compression_level = compression_level
        self.metadata_path = self.base_path / ".metadata"

        # Create directories if they don't exist
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.metadata_path.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"TimeSeriesStorage initialized with base_path={base_path}, "
            f"compression={compression}, level={compression_level}"
        )

    def _get_file_path(self, symbol: str, date: date) -> Path:
        """
        Get the file path for a specific symbol and date.

        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            date: Date for the data

        Returns:
            Path object for the Parquet file
        """
        # Create symbol directory
        symbol_dir = self.base_path / symbol
        symbol_dir.mkdir(parents=True, exist_ok=True)

        # File name format: YYYY-MM-DD.parquet
        filename = f"{date.isoformat()}.parquet"
        return symbol_dir / filename

    def _get_metadata_path(self, symbol: str) -> Path:
        """
        Get the metadata file path for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Path object for the metadata JSON file
        """
        return self.metadata_path / f"{symbol}.json"

    def _deduplicate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Remove duplicate rows based on timestamp, keeping the latest entry.

        Args:
            df: DataFrame to deduplicate

        Returns:
            Deduplicated DataFrame
        """
        if "timestamp" not in df.columns:
            logger.warning("DataFrame has no 'timestamp' column, skipping deduplication")
            return df

        original_count = len(df)
        df_deduplicated = df.drop_duplicates(subset=["timestamp"], keep="last")
        removed_count = original_count - len(df_deduplicated)

        if removed_count > 0:
            logger.info(
                f"Deduplicated {removed_count} rows ({removed_count/original_count*100:.1f}%)"
            )

        return df_deduplicated

    def _save_metadata(
        self,
        symbol: str,
        file_path: Path,
        row_count: int,
        date_range: tuple[datetime, datetime],
        file_size: int,
    ) -> None:
        """
        Save metadata for a Parquet file.

        Args:
            symbol: Trading symbol
            file_path: Path to the Parquet file
            row_count: Number of rows in the file
            date_range: Tuple of (min_timestamp, max_timestamp)
            file_size: File size in bytes
        """
        import json

        metadata_file = self._get_metadata_path(symbol)

        # Load existing metadata or create new
        if metadata_file.exists():
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
        else:
            metadata = {}

        # Add entry for this file
        relative_path = str(file_path.relative_to(self.base_path))
        metadata[relative_path] = {
            "symbol": symbol,
            "row_count": row_count,
            "start_time": date_range[0].isoformat(),
            "end_time": date_range[1].isoformat(),
            "file_size_bytes": file_size,
            "file_size_mb": round(file_size / (1024 * 1024), 2),
            "last_updated": datetime.now().isoformat(),
        }

        # Save metadata
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        logger.debug(f"Saved metadata for {symbol}: {row_count} rows, {file_size} bytes")

    def save_market_data(
        self,
        df: pd.DataFrame,
        symbol: str,
        append_mode: bool = True,
    ) -> Dict[str, Any]:
        """
        Save market data to Parquet files with automatic date partitioning.

        Args:
            df: DataFrame with market data (must have 'timestamp' column)
            symbol: Trading symbol (e.g., 'EURUSD')
            append_mode: If True, append to existing files; if False, overwrite

        Returns:
            Dictionary with save statistics:
            {
                'rows_saved': int,
                'files_updated': List[str],
                'total_size_bytes': int,
                'compression_ratio': float,
            }
        """
        if df.empty:
            logger.warning("Empty DataFrame provided, nothing to save")
            return {
                "rows_saved": 0,
                "files_updated": [],
                "total_size_bytes": 0,
                "compression_ratio": 0.0,
            }

        if "timestamp" not in df.columns:
            raise ValueError("DataFrame must have a 'timestamp' column")

        # Ensure timestamp is datetime
        if not pd.api.types.is_datetime64_any_dtype(df["timestamp"]):
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        # Extract date from timestamp for partitioning
        df["date"] = df["timestamp"].dt.date

        # Group by date and save each partition
        files_updated: List[str] = []
        total_rows = 0
        total_size = 0
        total_csv_size = 0

        for date_partition, date_df in df.groupby("date"):
            file_path = self._get_file_path(symbol, date_partition)

            # Remove date column (used only for partitioning)
            date_df = date_df.drop(columns=["date"])

            # Deduplicate data
            date_df = self._deduplicate_data(date_df)

            # Load existing data if append_mode
            if append_mode and file_path.exists():
                existing_df = pq.read_table(file_path).to_pandas()
                # Combine and deduplicate
                combined_df = pd.concat([existing_df, date_df], ignore_index=True)
                combined_df = self._deduplicate_data(combined_df)
                combined_df = combined_df.sort_values("timestamp")
            else:
                combined_df = date_df.sort_values("timestamp")

            # Calculate CSV size for compression ratio
            csv_size = len(combined_df.to_csv(index=False).encode("utf-8"))

            # Save to Parquet with zstd compression
            table = pa.Table.from_pandas(combined_df)
            pq.write_table(
                table,
                file_path,
                compression=self.compression,
                compression_level=self.compression_level,
            )

            # Get file statistics
            file_size = file_path.stat().st_size
            total_size += file_size
            total_csv_size += csv_size
            rows_saved = len(combined_df)
            total_rows += rows_saved

            # Save metadata
            self._save_metadata(
                symbol=symbol,
                file_path=file_path,
                row_count=rows_saved,
                date_range=(
                    combined_df["timestamp"].min(),
                    combined_df["timestamp"].max(),
                ),
                file_size=file_size,
            )

            files_updated.append(str(file_path.relative_to(self.base_path)))
            logger.info(
                f"Saved {rows_saved} rows to {file_path} "
                f"({file_size / 1024:.1f} KB, compression: {csv_size / file_size:.1f}x)"
            )

        compression_ratio = total_csv_size / total_size if total_size > 0 else 0.0

        return {
            "rows_saved": total_rows,
            "files_updated": files_updated,
            "total_size_bytes": total_size,
            "compression_ratio": compression_ratio,
        }

    def load_market_data(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        """
        Load market data from Parquet files.

        Args:
            symbol: Trading symbol to load
            start_date: Start date (inclusive). If None, loads all available data
            end_date: End date (inclusive). If None, loads all available data

        Returns:
            DataFrame with market data
        """
        symbol_dir = self.base_path / symbol

        if not symbol_dir.exists():
            logger.warning(f"No data directory found for symbol {symbol}")
            return pd.DataFrame()

        # Get all Parquet files for the symbol
        parquet_files = list(symbol_dir.glob("*.parquet"))

        if not parquet_files:
            logger.warning(f"No Parquet files found for symbol {symbol}")
            return pd.DataFrame()

        # Filter files by date range if specified
        if start_date or end_date:
            filtered_files = []
            for file_path in parquet_files:
                # Extract date from filename (YYYY-MM-DD.parquet)
                file_date = datetime.strptime(file_path.stem, "%Y-%m-%d").date()

                if start_date and file_date < start_date:
                    continue
                if end_date and file_date > end_date:
                    continue

                filtered_files.append(file_path)

            parquet_files = filtered_files

        if not parquet_files:
            logger.warning(f"No files found for {symbol} in date range")
            return pd.DataFrame()

        # Load and combine all files
        dfs = []
        for file_path in sorted(parquet_files):
            try:
                df = pq.read_table(file_path).to_pandas()
                dfs.append(df)
                logger.debug(f"Loaded {len(df)} rows from {file_path.name}")
            except Exception as e:
                logger.error(f"Error loading {file_path}: {e}")

        if not dfs:
            return pd.DataFrame()

        combined_df = pd.concat(dfs, ignore_index=True)
        combined_df = combined_df.sort_values("timestamp").reset_index(drop=True)

        logger.info(
            f"Loaded {len(combined_df)} rows for {symbol} "
            f"from {len(parquet_files)} file(s)"
        )

        return combined_df

    def get_available_symbols(self) -> List[str]:
        """
        Get list of symbols with stored data.

        Returns:
            List of symbol names
        """
        if not self.base_path.exists():
            return []

        symbols = [
            d.name for d in self.base_path.iterdir() if d.is_dir() and not d.name.startswith(".")
        ]

        return sorted(symbols)

    def get_available_dates(self, symbol: str) -> List[date]:
        """
        Get list of dates with stored data for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of dates
        """
        symbol_dir = self.base_path / symbol

        if not symbol_dir.exists():
            return []

        dates = []
        for file_path in symbol_dir.glob("*.parquet"):
            try:
                file_date = datetime.strptime(file_path.stem, "%Y-%m-%d").date()
                dates.append(file_date)
            except ValueError:
                logger.warning(f"Could not parse date from filename: {file_path.name}")

        return sorted(dates)

    def get_storage_stats(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Get storage statistics.

        Args:
            symbol: Specific symbol to query. If None, returns stats for all symbols

        Returns:
            Dictionary with storage statistics
        """
        stats = {
            "symbols": {},
            "total_files": 0,
            "total_size_bytes": 0,
            "total_rows": 0,
        }

        symbols_to_query = [symbol] if symbol else self.get_available_symbols()

        for sym in symbols_to_query:
            metadata_file = self._get_metadata_path(sym)
            symbol_stats = {"files": 0, "size_bytes": 0, "rows": 0}

            if metadata_file.exists():
                import json

                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

                for file_path, file_info in metadata.items():
                    symbol_stats["files"] += 1
                    symbol_stats["size_bytes"] += file_info["file_size_bytes"]
                    symbol_stats["rows"] += file_info["row_count"]

            stats["symbols"][sym] = symbol_stats
            stats["total_files"] += symbol_stats["files"]
            stats["total_size_bytes"] += symbol_stats["size_bytes"]
            stats["total_rows"] += symbol_stats["rows"]

        stats["total_size_mb"] = round(stats["total_size_bytes"] / (1024 * 1024), 2)

        return stats

    def delete_data(self, symbol: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> int:
        """
        Delete market data files for a symbol within a date range.

        Args:
            symbol: Trading symbol
            start_date: Start date (inclusive). If None, starts from earliest
            end_date: End date (inclusive). If None, goes to latest

        Returns:
            Number of files deleted
        """
        symbol_dir = self.base_path / symbol

        if not symbol_dir.exists():
            logger.warning(f"No data directory found for symbol {symbol}")
            return 0

        parquet_files = list(symbol_dir.glob("*.parquet"))
        deleted_count = 0

        for file_path in parquet_files:
            # Extract date from filename
            file_date = datetime.strptime(file_path.stem, "%Y-%m-%d").date()

            # Check if file is within deletion range
            if start_date and file_date < start_date:
                continue
            if end_date and file_date > end_date:
                continue

            # Delete file
            file_path.unlink()
            deleted_count += 1
            logger.info(f"Deleted {file_path}")

        # Update metadata
        metadata_file = self._get_metadata_path(symbol)
        if metadata_file.exists():
            import json

            with open(metadata_file, "r") as f:
                metadata = json.load(f)

            # Remove deleted files from metadata
            updated_metadata = {}
            for rel_path, file_info in metadata.items():
                file_date = datetime.fromisoformat(file_info["start_time"]).date()

                if start_date and file_date < start_date:
                    updated_metadata[rel_path] = file_info
                    continue
                if end_date and file_date > end_date:
                    updated_metadata[rel_path] = file_info
                    continue

            # Save updated metadata
            with open(metadata_file, "w") as f:
                json.dump(updated_metadata, f, indent=2)

        return deleted_count
