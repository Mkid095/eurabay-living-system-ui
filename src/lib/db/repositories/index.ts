/**
 * Database Repositories Index
 *
 * Central export point for all database repositories and the database client.
 * Import from this file for access to all database operations.
 *
 * @example
 * ```ts
 * import { db, userRepository, tradeRepository } from '@/lib/db/repositories';
 *
 * const user = await userRepository.getUserById('user-001');
 * const trades = await tradeRepository.getActiveTrades();
 * ```
 */

// Database client
export { db } from '../index';

// Repositories
export { userRepository, UserRepository } from './user.repository';
export { tradeRepository, TradeRepository } from './trade.repository';
export { evolutionRepository, EvolutionRepository } from './evolution.repository';
export { signalRepository, SignalRepository } from './signal.repository';
export { logRepository, LogRepository } from './log.repository';

// Re-export commonly used schema types for convenience
export type {
  User,
  NewUser,
  Trade,
  NewTrade,
  EvolutionGeneration,
  NewEvolutionGeneration,
  Feature,
  NewFeature,
  Mutation,
  NewMutation,
  Signal,
  NewSignal,
  SystemLog,
  NewSystemLog,
} from '../schema';
