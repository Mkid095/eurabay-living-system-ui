# PRD: Database Integration (Drizzle ORM + libSQL)

## Overview

The EURABAY Living System uses Drizzle ORM with libSQL for persistent data storage. This PRD documents the database schema, migrations, and integration required for the system to function.

## Goals

- Design complete database schema for all system data
- Implement Drizzle ORM configuration
- Create database migrations
- Set up seed data for development
- Implement database queries for all features
- Handle connection pooling and scaling
- Implement data caching strategies

## Current State

**Libraries Installed:**
- `@libsql/client` - libSQL database client
- `drizzle-kit` - Drizzle ORM toolkit
- `drizzle-orm` - Drizzle ORM

**Problem:**
- No database schema exists
- No migrations created
- No database connection code
- No ORM integration implemented

## User Stories

### US-001: Configure Drizzle ORM

**Description:** As a developer, I need to set up Drizzle ORM with libSQL.

**Acceptance Criteria:**
- [ ] Create `src/lib/db/schema.ts` with Drizzle schema
- [ ] Create `src/lib/db/index.ts` with database client
- [ ] Configure environment variables for database connection
- [ ] Set up local libSQL instance for development
- [ ] Configure production libSQL connection
- [ ] Add Drizzle Kit configuration
- [ ] Create migration scripts
- [ ] Typecheck passes

**Priority:** 1

**Technical Implementation:**

```typescript
// src/lib/db/schema.ts
import { sqliteTable, text, integer, real } from 'drizzle-orm/sqlite-core';

export const users = sqliteTable('users', {
  id: text('id').primaryKey(),
  email: text('email').notNull().unique(),
  passwordHash: text('password_hash').notNull(),
  name: text('name').notNull(),
  role: text('role', { enum: ['admin', 'trader', 'viewer'] }).notNull().default('viewer'),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
});

export const trades = sqliteTable('trades', {
  systemTicket: text('system_ticket').primaryKey(),
  mt5Ticket: integer('mt5_ticket').unique().notNull(),
  symbol: text('symbol').notNull(),
  direction: text('direction', { enum: ['BUY', 'SELL'] }).notNull(),
  lots: real('lots').notNull(),
  entryPrice: real('entry_price').notNull(),
  currentPrice: real('current_price'),
  stopLoss: real('stop_loss'),
  takeProfit: real('take_profit'),
  openTime: integer('open_time', { mode: 'timestamp' }).notNull(),
  closeTime: integer('close_time', { mode: 'timestamp' }),
  pnl: real('pnl'),
  status: text('status', { enum: ['active', 'closed', 'pending'] }).notNull(),
  evolutionGeneration: integer('evolution_generation'),
  featuresUsed: text('features_used'), // JSON array
  confidence: real('confidence'),
  userId: text('user_id').references(() => users.id),
});

export const evolutionGenerations = sqliteTable('evolution_generations', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  generationNumber: integer('generation_number').notNull().unique(),
  timestamp: integer('timestamp', { mode: 'timestamp' }).notNull(),
  fitness: real('fitness').notNull(),
  avgPerformance: real('avg_performance').notNull(),
  controllerDecision: text('controller_decision').notNull(),
  reason: text('reason'),
});

export const features = sqliteTable('features', {
  featureId: text('feature_id').primaryKey(),
  featureName: text('feature_name').notNull(),
  successRate: real('success_rate').notNull(),
  totalUses: integer('total_uses').notNull(),
  wins: integer('wins').notNull(),
  losses: integer('losses').notNull(),
  avgPnl: real('avg_pnl'),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
});

export const mutations = sqliteTable('mutations', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  mutationType: text('mutation_type').notNull(),
  generationId: integer('generation_id').references(() => evolutionGenerations.id),
  targetFeatureId: text('target_feature_id').references(() => features.featureId),
  success: integer('success', { enum: [0, 1] }).notNull(),
  fitnessImprovement: real('fitness_improvement'),
  timestamp: integer('timestamp', { mode: 'timestamp' }).notNull(),
});

export const systemLogs = sqliteTable('system_logs', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  timestamp: integer('timestamp', { mode: 'timestamp' }).notNull(),
  level: text('level', { enum: ['INFO', 'WARN', 'ERROR', 'DEBUG'] }).notNull(),
  component: text('component').notNull(),
  message: text('message').notNull(),
  details: text('details'), // JSON object
});

export const signals = sqliteTable('signals', {
  signalId: text('signal_id').primaryKey(),
  symbol: text('symbol').notNull(),
  signalType: text('signal_type', { enum: ['STRONG_BUY', 'BUY', 'SELL', 'STRONG_SELL'] }).notNull(),
  confidence: real('confidence').notNull(),
  htfContext: text('htf_context').notNull(),
  featuresUsed: text('features_used'), // JSON array
  status: text('status', { enum: ['pending', 'approved', 'rejected', 'executed'] }).notNull(),
  timestamp: integer('timestamp', { mode: 'timestamp' }).notNull(),
  evolutionGeneration: integer('evolution_generation').notNull(),
});
```

### US-002: Create Initial Migration

**Description:** As a developer, I need to create the initial database migration.

**Acceptance Criteria:**
- [ ] Generate initial migration from schema
- [ ] Test migration on local database
- [ ] Verify all tables created correctly
- [ ] Verify all indexes created correctly
- [ ] Verify all foreign keys work correctly
- [ ] Add migration rollback
- [ ] Document migration process
- [ ] Typecheck passes

**Priority:** 1

### US-003: Implement Database Connection Pool

**Description:** As a system, I need to handle multiple database connections efficiently.

**Acceptance Criteria:**
- [ ] Create connection pool configuration
- [ ] Set maximum concurrent connections
- [ ] Implement connection timeout
- [ ] Handle connection errors gracefully
- [ ] Log connection pool metrics
- [ ] Support development single connection
- [ ] Support production connection pool
- [ ] Typecheck passes

**Priority:** 2

### US-004: Create Seed Data

**Description:** As a developer, I need seed data for development and testing.

**Acceptance Criteria:**
- [ ] Create admin user seed
- [ ] Create demo trader user
- [ ] Create sample trade history (50 trades)
- [ ] Create sample evolution generations (10 generations)
- [ ] Create sample features (20 features)
- [ ] Create sample mutations (100 mutations)
- [ ] Create seed script
- [ ] Document seed data structure
- [ ] Typecheck passes

**Priority:** 2

### US-005: Implement Repository Pattern

**Description:** As a developer, I need a clean way to interact with the database.

**Acceptance Criteria:**
- [ ] Create `src/lib/db/repositories/user.repository.ts`
- [ ] Create `src/lib/db/repositories/trade.repository.ts`
- [ ] Create `src/lib/db/repositories/evolution.repository.ts`
- [ ] Create `src/lib/db/repositories/feature.repository.ts`
- [ ] Implement CRUD operations for each entity
- [ ] Add query builders for complex queries
- [ ] Add transaction support
- [ ] Typecheck passes

**Priority:** 3

**Technical Implementation:**

```typescript
// src/lib/db/repositories/trade.repository.ts
import { db } from '../index';
import { trades } from '../schema';
import { eq, and, gte, lte, desc } from 'drizzle-orm';

export class TradeRepository {
  async createTrade(data: typeof trades.$inferInsert) {
    const [trade] = await db.insert(trades).values(data).returning();
    return trade;
  }

  async getTradeBySystemTicket(ticket: string) {
    const [trade] = await db.select().from(trades).where(eq(trades.systemTicket, ticket));
    return trade;
  }

  async getActiveTrades() {
    return await db.select().from(trades).where(eq(trades.status, 'active'));
  }

  async getRecentTrades(limit = 20) {
    return await db.select()
      .from(trades)
      .where(eq(trades.status, 'closed'))
      .orderBy(desc(trades.closeTime))
      .limit(limit);
  }

  async updateTrade(ticket: string, data: Partial<typeof trades.$inferInsert>) {
    const [trade] = await db.update(trades)
      .set(data)
      .where(eq(trades.systemTicket, ticket))
      .returning();
    return trade;
  }

  async getTradesByDateRange(startDate: Date, endDate: Date) {
    return await db.select()
      .from(trades)
      .where(
        and(
          gte(trades.openTime, startDate),
          lte(trades.openTime, endDate)
        )
      );
  }
}

export const tradeRepository = new TradeRepository();
```

### US-006: Implement Data Caching Layer

**Description:** As a system, I need to cache frequently accessed data.

**Acceptance Criteria:**
- [ ] Create `src/lib/db/cache.ts` with caching utilities
- [ ] Cache user sessions (5 minute TTL)
- [ ] Cache system configuration (10 minute TTL)
- [ ] Cache active trades (30 second TTL)
- [ ] Cache evolution metrics (1 minute TTL)
- [ ] Invalidate cache on data changes
- [ ] Implement cache warming
- [ ] Add cache statistics
- [ ] Typecheck passes

**Priority:** 4

## Database Schema

### Tables Required:

1. **users** - User accounts and authentication
2. **trades** - All trades with MT5 mapping
3. **evolution_generations** - Evolution generation tracking
4. **features** - Evolved features and performance
5. **mutations** - Mutation history
6. **system_logs** - System log entries
7. **signals** - Trading signals
8. **sessions** - User sessions (from Better Auth)

### Relationships:
- users → trades (1:many)
- trades → features (many:many via featuresUsed)
- evolution_generations → mutations (1:many)
- evolution_generations → features (1:many)

## Technical Considerations

### Database Choice
- **Development**: Local SQLite file (via libSQL)
- **Production**: libSQL cloud database
- **ORM**: Drizzle ORM
- **Migrations**: Drizzle Kit

### Performance Requirements
- Query response time < 100ms
- Support 100+ concurrent connections
- Handle 10,000+ trade records
- Sub-millisecond cache lookups

### Backup Strategy
- Daily automatic backups
- Point-in-time recovery
- Backup retention: 30 days
- Geographic redundancy

### Scaling Strategy
- Read replicas for analytics queries
- Connection pooling for high concurrency
- Query optimization with indexes
- Archive old trade data

## Success Metrics

- Database queries < 100ms (p95)
- Cache hit rate > 80%
- Zero data loss
- Migration success rate = 100%
- Backup success rate = 100%

## Implementation Order

1. US-001: Configure Drizzle ORM
2. US-002: Create Initial Migration
3. US-004: Create Seed Data
4. US-005: Implement Repository Pattern
5. US-003: Implement Database Connection Pool
6. US-006: Implement Data Caching Layer

## Related PRDs

- PRD: Backend API Integration (database queries)
- PRD: Authentication & User Management (user tables)
- PRD: Trading System Features (trade tables)
- PRD: Evolution System Features (evolution tables)
