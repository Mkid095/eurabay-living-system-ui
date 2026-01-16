"""
Database connection manager for EURABAY Living System.
Provides async SQLite database operations with connection pooling.
Uses aiosqlite directly for raw SQL operations.
"""
import aiosqlite
import asyncio
from pathlib import Path
from typing import Optional, AsyncIterator, Any, List, Dict
from contextlib import asynccontextmanager
from loguru import logger


class Database:
    """
    Async SQLite database connection manager with connection pooling.
    Provides a simple interface for database operations with proper connection management.
    """

    def __init__(self, db_path: str, pool_size: int = 5):
        """
        Initialize database connection manager.

        Args:
            db_path: Path to SQLite database file
            pool_size: Maximum number of connections in the pool
        """
        self.db_path = Path(db_path)
        self.pool_size = pool_size
        self._connection_pool: List[aiosqlite.Connection] = []
        self._pool_lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """
        Initialize database connection pool.
        Creates database directory if it doesn't exist and sets up connection pool.
        """
        if self._initialized:
            logger.warning("Database already initialized")
            return

        try:
            # Ensure database directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Initialize connection pool
            async with self._pool_lock:
                for _ in range(self.pool_size):
                    conn = await self._create_connection()
                    self._connection_pool.append(conn)

            self._initialized = True
            logger.info(f"Database initialized: {self.db_path} (pool size: {self.pool_size})")

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    async def _create_connection(self) -> aiosqlite.Connection:
        """
        Create a new database connection.

        Returns:
            aiosqlite.Connection: New database connection
        """
        conn = await aiosqlite.connect(
            self.db_path,
            check_same_thread=False
        )
        # Enable foreign keys
        await conn.execute("PRAGMA foreign_keys = ON")
        # Set journal mode to WAL for better concurrency
        await conn.execute("PRAGMA journal_mode = WAL")
        # Set synchronous mode to NORMAL for better performance
        await conn.execute("PRAGMA synchronous = NORMAL")
        # Set cache size (negative value means KB)
        await conn.execute("PRAGMA cache_size = -64000")
        # Set temp store to memory
        await conn.execute("PRAGMA temp_store = MEMORY")
        return conn

    async def get_connection(self) -> aiosqlite.Connection:
        """
        Get a connection from the pool.
        If pool is empty, creates a new temporary connection.

        Returns:
            aiosqlite.Connection: Database connection
        """
        if not self._initialized:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with self._pool_lock:
            if self._connection_pool:
                conn = self._connection_pool.pop()
                logger.debug(f"Connection retrieved from pool (pool size: {len(self._connection_pool)})")
                return conn
            else:
                # Create temporary connection if pool is empty
                logger.debug("Pool empty, creating temporary connection")
                return await self._create_connection()

    async def return_connection(self, conn: aiosqlite.Connection) -> None:
        """
        Return a connection to the pool.
        If pool is full, closes the connection.

        Args:
            conn: Database connection to return
        """
        async with self._pool_lock:
            if len(self._connection_pool) < self.pool_size:
                self._connection_pool.append(conn)
                logger.debug(f"Connection returned to pool (pool size: {len(self._connection_pool)})")
            else:
                # Close excess connection
                await conn.close()
                logger.debug("Pool full, connection closed")

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """
        Context manager for database transactions.
        Automatically handles commit/rollback.

        Yields:
            aiosqlite.Connection: Database connection

        Example:
            async with db.transaction() as conn:
                await conn.execute("INSERT INTO ...")
                # Automatically commits on success, rolls back on error
        """
        conn = await self.get_connection()
        try:
            yield conn
            await conn.commit()
            logger.debug("Transaction committed successfully")
        except Exception as e:
            await conn.rollback()
            logger.error(f"Transaction rolled back due to error: {e}")
            raise
        finally:
            await self.return_connection(conn)

    async def execute(
        self,
        sql: str,
        parameters: Optional[tuple] = None,
        fetch: str = "none"
    ) -> Optional[Any]:
        """
        Execute a SQL query with automatic connection management.

        Args:
            sql: SQL query to execute
            parameters: Query parameters (optional)
            fetch: What to fetch - "none", "one", "all", "many"

        Returns:
            Query result based on fetch parameter
        """
        async with self.transaction() as conn:
            cursor = await conn.execute(sql, parameters or ())

            if fetch == "none":
                return None
            elif fetch == "one":
                row = await cursor.fetchone()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                return dict(zip(columns, row)) if row and columns else row
            elif fetch == "all":
                rows = await cursor.fetchall()
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                return [dict(zip(columns, row)) for row in rows] if rows and columns else rows
            elif fetch == "many":
                rows = await cursor.fetchmany(10)
                columns = [desc[0] for desc in cursor.description] if cursor.description else []
                return [dict(zip(columns, row)) for row in rows] if rows and columns else rows
            else:
                raise ValueError(f"Invalid fetch parameter: {fetch}")

    async def execute_script(self, script: str) -> None:
        """
        Execute a multi-line SQL script.

        Args:
            script: SQL script to execute
        """
        async with self.transaction() as conn:
            await conn.executescript(script)
        logger.info("SQL script executed successfully")

    async def executemany(
        self,
        sql: str,
        parameters_list: List[tuple]
    ) -> None:
        """
        Execute a SQL query with multiple parameter sets.

        Args:
            sql: SQL query to execute
            parameters_list: List of parameter tuples
        """
        async with self.transaction() as conn:
            await conn.executemany(sql, parameters_list)
        logger.info(f"Executed {len(parameters_list)} operations")

    async def close(self) -> None:
        """
        Close all database connections in the pool.
        Should be called when shutting down the application.
        """
        if not self._initialized:
            logger.warning("Database not initialized, nothing to close")
            return

        async with self._pool_lock:
            for conn in self._connection_pool:
                await conn.close()
            self._connection_pool.clear()

        self._initialized = False
        logger.info("Database connections closed")

    async def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Get information about a table's columns.

        Args:
            table_name: Name of the table

        Returns:
            List of column information dictionaries
        """
        return await self.execute(
            f"PRAGMA table_info({table_name})",
            fetch="all"
        )

    async def table_exists(self, table_name: str) -> bool:
        """
        Check if a table exists in the database.

        Args:
            table_name: Name of the table

        Returns:
            True if table exists, False otherwise
        """
        result = await self.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
            fetch="one"
        )
        return result is not None

    async def get_all_tables(self) -> List[str]:
        """
        Get a list of all tables in the database.

        Returns:
            List of table names
        """
        result = await self.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name",
            fetch="all"
        )
        return [row["name"] for row in result] if result else []

    @property
    def is_initialized(self) -> bool:
        """Check if database is initialized."""
        return self._initialized

    @property
    def pool_size_current(self) -> int:
        """Get current pool size."""
        return len(self._connection_pool)


# Global database instance
_db_instance: Optional[Database] = None


def get_database(db_path: str, pool_size: int = 5) -> Database:
    """
    Get or create global database instance.

    Args:
        db_path: Path to SQLite database file
        pool_size: Maximum number of connections in the pool

    Returns:
        Database instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(db_path, pool_size)
    return _db_instance
