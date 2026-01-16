# Database Migration Guide

This document describes how to run database migrations for the EURABAY Living System v5.0.

## Prerequisites

- Node.js installed
- Dependencies installed (`npm install`)
- Database configured (see `.env.example`)

## Migration Files

Migrations are stored in the `drizzle/` directory:
- `0001_initial_schema.sql` - Initial schema with all tables
- `0001.json` - Migration metadata

## Running Migrations

### Development (Local SQLite)

For local development, the database uses a local SQLite file at `.local/db.sqlite`.

1. **Generate a new migration** (after schema changes):
   ```bash
   npm run db:generate
   ```

2. **Push schema changes directly** (for rapid development):
   ```bash
   npm run db:push
   ```

3. **Run migrations**:
   ```bash
   npm run db:migrate
   ```

### Production (Turso/libSQL)

For production, the system uses Turso (libSQL) as the database backend.

1. **Set environment variables** in `.env`:
   ```
   TURSO_DATABASE_URL=libsql://your-database-url.turso.io
   TURSO_AUTH_TOKEN=your-auth-token
   ```

2. **Run migrations**:
   ```bash
   npm run db:migrate
   ```

## Database Schema

The initial migration (0001) creates the following tables:

| Table | Description |
|-------|-------------|
| `users` | User accounts with authentication data |
| `sessions` | User sessions for Better Auth |
| `accounts` | OAuth and email/password accounts |
| `trades` | MT5 trading data with AI evolution tracking |
| `evolution_generations` | Evolution cycle tracking |
| `features` | Trading features and performance metrics |
| `mutations` | Mutation history |
| `system_logs` | System events and diagnostic information |
| `signals` | Trading signals from evolution system |

## Foreign Key Relationships

- `sessions.user_id` → `users.id`
- `accounts.user_id` → `users.id`
- `trades.user_id` → `users.id`
- `mutations.generation_id` → `evolution_generations.id`
- `mutations.target_feature_id` → `features.feature_id`

## Verification

To verify the migration was successful:

```bash
# Open Drizzle Studio to inspect the database
npm run db:studio
```

Or use the libsql client directly:

```javascript
const { createClient } = require('@libsql/client');
const client = createClient({ url: 'file:.local/db.sqlite' });
const result = await client.execute("SELECT name FROM sqlite_master WHERE type='table'");
console.log(result.rows);
```

## Testing

The migration has been tested with:
- All 10 tables created successfully
- Foreign key constraints verified
- Index creation verified
- Data insert/read operations verified

## Rollback

To rollback a migration:

1. Manually revert the schema changes
2. Delete the migration file from `drizzle/` directory
3. Or use `DROP TABLE` statements for manual rollback

## Notes

- Migrations use `CREATE TABLE IF NOT EXISTS` for idempotency
- Indexes use `CREATE INDEX IF NOT EXISTS` for idempotency
- Foreign keys are defined as table constraints
- Timestamps are stored as integers (Unix milliseconds)
- Enum values are stored as text with application-level validation
