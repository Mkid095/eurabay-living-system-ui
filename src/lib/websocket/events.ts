/**
 * WebSocket Event Type Definitions
 * Defines all event types and data structures for WebSocket communication
 */

/**
 * WebSocket Event Types Enum
 * All possible event types that can be received from the server
 */
export enum WSEventType {
  // System events
  SYSTEM_STATUS = 'system_status',
  // Trading events
  TRADE_UPDATE = 'trade_update',
  NEW_SIGNAL = 'new_signal',
  // Evolution events
  EVOLUTION_EVENT = 'evolution_event',
  GENERATION_CHANGED = 'generation_changed',
  CONTROLLER_DECISION = 'controller_decision',
  FEATURE_MUTATED = 'feature_mutated',
  // Market events
  MARKET_UPDATE = 'market_update',
  // Performance events
  PERFORMANCE_UPDATE = 'performance_update',
  // MT5 events
  MT5_CONNECTED = 'mt5_connected',
  MT5_DISCONNECTED = 'mt5_disconnected',
  MT5_ORDER_OPENED = 'mt5_order_opened',
  MT5_ORDER_CLOSED = 'mt5_order_closed',
  MT5_POSITION_MODIFIED = 'mt5_position_modified',
  MT5_ERROR = 'mt5_error',
}

/**
 * Base WebSocket Event Interface
 * Generic event wrapper with metadata
 */
export interface WSEvent<T = unknown> {
  event: WSEventType;
  data: T;
  timestamp: number;
  correlationId?: string;
}

/**
 * Trade Status Enum
 */
export enum TradeStatus {
  PENDING = 'pending',
  OPEN = 'open',
  CLOSED = 'closed',
  CANCELLED = 'cancelled',
}

/**
 * Trade Update Event Data
 */
export interface TradeUpdateEvent {
  tradeId: string;
  symbol: string;
  status: TradeStatus;
  entryPrice: number;
  currentPrice?: number;
  exitPrice?: number;
  quantity: number;
  pnl?: number;
  pnlPercentage?: number;
  stopLoss?: number;
  takeProfit?: number;
  openTime: string;
  closeTime?: string;
  strategy?: string;
}

/**
 * Evolution Event Type Enum
 */
export enum EvolutionEventType {
  GENERATION_STARTED = 'generation_started',
  GENERATION_COMPLETED = 'generation_completed',
  AGGRESSIVE_EVOLUTION = 'aggressive_evolution',
  CONSERVATIVE_EVOLUTION = 'conservative_evolution',
  NEW_FEATURE_DISCOVERED = 'new_feature_discovered',
  FEATURE_VALIDATED = 'feature_validated',
  FEATURE_REJECTED = 'feature_rejected',
}

/**
 * Evolution Event Data
 */
export interface EvolutionEvent {
  eventId: string;
  eventType: EvolutionEventType;
  generation: number;
  timestamp: string;
  details: string;
  featureId?: string;
  featureName?: string;
  fitness?: number;
}

/**
 * Generation Changed Event Data
 */
export interface GenerationChangedEvent {
  previousGeneration: number;
  newGeneration: number;
  timestamp: string;
  bestFitness: number;
  averageFitness: number;
  populationSize: number;
}

/**
 * Controller Decision Type Enum
 */
export enum ControllerDecisionType {
  OPEN_POSITION = 'open_position',
  CLOSE_POSITION = 'close_position',
  MODIFY_POSITION = 'modify_position',
  HOLD = 'hold',
  ANALYZE = 'analyze',
}

/**
 * Controller Decision Event Data
 */
export interface ControllerDecisionEvent {
  decisionId: string;
  decisionType: ControllerDecisionType;
  symbol: string;
  reasoning: string;
  confidence: number;
  timestamp: string;
  parameters?: Record<string, unknown>;
}

/**
 * Feature Mutation Type Enum
 */
export enum FeatureMutationType {
  ADDED = 'added',
  MODIFIED = 'modified',
  REMOVED = 'removed',
  WEIGHT_ADJUSTED = 'weight_adjusted',
}

/**
 * Feature Mutated Event Data
 */
export interface FeatureMutatedEvent {
  featureId: string;
  featureName: string;
  mutationType: FeatureMutationType;
  previousValue?: number;
  newValue: number;
  weight?: number;
  importance?: number;
  timestamp: string;
}

/**
 * Market Trend Enum
 */
export enum MarketTrend {
  BULLISH = 'bullish',
  BEARISH = 'bearish',
  NEUTRAL = 'neutral',
  VOLATILE = 'volatile',
}

/**
 * Market Update Event Data
 */
export interface MarketUpdateEvent {
  symbol: string;
  bid: number;
  ask: number;
  spread: number;
  priceChange: number;
  priceChangePercentage: number;
  trend: MarketTrend;
  volume?: number;
  volatility?: number;
  timestamp: string;
}

/**
 * System Health Status Enum
 */
export enum SystemHealthStatus {
  HEALTHY = 'healthy',
  DEGRADED = 'degraded',
  UNHEALTHY = 'unhealthy',
  CRITICAL = 'critical',
}

/**
 * System Status Event Data
 */
export interface SystemStatusEvent {
  status: SystemHealthStatus;
  cpuUsage: number;
  memoryUsage: number;
  uptime: number;
  activeConnections: number;
  timestamp: string;
  message?: string;
}

/**
 * Performance Update Event Data
 */
export interface PerformanceUpdateEvent {
  totalTrades: number;
  winRate: number;
  totalPnL: number;
  totalPnLPercentage: number;
  bestTrade?: TradeUpdateEvent;
  worstTrade?: TradeUpdateEvent;
  averageWin: number;
  averageLoss: number;
  profitFactor: number;
  sharpeRatio?: number;
  timestamp: string;
}

/**
 * MT5 Connection Status
 */
export interface MT5ConnectedEvent {
  timestamp: string;
  accountId: string;
  server: string;
  connectionType: string;
}

/**
 * MT5 Disconnected Event
 */
export interface MT5DisconnectedEvent {
  timestamp: string;
  reason?: string;
  accountId?: string;
}

/**
 * Order Side Enum
 */
export enum OrderSide {
  BUY = 'buy',
  SELL = 'sell',
}

/**
 * Order Type Enum
 */
export enum OrderType {
  MARKET = 'market',
  LIMIT = 'limit',
  STOP = 'stop',
  STOP_LIMIT = 'stop_limit',
}

/**
 * Order Status Enum
 */
export enum OrderStatus {
  PENDING = 'pending',
  FILLED = 'filled',
  PARTIALLY_FILLED = 'partially_filled',
  CANCELLED = 'cancelled',
  REJECTED = 'rejected',
  EXPIRED = 'expired',
}

/**
 * MT5 Order Opened Event Data
 */
export interface MT5OrderOpenedEvent {
  orderId: number;
  symbol: string;
  side: OrderSide;
  type: OrderType;
  lots: number;
  price: number;
  stopLoss?: number;
  takeProfit?: number;
  comment?: string;
  timestamp: string;
}

/**
 * MT5 Order Closed Event Data
 */
export interface MT5OrderClosedEvent {
  orderId: number;
  symbol: string;
  side: OrderSide;
  lots: number;
  entryPrice: number;
  exitPrice: number;
  profit: number;
  commission: number;
  swap: number;
  netProfit: number;
  closeTime: string;
  reason?: string;
}

/**
 * MT5 Position Modified Event Data
 */
export interface MT5PositionModifiedEvent {
  positionId: number;
  symbol: string;
  modificationType: 'stop_loss' | 'take_profit' | 'both';
  previousStopLoss?: number;
  previousTakeProfit?: number;
  newStopLoss?: number;
  newTakeProfit?: number;
  timestamp: string;
}

/**
 * MT5 Error Severity Enum
 */
export enum MT5ErrorSeverity {
  WARNING = 'warning',
  ERROR = 'error',
  CRITICAL = 'critical',
}

/**
 * MT5 Error Event Data
 */
export interface MT5ErrorEvent {
  errorCode: number;
  errorMessage: string;
  severity: MT5ErrorSeverity;
  timestamp: string;
  context?: {
    symbol?: string;
    orderId?: number;
    operation?: string;
  };
}

/**
 * Type guards for event data validation
 */
export const isTradeUpdateEvent = (data: unknown): data is TradeUpdateEvent => {
  const d = data as TradeUpdateEvent;
  return (
    typeof d === 'object' &&
    d !== null &&
    typeof d.tradeId === 'string' &&
    typeof d.symbol === 'string' &&
    typeof d.status === 'string' &&
    typeof d.entryPrice === 'number'
  );
};

export const isEvolutionEvent = (data: unknown): data is EvolutionEvent => {
  const d = data as EvolutionEvent;
  return (
    typeof d === 'object' &&
    d !== null &&
    typeof d.eventId === 'string' &&
    typeof d.eventType === 'string' &&
    typeof d.generation === 'number' &&
    typeof d.timestamp === 'string'
  );
};

export const isMarketUpdateEvent = (data: unknown): data is MarketUpdateEvent => {
  const d = data as MarketUpdateEvent;
  return (
    typeof d === 'object' &&
    d !== null &&
    typeof d.symbol === 'string' &&
    typeof d.bid === 'number' &&
    typeof d.ask === 'number' &&
    typeof d.priceChange === 'number'
  );
};

export const isSystemStatusEvent = (data: unknown): data is SystemStatusEvent => {
  const d = data as SystemStatusEvent;
  return (
    typeof d === 'object' &&
    d !== null &&
    typeof d.status === 'string' &&
    typeof d.cpuUsage === 'number' &&
    typeof d.memoryUsage === 'number' &&
    typeof d.uptime === 'number'
  );
};

export const isMT5ErrorEvent = (data: unknown): data is MT5ErrorEvent => {
  const d = data as MT5ErrorEvent;
  return (
    typeof d === 'object' &&
    d !== null &&
    typeof d.errorCode === 'number' &&
    typeof d.errorMessage === 'string' &&
    typeof d.severity === 'string' &&
    typeof d.timestamp === 'string'
  );
};
