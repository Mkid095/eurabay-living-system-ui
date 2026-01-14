# Database Schema - Users Table

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
