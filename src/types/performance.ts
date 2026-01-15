/**
 * Performance Types
 *
 * Type definitions for performance metrics and analytics data.
 */

export type DateRange = 'today' | 'week' | 'month' | 'all';

export interface PerformanceMetrics {
  totalReturn: number;
  totalReturnPercent: number;
  sharpeRatio: number;
  maxDrawdown: number;
  maxDrawdownPercent: number;
  winRate: number;
  winRatePercent: number;
  totalTrades: number;
  averageTradeDuration: number;
  profitFactor: number;
  benchmarkReturn?: number;
  benchmarkReturnPercent?: number;
}

export interface BenchmarkComparison {
  name: string;
  return: number;
  returnPercent: number;
}
