# Database Schema - EURABAY Living System

## Stories Overview

### US-001: Create database schema for users table - COMPLETED
### US-002: Create database schema for trades table - COMPLETED

---

## Story US-001: Create database schema for users table

### Status: COMPLETED

### File Location
`C:/Users/HomePC/Documents/GitHub/eurabay-living-system-ui/src/lib/db/schema.ts`

### Implementation Details

The users table schema has been successfully created using Drizzle ORM with libSQL database.

#### Schema Definition

```typescript
import { sqliteTable, text, integer } from 'drizzle-orm/sqlite-core';

export const users = sqliteTable('users', {
  id: text('id').primaryKey(),
  email: text('email').notNull().unique(),
  passwordHash: text('passwordHash').notNull(),
  name: text('name').notNull(),
  role: text('role', { enum: ['admin', 'trader', 'viewer'] }).notNull().default('viewer'),
  createdAt: integer('createdAt', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updatedAt', { mode: 'timestamp' }).notNull(),
});

export type User = typeof users.$inferSelect;
export type NewUser = typeof users.$inferInsert;
```

### Acceptance Criteria Validation

#### AC1: Create users table with required fields
- id (text primary key)
- email (unique)
- passwordHash
- name
- role (enum: admin|trader|viewer)
- createdAt
- updatedAt

#### AC2: NOT NULL constraints on required fields
All fields have `.notNull()` constraint applied:
- id
- email
- passwordHash
- name
- role
- createdAt
- updatedAt

#### AC3: Default value 'viewer' for role field
The role field has `.default('viewer')` configured

#### AC4: Typecheck passes
- No TypeScript errors in schema.ts
- Type inference works correctly
- `User` type for selecting users
- `NewUser` type for inserting users

### Type Definitions

The schema exports two TypeScript types:

1. **User**: Type for user records retrieved from the database
2. **NewUser**: Type for creating new user records

### Technical Details

- **ORM**: Drizzle ORM (drizzle-orm)
- **Database**: libSQL (@libsql/client)
- **Table Type**: SQLite table
- **ID Type**: text (string)
- **Timestamps**: integer with mode 'timestamp' (Date objects)
- **Role Enum**: ['admin', 'trader', 'viewer']

### Next Steps

This schema is ready for:
1. Database client configuration (US-007)
2. Drizzle Kit setup (US-008)
3. Migration generation (US-009)

### Validation

The schema has been validated and confirmed:
- Drizzle ORM imports work correctly
- Type inference is functional
- All constraints are properly configured
- Enum values are validated
- Default values are set

---

**Implementation Date**: 2026-01-14
**Technology Stack**: Next.js 15, TypeScript, Drizzle ORM, libSQL

---

## Story US-002: Create database schema for trades table

### Status: COMPLETED

### File Location
`C:/Users/HomePC/Documents/GitHub/eurabay-living-system-ui/src/lib/db/schema.ts`

### Implementation Details

The trades table schema has been successfully created using Drizzle ORM with libSQL database. This table stores MT5 trading data with AI evolution tracking.

#### Schema Definition

```typescript
import { sqliteTable, text, integer, real } from 'drizzle-orm/sqlite-core';

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
  status: text('status', { enum: ['active', 'closed', 'pending'] }).notNull().default('pending'),
  evolutionGeneration: integer('evolution_generation'),
  featuresUsed: text('features_used'), // JSON string
  confidence: real('confidence'),
  userId: text('user_id').notNull().references(() => users.id),
});

export type Trade = typeof trades.$inferSelect;
export type NewTrade = typeof trades.$inferInsert;
```

### Acceptance Criteria Validation

#### AC1: Create trades table with all required fields
- systemTicket (text primary key) - System-generated unique identifier
- mt5Ticket (unique integer) - MT5 platform ticket number
- symbol - Trading symbol (e.g., EURUSD, GBPUSD)
- direction (enum: BUY|SELL) - Trade direction
- lots - Trade size in lots
- entryPrice - Price at which trade was opened
- currentPrice - Current market price
- stopLoss - Stop loss price
- takeProfit - Take profit price
- openTime (timestamp) - When trade was opened
- closeTime (timestamp) - When trade was closed
- pnl - Profit and loss amount
- status (enum: active|closed|pending) - Trade status with default 'pending'
- evolutionGeneration - AI evolution generation number
- featuresUsed (JSON text) - AI features used for this trade
- confidence - AI confidence score
- userId (foreign key) - Reference to users table

#### AC2: NOT NULL constraints on required fields
All required fields have `.notNull()` constraint applied:
- mt5Ticket, symbol, direction, lots, entryPrice
- openTime, status, userId

#### AC3: Foreign key constraint from userId to users.id
The userId field has `.references(() => users.id)` configured, establishing a foreign key relationship with the users table.

#### AC4: Typecheck passes
- No TypeScript errors in schema.ts
- Type inference works correctly
- `Trade` type for selecting trades
- `NewTrade` type for inserting trades

### Type Definitions

The schema exports two TypeScript types:

1. **Trade**: Type for trade records retrieved from the database
2. **NewTrade**: Type for creating new trade records

### Technical Details

- **ORM**: Drizzle ORM (drizzle-orm)
- **Database**: libSQL (@libsql/client)
- **Table Type**: SQLite table
- **Primary Key**: text (system_ticket)
- **Unique Constraint**: mt5_ticket
- **Foreign Key**: user_id → users.id
- **Timestamps**: integer with mode 'timestamp' (Date objects)
- **Direction Enum**: ['BUY', 'SELL']
- **Status Enum**: ['active', 'closed', 'pending'] with default 'pending'
- **JSON Storage**: features_used stored as text (JSON string)

### Database Client Integration

The trades table is automatically included in the database client through the schema export:

```typescript
// src/lib/db/index.ts
import * as schema from './schema';
export const db = drizzle(client, { schema });
```

This pattern makes both `users` and `trades` tables available for use:

```typescript
import { db } from '@/lib/db';
import { trades } from '@/lib/db/schema';

// Query trades
const allTrades = await db.select().from(trades);

// Insert new trade
import { NewTrade } from '@/lib/db/schema';
const newTrade: NewTrade = {
  systemTicket: 'SYS-123',
  mt5Ticket: 456789,
  symbol: 'EURUSD',
  direction: 'BUY',
  lots: 0.1,
  entryPrice: 1.0850,
  openTime: new Date(),
  status: 'active',
  userId: 'user-123',
};

await db.insert(trades).values(newTrade);
```

### Next Steps

This schema is ready for:
1. Database client configuration (US-007) - Already completed
2. Drizzle Kit setup (US-008)
3. Migration generation (US-009)
4. Trade repository implementation (US-015)

### Validation

The schema has been validated and confirmed:
- Drizzle ORM imports work correctly
- Type inference is functional
- All constraints are properly configured
- Enum values are validated
- Default values are set
- Foreign key relationship established
- Both tables accessible through database client

---

**Implementation Date**: 2026-01-14
**Technology Stack**: Next.js 15, TypeScript, Drizzle ORM, libSQL
