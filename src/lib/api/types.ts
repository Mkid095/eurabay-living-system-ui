/**
 * API Types
 *
 * Central type definitions for all API requests and responses.
 * This file consolidates type definitions used across the API layer.
 */

// ============================================================================
// SYSTEM STATUS & HEALTH
// ============================================================================

/**
 * System status enumeration
 */
export type SystemStatusType = 'running' | 'stopped' | 'error' | 'starting' | 'stopping';

/**
 * System health status enumeration
 */
export type HealthStatus = 'healthy' | 'degraded' | 'unhealthy';

/**
 * System status information
 */
export interface SystemStatus {
  /** Current system status */
  status: SystemStatusType;
  /** Current generation number */
  generation: number;
  /** System uptime in human-readable format */
  uptime: string;
  /** System start timestamp (ISO 8601) */
  startTime: string;
  /** Last update timestamp (ISO 8601) */
  lastUpdate: string;
  /** System version */
  version: string;
}

/**
 * Detailed system health information
 */
export interface SystemHealth {
  /** Overall health status */
  health: HealthStatus;
  /** CPU usage percentage (0-100) */
  cpuUsage: number;
  /** Memory usage percentage (0-100) */
  memoryUsage: number;
  /** Available memory in bytes */
  availableMemory: number;
  /** Total memory in bytes */
  totalMemory: number;
  /** API latency in milliseconds */
  latency: number;
  /** Number of active connections */
  activeConnections: number;
  /** System uptime in human-readable format */
  uptime: string;
  /** Last health check timestamp (ISO 8601) */
  lastCheck: string;
  /** Additional health details */
  details?: Record<string, string | number | boolean>;
}

// ============================================================================
// EVOLUTION TYPES
// ============================================================================

/**
 * Controller decision type
 */
export type ControllerDecision = 'STABLE' | 'EVOLVE_CONSERVATIVE' | 'EVOLVE_MODERATE' | 'EVOLVE_AGGRESSIVE';

/**
 * Evolution metrics from current generation
 */
export interface EvolutionMetrics {
  /** Current generation number */
  currentGeneration: number;
  /** Current controller decision */
  controllerDecision: ControllerDecision;
  /** Number of evolution cycles completed */
  cyclesCompleted: number;
  /** System version */
  systemVersion: string;
  /** System birth timestamp (ISO 8601) */
  birthTime: string;
  /** System uptime in human-readable format */
  uptime: string;
}

/**
 * Single generation history entry
 */
export interface GenerationHistory {
  /** Generation number */
  generation: number;
  /** Generation timestamp (ISO 8601) */
  timestamp: string;
  /** Generation fitness score */
  fitness: number;
  /** Average performance of this generation */
  avgPerformance: number;
}

/**
 * Feature success statistics
 */
export interface FeatureSuccess {
  /** Feature identifier */
  featureId: string;
  /** Feature display name */
  featureName: string;
  /** Success rate (0-1) */
  successRate: number;
  /** Total number of times feature was used */
  totalUses: number;
  /** Number of wins with this feature */
  wins: number;
  /** Number of losses with this feature */
  losses: number;
  /** Average P&L when using this feature */
  avgPnL: number;
}

/**
 * Mutation success statistics
 */
export interface MutationSuccess {
  /** Type of mutation */
  mutationType: string;
  /** Success rate (0-1) */
  successRate: number;
  /** Total mutation attempts */
  totalAttempts: number;
  /** Number of successful mutations */
  successful: number;
  /** Average fitness improvement from mutation */
  avgFitnessImprovement: number;
}

/**
 * Controller decision history entry
 */
export interface ControllerDecisionHistory {
  /** Decision timestamp (ISO 8601) */
  timestamp: string;
  /** Decision made */
  decision: ControllerDecision;
  /** Performance at time of decision */
  performance: number;
  /** Generation number */
  generation: number;
  /** Fitness score */
  fitness: number;
  /** Reason for decision (optional) */
  reason?: string;
}

/**
 * Evolution log entry
 */
export interface EvolutionLog {
  /** Log timestamp (ISO 8601) */
  timestamp: string;
  /** Event type */
  type: 'MUTATION' | 'EVOLUTION_CYCLE' | 'FEATURE_SUCCESS' | 'FEATURE_FAILURE';
  /** Generation number */
  generation: number;
  /** Log message */
  message: string;
  /** Additional event details */
  details?: Record<string, unknown>;
}

/**
 * Feature detail information
 */
export interface FeatureDetail extends FeatureSuccess {
  /** Feature type (optional) */
  featureType?: string;
  /** Feature category (optional) */
  category?: string;
  /** Performance trend */
  trend?: 'improving' | 'declining' | 'stable';
  /** Trend percentage */
  trendPercent?: number;
  /** Win rates broken down by symbol */
  winRatesBySymbol: Array<{
    symbol: string;
    winRate: number;
    totalTrades: number;
    wins: number;
    losses: number;
  }>;
  /** Win rates broken down by timeframe */
  winRatesByTimeframe: Array<{
    timeframe: string;
    winRate: number;
    totalTrades: number;
    wins: number;
    losses: number;
  }>;
  /** Feature creation timestamp (ISO 8601) */
  createdAt: string;
  /** Last modified timestamp (ISO 8601) */
  lastModified: string;
  /** Feature parameters */
  parameters: Record<string, string | number | boolean>;
  /** Recent trades using this feature */
  recentTrades: EvolvedTrade[];
}

// ============================================================================
// TRADE TYPES
// ============================================================================

/**
 * Trade direction
 */
export type TradeDirection = 'BUY' | 'SELL';

/**
 * Trade status
 */
export type TradeStatus = 'active' | 'closed' | 'pending';

/**
 * Signal type for trades
 */
export type SignalType = 'STRONG_BUY' | 'BUY' | 'SELL' | 'STRONG_SELL';

/**
 * Base trade information
 */
export interface BaseTrade {
  /** System ticket identifier */
  ticket: string;
  /** Trading symbol */
  symbol: string;
  /** Trade direction */
  direction: TradeDirection;
  /** Number of lots */
  lots: number;
  /** Entry price */
  entryPrice: number;
  /** Stop loss price (optional) */
  stopLoss?: number;
  /** Take profit price (optional) */
  takeProfit?: number;
  /** Entry timestamp (ISO 8601) */
  entryTime: string;
}

/**
 * Active evolved trade
 */
export interface EvolvedTrade extends BaseTrade {
  /** Current market price */
  currentPrice: number;
  /** Current profit/loss */
  pnl: number;
  /** P&L percentage (optional) */
  pnlPercent?: number;
  /** Trade duration in human-readable format (optional) */
  duration?: string;
  /** Higher timeframe context */
  htfContext: string;
  /** Lower timeframe context */
  ltfContext: string;
  /** Features used for this trade */
  featuresUsed: string[];
  /** Feature success rates (optional) */
  featureSuccessRates?: Record<string, number>;
  /** Trade confidence score (0-1) */
  confidence: number;
  /** Confidence breakdown (optional) */
  confidenceBreakdown?: {
    technical: number;
    fundamental: number;
    sentiment: number;
  };
  /** Evolution generation that created this trade */
  generation?: number;
  /** MT5 position ticket number (optional) */
  mt5Ticket?: number;
  /** MT5 position comment (includes evolution generation) */
  mt5Comment?: string;
}

/**
 * Closed trade information
 */
export interface ClosedTrade extends BaseTrade {
  /** Exit price */
  exitPrice: number;
  /** Final profit/loss */
  pnl: number;
  /** P&L percentage */
  pnlPercent: number;
  /** Whether stop loss was hit */
  stopLossHit?: boolean;
  /** Whether take profit was hit */
  takeProfitHit?: boolean;
  /** Exit timestamp (ISO 8601) */
  exitTime: string;
  /** Trade duration in human-readable format */
  duration: string;
  /** Higher timeframe context */
  htfContext: string;
  /** Lower timeframe context */
  ltfContext: string;
  /** Features used for this trade */
  featuresUsed: string[];
  /** Feature success rates (optional) */
  featureSuccessRates?: Record<string, number>;
  /** Trade confidence score (0-1) */
  confidence: number;
  /** Confidence breakdown (optional) */
  confidenceBreakdown?: {
    technical: number;
    fundamental: number;
    sentiment: number;
  };
  /** Evolution generation that created this trade */
  generation?: number;
}

/**
 * Pending trading signal
 */
export interface PendingSignal {
  /** Signal identifier */
  id: string;
  /** Trading symbol */
  symbol: string;
  /** Signal type */
  signalType: SignalType;
  /** Signal confidence score (0-1) */
  confidence: number;
  /** Higher timeframe context */
  htfContext: string;
  /** Features used for signal */
  featuresUsed: string[];
  /** Signal timestamp (ISO 8601) */
  timestamp: string;
  /** Evolution generation (optional) */
  evolutionGeneration?: number;
}

/**
 * Signal action result
 */
export interface SignalActionResult {
  /** Whether the action was successful */
  success: boolean;
  /** Message describing the result */
  message: string;
  /** Updated signal (if applicable) */
  signal?: PendingSignal;
}

// ============================================================================
// EXECUTION LOG TYPES
// ============================================================================

/**
 * Execution log level
 */
export type ExecutionLogLevel = 'info' | 'warning' | 'error' | 'success';

/**
 * Execution log entry
 */
export interface ExecutionLogEntry {
  /** Log entry identifier */
  id: string;
  /** Timestamp (ISO 8601) */
  timestamp: string;
  /** Log level */
  level: ExecutionLogLevel;
  /** Log message */
  message: string;
  /** Associated trade ticket (optional) */
  tradeTicket?: string;
  /** Additional details (optional) */
  details?: Record<string, unknown>;
}

// ============================================================================
// PORTFOLIO TYPES
// ============================================================================

/**
 * Portfolio metrics summary
 */
export interface PortfolioMetrics {
  /** Total portfolio value */
  totalValue: number;
  /** Total profit/loss amount */
  totalPnL: number;
  /** Total P&L percentage */
  totalPnLPercent: number;
  /** Number of active trades */
  activeTrades: number;
  /** Win rate percentage (0-100) */
  winRate: number;
}

/**
 * Equity history data point
 */
export interface EquityHistoryPoint {
  /** Date string (ISO 8601) */
  date: string;
  /** Equity value */
  equity: number;
  /** Profit/loss since start */
  pnl: number;
  /** Drawdown from peak (0-1) */
  drawdown: number;
  /** Whether this is a peak equity point */
  isPeak: boolean;
}

/**
 * Equity history response
 */
export interface EquityHistory {
  /** Starting equity value */
  startingEquity: number;
  /** Current equity value */
  currentEquity: number;
  /** Peak equity value */
  peakEquity: number;
  /** Maximum drawdown (0-1) */
  maxDrawdown: number;
  /** Total return amount */
  totalReturn: number;
  /** Total return percentage */
  totalReturnPercent: number;
  /** Array of history points */
  history: EquityHistoryPoint[];
}

/**
 * P&L history data point
 */
export interface PnLHistoryPoint {
  /** Date string (ISO 8601) */
  date: string;
  /** P&L amount for the period */
  pnl: number;
  /** Cumulative P&L */
  cumulativePnl: number;
  /** Number of trades in this period */
  tradesCount: number;
  /** Symbol (if filtered) */
  symbol?: string;
}

/**
 * P&L history response
 */
export interface PnLHistory {
  /** Total P&L amount */
  totalPnl: number;
  /** Total P&L percentage */
  totalPnlPercent: number;
  /** Number of winning periods */
  winningPeriods: number;
  /** Number of losing periods */
  losingPeriods: number;
  /** Array of history points */
  history: PnLHistoryPoint[];
}

// ============================================================================
// PERFORMANCE TYPES
// ============================================================================

/**
 * Date range filter type
 */
export type DateRange = 'today' | 'week' | 'month' | 'all';

/**
 * Performance metrics
 */
export interface PerformanceMetrics {
  /** Total return amount */
  totalReturn: number;
  /** Total return percentage */
  totalReturnPercent: number;
  /** Sharpe ratio */
  sharpeRatio: number;
  /** Maximum drawdown amount */
  maxDrawdown: number;
  /** Maximum drawdown percentage */
  maxDrawdownPercent: number;
  /** Win rate (0-1) */
  winRate: number;
  /** Win rate percentage (0-100) */
  winRatePercent: number;
  /** Total number of trades */
  totalTrades: number;
  /** Average trade duration in seconds */
  averageTradeDuration: number;
  /** Profit factor (wins/losses ratio) */
  profitFactor: number;
  /** Benchmark return amount (optional) */
  benchmarkReturn?: number;
  /** Benchmark return percentage (optional) */
  benchmarkReturnPercent?: number;
}

/**
 * Trade statistics
 */
export interface TradeStatistics {
  /** Total number of trades */
  totalTrades: number;
  /** Win rate percentage (0-100) */
  winRate: number;
  /** Total profit/loss amount */
  totalProfitLoss: number;
  /** Average winning trade amount */
  averageWin: number;
  /** Average losing trade amount */
  averageLoss: number;
  /** Profit factor */
  profitFactor: number;
  /** Largest winning trade amount */
  largestWinningTrade: number;
  /** Largest losing trade amount */
  largestLosingTrade: number;
  /** Average trade duration in human-readable format */
  averageTradeDuration: string;
  /** Best performing symbol */
  bestPerformingSymbol: string;
  /** Worst performing symbol */
  worstPerformingSymbol: string;
}

// ============================================================================
// MARKET TYPES
// ============================================================================

/**
 * Market status
 */
export type MarketStatus = 'open' | 'closed';

/**
 * Market trend
 */
export type MarketTrend = 'BULLISH' | 'BEARISH' | 'NEUTRAL';

/**
 * Market overview data
 */
export interface MarketOverviewData {
  /** Market symbol (e.g., "V10", "V25") */
  symbol: string;
  /** Display name */
  displayName: string;
  /** Current price */
  price: number;
  /** Absolute price change */
  priceChange: number;
  /** Percentage price change */
  priceChangePercentage: number;
  /** 24-hour high price */
  high24h: number;
  /** 24-hour low price */
  low24h: number;
  /** Market status */
  status: MarketStatus;
  /** Last update timestamp (ISO 8601) */
  timestamp: string;
}

/**
 * Markets overview response
 */
export interface MarketsOverviewResponse {
  /** Array of market data */
  markets: MarketOverviewData[];
  /** Response timestamp (ISO 8601) */
  timestamp: string;
}

/**
 * Market data for a single symbol
 */
export interface MarketData {
  /** Market symbol */
  symbol: string;
  /** Display name */
  displayName: string;
  /** Current bid price */
  bid: number;
  /** Current ask price */
  ask: number;
  /** Spread */
  spread: number;
  /** Current price */
  price: number;
  /** Absolute price change */
  priceChange: number;
  /** Percentage price change */
  priceChangePercentage: number;
  /** Market trend */
  trend: MarketTrend;
  /** Trend strength (optional) */
  trendStrength?: 'strong' | 'moderate' | 'weak';
  /** Volatility index (optional) */
  volatility?: number;
  /** Market status */
  status: MarketStatus;
  /** 24-hour high */
  high24h: number;
  /** 24-hour low */
  low24h: number;
  /** Daily open */
  open24h?: number;
  /** Last update timestamp (ISO 8601) */
  timestamp: string;
}

/**
 * Market trend information
 */
export interface MarketTrendInfo {
  /** Market symbol */
  symbol: string;
  /** Current trend */
  trend: MarketTrend;
  /** Trend strength */
  strength: 'strong' | 'moderate' | 'weak';
  /** Trend confidence (0-1) */
  confidence: number;
  /** Last update timestamp (ISO 8601) */
  timestamp: string;
}

// ============================================================================
// CONFIGURATION TYPES
// ============================================================================

/**
 * Evolution parameters
 */
export interface EvolutionParameters {
  /** Mutation rate (0-1) */
  mutationRate?: number;
  /** Crossover rate (0-1) */
  crossoverRate?: number;
  /** Population size */
  populationSize?: number;
  /** Elite count */
  eliteCount?: number;
  /** Selection strategy */
  selectionStrategy?: 'roulette' | 'tournament' | 'rank';
  /** Fitness target */
  fitnessTarget?: number;
}

/**
 * System configuration
 */
export interface SystemConfiguration {
  /** System is running in override mode */
  overrideMode: boolean;
  /** Evolution enabled */
  evolutionEnabled: boolean;
  /** Auto-trading enabled */
  autoTradingEnabled: boolean;
  /** Risk percentage per trade */
  riskPercent: number;
  /** Maximum concurrent trades */
  maxConcurrentTrades: number;
  /** Evolution parameters */
  evolution: EvolutionParameters;
  /** API endpoints */
  apiEndpoints: Record<string, string>;
  /** WebSocket URL */
  wsUrl: string;
  /** Additional settings */
  settings?: Record<string, string | number | boolean>;
}

// ============================================================================
// ERROR TYPES
// ============================================================================

/**
 * API error response structure
 */
export interface ErrorResponse {
  /** Error message */
  message: string;
  /** Error code (optional) */
  code?: string;
  /** HTTP status code (optional) */
  status?: number;
  /** Additional error details (optional) */
  details?: Record<string, unknown>;
  /** Request ID for tracking (optional) */
  requestId?: string;
  /** Timestamp (ISO 8601) */
  timestamp: string;
}

/**
 * Validation error details
 */
export interface ValidationErrorDetail {
  /** Field that failed validation */
  field: string;
  /** Validation error message */
  message: string;
  /** Current value that failed */
  value?: unknown;
  /** Expected type or format */
  expected?: string;
}

/**
 * Validation error response
 */
export interface ValidationErrorResponse extends ErrorResponse {
  /** Array of validation errors */
  validationErrors: ValidationErrorDetail[];
}

// ============================================================================
// REQUEST TYPES
// ============================================================================

/**
 * Signal approval request
 */
export interface SignalApprovalRequest {
  /** Signal ID */
  signalId: string;
  /** Action to take */
  action: 'approve' | 'reject';
  /** Optional notes */
  notes?: string;
}

/**
 * Trade modification request
 */
export interface TradeModificationRequest {
  /** Trade ticket */
  ticket: string;
  /** New stop loss (optional) */
  stopLoss?: number;
  /** New take profit (optional) */
  takeProfit?: number;
  /** New lots (optional) */
  lots?: number;
}

/**
 * Trade close request
 */
export interface TradeCloseRequest {
  /** Trade ticket */
  ticket: string;
  /** Lots to close (optional, defaults to all) */
  lots?: number;
}

/**
 * Trade close result
 */
export interface TradeCloseResult {
  /** Whether the close was successful */
  success: boolean;
  /** Closed trade information */
  trade?: ClosedTrade;
  /** Result message */
  message: string;
}

// ============================================================================
// RESPONSE WRAPPER TYPES
// ============================================================================

/**
 * Standard paginated response
 */
export interface PaginatedResponse<T> {
  /** Array of items */
  items: T[];
  /** Total number of items */
  total: number;
  /** Current page number */
  page: number;
  /** Number of items per page */
  pageSize: number;
  /** Whether there is a next page */
  hasNext: boolean;
  /** Whether there is a previous page */
  hasPrevious: boolean;
}

/**
 * Standard API response wrapper (used internally by API client)
 */
export interface ApiResponse<T> {
  /** Response data */
  data: T;
  /** HTTP status code */
  status: number;
  /** Whether response was successful */
  ok: boolean;
}
