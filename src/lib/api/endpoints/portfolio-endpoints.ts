/**
 * Portfolio API Endpoints
 *
 * API endpoint functions for portfolio data including metrics,
 * equity history, and P&L history.
 * All functions are fully typed with JSDoc comments.
 */

import { apiClient } from '../client';
import type {
  PortfolioMetrics,
  EquityHistory,
  PnLHistory,
  DateRange,
} from '../types';

// ============================================================================
// PORTFOLIO METRICS ENDPOINTS
// ============================================================================

/**
 * Get portfolio metrics
 * GET /portfolio/metrics
 *
 * Retrieves current portfolio metrics including total value,
 * P&L, active trades count, and win rate.
 *
 * @returns Promise resolving to portfolio metrics
 *
 * @example
 * ```ts
 * const metrics = await getMetrics();
 * console.log(`Total Value: $${metrics.totalValue.toFixed(2)}`);
 * console.log(`P&L: ${metrics.totalPnLPercent.toFixed(2)}%`);
 * console.log(`Win Rate: ${metrics.winRate.toFixed(1)}%`);
 * ```
 */
export async function getMetrics(): Promise<PortfolioMetrics> {
  const { data } = await apiClient.get<PortfolioMetrics>('/portfolio/metrics');
  return data;
}

/**
 * Get equity history
 * GET /portfolio/equity-history
 *
 * Retrieves historical equity data for charting and analysis.
 * Supports filtering by date range.
 *
 * @param dateRange - Date range filter (default: 'all')
 * @returns Promise resolving to equity history
 *
 * @example
 * ```ts
 * // Get all equity history
 * const allHistory = await getEquityHistory();
 *
 * // Get last 7 days
 * const weekHistory = await getEquityHistory('week');
 *
 * // Get this month
 * const monthHistory = await getEquityHistory('month');
 *
 * console.log(`Peak equity: $${monthHistory.peakEquity.toFixed(2)}`);
 * console.log(`Max drawdown: ${(monthHistory.maxDrawdown * 100).toFixed(2)}%`);
 * ```
 */
export async function getEquityHistory(dateRange: DateRange = 'all'): Promise<EquityHistory> {
  const { data } = await apiClient.get<EquityHistory>('/portfolio/equity-history', {
    range: dateRange,
  });
  return data;
}

/**
 * Get P&L history
 * GET /portfolio/pnl-history
 *
 * Retrieves historical profit and loss data broken down by time period.
 * Supports filtering by date range and symbol.
 *
 * @param dateRange - Date range filter (default: 'all')
 * @param symbol - Optional symbol filter
 * @returns Promise resolving to P&L history
 *
 * @example
 * ```ts
 * // Get all P&L history
 * const allHistory = await getPnlHistory();
 *
 * // Get last 30 days
 * const monthHistory = await getPnlHistory('month');
 *
 * // Get P&L for specific symbol
 * const v10History = await getPnlHistory('all', 'V10');
 *
 * console.log(`Total P&L: $${allHistory.totalPnl.toFixed(2)}`);
 * console.log(`Winning periods: ${allHistory.winningPeriods}`);
 * console.log(`Losing periods: ${allHistory.losingPeriods}`);
 * ```
 */
export async function getPnlHistory(
  dateRange: DateRange = 'all',
  symbol?: string
): Promise<PnLHistory> {
  const params: Record<string, string> = { range: dateRange };
  if (symbol) {
    params.symbol = symbol;
  }
  const { data } = await apiClient.get<PnLHistory>('/portfolio/pnl-history', params);
  return data;
}

// ============================================================================
// EXPORTED API OBJECT
// ============================================================================

/**
 * Portfolio API object
 *
 * Provides a convenient way to import all portfolio-related functions:
 * ```ts
 * import { portfolioApi } from '@/lib/api';
 *
 * const metrics = await portfolioApi.getMetrics();
 * const equity = await portfolioApi.getEquityHistory('week');
 * ```
 */
export const portfolioApi = {
  getMetrics,
  getEquityHistory,
  getPnlHistory,
} as const;
