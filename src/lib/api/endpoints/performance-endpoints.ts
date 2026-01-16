/**
 * Performance API Endpoints
 *
 * API endpoint functions for performance metrics and analytics.
 * All functions are fully typed with JSDoc comments.
 */

import { apiClient } from '../client';
import type {
  PerformanceMetrics,
  TradeStatistics,
  DateRange,
} from '../types';

// ============================================================================
// PERFORMANCE METRICS ENDPOINTS
// ============================================================================

/**
 * Get performance metrics
 * GET /performance/metrics
 *
 * Retrieves comprehensive performance metrics including
 * Sharpe ratio, max drawdown, win rate, and more.
 *
 * @param dateRange - Date range filter (default: 'all')
 * @returns Promise resolving to performance metrics
 *
 * @example
 * ```ts
 * // Get all-time performance
 * const metrics = await getMetrics();
 *
 * // Get this month's performance
 * const monthlyMetrics = await getMetrics('month');
 *
 * console.log(`Sharpe Ratio: ${metrics.sharpeRatio.toFixed(2)}`);
 * console.log(`Max Drawdown: ${metrics.maxDrawdownPercent.toFixed(2)}%`);
 * console.log(`Win Rate: ${metrics.winRatePercent.toFixed(1)}%`);
 * console.log(`Profit Factor: ${metrics.profitFactor.toFixed(2)}`);
 * ```
 */
export async function getMetrics(dateRange: DateRange = 'all'): Promise<PerformanceMetrics> {
  const { data } = await apiClient.get<PerformanceMetrics>('/performance/metrics', {
    range: dateRange,
  });
  return data;
}

/**
 * Get detailed trade statistics
 * GET /performance/trade-statistics
 *
 * Retrieves detailed statistics about trades including
 * average win/loss amounts, best/worst performing symbols,
 * and average trade duration.
 *
 * @param dateRange - Date range filter (default: 'all')
 * @returns Promise resolving to trade statistics
 *
 * @example
 * ```ts
 * // Get all-time statistics
 * const stats = await getTradeStatistics();
 *
 * // Get this week's statistics
 * const weeklyStats = await getTradeStatistics('week');
 *
 * console.log(`Total Trades: ${stats.totalTrades}`);
 * console.log(`Win Rate: ${stats.winRate.toFixed(1)}%`);
 * console.log(`Average Win: $${stats.averageWin.toFixed(2)}`);
 * console.log(`Average Loss: $${stats.averageLoss.toFixed(2)}`);
 * console.log(`Best Symbol: ${stats.bestPerformingSymbol}`);
 * ```
 */
export async function getTradeStatistics(dateRange: DateRange = 'all'): Promise<TradeStatistics> {
  const { data } = await apiClient.get<TradeStatistics>('/performance/trade-statistics', {
    range: dateRange,
  });
  return data;
}

/**
 * Get benchmark comparison
 * GET /performance/benchmark
 *
 * Compares portfolio performance against a benchmark
 * (e.g., S&P 500, buy-and-hold strategy).
 *
 * @param benchmark - Benchmark identifier (default: 'sp500')
 * @param dateRange - Date range filter (default: 'all')
 * @returns Promise resolving to benchmark comparison data
 *
 * @example
 * ```ts
 * const comparison = await getBenchmarkComparison('sp500');
 * console.log(`Portfolio Return: ${comparison.returnPercent.toFixed(2)}%`);
 * console.log(`Benchmark Return: ${comparison.benchmarkReturnPercent?.toFixed(2)}%`);
 * ```
 */
export async function getBenchmarkComparison(
  benchmark: string = 'sp500',
  dateRange: DateRange = 'all'
): Promise<{
  name: string;
  return: number;
  returnPercent: number;
  benchmarkReturn?: number;
  benchmarkReturnPercent?: number;
  outperformance?: number;
}> {
  const { data } = await apiClient.get('/performance/benchmark', {
    benchmark,
    range: dateRange,
  });
  return data;
}

/**
 * Get performance by symbol
 * GET /performance/by-symbol
 *
 * Retrieves performance metrics broken down by trading symbol.
 *
 * @param dateRange - Date range filter (default: 'all')
 * @returns Promise resolving to array of symbol performance data
 *
 * @example
 * ```ts
 * const bySymbol = await getPerformanceBySymbol('month');
 * bySymbol.forEach(item => {
 *   console.log(`${item.symbol}: ${item.returnPercent.toFixed(2)}% (${item.trades} trades)`);
 * });
 * ```
 */
export async function getPerformanceBySymbol(dateRange: DateRange = 'all'): Promise<
  Array<{
    symbol: string;
    trades: number;
    winRate: number;
    return: number;
    returnPercent: number;
    avgWin: number;
    avgLoss: number;
    profitFactor: number;
  }>
> {
  const { data } = await apiClient.get('/performance/by-symbol', {
    range: dateRange,
  });
  return data;
}

// ============================================================================
// EXPORTED API OBJECT
// ============================================================================

/**
 * Performance API object
 *
 * Provides a convenient way to import all performance-related functions:
 * ```ts
 * import { performanceApi } from '@/lib/api';
 *
 * const metrics = await performanceApi.getMetrics('month');
 * const stats = await performanceApi.getTradeStatistics();
 * ```
 */
export const performanceApi = {
  getMetrics,
  getTradeStatistics,
  getBenchmarkComparison,
  getPerformanceBySymbol,
} as const;
