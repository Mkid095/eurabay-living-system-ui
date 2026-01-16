# EURABAY Living System - Database Backup and Restore Procedures

## Table of Contents
1. [Overview](#overview)
2. [Backup System Architecture](#backup-system-architecture)
3. [Automated Backup Configuration](#automated-backup-configuration)
4. [Manual Backup Procedures](#manual-backup-procedures)
5. [Restore Procedures](#restore-procedures)
6. [Backup Management](#backup-management)
7. [Disaster Recovery](#disaster-recovery)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The EURABAY Living System includes a comprehensive backup and restore system to protect against data loss. All backup operations are logged and include safety checks to prevent data corruption.

### Key Features

- **Automated Daily Backups**: Runs at 3 AM daily by default
- **Gzip Compression**: Reduces backup file size by 80-90%
- **Automatic Cleanup**: Keeps last 7 backups by default
- **Pre-Restore Backup**: Creates safety backup before restore operations
- **Integrity Verification**: Validates backup files before restore
- **Comprehensive Logging**: All operations logged via loguru

### File Locations

| Item | Location |
|------|----------|
| Main Database | `backend/data/eurabay_trading.db` |
| Backup Directory | `backend/backups/` |
| Backup Naming | `eurabay_trading_YYYYMMDD_HHMMSS.microseconds.db.gz` |

---

## Backup System Architecture

### Components

#### 1. BackupService Class

Location: `backend/storage/backup_service.py`

**Key Methods**:
- `backup_database()` - Create timestamped backup with optional compression
- `restore_database()` - Restore from backup file with safety checks
- `list_backups()` - List all available backups
- `delete_backup()` - Delete specific backup file
- `verify_backup()` - Verify backup file integrity
- `get_backup_statistics()` - Get backup analytics
- `_cleanup_old_backups()` - Automatic cleanup (keeps last N backups)

#### 2. BackupScheduler Class

Location: `backend/storage/backup_scheduler.py`

**Key Methods**:
- `start()` - Start automated backup scheduler
- `stop()` - Stop automated backup scheduler
- `run_once()` - Manually trigger a backup
- `get_next_backup_time()` - Get next scheduled backup time

**Scheduler Configuration**:
- Default Schedule: Daily at 3:00 AM
- Timezone: Local system timezone
- Singleton Pattern: Single scheduler instance

---

## Automated Backup Configuration

### Starting the Backup Scheduler

The backup scheduler should be started when the application initializes:

```python
from backend.storage.backup_scheduler import get_scheduler

# Get the singleton scheduler instance
scheduler = get_scheduler()

# Start automated backups (runs daily at 3 AM)
await scheduler.start()

# Check next backup time
next_backup = scheduler.get_next_backup_time()
print(f"Next backup scheduled for: {next_backup}")
```

### Application Startup Example

```python
# In your application startup code
async def start_application():
    """Start the application with automated backups"""
    from backend.storage.backup_scheduler import get_scheduler
    from loguru import logger

    # Start backup scheduler
    scheduler = get_scheduler()
    await scheduler.start()

    logger.info("Backup scheduler started")
    logger.info(f"Next backup: {scheduler.get_next_backup_time()}")

    # Continue with application startup...
```

### Stopping the Backup Scheduler

```python
async def shutdown_application():
    """Gracefully shutdown the application"""
    from backend.storage.backup_scheduler import get_scheduler
    from loguru import logger

    # Stop backup scheduler
    scheduler = get_scheduler()
    await scheduler.stop()

    logger.info("Backup scheduler stopped")
```

### Custom Backup Schedule

To customize the backup schedule, modify the scheduler configuration:

```python
from backend.storage.backup_scheduler import BackupScheduler
from datetime import time

# Create custom scheduler (runs at 2 AM)
custom_scheduler = BackupScheduler(
    backup_time=time(hour=2, minute=0),  # Run at 2 AM
    backup_dir="custom_backups/"  # Custom backup directory
)

await custom_scheduler.start()
```

---

## Manual Backup Procedures

### Creating a Backup

#### Using Python API

```python
from backend.storage.backup_service import BackupService
from loguru import logger

# Initialize backup service
backup_service = BackupService()

# Create a compressed backup
backup_path = await backup_service.backup_database(
    compress=True  # Use gzip compression
)

logger.info(f"Backup created: {backup_path}")
```

#### Creating Uncompressed Backup

```python
# Create backup without compression (faster, larger files)
backup_path = await backup_service.backup_database(
    compress=False
)

logger.info(f"Uncompressed backup: {backup_path}")
```

#### Custom Backup Directory

```python
# Create backup in custom location
backup_service = BackupService(
    backup_dir="/path/to/custom/backups",
    max_backups=10  # Keep last 10 backups
)

backup_path = await backup_service.backup_database()
```

### Listing Available Backups

```python
from backend.storage.backup_service import BackupService

backup_service = BackupService()

# List all backups (newest first)
backups = await backup_service.list_backups()

for backup in backups:
    print(f"File: {backup.filename}")
    print(f"Created: {backup.created_at}")
    print(f"Size: {backup.size_human}")
    print(f"Compressed: {backup.is_compressed}")
    print("---")
```

**BackupInfo Object**:

| Field | Type | Description |
|-------|------|-------------|
| filename | str | Backup filename |
| filepath | str | Full path to backup file |
| created_at | datetime | When backup was created |
| size | int | File size in bytes |
| size_human | str | Human-readable size (e.g., "2.5 MB") |
| is_compressed | bool | Whether backup is compressed |

### Getting Backup Statistics

```python
# Get backup analytics
stats = await backup_service.get_backup_statistics()

print(f"Total backups: {stats.total_backups}")
print(f"Total size: {stats.total_size_human}")
print(f"Oldest backup: {stats.oldest_backup}")
print(f"Newest backup: {stats.newest_backup}")
print(f"Compression ratio: {stats.compression_ratio}")
```

---

## Restore Procedures

### Restoring from Backup

#### Basic Restore

```python
from backend.storage.backup_service import BackupService
from loguru import logger

backup_service = BackupService()

# List available backups
backups = await backup_service.list_backups()

# Restore the most recent backup
latest_backup = backups[0]
logger.info(f"Restoring from: {latest_backup.filename}")

# Perform restore (automatically creates pre-restore backup)
restore_path = await backup_service.restore_database(
    backup_path=latest_backup.filepath
)

logger.info(f"Database restored from: {restore_path}")
```

#### Safety Features

The restore operation includes automatic safety measures:

1. **Pre-Restore Backup**: Automatically backs up current database before restore
2. **Integrity Check**: Verifies backup file is valid before restore
3. **Atomic Operation**: Ensures restore completes fully or rolls back
4. **Comprehensive Logging**: All steps logged for audit trail

### Restore to Specific Backup

```python
# Restore from a specific backup file
restore_path = await backup_service.restore_database(
    backup_path="backend/backups/eurabay_trading_20250117_030000.123456.db.gz"
)

logger.info(f"Restored specific backup: {restore_path}")
```

### Verify Backup Before Restore

```python
# Verify backup integrity before restore
backup_path = "backend/backups/eurabay_trading_20250117_030000.123456.db.gz"

is_valid = await backup_service.verify_backup(backup_path)

if is_valid:
    logger.info("Backup is valid, proceeding with restore")
    await backup_service.restore_database(backup_path)
else:
    logger.error("Backup is corrupted, cannot restore")
```

### Manual Restore Steps (Advanced)

If you need to restore manually without the Python API:

```bash
# 1. Stop the application
# 2. Backup current database (safety)
cp backend/data/eurabay_trading.db backend/data/eurabay_trading.db.backup

# 3. Decompress and restore
gunzip -c backend/backups/eurabay_trading_20250117_030000.123456.db.gz > backend/data/eurabay_trading.db

# 4. Verify database integrity
sqlite3 backend/data/eurabay_trading.db "PRAGMA integrity_check;"

# 5. Restart the application
```

---

## Backup Management

### Deleting Old Backups

```python
from backend.storage.backup_service import BackupService

backup_service = BackupService()

# List backups
backups = await backup_service.list_backups()

# Delete a specific backup
old_backup = backups[-1]  # Get oldest backup
await backup_service.delete_backup(old_backup.filepath)

logger.info(f"Deleted backup: {old_backup.filename}")
```

### Automatic Cleanup

The backup service automatically maintains the configured number of backups:

```python
# Default: Keep last 7 backups
backup_service = BackupService(max_backups=7)

# After each backup, old backups are automatically removed
await backup_service.backup_database()

# Cleanup happens automatically, keeping only the 7 most recent
```

### Backup Retention Policy

Configure retention based on your requirements:

```python
# Keep last 30 days of backups
backup_service = BackupService(
    max_backups=30  # Adjust based on backup frequency
)
```

**Recommended Retention**:
- Daily backups: Keep 7-14 days
- Weekly backups: Keep 4-8 weeks
- Monthly backups: Keep 3-12 months

---

## Disaster Recovery

### Recovery Procedures

#### Scenario 1: Database Corruption

```python
from backend.storage.backup_service import BackupService
from loguru import logger

backup_service = BackupService()

# 1. Detect corruption
try:
    # Try to access database
    await backup_service.verify_database()
except DatabaseCorruptedError:
    logger.error("Database corrupted, initiating recovery")

    # 2. List available backups
    backups = await backup_service.list_backups()

    # 3. Restore from most recent good backup
    latest_valid = None
    for backup in backups:
        if await backup_service.verify_backup(backup.filepath):
            latest_valid = backup
            break

    if latest_valid:
        await backup_service.restore_database(latest_valid.filepath)
        logger.info("Database recovered from backup")
    else:
        logger.critical("No valid backups found")
```

#### Scenario 2: Accidental Data Deletion

```python
# If you accidentally delete important data

# 1. Stop all database operations immediately
# 2. Create emergency backup of current state
emergency_backup = await backup_service.backup_database(
    filename="emergency_before_restore"
)

# 3. Restore from backup before the deletion
target_backup = "path/to/backup_before_deletion.db.gz"
await backup_service.restore_database(target_backup)

# 4. Export the missing data
# 5. Restore current state and merge missing data
await backup_service.restore_database(emergency_backup)
```

#### Scenario 3: Migration Failure

```python
from backend.migrations.migration_manager import MigrationManager
from backend.storage.backup_service import BackupService

# Before running migrations, always backup
backup_service = BackupService()
pre_migration_backup = await backup_service.backup_database()

logger.info(f"Pre-migration backup: {pre_migration_backup}")

# Run migrations
try:
    manager = MigrationManager()
    await manager.migrate()
    logger.info("Migration successful")
except Exception as e:
    logger.error(f"Migration failed: {e}")

    # Rollback using backup
    logger.info("Rolling back to pre-migration state")
    await backup_service.restore_database(pre_migration_backup)
    raise
```

### Recovery Time Objective (RTO)

| Scenario | Estimated RTO |
|----------|---------------|
| Restore from local backup | 1-5 minutes |
| Restore + verify | 5-10 minutes |
| Restore + data export | 10-30 minutes |
| Full disaster recovery | 30-60 minutes |

### Recovery Point Objective (RPO)

| Backup Frequency | RPO |
|------------------|-----|
| Daily | Up to 24 hours |
| Hourly | Up to 1 hour |
| Real-time (WAL) | Seconds to minutes |

---

## Troubleshooting

### Common Issues

#### Issue: Backup File is Corrupted

**Symptoms**:
- `verify_backup()` returns False
- Restore fails with corruption error

**Solutions**:
```python
# Try the next most recent backup
backups = await backup_service.list_backups()

for backup in backups:
    if await backup_service.verify_backup(backup.filepath):
        logger.info(f"Found valid backup: {backup.filename}")
        await backup_service.restore_database(backup.filepath)
        break
```

#### Issue: Insufficient Disk Space

**Symptoms**:
- Backup fails with disk space error
- Very slow backup performance

**Solutions**:
```python
# 1. Check available space
import shutil
total, used, free = shutil.disk_usage("backend/backups/")
free_gb = free / (1024**3)

logger.info(f"Free space: {free_gb:.2f} GB")

# 2. Reduce backup retention if needed
if free_gb < 5:
    backup_service = BackupService(max_backups=3)  # Keep fewer backups

# 3. Use compression
backup_service = BackupService()
await backup_service.backup_database(compress=True)
```

#### Issue: Restore Fails with "Database is Locked"

**Symptoms**:
- Restore fails with database locked error
- Application is still running

**Solutions**:
```python
# 1. Stop all database operations
# 2. Close all database connections
await database_service.close()

# 3. Then restore
await backup_service.restore_database(backup_path)

# 4. Restart database connections
await database_service.initialize()
```

#### Issue: Backup Schedule Not Running

**Symptoms**:
- No new backups created
- Scheduler appears to start but no backups

**Solutions**:
```python
# Check scheduler status
from backend.storage.backup_scheduler import get_scheduler

scheduler = get_scheduler()

# Check if scheduler is running
if not scheduler.is_running:
    logger.warning("Scheduler is not running, starting...")
    await scheduler.start()

# Check next scheduled time
next_time = scheduler.get_next_backup_time()
logger.info(f"Next backup: {next_time}")

# Manually trigger a backup
await scheduler.run_once()
```

### Logging and Monitoring

All backup operations are logged via loguru:

```python
from loguru import logger

# Backup logs are written with these levels:
# - INFO: Successful operations
# - WARNING: Backup cleanup, compression info
# - ERROR: Backup failures, corruption detected
# - CRITICAL: Restore failures, data loss risk

# Monitor backup health
recent_backups = await backup_service.list_backups()
if len(recent_backups) == 0:
    logger.critical("No backups found!")
elif len(recent_backups) < 3:
    logger.warning("Less than 3 backups available")
else:
    logger.info(f"Healthy: {len(recent_backups)} backups available")
```

### Backup Health Checks

```python
async def check_backup_health():
    """Check backup system health"""
    from backend.storage.backup_service import BackupService
    from datetime import datetime, timedelta

    backup_service = BackupService()
    backups = await backup_service.list_backups()

    # Check 1: Have recent backups
    if not backups:
        return {"status": "error", "message": "No backups found"}

    # Check 2: Most recent backup age
    latest = backups[0]
    age = datetime.now() - latest.created_at
    if age > timedelta(days=2):
        return {"status": "warning", "message": f"Latest backup is {age.days} days old"}

    # Check 3: Backup integrity
    valid_backups = 0
    for backup in backups[:5]:  # Check last 5
        if await backup_service.verify_backup(backup.filepath):
            valid_backups += 1

    if valid_backups < 3:
        return {"status": "warning", "message": f"Only {valid_backups}/5 recent backups are valid"}

    # Check 4: Disk space
    stats = await backup_service.get_backup_statistics()
    if stats.total_size > 10 * 1024**3:  # 10 GB
        return {"status": "warning", "message": "Backup size exceeds 10 GB"}

    return {"status": "healthy", "message": "All checks passed"}

# Run health check
health = await check_backup_health()
logger.info(f"Backup health: {health}")
```

---

## Best Practices

### 1. Backup Frequency

- **Critical Trading Data**: Daily backups minimum
- **High-Frequency Trading**: Hourly backups during trading hours
- **Development/Staging**: Before schema changes or migrations

### 2. Backup Storage

- **Local Storage**: Fast access, primary backup location
- **External Drive**: Off-site backup for disaster recovery
- **Cloud Storage**: Optional additional layer (AWS S3, etc.)

### 3. Backup Testing

```python
# Regularly test restore procedure
async def test_backup_restore():
    """Test backup and restore on staging database"""
    from backend.storage.backup_service import BackupService
    import tempfile
    import shutil

    # Use test database
    test_db = "backend/data/eurabay_trading_test.db"
    backup_service = BackupService(
        database_path=test_db,
        backup_dir=tempfile.mkdtemp()
    )

    # Create test backup
    backup_path = await backup_service.backup_database()

    # Corrupt test database
    shutil.copy(test_db, test_db + ".original")
    with open(test_db, 'w') as f:
        f.write("corrupted data")

    # Restore from backup
    await backup_service.restore_database(backup_path)

    # Verify restore
    is_valid = await backup_service.verify_backup(backup_path)

    # Cleanup
    shutil.move(test_db + ".original", test_db)

    return is_valid
```

### 4. Documentation

- Document all backup and restore procedures
- Maintain runbook for disaster recovery scenarios
- Document custom backup schedules and retention policies

### 5. Monitoring

```python
# Add to application monitoring
async def monitor_backups():
    """Monitor backup system health"""
    health = await check_backup_health()

    if health["status"] == "error":
        # Send alert
        send_critical_alert(health["message"])
    elif health["status"] == "warning":
        # Send warning
        send_warning_alert(health["message"])
```

---

## Next Steps

- See [Database Schema](./database-schema.md) for complete schema documentation
- See [Data Dictionary](./data-dictionary.md) for detailed field descriptions
- See [Query Patterns](./query-patterns.md) for common query examples
