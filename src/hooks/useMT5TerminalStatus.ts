/**
 * useMT5TerminalStatus Hook
 *
 * Provides access to MT5 terminal status information including
 * connection state, terminal info, trading permissions, and error logs.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiClient } from '@/lib/api/client';
import type { MT5TerminalStatus } from '@/lib/mt5/types';

export interface MT5TerminalStatusData {
  terminalStatus: MT5TerminalStatus | null;
  isLoading: boolean;
  error: Error | null;
}

export interface UseMT5TerminalStatusReturn extends MT5TerminalStatusData {
  refreshStatus: () => Promise<void>;
  testConnection: () => Promise<boolean>;
  restartConnection: () => Promise<boolean>;
}

/**
 * Hook to access and manage MT5 terminal status
 * Auto-refreshes every 5 seconds
 */
export function useMT5TerminalStatus(): UseMT5TerminalStatusReturn {
  const [terminalStatus, setTerminalStatus] = useState<MT5TerminalStatus | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Use ref to track mounted state
  const isMounted = useRef(true);

  /**
   * Fetch terminal status from API
   */
  const fetchTerminalStatus = useCallback(async (): Promise<MT5TerminalStatus | null> => {
    if (!isMounted.current) return null;

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.get<MT5TerminalStatus>('mt5/terminal-info');

      if (!isMounted.current) return null;

      const status = response.data;
      // Convert date strings to Date objects
      if (status.lastHeartbeat && typeof status.lastHeartbeat === 'string') {
        status.lastHeartbeat = new Date(status.lastHeartbeat) as unknown as Date;
      }
      // Convert error log timestamps
      if (status.errors && Array.isArray(status.errors)) {
        status.errors = status.errors.map((err) => ({
          ...err,
          timestamp: typeof err.timestamp === 'string' ? new Date(err.timestamp) : err.timestamp,
        }));
      }

      setTerminalStatus(status);
      return status;
    } catch (err) {
      if (!isMounted.current) return null;

      const errorObj = err instanceof Error ? err : new Error('Failed to fetch MT5 terminal status');
      setError(errorObj);
      console.error('[useMT5TerminalStatus] Fetch failed:', errorObj);
      return null;
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, []);

  /**
   * Refresh terminal status
   */
  const refreshStatus = useCallback(async () => {
    await fetchTerminalStatus();
  }, [fetchTerminalStatus]);

  /**
   * Test connection to MT5 terminal
   */
  const testConnection = useCallback(async (): Promise<boolean> => {
    if (!isMounted.current) return false;

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.post<{ success: boolean }>('mt5/test-connection', {});
      const success = response.data?.success ?? false;

      if (success && isMounted.current) {
        // Refresh status after successful test
        await fetchTerminalStatus();
      }

      return success;
    } catch (err) {
      if (!isMounted.current) return false;

      const errorObj = err instanceof Error ? err : new Error('Connection test failed');
      setError(errorObj);
      console.error('[useMT5TerminalStatus] Test connection failed:', errorObj);
      return false;
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, [fetchTerminalStatus]);

  /**
   * Restart connection to MT5 terminal
   */
  const restartConnection = useCallback(async (): Promise<boolean> => {
    if (!isMounted.current) return false;

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.post<{ success: boolean }>('mt5/restart-connection', {});
      const success = response.data?.success ?? false;

      if (success && isMounted.current) {
        // Refresh status after successful restart
        await fetchTerminalStatus();
      }

      return success;
    } catch (err) {
      if (!isMounted.current) return false;

      const errorObj = err instanceof Error ? err : new Error('Connection restart failed');
      setError(errorObj);
      console.error('[useMT5TerminalStatus] Restart connection failed:', errorObj);
      return false;
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, [fetchTerminalStatus]);

  // Initial fetch on mount
  useEffect(() => {
    fetchTerminalStatus();
  }, [fetchTerminalStatus]);

  // Auto-refresh every 5 seconds
  useEffect(() => {
    const intervalId = setInterval(() => {
      refreshStatus();
    }, 5000);

    return () => {
      clearInterval(intervalId);
    };
  }, [refreshStatus]);

  // Cleanup on unmount
  useEffect(() => {
    isMounted.current = true;

    return () => {
      isMounted.current = false;
    };
  }, []);

  return {
    terminalStatus,
    isLoading,
    error,
    refreshStatus,
    testConnection,
    restartConnection,
  };
}
