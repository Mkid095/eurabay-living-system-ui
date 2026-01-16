/**
 * useRecentTrades Hook
 *
 * Fetches and manages recent closed trades from the API.
 * Includes filtering, search, pagination, loading states, and error handling.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { get } from '@/lib/api/client';
import type { ClosedTrade } from '@/types/evolution';

export type DateRange = 'today' | 'week' | 'month' | 'all';
export type OutcomeFilter = 'all' | 'profit' | 'loss';

export interface UseRecentTradesOptions {
  symbol?: string;
  outcome?: OutcomeFilter;
  dateRange?: DateRange;
  searchTicket?: string;
  page?: number;
  pageSize?: number;
}

export interface UseRecentTradesReturn {
  trades: ClosedTrade[];
  isLoading: boolean;
  error: Error | null;
  totalCount: number;
  currentPage: number;
  pageSize: number;
  totalPages: number;
  refreshTrades: () => Promise<void>;
  setFilters: (filters: Partial<UseRecentTradesOptions>) => void;
  setPage: (page: number) => void;
}

/**
 * Hook to fetch and manage recent closed trades
 */
export function useRecentTrades(options: UseRecentTradesOptions = {}): UseRecentTradesReturn {
  const {
    symbol: initialSymbol = 'all',
    outcome: initialOutcome = 'all',
    dateRange: initialDateRange = 'all',
    searchTicket: initialSearchTicket = '',
    page: initialPage = 1,
    pageSize: initialPageSize = 20,
  } = options;

  const [trades, setTrades] = useState<ClosedTrade[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [pageSize] = useState(initialPageSize);

  // Filter states
  const [symbolFilter, setSymbolFilter] = useState(initialSymbol);
  const [outcomeFilter, setOutcomeFilter] = useState<OutcomeFilter>(initialOutcome);
  const [dateRangeFilter, setDateRangeFilter] = useState<DateRange>(initialDateRange);
  const [searchTicketFilter, setSearchTicketFilter] = useState(initialSearchTicket);

  const isMounted = useRef(true);

  /**
   * Calculate days offset from date range
   */
  const getDaysFromRange = useCallback((range: DateRange): number | undefined => {
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
   * Fetch recent trades from API
   */
  const fetchTrades = useCallback(async (): Promise<void> => {
    if (!isMounted.current) return;

    setIsLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();

      // Add symbol filter
      if (symbolFilter && symbolFilter !== 'all') {
        params.append('symbol', symbolFilter);
      }

      // Add outcome filter
      if (outcomeFilter && outcomeFilter !== 'all') {
        params.append('outcome', outcomeFilter);
      }

      // Add date range filter
      const days = getDaysFromRange(dateRangeFilter);
      if (days !== undefined) {
        params.append('days', days.toString());
      }

      // Add search filter
      if (searchTicketFilter) {
        params.append('search', searchTicketFilter);
      }

      // Add pagination
      params.append('page', currentPage.toString());
      params.append('pageSize', pageSize.toString());

      const queryString = params.toString();
      const endpoint = `/trades/recent${queryString ? `?${queryString}` : ''}`;

      const response = await get<{ trades: ClosedTrade[]; total: number }>(endpoint);

      if (isMounted.current && response.ok) {
        setTrades(response.data.trades);
        setTotalCount(response.data.total);
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to fetch recent trades');
        setError(errorObj);
        console.error('[useRecentTrades] Fetch failed:', errorObj);
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, [symbolFilter, outcomeFilter, dateRangeFilter, searchTicketFilter, currentPage, pageSize, getDaysFromRange]);

  /**
   * Refresh trades (can be called manually)
   */
  const refreshTrades = useCallback(async () => {
    await fetchTrades();
  }, [fetchTrades]);

  /**
   * Set filters and reset to page 1
   */
  const setFilters = useCallback((filters: Partial<UseRecentTradesOptions>) => {
    if (filters.symbol !== undefined) {
      setSymbolFilter(filters.symbol);
    }
    if (filters.outcome !== undefined) {
      setOutcomeFilter(filters.outcome);
    }
    if (filters.dateRange !== undefined) {
      setDateRangeFilter(filters.dateRange);
    }
    if (filters.searchTicket !== undefined) {
      setSearchTicketFilter(filters.searchTicket);
    }
    // Reset to page 1 when filters change
    setCurrentPage(1);
  }, []);

  /**
   * Set current page
   */
  const setPage = useCallback((page: number) => {
    setCurrentPage(page);
  }, []);

  /**
   * Fetch trades when filters or page change
   */
  useEffect(() => {
    fetchTrades();
  }, [fetchTrades]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    isMounted.current = true;

    return () => {
      isMounted.current = false;
    };
  }, []);

  const totalPages = Math.ceil(totalCount / pageSize);

  return {
    trades,
    isLoading,
    error,
    totalCount,
    currentPage,
    pageSize,
    totalPages,
    refreshTrades,
    setFilters,
    setPage,
  };
}
