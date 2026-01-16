/**
 * useMT5Connection Hook
 *
 * Provides access to MT5 connection state, account info,
 * and connection management functions.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  mt5Client,
  MT5ConnectionState,
  MT5ConnectionInfo,
  MT5AccountInfo,
} from '@/lib/mt5/client';

export interface MT5ConnectionData {
  connectionState: MT5ConnectionState;
  connectionInfo: MT5ConnectionInfo | null;
  accountInfo: MT5AccountInfo | null;
  latency: number | null;
  isLoading: boolean;
  error: Error | null;
}

export interface UseMT5ConnectionReturn extends MT5ConnectionData {
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  refreshStatus: () => Promise<void>;
}

/**
 * Hook to access and manage MT5 connection state
 * Auto-refreshes connection status every 5 seconds
 */
export function useMT5Connection(): UseMT5ConnectionReturn {
  const [connectionState, setConnectionState] = useState<MT5ConnectionState>(() => mt5Client.getState());
  const [connectionInfo, setConnectionInfo] = useState<MT5ConnectionInfo | null>(() => mt5Client.getConnectionInfo());
  const [accountInfo, setAccountInfo] = useState<MT5AccountInfo | null>(() => mt5Client.getAccountInfo());
  const [latency, setLatency] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Use ref to track mounted state
  const isMounted = useRef(true);

  /**
   * Refresh connection status from MT5 client
   */
  const refreshStatus = useCallback(async () => {
    if (!isMounted.current) return;

    setIsLoading(true);
    setError(null);

    try {
      const isConnected = await mt5Client.isConnected();
      const info = mt5Client.getConnectionInfo();
      const account = mt5Client.getAccountInfo();
      const state = mt5Client.getState();

      if (isMounted.current) {
        setConnectionState(state);
        setConnectionInfo(info);
        setAccountInfo(account);
        setLatency(info?.latency ?? null);
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to refresh MT5 status');
        setError(errorObj);
        console.error('[useMT5Connection] Status refresh failed:', errorObj);
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, []);

  /**
   * Connect to MT5 terminal
   */
  const connect = useCallback(async () => {
    if (!isMounted.current) return;

    setIsLoading(true);
    setError(null);

    try {
      const info = await mt5Client.connect();

      if (isMounted.current) {
        setConnectionInfo(info);
        setAccountInfo(mt5Client.getAccountInfo());
        setConnectionState(mt5Client.getState());
        setLatency(info.latency ?? null);
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to connect to MT5');
        setError(errorObj);
        console.error('[useMT5Connection] Connection failed:', errorObj);
      }
      throw err;
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, []);

  /**
   * Disconnect from MT5 terminal
   */
  const disconnect = useCallback(async () => {
    if (!isMounted.current) return;

    setIsLoading(true);
    setError(null);

    try {
      await mt5Client.disconnect();

      if (isMounted.current) {
        setConnectionState(mt5Client.getState());
        setConnectionInfo(null);
        setAccountInfo(null);
        setLatency(null);
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to disconnect from MT5');
        setError(errorObj);
        console.error('[useMT5Connection] Disconnect failed:', errorObj);
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, []);

  // Set up state change listener
  useEffect(() => {
    const unsubscribe = mt5Client.onStateChange((newState) => {
      if (isMounted.current) {
        setConnectionState(newState);
      }
    });

    return unsubscribe;
  }, []);

  // Auto-refresh connection status every 5 seconds
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
    connectionState,
    connectionInfo,
    accountInfo,
    latency,
    isLoading,
    error,
    connect,
    disconnect,
    refreshStatus,
  };
}
