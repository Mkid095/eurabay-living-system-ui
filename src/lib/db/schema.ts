import { sqliteTable, text, integer, real } from 'drizzle-orm/sqlite-core';

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

/**
 * Trades table schema
 * Stores MT5 trading data with AI evolution tracking
 */
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

/**
 * Type definitions for trades table
 */
export type Trade = typeof trades.$inferSelect;
export type NewTrade = typeof trades.$inferInsert;

/**
 * Evolution generations table schema
 * Tracks evolution cycles and their performance
 */
export const evolutionGenerations = sqliteTable('evolution_generations', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  generationNumber: integer('generation_number').notNull().unique(),
  timestamp: integer('timestamp', { mode: 'timestamp' }).notNull(),
  fitness: real('fitness').notNull(),
  avgPerformance: real('avg_performance').notNull(),
  controllerDecision: text('controller_decision').notNull(),
  reason: text('reason').notNull(),
});

/**
 * Type definitions for evolution_generations table
 */
export type EvolutionGeneration = typeof evolutionGenerations.$inferSelect;
export type NewEvolutionGeneration = typeof evolutionGenerations.$inferInsert;
