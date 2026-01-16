"""
Test suite for Migration System.

Simplified test suite focused on core migration functionality.
"""
import asyncio
import pytest
import tempfile
from pathlib import Path

from migrations import MigrationManager


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

    async def up(self, conn: Connection) -> None:
        await conn.execute('''
            CREATE TABLE test_users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
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

    async def up(self, conn: Connection) -> None:
        await conn.execute('''
            CREATE TABLE test_posts (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL
            )
        ''')

    async def down(self, conn: Connection) -> None:
        await conn.execute('DROP TABLE IF EXISTS test_posts')
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

    assert len(migrations) == 2
    assert "001" in migrations
    assert "002" in migrations
    assert migrations["001"].description == "Create test_users table"


@pytest.mark.asyncio
async def test_apply_single_migration(setup_test_migrations, migration_manager):
    """Test applying a single migration."""
    results = await migration_manager.migrate(target_version="001")

    assert len(results) == 1
    assert results[0].success is True
    assert results[0].version == "001"

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

    assert len(results) == 2
    assert all(r.success for r in results)

    # Verify tables exist
    tables = await migration_manager.database.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'test_%'",
        fetch="all"
    )
    table_names = [t["name"] for t in tables]
    assert "test_users" in table_names
    assert "test_posts" in table_names


@pytest.mark.asyncio
async def test_get_applied_migrations(setup_test_migrations, migration_manager):
    """Test retrieving applied migrations."""
    await migration_manager.migrate()

    applied = await migration_manager.get_applied_migrations()

    assert len(applied) == 2
    assert applied[0].version == "001"
    assert applied[1].version == "002"


@pytest.mark.asyncio
async def test_get_pending_migrations(setup_test_migrations, migration_manager):
    """Test retrieving pending migrations."""
    # Apply one migration
    await migration_manager.migrate(target_version="001")

    pending = await migration_manager.get_pending_migrations()

    assert len(pending) == 1
    assert pending[0].version == "002"


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

    # Verify only one migration remains
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

    assert len(results) == 1  # Rolls back 002 only
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
    assert status["pending_count"] == 1
    assert status["current_version"] == "001"


@pytest.mark.asyncio
async def test_dry_run_migration(setup_test_migrations, migration_manager):
    """Test dry run mode for migrations."""
    results = await migration_manager.migrate(dry_run=True)

    assert len(results) == 2
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
        version="003",
        description="add test table"
    )

    assert Path(file_path).exists()
    assert "003_add_test_table.py" in file_path

    # Verify file content
    content = Path(file_path).read_text()
    assert "Migration_003" in content
    assert "add test table" in content


@pytest.mark.asyncio
async def test_error_on_invalid_version(migration_manager):
    """Test error handling for invalid migration version."""
    with pytest.raises(ValueError, match="Version must be numeric"):
        await migration_manager.create_migration(
            version="abc",
            description="test"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
