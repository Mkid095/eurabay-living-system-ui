"""
Migration 002: Add Query Optimization Indexes

Adds composite indexes for commonly queried column combinations
to improve query performance with large datasets.

Run: python -m migrations.migration_manager migrate 002
"""
from typing import Optional
from loguru import logger

from migration_base import Migration


class Migration002AddQueryOptimizationIndexes(Migration):
    """Add composite indexes for query optimization."""

    version = "002"
    description = "Add composite indexes for query optimization"

    async def up(self) -> None:
        """Apply the migration - add composite indexes."""
        logger.info("Applying migration 002: Adding query optimization indexes")

        # Trades table composite indexes
        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_trades_symbol_status_entry_time
            ON trades(symbol, status, entry_time DESC);
        """)

        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_trades_status_entry_time
            ON trades(status, entry_time DESC);
        """)

        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_trades_entry_time_exit_time
            ON trades(entry_time, exit_time);
        """)

        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_trades_symbol_entry_time_status
            ON trades(symbol, entry_time DESC, status);
        """)

        # Market data table composite indexes
        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_market_data_timestamp_symbol
            ON market_data(timestamp DESC, symbol);
        """)

        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_market_data_symbol_timestamp_timeframe
            ON market_data(symbol, timestamp DESC, timeframe);
        """)

        # Signals table composite indexes
        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_signals_executed_timestamp
            ON signals(executed, timestamp DESC);
        """)

        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_signals_symbol_executed_timestamp
            ON signals(symbol, executed, timestamp DESC);
        """)

        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_signals_timestamp_executed_symbol
            ON signals(timestamp DESC, executed, symbol);
        """)

        # Performance metrics composite indexes
        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_performance_period_start_end
            ON performance_metrics(period, period_start DESC, period_end DESC);
        """)

        # Models table composite indexes
        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_models_symbol_active_training_time
            ON models(symbol, is_active, training_time DESC);
        """)

        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_models_active_training_time
            ON models(is_active, training_time DESC);
        """)

        # System logs composite indexes
        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_system_logs_timestamp_level_source
            ON system_logs(timestamp DESC, level, source);
        """)

        # Covering indexes for common query patterns
        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_trades_covering_active
            ON trades(status, symbol, entry_time DESC)
            WHERE status = 'OPEN';
        """)

        await self._execute("""
            CREATE INDEX IF NOT EXISTS ix_signals_covering_unexecuted
            ON signals(executed, timestamp DESC)
            WHERE executed = 0;
        """)

        logger.info("Migration 002 completed successfully: Added 15 composite indexes")

    async def down(self) -> None:
        """Rollback the migration - remove composite indexes."""
        logger.info("Rolling back migration 002: Removing query optimization indexes")

        # Drop covering indexes first
        await self._execute("DROP INDEX IF EXISTS ix_signals_covering_unexecuted;")
        await self._execute("DROP INDEX IF EXISTS ix_trades_covering_active;")

        # Drop system logs indexes
        await self._execute("DROP INDEX IF EXISTS ix_system_logs_timestamp_level_source;")

        # Drop models indexes
        await self._execute("DROP INDEX IF EXISTS ix_models_active_training_time;")
        await self._execute("DROP INDEX IF EXISTS ix_models_symbol_active_training_time;")

        # Drop performance metrics indexes
        await self._execute("DROP INDEX IF EXISTS ix_performance_period_start_end;")

        # Drop signals indexes
        await self._execute("DROP INDEX IF EXISTS ix_signals_timestamp_executed_symbol;")
        await self._execute("DROP INDEX IF EXISTS ix_signals_symbol_executed_timestamp;")
        await self._execute("DROP INDEX IF EXISTS ix_signals_executed_timestamp;")

        # Drop market data indexes
        await self._execute("DROP INDEX IF EXISTS ix_market_data_symbol_timestamp_timeframe;")
        await self._execute("DROP INDEX IF EXISTS ix_market_data_timestamp_symbol;")

        # Drop trades indexes
        await self._execute("DROP INDEX IF EXISTS ix_trades_symbol_entry_time_status;")
        await self._execute("DROP INDEX IF EXISTS ix_trades_entry_time_exit_time;")
        await self._execute("DROP INDEX IF EXISTS ix_trades_status_entry_time;")
        await self._execute("DROP INDEX IF EXISTS ix_trades_symbol_status_entry_time;")

        logger.info("Migration 002 rollback completed: Removed 15 composite indexes")

    async def pre_up_check(self) -> bool:
        """Verify database is ready for this migration."""
        # Check if we can query the schema
        result = await self._execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in result.fetchall()]

        required_tables = ["trades", "market_data", "signals", "performance_metrics", "models"]
        for table in required_tables:
            if table not in tables:
                logger.error(f"Required table '{table}' not found for migration 002")
                return False

        logger.info("Pre-up check passed for migration 002")
        return True

    async def post_up_check(self) -> bool:
        """Verify migration was applied successfully."""
        # Check that indexes were created
        result = await self._execute("""
            SELECT name FROM sqlite_master
            WHERE type='index'
            AND name LIKE 'ix_%_%_%'
            ORDER BY name;
        """)

        indexes = [row[0] for row in result.fetchall()]

        # Check a few key indexes
        key_indexes = [
            "ix_trades_symbol_status_entry_time",
            "ix_market_data_timestamp_symbol",
            "ix_signals_executed_timestamp",
            "ix_performance_period_start_end",
            "ix_models_symbol_active_training_time"
        ]

        for index in key_indexes:
            if index not in indexes:
                logger.error(f"Expected index '{index}' not found after migration")
                return False

        logger.info(f"Post-up check passed: Found {len(indexes)} composite indexes")
        return True


# Export migration instance
migration = Migration002AddQueryOptimizationIndexes
