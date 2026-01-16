/**
 * Zod Validation Schemas for WebSocket Events
 * Runtime validation for all WebSocket message types
 */

import { z } from 'zod';

/**
 * Base Enums
 */

// Trade Status Enum
export const TradeStatusEnum = z.enum([
  'pending',
  'open',
  'closed',
  'cancelled',
]);

// Evolution Event Type Enum
export const EvolutionEventTypeEnum = z.enum([
  'generation_started',
  'generation_completed',
  'aggressive_evolution',
  'conservative_evolution',
  'new_feature_discovered',
  'feature_validated',
  'feature_rejected',
]);

// Controller Decision Type Enum
export const ControllerDecisionTypeEnum = z.enum([
  'open_position',
  'close_position',
  'modify_position',
  'hold',
  'analyze',
]);

// Feature Mutation Type Enum
export const FeatureMutationTypeEnum = z.enum([
  'added',
  'modified',
  'removed',
  'weight_adjusted',
]);

// Market Trend Enum
export const MarketTrendEnum = z.enum([
  'bullish',
  'bearish',
  'neutral',
  'volatile',
]);

// System Health Status Enum
export const SystemHealthStatusEnum = z.enum([
  'healthy',
  'degraded',
  'unhealthy',
  'critical',
]);

// Order Side Enum
export const OrderSideEnum = z.enum([
  'buy',
  'sell',
]);

// Order Type Enum
export const OrderTypeEnum = z.enum([
  'market',
  'limit',
  'stop',
  'stop_limit',
]);

// Order Status Enum
export const OrderStatusEnum = z.enum([
  'pending',
  'filled',
  'partially_filled',
  'cancelled',
  'rejected',
  'expired',
]);

// MT5 Error Severity Enum
export const MT5ErrorSeverityEnum = z.enum([
  'warning',
  'error',
  'critical',
]);

/**
 * Base WebSocket Event Schema
 * Generic event wrapper with metadata
 */
export const WSEventSchema = z.object({
  event: z.string(),
  data: z.unknown(),
  timestamp: z.number(),
  correlationId: z.string().optional(),
});

/**
 * Trade Update Event Schema
 */
export const TradeUpdateEventSchema = z.object({
  tradeId: z.string(),
  symbol: z.string(),
  status: TradeStatusEnum,
  entryPrice: z.number(),
  currentPrice: z.number().optional(),
  exitPrice: z.number().optional(),
  quantity: z.number(),
  pnl: z.number().optional(),
  pnlPercentage: z.number().optional(),
  stopLoss: z.number().optional(),
  takeProfit: z.number().optional(),
  openTime: z.string(),
  closeTime: z.string().optional(),
  strategy: z.string().optional(),
});

/**
 * Evolution Event Schema
 */
export const EvolutionEventSchema = z.object({
  eventId: z.string(),
  eventType: EvolutionEventTypeEnum,
  generation: z.number(),
  timestamp: z.string(),
  details: z.string(),
  featureId: z.string().optional(),
  featureName: z.string().optional(),
  fitness: z.number().optional(),
});

/**
 * Generation Changed Event Schema
 */
export const GenerationChangedEventSchema = z.object({
  previousGeneration: z.number(),
  newGeneration: z.number(),
  timestamp: z.string(),
  bestFitness: z.number(),
  averageFitness: z.number(),
  populationSize: z.number(),
});

/**
 * Controller Decision Event Schema
 */
export const ControllerDecisionEventSchema = z.object({
  decisionId: z.string(),
  decisionType: ControllerDecisionTypeEnum,
  symbol: z.string(),
  reasoning: z.string(),
  confidence: z.number(),
  timestamp: z.string(),
  parameters: z.record(z.string(), z.unknown()).optional(),
});

/**
 * Feature Mutated Event Schema
 */
export const FeatureMutatedEventSchema = z.object({
  featureId: z.string(),
  featureName: z.string(),
  mutationType: FeatureMutationTypeEnum,
  previousValue: z.number().optional(),
  newValue: z.number(),
  weight: z.number().optional(),
  importance: z.number().optional(),
  timestamp: z.string(),
});

/**
 * Market Update Event Schema
 */
export const MarketUpdateEventSchema = z.object({
  symbol: z.string(),
  bid: z.number(),
  ask: z.number(),
  spread: z.number(),
  priceChange: z.number(),
  priceChangePercentage: z.number(),
  trend: MarketTrendEnum,
  volume: z.number().optional(),
  volatility: z.number().optional(),
  timestamp: z.string(),
});

/**
 * System Status Event Schema
 */
export const SystemStatusEventSchema = z.object({
  status: SystemHealthStatusEnum,
  cpuUsage: z.number(),
  memoryUsage: z.number(),
  uptime: z.number(),
  activeConnections: z.number(),
  timestamp: z.string(),
  message: z.string().optional(),
});

/**
 * Performance Update Event Schema
 */
export const PerformanceUpdateEventSchema = z.object({
  totalTrades: z.number(),
  winRate: z.number(),
  totalPnL: z.number(),
  totalPnLPercentage: z.number(),
  bestTrade: TradeUpdateEventSchema.optional(),
  worstTrade: TradeUpdateEventSchema.optional(),
  averageWin: z.number(),
  averageLoss: z.number(),
  profitFactor: z.number(),
  sharpeRatio: z.number().optional(),
  timestamp: z.string(),
});

/**
 * MT5 Connected Event Schema
 */
export const MT5ConnectedEventSchema = z.object({
  timestamp: z.string(),
  accountId: z.string(),
  server: z.string(),
  connectionType: z.string(),
});

/**
 * MT5 Disconnected Event Schema
 */
export const MT5DisconnectedEventSchema = z.object({
  timestamp: z.string(),
  reason: z.string().optional(),
  accountId: z.string().optional(),
});

/**
 * MT5 Order Opened Event Schema
 */
export const MT5OrderOpenedEventSchema = z.object({
  orderId: z.number(),
  symbol: z.string(),
  side: OrderSideEnum,
  type: OrderTypeEnum,
  lots: z.number(),
  price: z.number(),
  stopLoss: z.number().optional(),
  takeProfit: z.number().optional(),
  comment: z.string().optional(),
  timestamp: z.string(),
});

/**
 * MT5 Order Closed Event Schema
 */
export const MT5OrderClosedEventSchema = z.object({
  orderId: z.number(),
  symbol: z.string(),
  side: OrderSideEnum,
  lots: z.number(),
  entryPrice: z.number(),
  exitPrice: z.number(),
  profit: z.number(),
  commission: z.number(),
  swap: z.number(),
  netProfit: z.number(),
  closeTime: z.string(),
  reason: z.string().optional(),
});

/**
 * MT5 Position Modified Event Schema
 */
export const MT5PositionModifiedEventSchema = z.object({
  positionId: z.number(),
  symbol: z.string(),
  modificationType: z.enum(['stop_loss', 'take_profit', 'both']),
  previousStopLoss: z.number().optional(),
  previousTakeProfit: z.number().optional(),
  newStopLoss: z.number().optional(),
  newTakeProfit: z.number().optional(),
  timestamp: z.string(),
});

/**
 * MT5 Position Update Event Schema
 * Real-time P&L and price updates for open positions
 */
export const MT5PositionUpdateEventSchema = z.object({
  positionId: z.number(),
  symbol: z.string(),
  currentPrice: z.number(),
  profit: z.number(),
  profitPercentage: z.number().optional(),
  timestamp: z.string(),
});

/**
 * MT5 Position Closed Event Schema
 * Fired when a position is closed in MT5
 */
export const MT5PositionClosedEventSchema = z.object({
  positionId: z.number(),
  symbol: z.string(),
  lots: z.number(),
  entryPrice: z.number(),
  exitPrice: z.number(),
  profit: z.number(),
  commission: z.number(),
  swap: z.number(),
  closeTime: z.string(),
  reason: z.string().optional(),
});

/**
 * MT5 Error Event Schema
 */
export const MT5ErrorEventSchema = z.object({
  errorCode: z.number(),
  errorMessage: z.string(),
  severity: MT5ErrorSeverityEnum,
  timestamp: z.string(),
  context: z.object({
    symbol: z.string().optional(),
    orderId: z.number().optional(),
    operation: z.string().optional(),
  }).optional(),
});

/**
 * Event Type to Schema Mapping
 * Maps each event type to its corresponding Zod schema for validation
 */
export const EventSchemaMap = {
  // System events
  system_status: SystemStatusEventSchema,

  // Trading events
  trade_update: TradeUpdateEventSchema,
  new_signal: z.object({
    signalId: z.string(),
    symbol: z.string(),
    type: z.enum(['buy', 'sell']),
    entryPrice: z.number(),
    stopLoss: z.number().optional(),
    takeProfit: z.number().optional(),
    confidence: z.number(),
    reasoning: z.string(),
    timestamp: z.string(),
  }),

  // Evolution events
  evolution_event: EvolutionEventSchema,
  generation_changed: GenerationChangedEventSchema,
  controller_decision: ControllerDecisionEventSchema,
  feature_mutated: FeatureMutatedEventSchema,

  // Market events
  market_update: MarketUpdateEventSchema,

  // Performance events
  performance_update: PerformanceUpdateEventSchema,

  // MT5 events
  mt5_connected: MT5ConnectedEventSchema,
  mt5_disconnected: MT5DisconnectedEventSchema,
  mt5_order_opened: MT5OrderOpenedEventSchema,
  mt5_order_closed: MT5OrderClosedEventSchema,
  mt5_position_modified: MT5PositionModifiedEventSchema,
  mt5_position_update: MT5PositionUpdateEventSchema,
  mt5_position_closed: MT5PositionClosedEventSchema,
  mt5_error: MT5ErrorEventSchema,
} as const;

/**
 * Type inference for event data
 */
export type EventDataType = {
  system_status: z.infer<typeof SystemStatusEventSchema>;
  trade_update: z.infer<typeof TradeUpdateEventSchema>;
  new_signal: z.infer<typeof EventSchemaMap.new_signal>;
  evolution_event: z.infer<typeof EvolutionEventSchema>;
  generation_changed: z.infer<typeof GenerationChangedEventSchema>;
  controller_decision: z.infer<typeof ControllerDecisionEventSchema>;
  feature_mutated: z.infer<typeof FeatureMutatedEventSchema>;
  market_update: z.infer<typeof MarketUpdateEventSchema>;
  performance_update: z.infer<typeof PerformanceUpdateEventSchema>;
  mt5_connected: z.infer<typeof MT5ConnectedEventSchema>;
  mt5_disconnected: z.infer<typeof MT5DisconnectedEventSchema>;
  mt5_order_opened: z.infer<typeof MT5OrderOpenedEventSchema>;
  mt5_order_closed: z.infer<typeof MT5OrderClosedEventSchema>;
  mt5_position_modified: z.infer<typeof MT5PositionModifiedEventSchema>;
  mt5_position_update: z.infer<typeof MT5PositionUpdateEventSchema>;
  mt5_position_closed: z.infer<typeof MT5PositionClosedEventSchema>;
  mt5_error: z.infer<typeof MT5ErrorEventSchema>;
};
