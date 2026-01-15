/**
 * Performance API Service
 *
 * Service methods for interacting with performance-related endpoints.
 * Provides type-safe API calls for performance metrics.
 */

import { apiClient } from './client';
import type { PerformanceMetrics, DateRange } from '@/types/performance';

/**
 * Fetch performance metrics
 * GET /performance/metrics
 *
 * @param dateRange - Date range filter (today, week, month, all)
 */
export async function fetchPerformanceMetrics(
  dateRange: DateRange = 'all'
): Promise<PerformanceMetrics> {
  const { data } = await apiClient.get<PerformanceMetrics>('/performance/metrics', {
    range: dateRange,
  });
  return data;
}

/**
 * Export performance service object
 */
export const performanceApi = {
  fetchPerformanceMetrics,
} as const;
