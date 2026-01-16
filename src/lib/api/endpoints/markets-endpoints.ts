/**
 * Markets API Endpoints
 *
 * API endpoint functions for market data including overview,
 * individual market data, and trend analysis.
 * All functions are fully typed with JSDoc comments.
 */

import { apiClient } from '../client';
import type {
  MarketsOverviewResponse,
  MarketData,
  MarketTrendInfo,
} from '../types';

// ============================================================================
// MARKET OVERVIEW ENDPOINTS
// ============================================================================

/**
 * Get markets overview
 * GET /markets/overview
 *
 * Retrieves an overview of all volatility indices markets
 * (V10, V25, V50, V75, V100) with current prices and changes.
 *
 * @returns Promise resolving to markets overview response
 *
 * @example
 * ```ts
 * const overview = await getOverview();
 * overview.markets.forEach(market => {
 *   console.log(`${market.symbol}: $${market.price.toFixed(2)} (${market.priceChangePercentage > 0 ? '+' : ''}${market.priceChangePercentage.toFixed(2)}%)`);
 * });
 * ```
 */
export async function getOverview(): Promise<MarketsOverviewResponse> {
  const { data } = await apiClient.get<MarketsOverviewResponse>('/markets/overview');
  return data;
}

// ============================================================================
// INDIVIDUAL MARKET DATA ENDPOINTS
// ============================================================================

/**
 * Get detailed market data for a symbol
 * GET /markets/{symbol}
 *
 * Retrieves detailed market information for a specific
 * volatility index symbol.
 *
 * @param symbol - Market symbol (e.g., 'V10', 'V25', 'V50', 'V75', 'V100')
 * @returns Promise resolving to market data
 *
 * @example
 * ```ts
 * const v10Data = await getMarketData('V10');
 * console.log(`Bid: $${v10Data.bid.toFixed(2)}`);
 * console.log(`Ask: $${v10Data.ask.toFixed(2)}`);
 * console.log(`Spread: $${v10Data.spread.toFixed(2)}`);
 * console.log(`24h High: $${v10Data.high24h.toFixed(2)}`);
 * console.log(`24h Low: $${v10Data.low24h.toFixed(2)}`);
 * console.log(`Trend: ${v10Data.trend}`);
 * ```
 */
export async function getMarketData(symbol: string): Promise<MarketData> {
  const { data } = await apiClient.get<MarketData>(`/markets/${symbol}`);
  return data;
}

/**
 * Get market data for multiple symbols
 * GET /markets?symbols={symbols}
 *
 * Retrieves market data for multiple symbols in a single request.
 *
 * @param symbols - Array of market symbols
 * @returns Promise resolving to array of market data
 *
 * @example
 * ```ts
 * const markets = await getMultipleMarkets(['V10', 'V25', 'V50']);
 * markets.forEach(m => {
 *   console.log(`${m.symbol}: $${m.price.toFixed(2)}`);
 * });
 * ```
 */
export async function getMultipleMarkets(symbols: string[]): Promise<MarketData[]> {
  const { data } = await apiClient.get<MarketData[]>('/markets', {
    symbols: symbols.join(','),
  });
  return data;
}

// ============================================================================
// MARKET TREND ENDPOINTS
// ============================================================================

/**
 * Get market trend analysis
 * GET /markets/{symbol}/trend
 *
 * Retrieves trend analysis for a specific market including
 * trend direction, strength, and confidence level.
 *
 * @param symbol - Market symbol (e.g., 'V10', 'V25')
 * @returns Promise resolving to trend information
 *
 * @example
 * ```ts
 * const trend = await getTrend('V10');
 * console.log(`Trend: ${trend.trend}`);
 * console.log(`Strength: ${trend.strength}`);
 * console.log(`Confidence: ${(trend.confidence * 100).toFixed(0)}%`);
 * ```
 */
export async function getTrend(symbol: string): Promise<MarketTrendInfo> {
  const { data } = await apiClient.get<MarketTrendInfo>(`/markets/${symbol}/trend`);
  return data;
}

/**
 * Get all market trends
 * GET /markets/trends
 *
 * Retrieves trend analysis for all supported markets.
 *
 * @returns Promise resolving to array of trend information
 *
 * @example
 * ```ts
 * const trends = await getAllTrends();
 * trends.forEach(t => {
 *   console.log(`${t.symbol}: ${t.trend} (${t.strength})`);
 * });
 * ```
 */
export async function getAllTrends(): Promise<MarketTrendInfo[]> {
  const { data } = await apiClient.get<MarketTrendInfo[]>('/markets/trends');
  return data;
}

// ============================================================================
// MARKET HISTORY ENDPOINTS
// ============================================================================

/**
 * Get historical market data
 * GET /markets/{symbol}/history
 *
 * Retrieves historical price data for a market.
 * Useful for charting and technical analysis.
 *
 * @param symbol - Market symbol
 * @param options - Optional filters for the data
 * @returns Promise resolving to array of price history points
 *
 * @example
 * ```ts
 * // Get last 24 hours of data with 5-minute intervals
 * const history = await getMarketHistory('V10', {
 *   interval: '5m',
 *   hours: 24
 * });
 *
 * history.forEach(point => {
 *   console.log(`${point.timestamp}: $${point.close.toFixed(2)}`);
 * });
 * ```
 */
export async function getMarketHistory(
  symbol: string,
  options?: {
    /** Time interval between data points */
    interval?: '1m' | '5m' | '15m' | '1h' | '4h' | '1d';
    /** Number of hours of history to retrieve */
    hours?: number;
    /** Number of data points to retrieve */
    limit?: number;
  }
): Promise<
  Array<{
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume?: number;
  }>
> {
  const params = options ? {
    interval: options.interval,
    hours: options.hours,
    limit: options.limit,
  } : undefined;
  const { data } = await apiClient.get(`/markets/${symbol}/history`, params);
  return data;
}

// ============================================================================
// EXPORTED API OBJECT
// ============================================================================

/**
 * Markets API object
 *
 * Provides a convenient way to import all market-related functions:
 * ```ts
 * import { marketsApi } from '@/lib/api';
 *
 * const overview = await marketsApi.getOverview();
 * const v10Data = await marketsApi.getMarketData('V10');
 * const trend = await marketsApi.getTrend('V10');
 * ```
 */
export const marketsApi = {
  // Overview
  getOverview,

  // Individual markets
  getMarketData,
  getMultipleMarkets,

  // Trends
  getTrend,
  getAllTrends,

  // History
  getMarketHistory,
} as const;
