"""
Base Migration class for EURABAY Living System migration system.

All migrations must inherit from this class and implement up() and down() methods.
"""
from abc import ABC, abstractmethod
from typing import Optional
from aiosqlite import Connection
from loguru import logger


class Migration(ABC):
    """
    Abstract base class for database migrations.

    Each migration must implement:
    - up(): Apply the migration changes
    - down(): Revert the migration changes

    Migration files should follow naming convention:
    {version}_{description}.py

    Example:
        001_create_schema.py
        002_add_user_table.py
    """

    # Migration metadata - must be overridden by subclasses
    version: str = ""  # e.g., "001", "002"
    description: str = ""  # e.g., "Create initial schema"
    author: str = "System"  # Optional: Migration author

    def __init__(self):
        """Initialize migration instance."""
        if not self.version:
            raise ValueError(f"Migration {self.__class__.__name__} must define a version")
        if not self.description:
            raise ValueError(f"Migration {self.__class__.__name__} must define a description")

    @abstractmethod
    async def up(self, conn: Connection) -> None:
        """
        Apply the migration.

        This method should contain all SQL operations to upgrade the schema.
        Use the provided connection to execute SQL statements.

        Args:
            conn: Database connection to execute migration

        Example:
            await conn.execute(\"\"\\
                CREATE TABLE users (\\
                    id INTEGER PRIMARY KEY,\\
                    name TEXT NOT NULL\\
                )\\
            \"\")
        """
        pass

    @abstractmethod
    async def down(self, conn: Connection) -> None:
        """
        Revert the migration.

        This method should contain all SQL operations to downgrade the schema.
        It must exactly reverse the changes made in up().

        Args:
            conn: Database connection to execute rollback

        Example:
            await conn.execute(\"DROP TABLE users\")
        """
        pass

    async def pre_up_check(self, conn: Connection) -> bool:
        """
        Optional pre-migration validation check.

        Override this method to perform validation before applying migration.
        Return False to abort the migration.

        Args:
            conn: Database connection for validation queries

        Returns:
            True if migration should proceed, False to abort

        Example:
            result = await conn.execute(\\
                \"SELECT name FROM sqlite_master WHERE type='table' AND name='users'\"\\
            )
            return await result.fetchone() is None
        """
        return True

    async def post_up_check(self, conn: Connection) -> bool:
        """
        Optional post-migration validation check.

        Override this method to perform validation after applying migration.
        Return False to indicate migration failed.

        Args:
            conn: Database connection for validation queries

        Returns:
            True if migration succeeded, False if it failed

        Example:
            result = await conn.execute(\\
                \"SELECT name FROM sqlite_master WHERE type='table' AND name='users'\"\\
            )
            return await result.fetchone() is not None
        """
        return True

    def __repr__(self) -> str:
        """String representation of migration."""
        return f"Migration(version={self.version}, description={self.description})"

    def __str__(self) -> str:
        """User-friendly string representation."""
        return f"{self.version}: {self.description}"
