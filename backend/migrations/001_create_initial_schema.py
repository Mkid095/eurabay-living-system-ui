"""
Initial Database Schema Migration

Creates all core tables for the EURABAY Living System:
- trades: Trading activity records
- performance_metrics: Performance statistics
- models: ML model metadata
- configurations: System configuration
- market_data: Historical price data
- signals: Trading signals
- system_logs: System logging

Migration Version: 001
Author: System
Created: 2026-01-17
"""
from aiosqlite import Connection
from backend.migrations import Migration


class Migration_001(Migration):
    """Create initial database schema with all core tables."""

    version = "001"
    description = "Create initial database schema with all core tables"
    author = "System"

    async def up(self, conn: Connection) -> None:
        """
        Apply the migration - create all tables, indexes, and triggers.
        """
        # Create trades table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mt5_ticket INTEGER UNIQUE,
                symbol VARCHAR(10) NOT NULL,
                direction VARCHAR(4) NOT NULL,
                entry_price REAL NOT NULL,
                entry_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                exit_price REAL,
                exit_time DATETIME,
                stop_loss REAL,
                take_profit REAL,
                lot_size REAL NOT NULL,
                confidence REAL NOT NULL,
                strategy_used VARCHAR(100) NOT NULL,
                profit_loss REAL,
                profit_loss_pips REAL,
                status VARCHAR(10) NOT NULL DEFAULT 'OPEN',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT check_trade_direction CHECK (direction IN ('BUY', 'SELL')),
                CONSTRAINT check_trade_status CHECK (status IN ('OPEN', 'CLOSED', 'PENDING')),
                CONSTRAINT check_confidence_range CHECK (confidence >= 0 AND confidence <= 1)
            )
        """)

        # Trades indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_trades_symbol ON trades(symbol)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_trades_status ON trades(status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_trades_entry_time ON trades(entry_time)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_trades_exit_time ON trades(exit_time)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_trades_symbol_status ON trades(symbol, status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_trades_mt5_ticket ON trades(mt5_ticket)")

        # Create performance_metrics table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                period VARCHAR(20) NOT NULL,
                period_start DATETIME NOT NULL,
                period_end DATETIME NOT NULL,
                total_trades INTEGER NOT NULL DEFAULT 0,
                winning_trades INTEGER NOT NULL DEFAULT 0,
                losing_trades INTEGER NOT NULL DEFAULT 0,
                win_rate REAL NOT NULL DEFAULT 0,
                total_profit REAL NOT NULL DEFAULT 0,
                total_loss REAL NOT NULL DEFAULT 0,
                profit_factor REAL NOT NULL DEFAULT 0,
                average_win REAL NOT NULL DEFAULT 0,
                average_loss REAL NOT NULL DEFAULT 0,
                max_drawdown REAL NOT NULL DEFAULT 0,
                max_drawdown_pct REAL NOT NULL DEFAULT 0,
                sharpe_ratio REAL,
                sortino_ratio REAL,
                calmar_ratio REAL,
                equity_curve TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT check_win_rate_range CHECK (win_rate >= 0 AND win_rate <= 100),
                CONSTRAINT check_period_type CHECK (period IN ('daily', 'weekly', 'monthly', 'all_time'))
            )
        """)

        # Performance metrics indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_performance_period ON performance_metrics(period)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_performance_period_start ON performance_metrics(period_start)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_performance_period_end ON performance_metrics(period_end)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_performance_metrics_period ON performance_metrics(period, period_start, period_end)")

        # Create models table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name VARCHAR(100) NOT NULL,
                model_type VARCHAR(50) NOT NULL,
                model_version VARCHAR(50) NOT NULL,
                symbol VARCHAR(10) NOT NULL,
                training_samples INTEGER NOT NULL,
                features_used TEXT NOT NULL,
                file_path VARCHAR(500) NOT NULL,
                accuracy REAL NOT NULL,
                precision REAL NOT NULL,
                recall REAL NOT NULL,
                f1_score REAL NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                training_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT check_accuracy_range CHECK (accuracy >= 0 AND accuracy <= 1),
                CONSTRAINT check_precision_range CHECK (precision >= 0 AND precision <= 1),
                CONSTRAINT check_recall_range CHECK (recall >= 0 AND recall <= 1),
                CONSTRAINT check_f1_range CHECK (f1_score >= 0 AND f1_score <= 1)
            )
        """)

        # Models indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_models_model_name ON models(model_name)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_models_symbol ON models(symbol)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_models_is_active ON models(is_active)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_models_symbol_active ON models(symbol, is_active)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_models_name_version ON models(model_name, model_version)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_models_training_time ON models(training_time)")

        # Create configurations table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS configurations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_key VARCHAR(100) NOT NULL UNIQUE,
                config_value TEXT NOT NULL,
                description VARCHAR(500) NOT NULL,
                category VARCHAR(50) NOT NULL,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Configurations indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_config_config_key ON configurations(config_key)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_config_category ON configurations(category)")

        # Create market_data table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol VARCHAR(10) NOT NULL,
                timeframe VARCHAR(10) NOT NULL,
                timestamp DATETIME NOT NULL,
                open_price REAL NOT NULL,
                high_price REAL NOT NULL,
                low_price REAL NOT NULL,
                close_price REAL NOT NULL,
                volume INTEGER NOT NULL DEFAULT 0,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT check_high_low CHECK (high_price >= low_price),
                CONSTRAINT check_high_open CHECK (high_price >= open_price),
                CONSTRAINT check_high_close CHECK (high_price >= close_price),
                CONSTRAINT check_low_open CHECK (low_price <= open_price),
                CONSTRAINT check_low_close CHECK (low_price <= close_price)
            )
        """)

        # Market data indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_market_data_symbol ON market_data(symbol)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_market_data_timeframe ON market_data(timeframe)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_market_data_timestamp ON market_data(timestamp)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_market_data_symbol_timeframe_timestamp ON market_data(symbol, timeframe, timestamp)")

        # Create signals table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol VARCHAR(10) NOT NULL,
                direction VARCHAR(10) NOT NULL,
                confidence REAL NOT NULL,
                price REAL NOT NULL,
                strategy VARCHAR(100) NOT NULL,
                reasons TEXT,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                executed BOOLEAN NOT NULL DEFAULT 0,
                trade_id INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT fk_signals_trade FOREIGN KEY (trade_id) REFERENCES trades(id) ON DELETE SET NULL,
                CONSTRAINT check_signal_direction CHECK (direction IN ('BUY', 'SELL', 'WAIT')),
                CONSTRAINT check_signal_confidence CHECK (confidence >= 0 AND confidence <= 1)
            )
        """)

        # Signals indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_signals_symbol ON signals(symbol)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_signals_direction ON signals(direction)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_signals_timestamp ON signals(timestamp)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_signals_symbol_timestamp ON signals(symbol, timestamp)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_signals_executed ON signals(executed)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_signals_trade_id ON signals(trade_id)")

        # Create system_logs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                level VARCHAR(20) NOT NULL,
                message TEXT NOT NULL,
                context TEXT,
                source VARCHAR(100),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

                CONSTRAINT check_log_level CHECK (level IN ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'))
            )
        """)

        # System logs indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_system_logs_timestamp ON system_logs(timestamp)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_system_logs_level ON system_logs(level)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_system_logs_source ON system_logs(source)")
        await conn.execute("CREATE INDEX IF NOT EXISTS ix_system_logs_timestamp_level ON system_logs(timestamp, level)")

        # Create triggers for automatic timestamp updates
        await conn.execute("""
            CREATE TRIGGER IF NOT EXISTS update_trades_timestamp
            AFTER UPDATE ON trades
            BEGIN
                UPDATE trades SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)

        await conn.execute("""
            CREATE TRIGGER IF NOT EXISTS update_performance_metrics_timestamp
            AFTER UPDATE ON performance_metrics
            BEGIN
                UPDATE performance_metrics SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)

        await conn.execute("""
            CREATE TRIGGER IF NOT EXISTS update_models_timestamp
            AFTER UPDATE ON models
            BEGIN
                UPDATE models SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)

        await conn.execute("""
            CREATE TRIGGER IF NOT EXISTS update_configurations_timestamp
            AFTER UPDATE ON configurations
            BEGIN
                UPDATE configurations SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
            END
        """)

        # Create views for common queries
        await conn.execute("""
            CREATE VIEW IF NOT EXISTS v_active_trades AS
            SELECT
                id,
                mt5_ticket,
                symbol,
                direction,
                entry_price,
                entry_time,
                stop_loss,
                take_profit,
                lot_size,
                confidence,
                strategy_used,
                profit_loss,
                profit_loss_pips,
                status,
                created_at,
                updated_at,
                datetime(entry_time) as entry_datetime,
                CASE
                    WHEN direction = 'BUY' THEN entry_price - stop_loss
                    ELSE stop_loss - entry_price
                END as stop_loss_distance,
                CASE
                    WHEN direction = 'BUY' THEN take_profit - entry_price
                    ELSE entry_price - take_profit
                END as take_profit_distance
            FROM trades
            WHERE status = 'OPEN'
            ORDER BY entry_time DESC
        """)

        await conn.execute("""
            CREATE VIEW IF NOT EXISTS v_performance_summary AS
            SELECT
                period,
                period_start,
                period_end,
                total_trades,
                winning_trades,
                losing_trades,
                win_rate,
                total_profit,
                total_loss,
                profit_factor,
                average_win,
                average_loss,
                max_drawdown,
                max_drawdown_pct,
                sharpe_ratio
            FROM performance_metrics
            ORDER BY period_start DESC
        """)

        await conn.execute("""
            CREATE VIEW IF NOT EXISTS v_active_models AS
            SELECT
                id,
                model_name,
                model_type,
                model_version,
                symbol,
                accuracy,
                precision,
                recall,
                f1_score,
                training_time,
                datetime(training_time) as training_datetime
            FROM models
            WHERE is_active = 1
            ORDER BY training_time DESC
        """)

        await conn.execute("""
            CREATE VIEW IF NOT EXISTS v_recent_signals AS
            SELECT
                id,
                symbol,
                direction,
                confidence,
                price,
                strategy,
                timestamp,
                executed,
                trade_id,
                datetime(timestamp) as signal_datetime
            FROM signals
            WHERE timestamp >= datetime('now', '-24 hours')
            ORDER BY timestamp DESC
        """)

    async def down(self, conn: Connection) -> None:
        """
        Revert the migration - drop all tables, indexes, triggers, and views.
        """
        # Drop views first (they depend on tables)
        await conn.execute("DROP VIEW IF EXISTS v_recent_signals")
        await conn.execute("DROP VIEW IF EXISTS v_active_models")
        await conn.execute("DROP VIEW IF EXISTS v_performance_summary")
        await conn.execute("DROP VIEW IF EXISTS v_active_trades")

        # Drop triggers
        await conn.execute("DROP TRIGGER IF EXISTS update_configurations_timestamp")
        await conn.execute("DROP TRIGGER IF EXISTS update_models_timestamp")
        await conn.execute("DROP TRIGGER IF EXISTS update_performance_metrics_timestamp")
        await conn.execute("DROP TRIGGER IF EXISTS update_trades_timestamp")

        # Drop tables (signals before trades due to foreign key)
        await conn.execute("DROP TABLE IF EXISTS system_logs")
        await conn.execute("DROP TABLE IF EXISTS signals")
        await conn.execute("DROP TABLE IF EXISTS market_data")
        await conn.execute("DROP TABLE IF EXISTS configurations")
        await conn.execute("DROP TABLE IF EXISTS models")
        await conn.execute("DROP TABLE IF EXISTS performance_metrics")
        await conn.execute("DROP TABLE IF EXISTS trades")
