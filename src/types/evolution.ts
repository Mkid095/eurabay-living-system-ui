export interface EvolutionMetrics {
  currentGeneration: number;
  controllerDecision: 'STABLE' | 'EVOLVE_CONSERVATIVE' | 'EVOLVE_MODERATE' | 'EVOLVE_AGGRESSIVE';
  cyclesCompleted: number;
  systemVersion: string;
  birthTime: string;
  uptime: string;
}

export interface ControllerDecisionHistory {
  timestamp: string;
  decision: 'STABLE' | 'EVOLVE_CONSERVATIVE' | 'EVOLVE_MODERATE' | 'EVOLVE_AGGRESSIVE';
  performance: number;
  generation: number;
  fitness: number;
  reason?: string;
}

export interface FeatureSuccess {
  featureId: string;
  featureName: string;
  successRate: number;
  totalUses: number;
  wins: number;
  losses: number;
  avgPnL: number;
}

export interface WinRateBreakdown {
  symbol: string;
  winRate: number;
  totalTrades: number;
  wins: number;
  losses: number;
}

export interface FeatureDetail extends FeatureSuccess {
  featureType?: string;
  category?: string;
  trend?: 'improving' | 'declining' | 'stable';
  trendPercent?: number;
  winRatesBySymbol: WinRateBreakdown[];
  winRatesByTimeframe: Array<{
    timeframe: string;
    winRate: number;
    totalTrades: number;
    wins: number;
    losses: number;
  }>;
  createdAt: string;
  lastModified: string;
  parameters: Record<string, number | string | boolean>;
  recentTrades: EvolvedTrade[];
}

export interface MutationSuccess {
  mutationType: string;
  successRate: number;
  totalAttempts: number;
  successful: number;
  avgFitnessImprovement: number;
}

export interface GenerationHistory {
  generation: number;
  timestamp: string;
  fitness: number;
  avgPerformance: number;
}

export interface EvolutionLog {
  timestamp: string;
  type: 'MUTATION' | 'EVOLUTION_CYCLE' | 'FEATURE_SUCCESS' | 'FEATURE_FAILURE';
  generation: number;
  message: string;
  details?: Record<string, any>;
}

export interface EvolvedTrade {
  ticket: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  lots: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent?: number;
  stopLoss?: number;
  takeProfit?: number;
  entryTime: string;
  duration?: string;
  htfContext: string;
  ltfContext: string;
  featuresUsed: string[];
  featureSuccessRates?: Record<string, number>;
  confidence: number;
  confidenceBreakdown?: {
    technical: number;
    fundamental: number;
    sentiment: number;
  };
  generation?: number;
}

export interface ClosedTrade {
  ticket: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  lots: number;
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  pnlPercent: number;
  stopLoss?: number;
  takeProfit?: number;
  stopLossHit?: boolean;
  takeProfitHit?: boolean;
  entryTime: string;
  exitTime: string;
  duration: string;
  htfContext: string;
  ltfContext: string;
  featuresUsed: string[];
  featureSuccessRates?: Record<string, number>;
  confidence: number;
  confidenceBreakdown?: {
    technical: number;
    fundamental: number;
    sentiment: number;
  };
  generation?: number;
}

export type SignalType = 'STRONG_BUY' | 'BUY' | 'SELL' | 'STRONG_SELL';

export interface PendingSignal {
  id: string;
  symbol: string;
  signalType: SignalType;
  confidence: number;
  htfContext: string;
  featuresUsed: string[];
  timestamp: string;
}

/**
 * Execution Log Types
 */
export type ExecutionLogLevel = 'info' | 'warning' | 'error' | 'success';

export interface ExecutionLogEntry {
  id: string;
  timestamp: string;
  level: ExecutionLogLevel;
  message: string;
  tradeTicket?: string;
  details?: Record<string, unknown>;
}

/**
 * Execution log filters
 */
export interface ExecutionLogFilters {
  eventTypes?: ExecutionLogLevel[];
  symbol?: string;
  ticket?: string;
}
