/**
 * usePendingSignals Hook
 *
 * Fetches and manages pending trading signals from the API.
 * Includes loading states, error handling, and approve/reject actions.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { get, post } from '@/lib/api/client';
import type { PendingSignal } from '@/types/evolution';

export interface UsePendingSignalsReturn {
  signals: PendingSignal[];
  isLoading: boolean;
  error: Error | null;
  refreshSignals: () => Promise<void>;
  approveSignal: (id: string) => Promise<void>;
  rejectSignal: (id: string) => Promise<void>;
  approveAllSignals: () => Promise<void>;
  rejectAllSignals: () => Promise<void>;
  retryCount: number;
}

export interface SignalActionResponse {
  success: boolean;
  message: string;
}

/**
 * Hook to fetch and manage pending signals
 */
export function usePendingSignals(): UsePendingSignalsReturn {
  const [signals, setSignals] = useState<PendingSignal[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [retryCount, setRetryCount] = useState(0);

  const isMounted = useRef(true);

  /**
   * Fetch pending signals from API
   */
  const fetchSignals = useCallback(async (): Promise<void> => {
    if (!isMounted.current) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await get<PendingSignal[]>('/trades/pending-signals');

      if (isMounted.current && response.ok) {
        setSignals(response.data);
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to fetch pending signals');
        setError(errorObj);
        setRetryCount((prev) => prev + 1);
        console.error('[usePendingSignals] Fetch failed:', errorObj);
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, []);

  /**
   * Refresh signals (can be called manually)
   */
  const refreshSignals = useCallback(async () => {
    await fetchSignals();
  }, [fetchSignals]);

  /**
   * Approve a single signal
   */
  const approveSignal = useCallback(async (id: string): Promise<void> => {
    try {
      const response = await post<SignalActionResponse>(`/trades/signals/${id}/approve`);

      if (isMounted.current && response.ok) {
        setSignals((prev) => prev.filter((signal) => signal.id !== id));
      }
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error('Failed to approve signal');
      console.error('[usePendingSignals] Approve failed:', errorObj);
      throw errorObj;
    }
  }, []);

  /**
   * Reject a single signal
   */
  const rejectSignal = useCallback(async (id: string): Promise<void> => {
    try {
      const response = await post<SignalActionResponse>(`/trades/signals/${id}/reject`);

      if (isMounted.current && response.ok) {
        setSignals((prev) => prev.filter((signal) => signal.id !== id));
      }
    } catch (err) {
      const errorObj = err instanceof Error ? err : new Error('Failed to reject signal');
      console.error('[usePendingSignals] Reject failed:', errorObj);
      throw errorObj;
    }
  }, []);

  /**
   * Approve all pending signals
   */
  const approveAllSignals = useCallback(async (): Promise<void> => {
    const signalIds = signals.map((s) => s.id);

    for (const id of signalIds) {
      try {
        await approveSignal(id);
      } catch (err) {
        console.error(`[usePendingSignals] Failed to approve signal ${id}:`, err);
      }
    }
  }, [signals, approveSignal]);

  /**
   * Reject all pending signals
   */
  const rejectAllSignals = useCallback(async (): Promise<void> => {
    const signalIds = signals.map((s) => s.id);

    for (const id of signalIds) {
      try {
        await rejectSignal(id);
      } catch (err) {
        console.error(`[usePendingSignals] Failed to reject signal ${id}:`, err);
      }
    }
  }, [signals, rejectSignal]);

  /**
   * Initial fetch and auto-refresh interval
   */
  useEffect(() => {
    fetchSignals();

    const intervalId = setInterval(() => {
      fetchSignals();
    }, 30000);

    return () => {
      clearInterval(intervalId);
    };
  }, [fetchSignals]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    isMounted.current = true;

    return () => {
      isMounted.current = false;
    };
  }, []);

  return {
    signals,
    isLoading,
    error,
    refreshSignals,
    approveSignal,
    rejectSignal,
    approveAllSignals,
    rejectAllSignals,
    retryCount,
  };
}
