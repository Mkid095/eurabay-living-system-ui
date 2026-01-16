/**
 * Markets API Service
 *
 * API endpoints for market data including volatility indices.
 */

import { get } from './client';
import type { MarketsOverviewResponse } from '@/types/market';

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
 * Re-export market types for convenience
 */
export type { MarketsOverviewResponse } from '@/types/market';
