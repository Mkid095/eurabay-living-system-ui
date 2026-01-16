"""
Read Replica Service for EURABAY Living System.

Provides read-only database connections for complex analytical queries.

Note: For SQLite, true read replicas are not applicable. This service provides:
- Separate read-only connections to avoid write lock contention
- Connection pooling for read operations
- Read-only transaction management
- Analytics query optimization
"""
from typing import Optional, List, Dict, Any, AsyncIterator
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine, create_async_engine, async_sessionmaker
from sqlalchemy import text, select
from sqlalchemy.pool import StaticPool
from aiosqlite import Connection
from loguru import logger
import os


class ReadReplicaService:
    """
    Read replica service for analytical queries.

    Provides read-only database access with connection pooling
    to avoid contention with write operations.
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        pool_size: int = 5,
        read_only_mode: bool = True
    ):
        """
        Initialize read replica service.

        Args:
            db_path: Path to SQLite database file
            pool_size: Number of connections in the pool
            read_only_mode: Whether to enforce read-only mode
        """
        from pathlib import Path

        if db_path is None:
            # Default to backend/data directory
            backend_dir = Path(__file__).parent.parent.parent / "data"
            backend_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(backend_dir / "eurabay_trading.db")

        self.db_path = db_path
        self.pool_size = pool_size
        self.read_only_mode = read_only_mode

        # Create read-only engine
        database_url = f"sqlite+aiosqlite:///{db_path}"

        self._engine: Optional[AsyncEngine] = None
        self._session_factory: Optional[async_sessionmaker[AsyncSession]] = None

        logger.info(
            f"ReadReplicaService initialized with db_path={db_path}, "
            f"pool_size={pool_size}, read_only={read_only_mode}"
        )

    async def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if self._engine is not None:
            logger.warning("ReadReplicaService already initialized")
            return

        # Create engine with connection pooling
        self._engine = create_async_engine(
            f"sqlite+aiosqlite:///{self.db_path}",
            poolclass=StaticPool,
            pool_size=self.pool_size,
            connect_args={
                "check_same_thread": False,
                "isolation_level": None  # Autocommit mode for reads
            },
            echo=False
        )

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )

        logger.info("ReadReplicaService engine initialized successfully")

    async def close(self) -> None:
        """Close database connections and dispose engine."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
            logger.info("ReadReplicaService closed")

    @asynccontextmanager
    async def get_read_session(self) -> AsyncIterator[AsyncSession]:
        """
        Get a read-only database session.

        Yields:
            AsyncSession configured for read operations

        Example:
            async with read_replica.get_read_session() as session:
                result = await session.execute(query)
        """
        if self._session_factory is None:
            await self.initialize()

        async with self._session_factory() as session:
            # Set read-only mode if enabled
            if self.read_only_mode:
                await session.execute(text("PRAGMA query_only = 1"))

            try:
                yield session
            finally:
                # Reset read-only mode
                if self.read_only_mode:
                    await session.execute(text("PRAGMA query_only = 0"))

    async def execute_analytic_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute an analytical query with optimization.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query results as list of dictionaries
        """
        async with self.get_read_session() as session:
            # Set optimization pragmas for analytical queries
            await session.execute(text("PRAGMA temp_store = MEMORY"))
            await session.execute(text("PRAGMA mmap_size = 30000000000"))
            await session.execute(text("PRAGMA page_size = 4096"))

            result = await session.execute(text(query), params or {})
            rows = result.fetchall()
            columns = result.keys()

            return [dict(zip(columns, row)) for row in rows]

    async def get_aggregated_metrics(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: str = "day"
    ) -> List[Dict[str, Any]]:
        """
        Get aggregated performance metrics for analytics.

        Args:
            start_date: Start date for aggregation
            end_date: End date for aggregation
            group_by: Grouping period ('day', 'week', 'month')

        Returns:
            Aggregated metrics
        """
        # Determine date truncation format
        date_format = {
            "day": "%Y-%m-%d",
            "week": "%Y-W%W",
            "month": "%Y-%m"
        }.get(group_by, "%Y-%m-%d")

        query = f"""
            SELECT
                strftime('{date_format}', t.entry_time) as period,
                COUNT(*) as total_trades,
                SUM(CASE WHEN t.status = 'CLOSED' THEN 1 ELSE 0 END) as closed_trades,
                SUM(CASE WHEN t.profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                SUM(CASE WHEN t.profit_loss <= 0 THEN 1 ELSE 0 END) as losing_trades,
                AVG(t.profit_loss) as avg_profit_loss,
                SUM(t.profit_loss) as total_profit_loss,
                MAX(t.profit_loss) as max_profit,
                MIN(t.profit_loss) as max_loss,
                AVG(t.confidence) as avg_confidence
            FROM trades t
            WHERE t.entry_time >= :start_date
            AND t.entry_time <= :end_date
            AND t.status = 'CLOSED'
            GROUP BY period
            ORDER BY period DESC
        """

        return await self.execute_analytic_query(
            query,
            {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()}
        )

    async def get_symbol_performance(
        self,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get performance metrics grouped by symbol.

        Args:
            limit: Maximum number of symbols to return

        Returns:
            Symbol performance metrics
        """
        query = """
            SELECT
                symbol,
                COUNT(*) as total_trades,
                SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed_trades,
                SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                CAST(SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) AS FLOAT) /
                    COUNT(*) * 100 as win_rate,
                AVG(profit_loss) as avg_profit_loss,
                SUM(profit_loss) as total_profit_loss,
                AVG(confidence) as avg_confidence
            FROM trades
            WHERE status = 'CLOSED'
            GROUP BY symbol
            HAVING COUNT(*) >= 5
            ORDER BY total_profit_loss DESC
            LIMIT :limit
        """

        return await self.execute_analytic_query(query, {"limit": limit})

    async def get_strategy_performance(
        self,
        min_trades: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get performance metrics grouped by strategy.

        Args:
            min_trades: Minimum number of trades to include

        Returns:
            Strategy performance metrics
        """
        query = """
            SELECT
                strategy_used,
                COUNT(*) as total_trades,
                SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) as winning_trades,
                CAST(SUM(CASE WHEN profit_loss > 0 THEN 1 ELSE 0 END) AS FLOAT) /
                    COUNT(*) * 100 as win_rate,
                AVG(profit_loss) as avg_profit_loss,
                SUM(profit_loss) as total_profit_loss,
                AVG(confidence) as avg_confidence,
                AVG(CASE WHEN profit_loss > 0 THEN profit_loss ELSE NULL END) as avg_win,
                AVG(CASE WHEN profit_loss <= 0 THEN profit_loss ELSE NULL END) as avg_loss,
                MAX(profit_loss) as max_profit,
                MIN(profit_loss) as max_loss
            FROM trades
            WHERE status = 'CLOSED'
            GROUP BY strategy_used
            HAVING COUNT(*) >= :min_trades
            ORDER BY win_rate DESC, total_profit_loss DESC
        """

        return await self.execute_analytic_query(query, {"min_trades": min_trades})

    async def get_time_series_analysis(
        self,
        symbol: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get time series analysis for a symbol.

        Args:
            symbol: Trading symbol
            days: Number of days to analyze

        Returns:
            Time series data
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        query = """
            SELECT
                DATE(entry_time) as trade_date,
                COUNT(*) as trade_count,
                SUM(profit_loss) as daily_profit_loss,
                AVG(profit_loss) as avg_profit_loss,
                MAX(profit_loss) as max_profit,
                MIN(profit_loss) as max_loss,
                AVG(confidence) as avg_confidence,
                SUM(CASE WHEN direction = 'BUY' THEN 1 ELSE 0 END) as buy_count,
                SUM(CASE WHEN direction = 'SELL' THEN 1 ELSE 0 END) as sell_count
            FROM trades
            WHERE symbol = :symbol
            AND entry_time >= :start_date
            AND status = 'CLOSED'
            GROUP BY DATE(entry_time)
            ORDER BY trade_date DESC
        """

        return await self.execute_analytic_query(
            query,
            {"symbol": symbol, "start_date": start_date.isoformat()}
        )

    async def get_market_statistics(
        self,
        symbol: Optional[str] = None,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get comprehensive market statistics.

        Args:
            symbol: Optional symbol filter
            days: Number of days to analyze

        Returns:
            Market statistics
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        # Get trade statistics
        trade_query = """
            SELECT
                COUNT(*) as total_trades,
                SUM(CASE WHEN status = 'CLOSED' THEN 1 ELSE 0 END) as closed_trades,
                SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open_trades,
                AVG(CASE WHEN status = 'CLOSED' THEN profit_loss ELSE NULL END) as avg_profit_loss,
                SUM(CASE WHEN status = 'CLOSED' THEN profit_loss ELSE 0 END) as total_profit_loss
            FROM trades
            WHERE entry_time >= :start_date
        """

        params: Dict[str, Any] = {"start_date": start_date.isoformat()}

        if symbol:
            trade_query += " AND symbol = :symbol"
            params["symbol"] = symbol

        trades_stats = await self.execute_analytic_query(trade_query, params)

        # Get signal statistics
        signal_query = """
            SELECT
                COUNT(*) as total_signals,
                SUM(CASE WHEN executed = 1 THEN 1 ELSE 0 END) as executed_signals,
                AVG(confidence) as avg_confidence
            FROM signals
            WHERE timestamp >= :start_date
        """

        signal_params = {"start_date": start_date.isoformat()}
        if symbol:
            signal_query += " AND symbol = :symbol"
            signal_params["symbol"] = symbol

        signals_stats = await self.execute_analytic_query(signal_query, signal_params)

        return {
            "period_days": days,
            "symbol": symbol,
            "trades": trades_stats[0] if trades_stats else {},
            "signals": signals_stats[0] if signals_stats else {}
        }

    async def get_table_statistics(self) -> Dict[str, Any]:
        """
        Get database table statistics for monitoring.

        Returns:
            Table statistics
        """
        tables = ["trades", "market_data", "signals", "performance_metrics", "models"]
        stats = {}

        for table in tables:
            query = f"""
                SELECT
                    COUNT(*) as row_count,
                    MIN(created_at) as earliest_record,
                    MAX(created_at) as latest_record
                FROM {table}
            """

            try:
                result = await self.execute_analytic_query(query)
                if result:
                    stats[table] = result[0]
            except Exception as e:
                logger.warning(f"Failed to get statistics for table {table}: {e}")
                stats[table] = {"error": str(e)}

        return stats


# Global read replica instance
_read_replica_instance: Optional[ReadReplicaService] = None


def get_read_replica() -> ReadReplicaService:
    """
    Get or create global read replica service instance.

    Returns:
        ReadReplicaService instance
    """
    global _read_replica_instance
    if _read_replica_instance is None:
        _read_replica_instance = ReadReplicaService()
    return _read_replica_instance


async def close_read_replica() -> None:
    """Close global read replica service."""
    global _read_replica_instance
    if _read_replica_instance:
        await _read_replica_instance.close()
        _read_replica_instance = None
