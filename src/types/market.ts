/**
 * Market Types
 *
 * Type definitions for market data structures including
 * Deriv.com volatility indices (V10, V25, V50, V75, V100).
 */

/**
 * Market status enumeration
 */
export type MarketStatus = 'open' | 'closed';

/**
 * Market trend enumeration
 */
export type MarketTrend = 'BULLISH' | 'BEARISH' | 'NEUTRAL';

/**
 * Market overview data structure
 * Represents a single market in the overview
 */
export interface MarketOverviewData {
  /** Market symbol (e.g., "V10", "V25", "V50", "V75", "V100") */
  symbol: string;
  /** Display name for the market */
  displayName: string;
  /** Current market price */
  price: number;
  /** Absolute price change (positive or negative) */
  priceChange: number;
  /** Percentage price change (positive or negative) */
  priceChangePercentage: number;
  /** 24-hour high price */
  high24h: number;
  /** 24-hour low price */
  low24h: number;
  /** Current market status */
  status: MarketStatus;
  /** Last update timestamp (ISO 8601 string) */
  timestamp: string;
}

/**
 * Markets overview API response
 */
export interface MarketsOverviewResponse {
  /** Array of market data */
  markets: MarketOverviewData[];
  /** Response timestamp */
  timestamp: string;
}

/**
 * Market update event from WebSocket
 * Real-time price updates for individual markets
 */
export interface MarketUpdateEvent {
  /** Market symbol */
  symbol: string;
  /** Current bid price */
  bid: number;
  /** Current ask price */
  ask: number;
  /** Current spread */
  spread: number;
  /** Absolute price change */
  priceChange: number;
  /** Percentage price change */
  priceChangePercentage: number;
  /** Current market trend */
  trend: 'bullish' | 'bearish' | 'neutral' | 'volatile';
  /** Trading volume (optional) */
  volume?: number;
  /** Volatility index value (optional) */
  volatility?: number;
  /** Update timestamp (ISO 8601 string) */
  timestamp: string;
}

/**
 * Flash animation state for price updates
 */
export type FlashState = 'up' | 'down' | null;

/**
 * Market card props for UI components
 */
export interface MarketCardProps {
  /** Market symbol */
  symbol: string;
  /** Display name */
  displayName: string;
  /** Current price */
  price: number;
  /** Price change percentage */
  priceChangePercentage: number;
  /** Market status */
  status: MarketStatus;
  /** Flash animation state */
  flashState: FlashState;
  /** Last update timestamp */
  lastUpdate: Date;
}

/**
 * Volatility index symbols supported by Deriv.com
 */
export const VOLATILITY_INDICES = ['V10', 'V25', 'V50', 'V75', 'V100'] as const;
export type VolatilityIndex = typeof VOLATILITY_INDICES[number];

/**
 * Market detail data structure
 * Detailed information for a single market
 */
export interface MarketDetailData {
  /** Market symbol (e.g., "V10", "V25") */
  symbol: string;
  /** Display name for the market */
  displayName: string;
  /** Current market price */
  price: number;
  /** Absolute price change (positive or negative) */
  priceChange: number;
  /** Percentage price change (positive or negative) */
  priceChangePercentage: number;
  /** 24-hour open price */
  open24h: number;
  /** 24-hour high price */
  high24h: number;
  /** 24-hour low price */
  low24h: number;
  /** 24-hour close price (previous close) */
  close24h: number;
  /** Current market trend */
  trend: MarketTrend;
  /** Market spread (ask - bid) */
  spread: number;
  /** Volatility index value */
  volatilityIndex: number;
  /** Recent price updates (last 10) */
  recentUpdates: PriceUpdate[];
  /** Market status */
  status: MarketStatus;
  /** Last update timestamp (ISO 8601 string) */
  timestamp: string;
}

/**
 * Price update entry
 */
export interface PriceUpdate {
  /** Price value */
  price: number;
  /** Update timestamp (ISO 8601 string) */
  timestamp: string;
  /** Price change from previous update */
  change: number;
}

/**
 * Market detail API response
 */
export interface MarketDetailResponse {
  /** Market detail data */
  market: MarketDetailData;
  /** Response timestamp */
  timestamp: string;
}

/**
 * Market trend strength enumeration
 */
export type TrendStrength = 'strong' | 'moderate' | 'weak';

/**
 * Market trend data structure
 */
export interface MarketTrendData {
  /** Market symbol */
  symbol: string;
  /** Current trend direction */
  trend: MarketTrend;
  /** Trend strength indicator */
  strength: TrendStrength;
  /** Confidence score (0-100) */
  confidence: number;
  /** Recent price history for sparkline (last 20 prices) */
  priceHistory: number[];
  /** Trend calculation timestamp */
  timestamp: string;
}

/**
 * Market trend API response
 */
export interface MarketTrendResponse {
  /** Market trend data */
  trend: MarketTrendData;
  /** Response timestamp */
  timestamp: string;
}
