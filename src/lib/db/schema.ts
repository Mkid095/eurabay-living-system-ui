import { sqliteTable, text, integer, real } from 'drizzle-orm/sqlite-core';

/**
 * Users table schema
 * Stores user account information with authentication data
 * Extended with Better Auth required fields (emailVerified, image)
 */
export const users = sqliteTable('users', {
  id: text('id').primaryKey(),
  email: text('email').notNull().unique(),
  passwordHash: text('passwordHash').notNull(),
  name: text('name').notNull(),
  role: text('role', { enum: ['admin', 'trader', 'viewer'] }).notNull().default('viewer'),
  emailVerified: integer('emailVerified', { mode: 'boolean' }).notNull().default(false),
  image: text('image'),
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

/**
 * Sessions table schema for Better Auth
 * Stores user session data for authentication
 */
export const sessions = sqliteTable('sessions', {
  id: text('id').primaryKey(),
  userId: text('user_id').notNull().references(() => users.id),
  token: text('token').notNull(),
  expiresAt: integer('expires_at', { mode: 'timestamp' }).notNull(),
  ipAddress: text('ip_address'),
  userAgent: text('user_agent'),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
});

/**
 * Type definitions for sessions table
 */
export type Session = typeof sessions.$inferSelect;
export type NewSession = typeof sessions.$inferInsert;

/**
 * Accounts table schema for Better Auth
 * Stores account information for OAuth providers and email/password auth
 */
export const accounts = sqliteTable('accounts', {
  id: text('id').primaryKey(),
  userId: text('user_id').notNull().references(() => users.id),
  accountId: text('account_id').notNull(),
  providerId: text('provider_id').notNull(),
  accessToken: text('access_token'),
  refreshToken: text('refresh_token'),
  accessTokenExpiresAt: integer('access_token_expires_at', { mode: 'timestamp' }),
  refreshTokenExpiresAt: integer('refresh_token_expires_at', { mode: 'timestamp' }),
  scope: text('scope'),
  idToken: text('id_token'),
  password: text('password'),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
});

/**
 * Type definitions for accounts table
 */
export type Account = typeof accounts.$inferSelect;
export type NewAccount = typeof accounts.$inferInsert;

/**
 * Features table schema
 * Stores evolved trading features and their performance metrics
 */
export const features = sqliteTable('features', {
  featureId: text('feature_id').primaryKey(),
  featureName: text('feature_name').notNull(),
  successRate: real('success_rate').notNull(),
  totalUses: integer('total_uses').notNull().default(0),
  wins: integer('wins').notNull().default(0),
  losses: integer('losses').notNull().default(0),
  avgPnl: real('avg_pnl').notNull(),
  createdAt: integer('created_at', { mode: 'timestamp' }).notNull(),
  updatedAt: integer('updated_at', { mode: 'timestamp' }).notNull(),
});

/**
 * Type definitions for features table
 */
export type Feature = typeof features.$inferSelect;
export type NewFeature = typeof features.$inferInsert;

/**
 * Mutations table schema
 * Tracks mutation history with evolution and feature relationships
 */
export const mutations = sqliteTable('mutations', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  mutationType: text('mutation_type').notNull(),
  generationId: integer('generation_id').notNull().references(() => evolutionGenerations.id),
  targetFeatureId: text('target_feature_id').notNull().references(() => features.featureId),
  success: integer('success', { mode: 'boolean' }).notNull(),
  fitnessImprovement: real('fitness_improvement').notNull(),
  timestamp: integer('timestamp', { mode: 'timestamp' }).notNull(),
});

/**
 * Type definitions for mutations table
 */
export type Mutation = typeof mutations.$inferSelect;
export type NewMutation = typeof mutations.$inferInsert;

/**
 * System logs table schema
 * Stores system events and diagnostic information
 */
export const systemLogs = sqliteTable('system_logs', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  timestamp: integer('timestamp', { mode: 'timestamp' }).notNull(),
  level: text('level', { enum: ['INFO', 'WARN', 'ERROR', 'DEBUG'] }).notNull(),
  component: text('component').notNull(),
  message: text('message').notNull(),
  details: text('details'), // JSON string
});

/**
 * Type definitions for system_logs table
 */
export type SystemLog = typeof systemLogs.$inferSelect;
export type NewSystemLog = typeof systemLogs.$inferInsert;

/**
 * Signals table schema
 * Stores trading signals generated by the evolution system
 */
export const signals = sqliteTable('signals', {
  signalId: text('signal_id').primaryKey(),
  symbol: text('symbol').notNull(),
  signalType: text('signal_type', { enum: ['STRONG_BUY', 'BUY', 'SELL', 'STRONG_SELL'] }).notNull(),
  confidence: real('confidence').notNull(),
  htfContext: text('htf_context'),
  featuresUsed: text('features_used'), // JSON string
  status: text('status', { enum: ['pending', 'approved', 'rejected', 'executed'] }).notNull().default('pending'),
  timestamp: integer('timestamp', { mode: 'timestamp' }).notNull(),
  evolutionGeneration: integer('evolution_generation'),
});

/**
 * Type definitions for signals table
 */
export type Signal = typeof signals.$inferSelect;
export type NewSignal = typeof signals.$inferInsert;

/**
 * Manual overrides table schema
 * Stores manual override actions for active trade management
 */
export const manualOverrides = sqliteTable('manual_overrides', {
  id: integer('id').primaryKey({ autoIncrement: true }),
  ticket: integer('ticket').notNull(),
  action: text('action', {
    enum: ['close_position', 'disable_trailing_stop', 'disable_breakeven', 'set_manual_stop_loss', 'set_manual_take_profit', 'pause_management', 'resume_management']
  }).notNull(),
  previousValue: real('previous_value'),
  newValue: real('new_value'),
  timestamp: integer('timestamp', { mode: 'timestamp' }).notNull(),
  user: text('user').notNull(),
  reason: text('reason').notNull(),
  confirmed: integer('confirmed', { mode: 'boolean' }).notNull().default(false),
});

/**
 * Type definitions for manual_overrides table
 */
export type ManualOverride = typeof manualOverrides.$inferSelect;
export type NewManualOverride = typeof manualOverrides.$inferInsert;
