/**
 * API Validation Schemas
 *
 * Zod schemas for runtime validation of all API requests and responses.
 * These schemas ensure type safety between frontend and backend by validating
 * API responses match expected TypeScript types.
 */

import { z } from 'zod';

// ============================================================================
// PRIMITIVE SCHEMAS
// ============================================================================

/**
 * Common string validation patterns
 */
const emailSchema = z.string().email('Invalid email format');
const uuidSchema = z.string().uuid('Invalid UUID format');
const isoDateTimeSchema = z.string().datetime('Invalid ISO 8601 datetime format');
const nonEmptyStringSchema = z.string().min(1, 'String cannot be empty');

// ============================================================================
// SYSTEM STATUS & HEALTH SCHEMAS
// ============================================================================

/**
 * System status enumeration schema
 */
export const SystemStatusTypeSchema = z.enum([
  'running',
  'stopped',
  'error',
  'starting',
  'stopping',
], {
  errorMap: () => ({ message: 'Invalid system status' }),
});

/**
 * Health status enumeration schema
 */
export const HealthStatusSchema = z.enum(['healthy', 'degraded', 'unhealthy'], {
  errorMap: () => ({ message: 'Invalid health status' }),
});

/**
 * System status schema
 */
export const SystemStatusSchema = z.object({
  status: SystemStatusTypeSchema,
  generation: z.number().int().nonnegative(),
  uptime: z.string(),
  startTime: isoDateTimeSchema,
  lastUpdate: isoDateTimeSchema,
  version: z.string(),
});

/**
 * System health schema
 */
export const SystemHealthSchema = z.object({
  health: HealthStatusSchema,
  cpuUsage: z.number().min(0).max(100),
  memoryUsage: z.number().min(0).max(100),
  availableMemory: z.number().nonnegative(),
  totalMemory: z.number().positive(),
  latency: z.number().nonnegative(),
  activeConnections: z.number().int().nonnegative(),
  uptime: z.string(),
  lastCheck: isoDateTimeSchema,
  details: z.record(z.union([z.string(), z.number(), z.boolean()])).optional(),
});

// ============================================================================
// EVOLUTION SCHEMAS
// ============================================================================

/**
 * Controller decision schema
 */
export const ControllerDecisionSchema = z.enum([
  'STABLE',
  'EVOLVE_CONSERVATIVE',
  'EVOLVE_MODERATE',
  'EVOLVE_AGGRESSIVE',
], {
  errorMap: () => ({ message: 'Invalid controller decision' }),
});

/**
 * Evolution metrics schema
 */
export const EvolutionMetricsSchema = z.object({
  currentGeneration: z.number().int().positive(),
  controllerDecision: ControllerDecisionSchema,
  cyclesCompleted: z.number().int().nonnegative(),
  systemVersion: z.string(),
  birthTime: isoDateTimeSchema,
  uptime: z.string(),
});

/**
 * Generation history entry schema
 */
export const GenerationHistorySchema = z.object({
  generation: z.number().int().positive(),
  timestamp: isoDateTimeSchema,
  fitness: z.number(),
  avgPerformance: z.number(),
});

/**
 * Feature success schema
 */
export const FeatureSuccessSchema = z.object({
  featureId: z.string().min(1),
  featureName: z.string().min(1),
  successRate: z.number().min(0).max(1),
  totalUses: z.number().int().nonnegative(),
  wins: z.number().int().nonnegative(),
  losses: z.number().int().nonnegative(),
  avgPnL: z.number(),
});

/**
 * Mutation success schema
 */
export const MutationSuccessSchema = z.object({
  mutationType: z.string().min(1),
  successRate: z.number().min(0).max(1),
  totalAttempts: z.number().int().nonnegative(),
  successful: z.number().int().nonnegative(),
  avgFitnessImprovement: z.number(),
});

/**
 * Controller decision history schema
 */
export const ControllerDecisionHistorySchema = z.object({
  timestamp: isoDateTimeSchema,
  decision: ControllerDecisionSchema,
  performance: z.number(),
  generation: z.number().int().positive(),
  fitness: z.number(),
  reason: z.string().optional(),
});

/**
 * Evolution log entry schema
 */
export const EvolutionLogSchema = z.object({
  timestamp: isoDateTimeSchema,
  type: z.enum(['MUTATION', 'EVOLUTION_CYCLE', 'FEATURE_SUCCESS', 'FEATURE_FAILURE']),
  generation: z.number().int().positive(),
  message: z.string(),
  details: z.record(z.unknown()).optional(),
});

/**
 * Win rate breakdown schema (used in FeatureDetail)
 */
const winRateBreakdownSchema = z.object({
  symbol: z.string(),
  winRate: z.number().min(0).max(1),
  totalTrades: z.number().int().nonnegative(),
  wins: z.number().int().nonnegative(),
  losses: z.number().int().nonnegative(),
});

/**
 * Confidence breakdown schema
 */
const confidenceBreakdownSchema = z.object({
  technical: z.number().min(0).max(1),
  fundamental: z.number().min(0).max(1),
  sentiment: z.number().min(0).max(1),
});

/**
 * Evolved trade schema (used in FeatureDetail)
 */
const EvolvedTradeSchema = z.object({
  ticket: z.string().min(1),
  symbol: z.string(),
  direction: z.enum(['BUY', 'SELL']),
  lots: z.number().positive(),
  entryPrice: z.number().positive(),
  currentPrice: z.number().positive(),
  pnl: z.number(),
  pnlPercent: z.number().optional(),
  duration: z.string().optional(),
  htfContext: z.string(),
  ltfContext: z.string(),
  featuresUsed: z.array(z.string()),
  featureSuccessRates: z.record(z.number()).optional(),
  confidence: z.number().min(0).max(1),
  confidenceBreakdown: confidenceBreakdownSchema.optional(),
  generation: z.number().int().positive().optional(),
});

/**
 * Feature detail schema
 */
export const FeatureDetailSchema = FeatureSuccessSchema.extend({
  featureType: z.string().optional(),
  category: z.string().optional(),
  trend: z.enum(['improving', 'declining', 'stable']).optional(),
  trendPercent: z.number().optional(),
  winRatesBySymbol: z.array(winRateBreakdownSchema),
  winRatesByTimeframe: z.array(winRateBreakdownSchema),
  createdAt: isoDateTimeSchema,
  lastModified: isoDateTimeSchema,
  parameters: z.record(z.union([z.string(), z.number(), z.boolean()])),
  recentTrades: z.array(EvolvedTradeSchema),
});

// ============================================================================
// TRADE SCHEMAS
// ============================================================================

/**
 * Trade direction schema
 */
export const TradeDirectionSchema = z.enum(['BUY', 'SELL'], {
  errorMap: () => ({ message: 'Invalid trade direction' }),
});

/**
 * Trade status schema
 */
export const TradeStatusSchema = z.enum(['active', 'closed', 'pending'], {
  errorMap: () => ({ message: 'Invalid trade status' }),
});

/**
 * Signal type schema
 */
export const SignalTypeSchema = z.enum(['STRONG_BUY', 'BUY', 'SELL', 'STRONG_SELL'], {
  errorMap: () => ({ message: 'Invalid signal type' }),
});

/**
 * Base trade schema (shared fields)
 */
const BaseTradeSchema = z.object({
  ticket: z.string().min(1),
  symbol: z.string().min(1),
  direction: TradeDirectionSchema,
  lots: z.number().positive(),
  entryPrice: z.number().positive(),
  stopLoss: z.number().positive().optional(),
  takeProfit: z.number().positive().optional(),
  entryTime: isoDateTimeSchema,
});

/**
 * Evolved trade schema (active trades)
 */
export const EvolvedTradeSchemaFull = BaseTradeSchema.extend({
  currentPrice: z.number().positive(),
  pnl: z.number(),
  pnlPercent: z.number().optional(),
  duration: z.string().optional(),
  htfContext: z.string(),
  ltfContext: z.string(),
  featuresUsed: z.array(z.string()),
  featureSuccessRates: z.record(z.number()).optional(),
  confidence: z.number().min(0).max(1),
  confidenceBreakdown: confidenceBreakdownSchema.optional(),
  generation: z.number().int().positive().optional(),
});

/**
 * Closed trade schema
 */
export const ClosedTradeSchema = BaseTradeSchema.extend({
  exitPrice: z.number().positive(),
  pnl: z.number(),
  pnlPercent: z.number(),
  stopLossHit: z.boolean().optional(),
  takeProfitHit: z.boolean().optional(),
  exitTime: isoDateTimeSchema,
  duration: z.string(),
  htfContext: z.string(),
  ltfContext: z.string(),
  featuresUsed: z.array(z.string()),
  featureSuccessRates: z.record(z.number()).optional(),
  confidence: z.number().min(0).max(1),
  confidenceBreakdown: confidenceBreakdownSchema.optional(),
  generation: z.number().int().positive().optional(),
});

/**
 * Pending signal schema
 */
export const PendingSignalSchema = z.object({
  id: z.string().min(1),
  symbol: z.string().min(1),
  signalType: SignalTypeSchema,
  confidence: z.number().min(0).max(1),
  htfContext: z.string(),
  featuresUsed: z.array(z.string()),
  timestamp: isoDateTimeSchema,
  evolutionGeneration: z.number().int().positive().optional(),
});

/**
 * Signal action result schema
 */
export const SignalActionResultSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  signal: PendingSignalSchema.optional(),
});

// ============================================================================
// EXECUTION LOG SCHEMAS
// ============================================================================

/**
 * Execution log level schema
 */
export const ExecutionLogLevelSchema = z.enum(['info', 'warning', 'error', 'success'], {
  errorMap: () => ({ message: 'Invalid log level' }),
});

/**
 * Execution log entry schema
 */
export const ExecutionLogEntrySchema = z.object({
  id: z.string().min(1),
  timestamp: isoDateTimeSchema,
  level: ExecutionLogLevelSchema,
  message: z.string(),
  tradeTicket: z.string().optional(),
  details: z.record(z.unknown()).optional(),
});

// ============================================================================
// PORTFOLIO SCHEMAS
// ============================================================================

/**
 * Portfolio metrics schema
 */
export const PortfolioMetricsSchema = z.object({
  totalValue: z.number(),
  totalPnL: z.number(),
  totalPnLPercent: z.number(),
  activeTrades: z.number().int().nonnegative(),
  winRate: z.number().min(0).max(1),
});

/**
 * Equity history point schema
 */
export const EquityHistoryPointSchema = z.object({
  date: isoDateTimeSchema,
  equity: z.number(),
  pnl: z.number(),
  drawdown: z.number().min(0).max(1),
  isPeak: z.boolean(),
});

/**
 * Equity history schema
 */
export const EquityHistorySchema = z.object({
  startingEquity: z.number(),
  currentEquity: z.number(),
  peakEquity: z.number(),
  maxDrawdown: z.number().min(0).max(1),
  totalReturn: z.number(),
  totalReturnPercent: z.number(),
  history: z.array(EquityHistoryPointSchema),
});

/**
 * P&L history point schema
 */
export const PnLHistoryPointSchema = z.object({
  date: isoDateTimeSchema,
  pnl: z.number(),
  cumulativePnl: z.number(),
  tradesCount: z.number().int().nonnegative(),
  symbol: z.string().optional(),
});

/**
 * P&L history schema
 */
export const PnLHistorySchema = z.object({
  totalPnl: z.number(),
  totalPnlPercent: z.number(),
  winningPeriods: z.number().int().nonnegative(),
  losingPeriods: z.number().int().nonnegative(),
  history: z.array(PnLHistoryPointSchema),
});

// ============================================================================
// PERFORMANCE SCHEMAS
// ============================================================================

/**
 * Date range schema
 */
export const DateRangeSchema = z.enum(['today', 'week', 'month', 'all'], {
  errorMap: () => ({ message: 'Invalid date range' }),
});

/**
 * Performance metrics schema
 */
export const PerformanceMetricsSchema = z.object({
  totalReturn: z.number(),
  totalReturnPercent: z.number(),
  sharpeRatio: z.number(),
  maxDrawdown: z.number(),
  maxDrawdownPercent: z.number(),
  winRate: z.number().min(0).max(1),
  winRatePercent: z.number().min(0).max(100),
  totalTrades: z.number().int().nonnegative(),
  averageTradeDuration: z.number().nonnegative(),
  profitFactor: z.number().nonnegative(),
  benchmarkReturn: z.number().optional(),
  benchmarkReturnPercent: z.number().optional(),
});

/**
 * Trade statistics schema
 */
export const TradeStatisticsSchema = z.object({
  totalTrades: z.number().int().nonnegative(),
  winRate: z.number().min(0).max(100),
  totalProfitLoss: z.number(),
  averageWin: z.number(),
  averageLoss: z.number(),
  profitFactor: z.number().nonnegative(),
  largestWinningTrade: z.number(),
  largestLosingTrade: z.number(),
  averageTradeDuration: z.string(),
  bestPerformingSymbol: z.string(),
  worstPerformingSymbol: z.string(),
});

// ============================================================================
// MARKET SCHEMAS
// ============================================================================

/**
 * Market status schema
 */
export const MarketStatusSchema = z.enum(['open', 'closed'], {
  errorMap: () => ({ message: 'Invalid market status' }),
});

/**
 * Market trend schema
 */
export const MarketTrendSchema = z.enum(['BULLISH', 'BEARISH', 'NEUTRAL'], {
  errorMap: () => ({ message: 'Invalid market trend' }),
});

/**
 * Market trend strength schema
 */
export const MarketTrendStrengthSchema = z.enum(['strong', 'moderate', 'weak'], {
  errorMap: () => ({ message: 'Invalid trend strength' }),
});

/**
 * Market overview data schema
 */
export const MarketOverviewDataSchema = z.object({
  symbol: z.string().min(1),
  displayName: z.string(),
  price: z.number().positive(),
  priceChange: z.number(),
  priceChangePercentage: z.number(),
  high24h: z.number().nonnegative(),
  low24h: z.number().nonnegative(),
  status: MarketStatusSchema,
  timestamp: isoDateTimeSchema,
});

/**
 * Markets overview response schema
 */
export const MarketsOverviewResponseSchema = z.object({
  markets: z.array(MarketOverviewDataSchema),
  timestamp: isoDateTimeSchema,
});

/**
 * Market data schema
 */
export const MarketDataSchema = z.object({
  symbol: z.string().min(1),
  displayName: z.string(),
  bid: z.number().positive(),
  ask: z.number().positive(),
  spread: z.number().nonnegative(),
  price: z.number().positive(),
  priceChange: z.number(),
  priceChangePercentage: z.number(),
  trend: MarketTrendSchema,
  trendStrength: MarketTrendStrengthSchema.optional(),
  volatility: z.number().nonnegative().optional(),
  status: MarketStatusSchema,
  high24h: z.number().nonnegative(),
  low24h: z.number().nonnegative(),
  open24h: z.number().nonnegative().optional(),
  timestamp: isoDateTimeSchema,
});

/**
 * Market trend info schema
 */
export const MarketTrendInfoSchema = z.object({
  symbol: z.string().min(1),
  trend: MarketTrendSchema,
  strength: MarketTrendStrengthSchema,
  confidence: z.number().min(0).max(1),
  timestamp: isoDateTimeSchema,
});

// ============================================================================
// CONFIGURATION SCHEMAS
// ============================================================================

/**
 * Selection strategy schema
 */
export const SelectionStrategySchema = z.enum(['roulette', 'tournament', 'rank'], {
  errorMap: () => ({ message: 'Invalid selection strategy' }),
});

/**
 * Evolution parameters schema
 */
export const EvolutionParametersSchema = z.object({
  mutationRate: z.number().min(0).max(1).optional(),
  crossoverRate: z.number().min(0).max(1).optional(),
  populationSize: z.number().int().positive().optional(),
  eliteCount: z.number().int().nonnegative().optional(),
  selectionStrategy: SelectionStrategySchema.optional(),
  fitnessTarget: z.number().optional(),
});

/**
 * System configuration schema
 */
export const SystemConfigurationSchema = z.object({
  overrideMode: z.boolean(),
  evolutionEnabled: z.boolean(),
  autoTradingEnabled: z.boolean(),
  riskPercent: z.number().min(0).max(100),
  maxConcurrentTrades: z.number().int().positive(),
  evolution: EvolutionParametersSchema,
  apiEndpoints: z.record(z.string()),
  wsUrl: z.string().url(),
  settings: z.record(z.union([z.string(), z.number(), z.boolean()])).optional(),
});

// ============================================================================
// ERROR SCHEMAS
// ============================================================================

/**
 * Validation error detail schema
 */
export const ValidationErrorDetailSchema = z.object({
  field: z.string(),
  message: z.string(),
  value: z.unknown().optional(),
  expected: z.string().optional(),
});

/**
 * Error response schema
 */
export const ErrorResponseSchema = z.object({
  message: z.string(),
  code: z.string().optional(),
  status: z.number().int().optional(),
  details: z.record(z.unknown()).optional(),
  requestId: z.string().optional(),
  timestamp: isoDateTimeSchema,
});

/**
 * Validation error response schema
 */
export const ValidationErrorResponseSchema = ErrorResponseSchema.extend({
  validationErrors: z.array(ValidationErrorDetailSchema),
});

// ============================================================================
// REQUEST SCHEMAS
// ============================================================================

/**
 * Signal approval request schema
 */
export const SignalApprovalRequestSchema = z.object({
  signalId: z.string().min(1),
  action: z.enum(['approve', 'reject']),
  notes: z.string().optional(),
});

/**
 * Trade modification request schema
 */
export const TradeModificationRequestSchema = z.object({
  ticket: z.string().min(1),
  stopLoss: z.number().positive().optional(),
  takeProfit: z.number().positive().optional(),
  lots: z.number().positive().optional(),
});

/**
 * Trade close request schema
 */
export const TradeCloseRequestSchema = z.object({
  ticket: z.string().min(1),
  lots: z.number().positive().optional(),
});

/**
 * Trade close result schema
 */
export const TradeCloseResultSchema = z.object({
  success: z.boolean(),
  message: z.string(),
  trade: ClosedTradeSchema.optional(),
});

// ============================================================================
// RESPONSE WRAPPER SCHEMAS
// ============================================================================

/**
 * Generic paginated response schema
 */
export function PaginatedResponseSchema<T extends z.ZodType>(itemSchema: T) {
  return z.object({
    items: z.array(itemSchema),
    total: z.number().int().nonnegative(),
    page: z.number().int().positive(),
    pageSize: z.number().int().positive(),
    hasNext: z.boolean(),
    hasPrevious: z.boolean(),
  });
}

/**
 * Generic API response schema
 */
export function ApiResponseSchema<T extends z.ZodType>(dataSchema: T) {
  return z.object({
    data: dataSchema,
    status: z.number().int(),
    ok: z.boolean(),
  });
}

// ============================================================================
// EXPORT ALL SCHEMAS
// ============================================================================

/**
 * Map of all API response schemas for easy access
 */
export const ApiSchemas = {
  // System
  SystemStatus: SystemStatusSchema,
  SystemHealth: SystemHealthSchema,

  // Evolution
  EvolutionMetrics: EvolutionMetricsSchema,
  GenerationHistory: GenerationHistorySchema,
  FeatureSuccess: FeatureSuccessSchema,
  MutationSuccess: MutationSuccessSchema,
  ControllerDecisionHistory: ControllerDecisionHistorySchema,
  EvolutionLog: EvolutionLogSchema,
  FeatureDetail: FeatureDetailSchema,

  // Trades
  EvolvedTrade: EvolvedTradeSchemaFull,
  ClosedTrade: ClosedTradeSchema,
  PendingSignal: PendingSignalSchema,
  SignalActionResult: SignalActionResultSchema,

  // Execution
  ExecutionLogEntry: ExecutionLogEntrySchema,

  // Portfolio
  PortfolioMetrics: PortfolioMetricsSchema,
  EquityHistory: EquityHistorySchema,
  PnLHistory: PnLHistorySchema,

  // Performance
  PerformanceMetrics: PerformanceMetricsSchema,
  TradeStatistics: TradeStatisticsSchema,

  // Markets
  MarketOverviewData: MarketOverviewDataSchema,
  MarketsOverviewResponse: MarketsOverviewResponseSchema,
  MarketData: MarketDataSchema,
  MarketTrendInfo: MarketTrendInfoSchema,

  // Configuration
  EvolutionParameters: EvolutionParametersSchema,
  SystemConfiguration: SystemConfigurationSchema,

  // Errors
  ErrorResponse: ErrorResponseSchema,
  ValidationErrorResponse: ValidationErrorResponseSchema,
  ValidationErrorDetail: ValidationErrorDetailSchema,

  // Requests
  SignalApprovalRequest: SignalApprovalRequestSchema,
  TradeModificationRequest: TradeModificationRequestSchema,
  TradeCloseRequest: TradeCloseRequestSchema,
  TradeCloseResult: TradeCloseResultSchema,
} as const;

// Export type inference helpers
export type SystemStatusInput = z.infer<typeof SystemStatusSchema>;
export type SystemHealthInput = z.infer<typeof SystemHealthSchema>;
export type EvolutionMetricsInput = z.infer<typeof EvolutionMetricsSchema>;
export type GenerationHistoryInput = z.infer<typeof GenerationHistorySchema>;
export type FeatureSuccessInput = z.infer<typeof FeatureSuccessSchema>;
export type MutationSuccessInput = z.infer<typeof MutationSuccessSchema>;
export type PendingSignalInput = z.infer<typeof PendingSignalSchema>;
export type PortfolioMetricsInput = z.infer<typeof PortfolioMetricsSchema>;
export type PerformanceMetricsInput = z.infer<typeof PerformanceMetricsSchema>;
export type MarketDataInput = z.infer<typeof MarketDataSchema>;
export type ErrorResponseInput = z.infer<typeof ErrorResponseSchema>;
