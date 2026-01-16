/**
 * usePnlHistory Hook
 *
 * Custom hook for fetching P&L history with date range filtering,
 * symbol filtering, auto-refresh, loading states, and error handling.
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { portfolioApi, ApiRequestError } from '@/lib/api';
import type { PnLHistory } from '@/types/portfolio';
import type { DateRange } from '@/types/performance';

interface UsePnlHistoryResult {
  history: PnLHistory | null;
  isLoading: boolean;
  error: string | null;
  dateRange: DateRange;
  setDateRange: (range: DateRange) => void;
  symbol: string | undefined;
  setSymbol: (symbol: string | undefined) => void;
  retry: () => void;
}

export function usePnlHistory(
  initialDateRange: DateRange = 'all',
  autoRefreshInterval: number = 30000 // 30 seconds
): UsePnlHistoryResult {
  const [history, setHistory] = useState<PnLHistory | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<DateRange>(initialDateRange);
  const [symbol, setSymbol] = useState<string | undefined>(undefined);
  const [retryCount, setRetryCount] = useState(0);

  const fetchHistory = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await portfolioApi.fetchPnLHistory(dateRange, symbol);
      setHistory(data);
    } catch (err) {
      if (err instanceof ApiRequestError) {
        setError(err.message);
      } else {
        setError('Failed to fetch P&L history');
      }
    } finally {
      setIsLoading(false);
    }
  }, [dateRange, symbol]);

  const retry = useCallback(() => {
    setRetryCount(prev => prev + 1);
  }, []);

  // Fetch history when date range, symbol, or retry count changes
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
    symbol,
    setSymbol,
    retry,
  };
}
