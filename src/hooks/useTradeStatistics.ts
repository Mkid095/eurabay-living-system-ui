/**
 * useTradeStatistics Hook
 *
 * Fetches and manages trading performance statistics from the API.
 * Includes date range filtering, loading states, error handling, and auto-refresh.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { get } from '@/lib/api/client';
import type { TradeStatistics, StatisticsDateRange } from '@/types/evolution';

export interface UseTradeStatisticsOptions {
  dateRange?: StatisticsDateRange;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export interface UseTradeStatisticsReturn {
  statistics: TradeStatistics | null;
  isLoading: boolean;
  error: Error | null;
  lastUpdated: Date | null;
  refreshStatistics: () => Promise<void>;
  setDateRange: (range: StatisticsDateRange) => void;
}

const AUTO_REFRESH_INTERVAL = 30000; // 30 seconds

/**
 * Hook to fetch and manage trading statistics
 */
export function useTradeStatistics(options: UseTradeStatisticsOptions = {}): UseTradeStatisticsReturn {
  const {
    dateRange: initialDateRange = 'all',
    autoRefresh = true,
    refreshInterval = AUTO_REFRESH_INTERVAL,
  } = options;

  const [statistics, setStatistics] = useState<TradeStatistics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [dateRange, setDateRange] = useState<StatisticsDateRange>(initialDateRange);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const isMounted = useRef(true);
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Calculate days offset from date range
   */
  const getDaysFromRange = useCallback((range: StatisticsDateRange): number | undefined => {
    switch (range) {
      case 'today':
        return 1;
      case 'week':
        return 7;
      case 'month':
        return 30;
      case 'all':
        return undefined;
      default:
        return undefined;
    }
  }, []);

  /**
   * Fetch statistics from API
   */
  const fetchStatistics = useCallback(async (): Promise<void> => {
    if (!isMounted.current) return;

    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();

      // Add date range filter
      const days = getDaysFromRange(dateRange);
      if (days !== undefined) {
        params.append('days', days.toString());
      }

      const queryString = params.toString();
      const endpoint = `/trades/statistics${queryString ? `?${queryString}` : ''}`;

      const response = await get<TradeStatistics>(endpoint);

      if (isMounted.current && response.ok) {
        setStatistics(response.data);
        setLastUpdated(new Date());
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to fetch trade statistics');
        setError(errorObj);
        console.error('[useTradeStatistics] Fetch failed:', errorObj);
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, [dateRange, getDaysFromRange]);

  /**
   * Refresh statistics (can be called manually)
   */
  const refreshStatistics = useCallback(async () => {
    await fetchStatistics();
  }, [fetchStatistics]);

  /**
   * Set date range and refetch
   */
  const setDateRangeCallback = useCallback((range: StatisticsDateRange) => {
    setDateRange(range);
  }, []);

  /**
   * Setup auto-refresh timer
   */
  useEffect(() => {
    if (!autoRefresh) {
      return;
    }

    // Clear existing timer
    if (refreshTimerRef.current) {
      clearInterval(refreshTimerRef.current);
    }

    // Setup new timer
    refreshTimerRef.current = setInterval(() => {
      fetchStatistics();
    }, refreshInterval);

    // Cleanup timer on unmount
    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
    };
  }, [autoRefresh, refreshInterval, fetchStatistics]);

  /**
   * Fetch statistics when date range changes
   */
  useEffect(() => {
    fetchStatistics();
  }, [fetchStatistics]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    isMounted.current = true;

    return () => {
      isMounted.current = false;
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
      }
    };
  }, []);

  return {
    statistics,
    isLoading,
    error,
    lastUpdated,
    refreshStatistics,
    setDateRange: setDateRangeCallback,
  };
}
