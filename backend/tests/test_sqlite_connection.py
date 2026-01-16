"""
Test SQLite connection manager for EURABAY Living System.
Tests the Database class with connection pooling and async operations.
"""
import asyncio
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from app.services.sqlite_connection import Database, get_database


# Remove default handler and add custom one
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
)


async def test_database_initialization():
    """Test database initialization and connection pool setup."""
    logger.info("Testing database initialization...")

    try:
        # Use temp file for testing
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = Database(db_path, pool_size=3)

        # Test initialization
        assert not db.is_initialized, "Database should not be initialized yet"
        await db.initialize()
        assert db.is_initialized, "Database should be initialized"
        assert db.pool_size_current == 3, f"Pool size should be 3, got {db.pool_size_current}"

        # Test close
        await db.close()
        assert not db.is_initialized, "Database should not be initialized after close"
        assert db.pool_size_current == 0, f"Pool should be empty, got {db.pool_size_current}"

        # Cleanup
        Path(db_path).unlink(missing_ok=True)

        logger.success("Database initialization test PASSED")
        return True
    except Exception as e:
        logger.error(f"Database initialization test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_get_connection():
    """Test getting connections from pool."""
    logger.info("Testing get_connection...")

    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = Database(db_path, pool_size=2)
        await db.initialize()

        # Get connection from pool
        conn1 = await db.get_connection()
        assert conn1 is not None, "Should get connection"
        assert db.pool_size_current == 1, f"Pool should have 1 connection, got {db.pool_size_current}"

        # Get another connection
        conn2 = await db.get_connection()
        assert db.pool_size_current == 0, f"Pool should be empty, got {db.pool_size_current}"

        # Return connections
        await db.return_connection(conn1)
        assert db.pool_size_current == 1, f"Pool should have 1 connection, got {db.pool_size_current}"

        await db.return_connection(conn2)
        assert db.pool_size_current == 2, f"Pool should have 2 connections, got {db.pool_size_current}"

        # Cleanup
        await db.close()
        Path(db_path).unlink(missing_ok=True)

        logger.success("get_connection test PASSED")
        return True
    except Exception as e:
        logger.error(f"get_connection test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_transaction_context_manager():
    """Test transaction context manager."""
    logger.info("Testing transaction context manager...")

    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = Database(db_path, pool_size=2)
        await db.initialize()

        # Create table
        await db.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value INTEGER
            )
        """)

        # Test successful transaction
        async with db.transaction() as conn:
            await conn.execute(
                "INSERT INTO test_table (name, value) VALUES (?, ?)",
                ("test1", 100)
            )

        # Verify data was committed
        result = await db.execute(
            "SELECT * FROM test_table WHERE name = ?",
            ("test1",),
            fetch="one"
        )
        assert result is not None, "Data should be committed"
        assert result["name"] == "test1", "Name mismatch"
        assert result["value"] == 100, "Value mismatch"

        # Test transaction rollback
        try:
            async with db.transaction() as conn:
                await conn.execute(
                    "INSERT INTO test_table (name, value) VALUES (?, ?)",
                    ("test2", 200)
                )
                # Force rollback
                raise ValueError("Test rollback")
        except ValueError:
            pass

        # Verify data was rolled back
        result = await db.execute(
            "SELECT * FROM test_table WHERE name = ?",
            ("test2",),
            fetch="one"
        )
        assert result is None, "Data should be rolled back"

        # Cleanup
        await db.close()
        Path(db_path).unlink(missing_ok=True)

        logger.success("Transaction context manager test PASSED")
        return True
    except Exception as e:
        logger.error(f"Transaction context manager test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_execute_methods():
    """Test various execute methods."""
    logger.info("Testing execute methods...")

    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = Database(db_path, pool_size=2)
        await db.initialize()

        # Create table
        await db.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value INTEGER
            )
        """)

        # Test execute (insert)
        await db.execute(
            "INSERT INTO test_table (name, value) VALUES (?, ?)",
            ("test1", 100)
        )
        await db.execute(
            "INSERT INTO test_table (name, value) VALUES (?, ?)",
            ("test2", 200)
        )
        await db.execute(
            "INSERT INTO test_table (name, value) VALUES (?, ?)",
            ("test3", 300)
        )

        # Test fetch one
        result = await db.execute(
            "SELECT * FROM test_table WHERE name = ?",
            ("test1",),
            fetch="one"
        )
        assert result is not None, "Should fetch one row"
        assert result["name"] == "test1", "Name mismatch"

        # Test fetch all
        results = await db.execute(
            "SELECT * FROM test_table ORDER BY value",
            fetch="all"
        )
        assert len(results) == 3, f"Should fetch 3 rows, got {len(results)}"
        assert results[0]["value"] == 100, "First row value mismatch"

        # Test fetch many
        results = await db.execute(
            "SELECT * FROM test_table ORDER BY value",
            fetch="many"
        )
        assert len(results) <= 10, "Should fetch up to 10 rows"

        # Test executemany
        await db.executemany(
            "INSERT INTO test_table (name, value) VALUES (?, ?)",
            [("batch1", 400), ("batch2", 500), ("batch3", 600)]
        )

        count_result = await db.execute(
            "SELECT COUNT(*) as count FROM test_table",
            fetch="one"
        )
        assert count_result["count"] == 6, f"Should have 6 rows, got {count_result['count']}"

        # Cleanup
        await db.close()
        Path(db_path).unlink(missing_ok=True)

        logger.success("Execute methods test PASSED")
        return True
    except Exception as e:
        logger.error(f"Execute methods test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_utility_methods():
    """Test utility methods like table_exists, get_table_info, etc."""
    logger.info("Testing utility methods...")

    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = Database(db_path, pool_size=2)
        await db.initialize()

        # Create table
        await db.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value INTEGER
            )
        """)

        # Test table_exists
        exists = await db.table_exists("test_table")
        assert exists is True, "Table should exist"

        not_exists = await db.table_exists("non_existent_table")
        assert not_exists is False, "Table should not exist"

        # Test get_all_tables
        tables = await db.get_all_tables()
        assert "test_table" in tables, "test_table should be in tables list"

        # Test get_table_info
        info = await db.get_table_info("test_table")
        assert len(info) == 3, f"Should have 3 columns, got {len(info)}"
        assert info[0]["name"] == "id", "First column should be id"

        # Cleanup
        await db.close()
        Path(db_path).unlink(missing_ok=True)

        logger.success("Utility methods test PASSED")
        return True
    except Exception as e:
        logger.error(f"Utility methods test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_async_operations():
    """Test that async operations work correctly."""
    logger.info("Testing async operations...")

    try:
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        db = Database(db_path, pool_size=5)
        await db.initialize()

        # Create table
        await db.execute("""
            CREATE TABLE test_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                value INTEGER
            )
        """)

        # Test concurrent inserts
        async def insert_value(name: str, value: int):
            await db.execute(
                "INSERT INTO test_table (name, value) VALUES (?, ?)",
                (name, value)
            )

        # Run concurrent operations
        tasks = [
            insert_value(f"concurrent_{i}", i * 10)
            for i in range(10)
        ]
        await asyncio.gather(*tasks)

        # Verify all inserts
        result = await db.execute(
            "SELECT COUNT(*) as count FROM test_table",
            fetch="one"
        )
        assert result["count"] == 10, f"Should have 10 rows, got {result['count']}"

        # Cleanup
        await db.close()
        Path(db_path).unlink(missing_ok=True)

        logger.success("Async operations test PASSED")
        return True
    except Exception as e:
        logger.error(f"Async operations test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all SQLite connection tests."""
    logger.info("=" * 60)
    logger.info("Starting SQLite Connection Tests")
    logger.info("=" * 60)

    tests = [
        ("Database Initialization", test_database_initialization),
        ("Get Connection", test_get_connection),
        ("Transaction Context Manager", test_transaction_context_manager),
        ("Execute Methods", test_execute_methods),
        ("Utility Methods", test_utility_methods),
        ("Async Operations", test_async_operations),
    ]

    results = []
    for name, test_func in tests:
        logger.info("-" * 60)
        result = await test_func()
        results.append((name, result))

    # Print summary
    logger.info("=" * 60)
    logger.info("Test Summary")
    logger.info("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "PASSED" if result else "FAILED"
        symbol = "PASS" if result else "FAIL"
        logger.info(f"{symbol}: {name}: {status}")

    logger.info("-" * 60)
    logger.info(f"Total: {passed}/{total} tests passed")

    if passed == total:
        logger.success("All tests PASSED!")
        return True
    else:
        logger.error(f"{total - passed} test(s) FAILED")
        return False


if __name__ == "__main__":
    # Run tests
    success = asyncio.run(run_all_tests())

    # Exit with appropriate code
    sys.exit(0 if success else 1)
