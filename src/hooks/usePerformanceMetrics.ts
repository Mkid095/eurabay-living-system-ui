/**
 * usePerformanceMetrics Hook
 *
 * Custom hook for fetching performance metrics with date range filtering,
 * auto-refresh, loading states, and error handling.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { performanceApi, ApiRequestError } from '@/lib/api';
import type { PerformanceMetrics, DateRange } from '@/types/performance';

interface UsePerformanceMetricsResult {
  metrics: PerformanceMetrics | null;
  isLoading: boolean;
  error: string | null;
  dateRange: DateRange;
  setDateRange: (range: DateRange) => void;
  retry: () => void;
}

export function usePerformanceMetrics(
  initialDateRange: DateRange = 'all',
  autoRefreshInterval: number = 30000 // 30 seconds
): UsePerformanceMetricsResult {
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<DateRange>(initialDateRange);
  const [retryCount, setRetryCount] = useState(0);

  const fetchMetrics = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await performanceApi.fetchPerformanceMetrics(dateRange);
      setMetrics(data);
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.message);
      } else {
        setError('Failed to fetch performance metrics');
      }
    } finally {
      setIsLoading(false);
    }
  }, [dateRange]);

  const retry = useCallback(() => {
    setRetryCount(prev => prev + 1);
  }, []);

  // Fetch metrics when date range or retry count changes
  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics, retryCount]);

  // Set up auto-refresh
  useEffect(() => {
    if (autoRefreshInterval > 0) {
      const interval = setInterval(() => {
        fetchMetrics();
      }, autoRefreshInterval);

      return () => clearInterval(interval);
    }
  }, [fetchMetrics, autoRefreshInterval]);

  return {
    metrics,
    isLoading,
    error,
    dateRange,
    setDateRange,
    retry,
  };
}
