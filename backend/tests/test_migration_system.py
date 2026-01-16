"""
Test suite for Migration System.

Tests cover:
- Migration manager initialization
- Migration discovery and loading
- Applying migrations
- Rolling back migrations
- Migration tracking
- Status reporting
- Error handling
"""
import asyncio
import pytest
import tempfile
from pathlib import Path
from datetime import datetime

from migrations import Migration, MigrationManager
from app.services.sqlite_connection import Database


# ============================================================================
# Test Migrations
# ============================================================================

class TestMigration001(Migration):
    """Test migration 001 - Create test table."""

    version = "001"
    description = "Create test_users table"
    author = "Test"

    async def up(self, conn) -> None:
        await conn.execute("""
            CREATE TABLE test_users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE
            )
        """)

    async def down(self, conn) -> None:
        await conn.execute("DROP TABLE IF EXISTS test_users")


class TestMigration002(Migration):
    """Test migration 002 - Add another table."""

    version = "002"
    description = "Create test_posts table"
    author = "Test"

    async def up(self, conn) -> None:
        await conn.execute("""
            CREATE TABLE test_posts (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES test_users(id)
            )
        """)

    async def down(self, conn) -> None:
        await conn.execute("DROP TABLE IF EXISTS test_posts")


class TestMigration003(Migration):
    """Test migration 003 - Add column to existing table."""

    version = "003"
    description = "Add age column to test_users"
    author = "Test"

    async def up(self, conn) -> None:
        await conn.execute("ALTER TABLE test_users ADD COLUMN age INTEGER")

    async def down(self, conn) -> None:
        # SQLite doesn't support DROP COLUMN directly
        # For testing, we recreate the table without the column
        await conn.execute("""
            CREATE TABLE test_users_new (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE
            )
        """)
        await conn.execute("""
            INSERT INTO test_users_new (id, name, email)
            SELECT id, name, email FROM test_users
        """)
        await conn.execute("DROP TABLE test_users")
        await conn.execute("ALTER TABLE test_users_new RENAME TO test_users")


class TestMigrationWithValidation(Migration):
    """Test migration with pre/post validation."""

    version = "999"
    description = "Test migration with validation"
    author = "Test"

    async def pre_up_check(self, conn) -> bool:
        # Check that test_users doesn't exist yet
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_validation'"
        )
        result = await cursor.fetchone()
        return result is None

    async def up(self, conn) -> None:
        await conn.execute("""
            CREATE TABLE test_validation (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

    async def down(self, conn) -> None:
        await conn.execute("DROP TABLE IF EXISTS test_validation")


class TestMigrationFailingValidation(Migration):
    """Test migration that fails post-validation."""

    version = "998"
    description = "Test migration with failing post validation"
    author = "Test"

    async def up(self, conn) -> None:
        await conn.execute("""
            CREATE TABLE test_fail_validation (
                id INTEGER PRIMARY KEY,
                value TEXT
            )
        """)

    async def post_up_check(self, conn) -> bool:
        # Always fail to test rollback
        return False

    async def down(self, conn) -> None:
        await conn.execute("DROP TABLE IF EXISTS test_fail_validation")


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_db_path():
    """Create a temporary database path for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def temp_migrations_dir():
    """Create a temporary migrations directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        migrations_dir = Path(tmpdir) / "migrations"
        migrations_dir.mkdir()
        yield migrations_dir


@pytest.fixture
async def migration_manager(temp_db_path, temp_migrations_dir):
    """Create a migration manager instance for testing."""
    manager = MigrationManager(temp_db_path, str(temp_migrations_dir))
    await manager.initialize()
    yield manager
    await manager.close()


# Write test migration files
@pytest.fixture
def setup_test_migrations(temp_migrations_dir):
    """Write test migration files to temp directory."""
    # Write migration 001
    (temp_migrations_dir / "001_test_users.py").write_text("""
from aiosqlite import Connection
from migrations import Migration

class Migration_001(Migration):
    version = "001"
    description = "Create test_users table"
    author = "Test"

    async def up(self, conn: Connection) -> None:
        await conn.execute('''
            CREATE TABLE test_users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE
            )
        ''')

    async def down(self, conn: Connection) -> None:
        await conn.execute('DROP TABLE IF EXISTS test_users')
""")

    # Write migration 002
    (temp_migrations_dir / "002_test_posts.py").write_text("""
from aiosqlite import Connection
from migrations import Migration

class Migration_002(Migration):
    version = "002"
    description = "Create test_posts table"
    author = "Test"

    async def up(self, conn: Connection) -> None:
        await conn.execute('''
            CREATE TABLE test_posts (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                user_id INTEGER
            )
        ''')

    async def down(self, conn: Connection) -> None:
        await conn.execute('DROP TABLE IF EXISTS test_posts')
""")

    # Write migration 003
    (temp_migrations_dir / "003_add_age_column.py").write_text("""
from aiosqlite import Connection
from migrations import Migration

class Migration_003(Migration):
    version = "003"
    description = "Add age column to test_users"
    author = "Test"

    async def up(self, conn: Connection) -> None:
        await conn.execute('ALTER TABLE test_users ADD COLUMN age INTEGER')

    async def down(self, conn: Connection) -> None:
        await conn.execute('''
            CREATE TABLE test_users_new (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE
            )
        ''')
        await conn.execute('''
            INSERT INTO test_users_new (id, name, email)
            SELECT id, name, email FROM test_users
        ''')
        await conn.execute('DROP TABLE test_users')
        await conn.execute('ALTER TABLE test_users_new RENAME TO test_users')
""")


# ============================================================================
# Tests
# ============================================================================

@pytest.mark.asyncio
async def test_migration_manager_initialization(temp_db_path, temp_migrations_dir):
    """Test migration manager initialization."""
    manager = MigrationManager(temp_db_path, str(temp_migrations_dir))
    await manager.initialize()

    # Verify schema_migrations table was created
    async with manager.database.transaction() as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        )
        result = await cursor.fetchone()
        assert result is not None

    await manager.close()


@pytest.mark.asyncio
async def test_migration_discovery(setup_test_migrations, migration_manager):
    """Test migration discovery from files."""
    migrations = migration_manager._discover_migrations()

    assert len(migrations) == 3
    assert "001" in migrations
    assert "002" in migrations
    assert "003" in migrations

    # Verify migration properties
    assert migrations["001"].description == "Create test_users table"
    assert migrations["002"].description == "Create test_posts table"
    assert migrations["003"].description == "Add age column to test_users"


@pytest.mark.asyncio
async def test_apply_single_migration(setup_test_migrations, migration_manager):
    """Test applying a single migration."""
    results = await migration_manager.migrate(target_version="001")

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].version == "001"
    assert "Applied" in results[0].message

    # Verify table was created
    async with migration_manager.database.transaction() as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_users'"
        )
        result = await cursor.fetchone()
        assert result is not None


@pytest.mark.asyncio
async def test_apply_multiple_migrations(setup_test_migrations, migration_manager):
    """Test applying multiple migrations in order."""
    results = await migration_manager.migrate()

    assert len(results) == 3
    assert all(r.success for r in results)

    # Verify all tables exist
    async with migration_manager.database.transaction() as conn:
        cursor = await conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'test_%'"
        )
        tables = await cursor.fetchall()
        table_names = [t[0] for t in tables]
        assert "test_users" in table_names
        assert "test_posts" in table_names


@pytest.mark.asyncio
async def test_get_applied_migrations(setup_test_migrations, migration_manager):
    """Test retrieving applied migrations."""
    await migration_manager.migrate()

    applied = await migration_manager.get_applied_migrations()

    assert len(applied) == 3
    assert applied[0].version == "001"
    assert applied[1].version == "002"
    assert applied[2].version == "003"


@pytest.mark.asyncio
async def test_get_pending_migrations(setup_test_migrations, migration_manager):
    """Test retrieving pending migrations."""
    # Apply one migration
    await migration_manager.migrate(target_version="001")

    pending = await migration_manager.get_pending_migrations()

    assert len(pending) == 2
    assert pending[0].version == "002"
    assert pending[1].version == "003"


@pytest.mark.asyncio
async def test_rollback_single_migration(setup_test_migrations, migration_manager):
    """Test rolling back a single migration."""
    # Apply migrations
    await migration_manager.migrate(target_version="002")

    # Rollback one step
    results = await migration_manager.rollback(steps=1)

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].version == "002"

    # Verify migration 002 table is gone
    applied = await migration_manager.get_applied_migrations()
    assert len(applied) == 1
    assert applied[0].version == "001"


@pytest.mark.asyncio
async def test_rollback_to_version(setup_test_migrations, migration_manager):
    """Test rolling back to a specific version."""
    # Apply all migrations
    await migration_manager.migrate()

    # Rollback to version 001
    results = await migration_manager.rollback(target_version="001")

    assert len(results) == 2  # Rolls back 003 and 002
    assert all(r.success for r in results)

    # Verify only migration 001 remains
    applied = await migration_manager.get_applied_migrations()
    assert len(applied) == 1
    assert applied[0].version == "001"


@pytest.mark.asyncio
async def test_get_status(setup_test_migrations, migration_manager):
    """Test getting migration status."""
    # Apply one migration
    await migration_manager.migrate(target_version="001")

    status = await migration_manager.get_status()

    assert status["applied_count"] == 1
    assert status["pending_count"] == 2
    assert status["current_version"] == "001"
    assert len(status["applied_migrations"]) == 1
    assert len(status["pending_migrations"]) == 2


@pytest.mark.asyncio
async def test_dry_run_migration(setup_test_migrations, migration_manager):
    """Test dry run mode for migrations."""
    results = await migration_manager.migrate(dry_run=True)

    assert len(results) == 3
    assert all(r.success for r in results)
    assert all("Dry run" in r.message for r in results)

    # Verify no tables were actually created
    applied = await migration_manager.get_applied_migrations()
    assert len(applied) == 0


@pytest.mark.asyncio
async def test_dry_run_rollback(setup_test_migrations, migration_manager):
    """Test dry run mode for rollback."""
    # Apply migrations first
    await migration_manager.migrate(target_version="002")

    # Dry run rollback
    results = await migration_manager.rollback(steps=1, dry_run=True)

    assert len(results) == 1
    assert results[0].success is True
    assert "Dry run" in results[0].message

    # Verify migration is still applied
    applied = await migration_manager.get_applied_migrations()
    assert len(applied) == 2


@pytest.mark.asyncio
async def test_migration_idempotency(setup_test_migrations, migration_manager):
    """Test that applying already-applied migrations is safe."""
    # Apply migrations
    await migration_manager.migrate()

    # Try to apply again - should be no-op
    results = await migration_manager.migrate()

    assert len(results) == 0  # No pending migrations


@pytest.mark.asyncio
async def test_migration_execution_time_tracking(setup_test_migrations, migration_manager):
    """Test that migration execution time is tracked."""
    await migration_manager.migrate(target_version="001")

    applied = await migration_manager.get_applied_migrations()
    assert applied[0].execution_time_ms is not None
    assert applied[0].execution_time_ms >= 0


@pytest.mark.asyncio
async def test_rollback_then_reapply(setup_test_migrations, migration_manager):
    """Test rolling back and then reapplying migrations."""
    # Apply migrations
    await migration_manager.migrate(target_version="002")

    # Rollback
    await migration_manager.rollback(steps=1)

    # Reapply
    results = await migration_manager.migrate(target_version="002")

    assert len(results) == 1
    assert results[0].success is True

    # Verify both migrations are applied
    applied = await migration_manager.get_applied_migrations()
    assert len(applied) == 2


@pytest.mark.asyncio
async def test_create_migration_file(migration_manager):
    """Test creating a new migration file."""
    file_path = await migration_manager.create_migration(
        version="004",
        description="add test table",
        author="Test Suite"
    )

    assert Path(file_path).exists()
    assert "004_add_test_table.py" in file_path

    # Verify file content
    content = Path(file_path).read_text()
    assert "Migration_004" in content
    assert "add test table" in content
    assert "async def up" in content
    assert "async def down" in content


@pytest.mark.asyncio
async def test_error_on_invalid_version(migration_manager):
    """Test error handling for invalid migration version."""
    with pytest.raises(ValueError, match="Version must be numeric"):
        await migration_manager.create_migration(
            version="abc",
            description="test"
        )


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
