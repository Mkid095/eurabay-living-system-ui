import { sqliteTable, text, integer } from 'drizzle-orm/sqlite-core';

/**
 * Users table schema
 * Stores user account information with authentication data
 */
export const users = sqliteTable('users', {
  id: text('id').primaryKey(),
  email: text('email').notNull().unique(),
  passwordHash: text('passwordHash').notNull(),
  name: text('name').notNull(),
  role: text('role', { enum: ['admin', 'trader', 'viewer'] }).notNull().default('viewer'),
  createdAt: integer('createdAt', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updatedAt', { mode: 'timestamp' }).notNull(),
});

/**
 * Type definitions for users table
 */
export type User = typeof users.$inferSelect;
export type NewUser = typeof users.$inferInsert;
