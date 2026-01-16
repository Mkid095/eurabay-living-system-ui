/**
 * useRecoveryDataRefresh Hook
 *
 * Registers a callback to refresh data after WebSocket reconnection.
 * Components can use this to fetch fresh data from the API when
 * the connection is restored.
 */

import { useEffect, useRef } from 'react';
import { recoveryManager, RecoveryCallbacks } from '@/lib/websocket/recovery';

/**
 * Options for useRecoveryDataRefresh hook
 */
export interface UseRecoveryDataRefreshOptions {
  /** Callback function to refresh data after reconnection */
  onDataRefresh?: () => void | Promise<void>;
  /** Whether the refresh is enabled */
  enabled?: boolean;
}

/**
 * Hook to register a data refresh callback for WebSocket reconnection
 *
 * @param options - Hook options
 *
 * @example
 * ```tsx
 * useRecoveryDataRefresh({
 *   onDataRefresh: async () => {
 *     // Refresh trades data
 *     await refreshTrades();
 *     // Refresh markets data
 *     await refreshMarkets();
 *   },
 * });
 * ```
 */
export function useRecoveryDataRefresh(options: UseRecoveryDataRefreshOptions): void {
  const { onDataRefresh, enabled = true } = options;

  // Use ref to avoid stale closure issues
  const callbackRef = useRef(onDataRefresh);
  callbackRef.current = onDataRefresh;

  useEffect(() => {
    if (!enabled || !onDataRefresh) {
      return;
    }

    // Create recovery callbacks with data refresh
    const recoveryCallbacks: RecoveryCallbacks = {
      onDataRefreshRequested: async () => {
        if (callbackRef.current) {
          try {
            await callbackRef.current();
          } catch (error) {
            console.error('[useRecoveryDataRefresh] Error refreshing data:', error);
          }
        }
      },
    };

    // Register with recovery manager
    const unsubscribe = recoveryManager.registerCallbacks(recoveryCallbacks);

    if (process.env.NODE_ENV === 'development') {
      console.log('[useRecoveryDataRefresh] Registered data refresh callback');
    }

    return () => {
      unsubscribe();
      if (process.env.NODE_ENV === 'development') {
        console.log('[useRecoveryDataRefresh] Unregistered data refresh callback');
      }
    };
  }, [enabled, onDataRefresh]);
}
