/**
 * useEquityHistory Hook
 *
 * Custom hook for fetching equity history with date range filtering,
 * auto-refresh, loading states, and error handling.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { portfolioApi, ApiRequestError } from '@/lib/api';
import type { EquityHistory } from '@/types/portfolio';
import type { DateRange } from '@/types/performance';

interface UseEquityHistoryResult {
  history: EquityHistory | null;
  isLoading: boolean;
  error: string | null;
  dateRange: DateRange;
  setDateRange: (range: DateRange) => void;
  retry: () => void;
}

export function useEquityHistory(
  initialDateRange: DateRange = 'all',
  autoRefreshInterval: number = 30000 // 30 seconds
): UseEquityHistoryResult {
  const [history, setHistory] = useState<EquityHistory | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<DateRange>(initialDateRange);
  const [retryCount, setRetryCount] = useState(0);

  const fetchHistory = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await portfolioApi.fetchEquityHistory(dateRange);
      setHistory(data);
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.message);
      } else {
        setError('Failed to fetch equity history');
      }
    } finally {
      setIsLoading(false);
    }
  }, [dateRange]);

  const retry = useCallback(() => {
    setRetryCount(prev => prev + 1);
  }, []);

  // Fetch history when date range or retry count changes
  useEffect(() => {
    fetchHistory();
  }, [fetchHistory, retryCount]);

  // Set up auto-refresh
  useEffect(() => {
    if (autoRefreshInterval > 0) {
      const interval = setInterval(() => {
        fetchHistory();
      }, autoRefreshInterval);

      return () => clearInterval(interval);
    }
  }, [fetchHistory, autoRefreshInterval]);

  return {
    history,
    isLoading,
    error,
    dateRange,
    setDateRange,
    retry,
  };
}
