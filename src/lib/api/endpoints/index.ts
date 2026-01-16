/**
 * API Endpoints Module Export
 *
 * Central export point for all API endpoint modules.
 * Provides organized access to all endpoint functions.
 */

// System endpoints
export { systemApi } from './system';
export type {
  SystemStatus,
  SystemHealth,
  SystemConfiguration,
} from '../types';

// Evolution endpoints
export { evolutionApi } from './evolution';
export type {
  EvolutionMetrics,
  GenerationHistory,
  FeatureSuccess,
  MutationSuccess,
  ControllerDecisionHistory,
  EvolutionLog,
  EvolutionParameters,
} from '../types';

// Trades and signals endpoints
export { tradesApi } from './trades';
export type {
  EvolvedTrade,
  ClosedTrade,
  PendingSignal,
  SignalActionResult,
  ExecutionLogEntry,
  TradeModificationRequest,
  TradeCloseRequest,
  TradeCloseResult,
} from '../types';

// Portfolio endpoints
export { portfolioApi } from './portfolio-endpoints';
export type {
  PortfolioMetrics,
  EquityHistory,
  PnLHistory,
  DateRange,
} from '../types';

// Performance endpoints
export { performanceApi } from './performance-endpoints';
export type {
  PerformanceMetrics,
  TradeStatistics,
} from '../types';

// Markets endpoints
export { marketsApi } from './markets-endpoints';
export type {
  MarketsOverviewResponse,
  MarketData,
  MarketTrendInfo,
  MarketOverviewData,
  MarketStatus,
  MarketTrend,
} from '../types';

// Configuration endpoints
export { configApi } from './config-endpoints';
export type {
  SystemConfiguration,
  EvolutionParameters,
} from '../types';

/**
 * Re-export all API objects for convenience
 */
export const apiEndpoints = {
  system: systemApi,
  evolution: evolutionApi,
  trades: tradesApi,
  portfolio: portfolioApi,
  performance: performanceApi,
  markets: marketsApi,
  config: configApi,
} as const;
