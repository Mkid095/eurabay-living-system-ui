"""
Migration Manager for EURABAY Living System.

Manages database schema migrations including applying, rolling back,
and tracking migration status.
"""
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from aiosqlite import Connection
from loguru import logger

from .migration_base import Migration
from app.services.sqlite_connection import Database


class MigrationRecord:
    """Represents a migration record in the database."""

    def __init__(
        self,
        id: int,
        version: str,
        description: str,
        applied_at: str,
        execution_time_ms: Optional[int] = None
    ):
        self.id = id
        self.version = version
        self.description = description
        self.applied_at = applied_at
        self.execution_time_ms = execution_time_ms

    def __repr__(self) -> str:
        return f"MigrationRecord(version={self.version}, applied_at={self.applied_at})"


class MigrationResult:
    """Result of a migration operation."""

    def __init__(
        self,
        success: bool,
        version: str,
        message: str,
        execution_time_ms: Optional[int] = None,
        error: Optional[str] = None
    ):
        self.success = success
        self.version = version
        self.message = message
        self.execution_time_ms = execution_time_ms
        self.error = error

    def __repr__(self) -> str:
        status = "SUCCESS" if self.success else "FAILED"
        return f"MigrationResult({status}, version={self.version}, message={self.message})"


class MigrationManager:
    """
    Manages database schema migrations.

    Features:
    - Track applied migrations in schema_migrations table
    - Apply pending migrations in order
    - Rollback migrations to previous versions
    - Auto-discover migration files
    - Comprehensive logging and error handling
    """

    def __init__(self, db_path: str, migrations_dir: str):
        """
        Initialize migration manager.

        Args:
            db_path: Path to SQLite database file
            migrations_dir: Path to migrations directory containing migration files
        """
        self.db_path = db_path
        self.migrations_dir = Path(migrations_dir)
        self.database = Database(db_path)
        self._migrations_cache: Optional[Dict[str, Migration]] = None

    async def initialize(self) -> None:
        """
        Initialize migration manager and database connection.

        Creates schema_migrations tracking table if it doesn't exist.
        """
        await self.database.initialize()

        # Create schema_migrations table
        await self.database.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version VARCHAR(20) NOT NULL UNIQUE,
                description TEXT NOT NULL,
                applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                execution_time_ms INTEGER,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        logger.info("Migration manager initialized")

    async def close(self) -> None:
        """Close database connections."""
        await self.database.close()

    def _discover_migrations(self) -> Dict[str, Migration]:
        """
        Discover migration files in the migrations directory.

        Returns:
            Dictionary mapping version numbers to Migration instances

        Raises:
            ValueError: If migration files have invalid format or duplicate versions
        """
        if self._migrations_cache is not None:
            return self._migrations_cache

        migrations: Dict[str, Migration] = {}

        # Find all Python files in migrations directory
        migration_files = sorted(self.migrations_dir.glob("*.py"))

        for file_path in migration_files:
            # Skip __init__.py and base files
            if file_path.name.startswith("__") or file_path.name.startswith("migration_"):
                continue

            # Extract version from filename (e.g., "001_create_schema.py")
            stem = file_path.stem
            parts = stem.split("_", 1)

            if len(parts) < 2:
                logger.warning(f"Skipping invalid migration file: {file_path.name}")
                continue

            version = parts[0]

            # Validate version format (numeric)
            if not version.isdigit():
                logger.warning(f"Skipping migration with non-numeric version: {file_path.name}")
                continue

            # Dynamically import migration class
            try:
                # Import module from migrations directory
                import importlib.util
                spec = importlib.util.spec_from_file_location(stem, file_path)
                if spec is None or spec.loader is None:
                    logger.warning(f"Could not load migration: {file_path.name}")
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Find Migration subclass in module
                migration_class = None
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, Migration)
                        and attr is not Migration
                    ):
                        migration_class = attr
                        break

                if migration_class is None:
                    logger.warning(f"No Migration subclass found in: {file_path.name}")
                    continue

                # Instantiate migration
                migration = migration_class()

                # Validate version matches filename
                if migration.version != version:
                    logger.warning(
                        f"Migration version mismatch: file={version}, class={migration.version}"
                    )
                    continue

                # Check for duplicate versions
                if version in migrations:
                    raise ValueError(f"Duplicate migration version: {version}")

                migrations[version] = migration
                logger.debug(f"Discovered migration: {migration}")

            except Exception as e:
                logger.error(f"Error loading migration {file_path.name}: {e}")
                raise

        self._migrations_cache = migrations
        logger.info(f"Discovered {len(migrations)} migrations")
        return migrations

    async def get_applied_migrations(self) -> List[MigrationRecord]:
        """
        Get list of applied migrations from database.

        Returns:
            List of MigrationRecord objects sorted by version
        """
        rows = await self.database.execute(
            "SELECT id, version, description, applied_at, execution_time_ms "
            "FROM schema_migrations ORDER BY version",
            fetch="all"
        )

        records = []
        if rows:
            for row in rows:
                records.append(MigrationRecord(
                    id=row["id"],
                    version=row["version"],
                    description=row["description"],
                    applied_at=row["applied_at"],
                    execution_time_ms=row["execution_time_ms"]
                ))

        logger.debug(f"Found {len(records)} applied migrations")
        return records

    async def get_pending_migrations(self) -> List[Migration]:
        """
        Get list of pending migrations not yet applied.

        Returns:
            List of Migration objects sorted by version
        """
        all_migrations = self._discover_migrations()
        applied = await self.get_applied_migrations()
        applied_versions = {record.version for record in applied}

        pending = [
            migration for version, migration in sorted(all_migrations.items())
            if version not in applied_versions
        ]

        logger.debug(f"Found {len(pending)} pending migrations")
        return pending

    async def migrate(
        self,
        target_version: Optional[str] = None,
        dry_run: bool = False
    ) -> List[MigrationResult]:
        """
        Apply pending migrations.

        Args:
            target_version: Optional target version to migrate to.
                          If None, applies all pending migrations.
            dry_run: If True, simulate migration without applying changes

        Returns:
            List of MigrationResult objects for each migration

        Raises:
            ValueError: If target_version is not found or invalid
        """
        logger.info(f"Starting migration (target={target_version or 'latest'}, dry_run={dry_run})")

        pending = await self.get_pending_migrations()
        results: List[MigrationResult] = []

        if not pending:
            logger.info("No pending migrations to apply")
            return results

        # Filter by target version if specified
        if target_version:
            if target_version not in {m.version for m in pending}:
                # Check if it's already applied
                applied = await self.get_applied_migrations()
                applied_versions = {r.version for r in applied}
                if target_version in applied_versions:
                    logger.info(f"Target version {target_version} already applied")
                    return results
                raise ValueError(f"Target version {target_version} not found in pending migrations")

            pending = [m for m in pending if m.version <= target_version]

        # Apply migrations in order
        for migration in pending:
            result = await self._apply_migration(migration, dry_run)
            results.append(result)

            if not result.success and not dry_run:
                logger.error(f"Migration failed: {result.error}. Stopping migration pipeline.")
                break

        logger.info(f"Migration complete: {len([r for r in results if r.success])} successful")
        return results

    async def _apply_migration(
        self,
        migration: Migration,
        dry_run: bool = False
    ) -> MigrationResult:
        """
        Apply a single migration.

        Args:
            migration: Migration instance to apply
            dry_run: If True, simulate without applying

        Returns:
            MigrationResult with outcome details
        """
        start_time = datetime.now()
        logger.info(f"Applying migration: {migration}")

        if dry_run:
            logger.info(f"[DRY RUN] Would apply: {migration}")
            return MigrationResult(
                success=True,
                version=migration.version,
                message=f"Dry run: would apply {migration.description}",
                execution_time_ms=0
            )

        try:
            async with self.database.transaction() as conn:
                # Pre-migration validation
                if not await migration.pre_up_check(conn):
                    return MigrationResult(
                        success=False,
                        version=migration.version,
                        message="Pre-migration check failed",
                        error="Migration aborted by pre-up check"
                    )

                # Apply migration
                await migration.up(conn)

                # Post-migration validation
                if not await migration.post_up_check(conn):
                    await conn.rollback()
                    return MigrationResult(
                        success=False,
                        version=migration.version,
                        message="Post-migration check failed",
                        error="Migration rolled back by post-up check"
                    )

                # Record migration
                execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                await conn.execute(
                    "INSERT INTO schema_migrations (version, description, execution_time_ms) "
                    "VALUES (?, ?, ?)",
                    (migration.version, migration.description, execution_time_ms)
                )

                logger.success(f"Migration applied successfully: {migration} ({execution_time_ms}ms)")
                return MigrationResult(
                    success=True,
                    version=migration.version,
                    message=f"Applied: {migration.description}",
                    execution_time_ms=execution_time_ms
                )

        except Exception as e:
            logger.error(f"Migration failed: {migration} - {e}")
            return MigrationResult(
                success=False,
                version=migration.version,
                message="Migration failed with exception",
                error=str(e)
            )

    async def rollback(
        self,
        steps: int = 1,
        target_version: Optional[str] = None,
        dry_run: bool = False
    ) -> List[MigrationResult]:
        """
        Rollback migrations.

        Args:
            steps: Number of migrations to rollback (default: 1)
            target_version: Rollback to this specific version (exclusive)
            dry_run: If True, simulate rollback without applying

        Returns:
            List of MigrationResult objects for each rollback

        Raises:
            ValueError: If target version not found or invalid parameters
        """
        if steps < 1:
            raise ValueError("Steps must be at least 1")

        logger.info(f"Starting rollback (steps={steps}, target={target_version}, dry_run={dry_run})")

        applied = await self.get_applied_migrations()
        if not applied:
            logger.info("No migrations to rollback")
            return []

        # Sort by version descending (most recent first)
        applied_sorted = sorted(applied, key=lambda r: r.version, reverse=True)

        # Determine which migrations to rollback
        to_rollback: List[MigrationRecord] = []

        if target_version:
            # Rollback all migrations after target_version
            found_target = False
            for record in applied_sorted:
                if record.version == target_version:
                    found_target = True
                    break
                to_rollback.append(record)

            if not found_target:
                raise ValueError(f"Target version {target_version} not found in applied migrations")
        else:
            # Rollback N most recent migrations
            to_rollback = applied_sorted[:steps]

        # Sort ascending for proper rollback order
        to_rollback = sorted(to_rollback, key=lambda r: r.version, reverse=True)

        results: List[MigrationResult] = []
        all_migrations = self._discover_migrations()

        for record in to_rollback:
            if record.version not in all_migrations:
                logger.error(f"Migration file not found for version: {record.version}")
                results.append(MigrationResult(
                    success=False,
                    version=record.version,
                    message="Migration file not found",
                    error=f"No migration file for version {record.version}"
                ))
                continue

            migration = all_migrations[record.version]
            result = await self._rollback_migration(migration, record, dry_run)
            results.append(result)

            if not result.success and not dry_run:
                logger.error(f"Rollback failed: {result.error}. Stopping rollback pipeline.")
                break

        logger.info(f"Rollback complete: {len([r for r in results if r.success])} successful")
        return results

    async def _rollback_migration(
        self,
        migration: Migration,
        record: MigrationRecord,
        dry_run: bool = False
    ) -> MigrationResult:
        """
        Rollback a single migration.

        Args:
            migration: Migration instance to rollback
            record: MigrationRecord from database
            dry_run: If True, simulate without applying

        Returns:
            MigrationResult with outcome details
        """
        start_time = datetime.now()
        logger.info(f"Rolling back migration: {migration}")

        if dry_run:
            logger.info(f"[DRY RUN] Would rollback: {migration}")
            return MigrationResult(
                success=True,
                version=migration.version,
                message=f"Dry run: would rollback {migration.description}",
                execution_time_ms=0
            )

        try:
            async with self.database.transaction() as conn:
                # Apply down migration
                await migration.down(conn)

                # Remove migration record
                await conn.execute(
                    "DELETE FROM schema_migrations WHERE version = ?",
                    (migration.version,)
                )

                execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                logger.success(f"Migration rolled back successfully: {migration} ({execution_time_ms}ms)")
                return MigrationResult(
                    success=True,
                    version=migration.version,
                    message=f"Rolled back: {migration.description}",
                    execution_time_ms=execution_time_ms
                )

        except Exception as e:
            logger.error(f"Rollback failed: {migration} - {e}")
            return MigrationResult(
                success=False,
                version=migration.version,
                message="Rollback failed with exception",
                error=str(e)
            )

    async def get_status(self) -> Dict[str, any]:
        """
        Get current migration status.

        Returns:
            Dictionary with migration status information
        """
        applied = await self.get_applied_migrations()
        pending = await self.get_pending_migrations()

        current_version = applied[-1].version if applied else "None"

        return {
            "current_version": current_version,
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied_migrations": [str(m) for m in applied],
            "pending_migrations": [str(m) for m in pending],
            "database_path": str(self.db_path),
            "migrations_directory": str(self.migrations_dir)
        }

    async def create_migration(
        self,
        version: str,
        description: str,
        author: str = "System"
    ) -> str:
        """
        Create a new migration file template.

        Args:
            version: Migration version number (e.g., "003")
            description: Description of the migration
            author: Optional author name

        Returns:
            Path to created migration file

        Raises:
            ValueError: If version is invalid or file already exists
        """
        if not version.isdigit():
            raise ValueError(f"Version must be numeric: {version}")

        filename = f"{version}_{description.lower().replace(' ', '_').replace('-', '_')}.py"
        file_path = self.migrations_dir / filename

        if file_path.exists():
            raise ValueError(f"Migration file already exists: {filename}")

        # Generate migration template
        template = f'''"""
{description}

Migration Version: {version}
Author: {author}
Created: {datetime.now().isoformat()}
"""
from aiosqlite import Connection
from backend.migrations import Migration


class Migration_{version}(Migration):
    """{description}"""

    version = "{version}"
    description = "{description}"
    author = "{author}"

    async def up(self, conn: Connection) -> None:
        """
        Apply the migration.

        Add your schema changes here.
        """
        # Example: Create a table
        # await conn.execute("""
        #     CREATE TABLE example_table (
        #         id INTEGER PRIMARY KEY,
        #         name TEXT NOT NULL,
        #         created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        #     )
        # """)
        pass

    async def down(self, conn: Connection) -> None:
        """
        Revert the migration.

        Add your rollback logic here.
        """
        # Example: Drop the table
        # await conn.execute("DROP TABLE example_table")
        pass
'''

        # Write migration file
        file_path.write_text(template)

        logger.info(f"Created migration file: {file_path}")
        return str(file_path)

    async def generate_migration_from_schema(
        self,
        old_schema: str,
        new_schema: str,
        version: str,
        description: str
    ) -> str:
        """
        Auto-generate migration by comparing two schemas.

        This is a simplified implementation. For production use, consider
        using a more sophisticated schema diffing tool.

        Args:
            old_schema: Path to old schema.sql file
            new_schema: Path to new schema.sql file
            version: Migration version
            description: Migration description

        Returns:
            Path to generated migration file
        """
        # Read schemas
        old_path = Path(old_schema)
        new_path = Path(new_schema)

        if not old_path.exists():
            raise ValueError(f"Old schema file not found: {old_schema}")
        if not new_path.exists():
            raise ValueError(f"New schema file not found: {new_schema}")

        old_content = old_path.read_text()
        new_content = new_path.read_text()

        # Simple diff detection (for demonstration)
        # In production, use a proper SQL parser
        diff_lines = []
        new_lines = new_content.split('\n')
        old_lines = old_content.split('\n')

        # Find new CREATE TABLE statements
        new_tables = set()
        for line in new_lines:
            if line.strip().startswith('CREATE TABLE'):
                table_name = line.split()[2]
                new_tables.add(table_name)

        old_tables = set()
        for line in old_lines:
            if line.strip().startswith('CREATE TABLE'):
                table_name = line.split()[2]
                old_tables.add(table_name)

        added_tables = new_tables - old_tables

        # Generate migration
        file_path = await self.create_migration(version, description)

        # Read the template and modify it
        content = Path(file_path).read_text()

        # Add auto-generated content to up() method
        up_content = "        # Auto-generated from schema diff\n"
        for table in added_tables:
            up_content += f"        # Added table: {table}\n"

        # Replace the pass statement
        content = content.replace('        pass', up_content)

        Path(file_path).write_text(content)

        logger.info(f"Generated migration from schema diff: {file_path}")
        return file_path
