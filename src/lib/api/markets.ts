/**
 * Markets API Service
 *
 * API endpoints for market data including volatility indices.
 */

import { get } from './client';
import type { MarketsOverviewResponse, MarketDetailResponse } from '@/types/market';

/**
 * Fetch market overview data
 * GET /markets/overview
 *
 * Returns current market data for all volatility indices including:
 * - Current prices
 * - Price changes (absolute and percentage)
 * - 24-hour high and low
 * - Market status
 *
 * @returns Promise with markets overview response
 */
export async function fetchMarketsOverview(): Promise<MarketsOverviewResponse> {
  const response = await get<MarketsOverviewResponse>('/markets/overview');

  return response.data;
}

/**
 * Fetch market detail data
 * GET /markets/{symbol}
 *
 * Returns detailed information for a single market including:
 * - Current price and changes
 * - 24-hour statistics (open, high, low, close)
 * - Market trend and spread
 * - Volatility index value
 * - Recent price updates (last 10)
 *
 * @param symbol - Market symbol (e.g., "V10", "V25")
 * @returns Promise with market detail response
 */
export async function fetchMarketDetail(symbol: string): Promise<MarketDetailResponse> {
  const response = await get<MarketDetailResponse>(`/markets/${symbol}`);

  return response.data;
}

/**
 * Re-export market types for convenience
 */
export type { MarketsOverviewResponse, MarketDetailResponse } from '@/types/market';
