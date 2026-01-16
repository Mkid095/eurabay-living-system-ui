"""
Test script for database schema creation and relationships.
Tests the schema.sql file by creating a test database and verifying all tables.
"""
import asyncio
import sqlite3
import os
from pathlib import Path
from datetime import datetime
from loguru import logger


# Test database path
TEST_DB_PATH = Path(__file__).parent.parent / "data" / "test_schema.db"


def read_schema_file():
    """Read the schema.sql file."""
    schema_path = Path(__file__).parent.parent / "database" / "schema.sql"
    with open(schema_path, "r") as f:
        return f.read()


def setup_test_database():
    """Create test database and apply schema."""
    # Remove test database if exists
    if TEST_DB_PATH.exists():
        os.remove(TEST_DB_PATH)

    # Create test database directory
    TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Read schema
    schema_sql = read_schema_file()

    # Connect to test database
    conn = sqlite3.connect(str(TEST_DB_PATH))
    cursor = conn.cursor()

    # Execute schema
    cursor.executescript(schema_sql)
    conn.commit()

    return conn


def test_table_exists(cursor, table_name):
    """Test if a table exists."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    result = cursor.fetchone()
    assert result is not None, f"Table {table_name} does not exist"
    logger.success(f"Table {table_name} exists")


def test_table_columns(cursor, table_name, expected_columns):
    """Test if table has expected columns."""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = {row[1]: row[2] for row in cursor.fetchall()}

    for col_name, col_type in expected_columns.items():
        assert col_name in columns, f"Column {col_name} not found in {table_name}"
        logger.success(f"  Column {col_name}: {columns[col_name]}")


def test_indexes(cursor, table_name, expected_indexes):
    """Test if indexes exist for a table."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=?",
        (table_name,)
    )
    indexes = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]

    for index_name in expected_indexes:
        assert index_name in indexes, f"Index {index_name} not found for {table_name}"
        logger.success(f"  Index {index_name} exists")


def test_foreign_keys(cursor):
    """Test foreign key constraints."""
    cursor.execute("PRAGMA foreign_key_list(signals)")
    fks = cursor.fetchall()

    assert len(fks) > 0, "No foreign keys found in signals table"
    for fk in fks:
        logger.success(f"  Foreign key: signals.{fk[3]} -> {fk[2]}.{fk[4]}")


def test_views(cursor):
    """Test if views were created."""
    expected_views = [
        "v_active_trades",
        "v_performance_summary",
        "v_active_models",
        "v_recent_signals"
    ]

    for view_name in expected_views:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='view' AND name=?",
            (view_name,)
        )
        result = cursor.fetchone()
        assert result is not None, f"View {view_name} does not exist"
        logger.success(f"View {view_name} exists")


def test_triggers(cursor):
    """Test if triggers were created."""
    expected_triggers = [
        "update_trades_timestamp",
        "update_performance_metrics_timestamp",
        "update_models_timestamp",
        "update_configurations_timestamp"
    ]

    for trigger_name in expected_triggers:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name=?",
            (trigger_name,)
        )
        result = cursor.fetchone()
        assert result is not None, f"Trigger {trigger_name} does not exist"
        logger.success(f"Trigger {trigger_name} exists")


def test_constraints(cursor):
    """Test check constraints by testing valid/invalid data."""
    logger.info("Testing check constraints...")

    # Test trades table constraints
    try:
        cursor.execute(
            "INSERT INTO trades (symbol, direction, entry_price, lot_size, confidence, strategy_used) "
            "VALUES ('V10', 'INVALID', 1.0, 0.01, 0.8, 'test')"
        )
        assert False, "Direction constraint should have failed"
    except sqlite3.IntegrityError:
        logger.success("  Trades direction constraint works")

    # Test confidence range constraint
    try:
        cursor.execute(
            "INSERT INTO trades (symbol, direction, entry_price, lot_size, confidence, strategy_used) "
            "VALUES ('V10', 'BUY', 1.0, 0.01, 1.5, 'test')"
        )
        assert False, "Confidence range constraint should have failed"
    except sqlite3.IntegrityError:
        logger.success("  Confidence range constraint works")

    # Test signals direction constraint
    try:
        cursor.execute(
            "INSERT INTO signals (symbol, direction, confidence, price, strategy) "
            "VALUES ('V10', 'INVALID', 0.8, 1.0, 'test')"
        )
        assert False, "Signals direction constraint should have failed"
    except sqlite3.IntegrityError:
        logger.success("  Signals direction constraint works")

    # Test market data price constraints
    try:
        cursor.execute(
            "INSERT INTO market_data (symbol, timeframe, timestamp, open_price, high_price, low_price, close_price) "
            "VALUES ('V10', 'M1', datetime('now'), 1.0, 1.0, 1.5, 1.2)"
        )
        assert False, "High >= Low constraint should have failed"
    except sqlite3.IntegrityError:
        logger.success("  Market data price constraint works")


def test_sample_data(cursor):
    """Test inserting and querying sample data."""
    logger.info("Testing sample data operations...")

    # Insert sample trade
    cursor.execute(
        """INSERT INTO trades (symbol, direction, entry_price, lot_size, confidence, strategy_used)
        VALUES ('V10', 'BUY', 1.2345, 0.01, 0.85, 'XGBoost')"""
    )
    trade_id = cursor.lastrowid
    logger.success(f"  Inserted trade with ID: {trade_id}")

    # Insert sample signal with foreign key
    cursor.execute(
        """INSERT INTO signals (symbol, direction, confidence, price, strategy, trade_id)
        VALUES ('V10', 'BUY', 0.85, 1.2345, 'XGBoost', ?)""",
        (trade_id,)
    )
    signal_id = cursor.lastrowid
    logger.success(f"  Inserted signal with ID: {signal_id}")

    # Query signal with trade
    cursor.execute(
        """SELECT s.id, s.symbol, t.id, t.entry_price
        FROM signals s
        JOIN trades t ON s.trade_id = t.id
        WHERE s.id = ?""",
        (signal_id,)
    )
    result = cursor.fetchone()
    assert result is not None, "Foreign key join failed"
    assert result[2] == trade_id, "Foreign key relationship incorrect"
    logger.success("  Foreign key relationship works correctly")

    # Insert sample configuration
    cursor.execute(
        """INSERT INTO configurations (config_key, config_value, description, category)
        VALUES ('test.key', 'test_value', 'Test configuration', 'test')"""
    )
    logger.success("  Inserted configuration")

    # Insert sample performance metrics
    cursor.execute(
        """INSERT INTO performance_metrics (period, period_start, period_end, total_trades, win_rate)
        VALUES ('daily', datetime('now'), datetime('now'), 10, 60.0)"""
    )
    logger.success("  Inserted performance metrics")

    # Insert sample model
    cursor.execute(
        """INSERT INTO models (model_name, model_type, model_version, symbol, training_samples, features_used, file_path, accuracy, precision, recall, f1_score)
        VALUES ('TestModel', 'XGBoost', '1.0.0', 'V10', 1000, '[\"feature1\", \"feature2\"]', '/models/test.pkl', 0.85, 0.87, 0.83, 0.85)"""
    )
    logger.success("  Inserted model metadata")

    # Insert sample market data
    cursor.execute(
        """INSERT INTO market_data (symbol, timeframe, timestamp, open_price, high_price, low_price, close_price, volume)
        VALUES ('V10', 'M1', datetime('now'), 1.2340, 1.2350, 1.2335, 1.2345, 1000)"""
    )
    logger.success("  Inserted market data")

    # Insert sample system log
    cursor.execute(
        """INSERT INTO system_logs (level, message, context, source)
        VALUES ('INFO', 'Test log message', '{\"test\": true}', 'test_schema')"""
    )
    logger.success("  Inserted system log")


def test_views_queries(cursor):
    """Test views return correct data."""
    logger.info("Testing views...")

    # Test v_active_trades
    cursor.execute("SELECT * FROM v_active_trades")
    result = cursor.fetchall()
    logger.success(f"  v_active_trades: {len(result)} rows")

    # Test v_performance_summary
    cursor.execute("SELECT * FROM v_performance_summary")
    result = cursor.fetchall()
    logger.success(f"  v_performance_summary: {len(result)} rows")

    # Test v_active_models
    cursor.execute("SELECT * FROM v_active_models")
    result = cursor.fetchall()
    logger.success(f"  v_active_models: {len(result)} rows")

    # Test v_recent_signals
    cursor.execute("SELECT * FROM v_recent_signals")
    result = cursor.fetchall()
    logger.success(f"  v_recent_signals: {len(result)} rows")


def run_all_tests():
    """Run all schema tests."""
    logger.info("Starting schema tests...")
    logger.info(f"Test database: {TEST_DB_PATH}")

    conn = None
    try:
        # Setup
        conn = setup_test_database()
        cursor = conn.cursor()

        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        # Test tables exist
        logger.info("Testing table creation...")
        tables = [
            "trades",
            "performance_metrics",
            "models",
            "configurations",
            "market_data",
            "signals",
            "system_logs",
            "schema_migrations"
        ]
        for table in tables:
            test_table_exists(cursor, table)

        # Test indexes
        logger.info("Testing indexes...")
        test_indexes(cursor, "trades", [
            "ix_trades_symbol",
            "ix_trades_status",
            "ix_trades_entry_time",
            "ix_trades_symbol_status"
        ])
        test_indexes(cursor, "performance_metrics", [
            "ix_performance_period",
            "ix_performance_period_start"
        ])
        test_indexes(cursor, "signals", [
            "ix_signals_symbol",
            "ix_signals_timestamp",
            "ix_signals_executed"
        ])

        # Test foreign keys
        logger.info("Testing foreign keys...")
        test_foreign_keys(cursor)

        # Test views
        logger.info("Testing views...")
        test_views(cursor)

        # Test triggers
        logger.info("Testing triggers...")
        test_triggers(cursor)

        # Test constraints
        test_constraints(cursor)

        # Test sample data
        test_sample_data(cursor)

        # Test views with data
        test_views_queries(cursor)

        # Commit all test data
        conn.commit()

        logger.success("All schema tests passed successfully!")
        return True

    except AssertionError as e:
        logger.error(f"Test failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False
    finally:
        if conn:
            conn.close()
            # Clean up test database
            if TEST_DB_PATH.exists():
                os.remove(TEST_DB_PATH)
                logger.info(f"Cleaned up test database: {TEST_DB_PATH}")


if __name__ == "__main__":
    import sys

    # Configure logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

    success = run_all_tests()
    sys.exit(0 if success else 1)
