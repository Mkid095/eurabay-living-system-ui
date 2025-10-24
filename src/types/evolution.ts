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
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  stopLoss?: number;
  takeProfit?: number;
  entryTime: string;
  htfContext: string;
  ltfContext: string;
  featuresUsed: string[];
  confidence: number;
}
