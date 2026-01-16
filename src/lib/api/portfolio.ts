/**
 * Portfolio API Service
 *
 * Service methods for interacting with portfolio-related endpoints.
 * Provides type-safe API calls for equity history and P&L data.
 */

import { apiClient } from './client';
import type { EquityHistory, PnLHistory } from '@/types/portfolio';
import type { DateRange } from '@/types/performance';

/**
 * Fetch equity history
 * GET /portfolio/equity-history
 *
 * @param dateRange - Date range filter (today, week, month, all)
 */
export async function fetchEquityHistory(
  dateRange: DateRange = 'all'
): Promise<EquityHistory> {
  const { data } = await apiClient.get<EquityHistory>('/portfolio/equity-history', {
    range: dateRange,
  });
  return data;
}

/**
 * Fetch P&L history
 * GET /portfolio/pnl-history
 *
 * @param dateRange - Date range filter (today, week, month, all)
 * @param symbol - Optional symbol filter
 */
export async function fetchPnLHistory(
  dateRange: DateRange = 'all',
  symbol?: string
): Promise<PnLHistory> {
  const params: Record<string, string | number> = { range: dateRange };
  if (symbol) {
    params.symbol = symbol;
  }
  const { data } = await apiClient.get<PnLHistory>('/portfolio/pnl-history', params);
  return data;
}

/**
 * Export portfolio service object
 */
export const portfolioApi = {
  fetchEquityHistory,
  fetchPnLHistory,
} as const;
