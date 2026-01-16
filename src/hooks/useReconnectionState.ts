/**
 * useReconnectionState Hook
 *
 * Provides access to WebSocket reconnection state for UI components.
 * Displays "Reconnecting..." messages and error states.
 */

import { useState, useEffect } from 'react';
import { recoveryManager, ReconnectionState } from '@/lib/websocket/recovery';

/**
 * Return type for useReconnectionState hook
 */
export interface UseReconnectionStateReturn extends ReconnectionState {
  /** Reset recovery state (e.g., after manual reconnect) */
  reset: () => void;
  /** Check if max consecutive failures reached */
  hasMaxFailures: boolean;
}

/**
 * Hook to access WebSocket reconnection state
 *
 * @returns Reconnection state and controls
 *
 * @example
 * ```tsx
 * const { isReconnecting, attempt, consecutiveFailures, hasMaxFailures, reset } = useReconnectionState();
 *
 * return (
 *   <div>
 *     {isReconnecting && <div>Reconnecting... Attempt {attempt}</div>}
 *     {hasMaxFailures && (
 *       <div>
 *         Connection failed after {consecutiveFailures} attempts.
 *         <button onClick={reset}>Try Again</button>
 *       </div>
 *     )}
 *   </div>
 * );
 * ```
 */
export function useReconnectionState(): UseReconnectionStateReturn {
  const [state, setState] = useState<ReconnectionState>(() => recoveryManager.getReconnectionState());

  useEffect(() => {
    // Subscribe to reconnection state changes
    const unsubscribe = recoveryManager.onReconnectionStateChange((newState) => {
      setState({ ...newState });
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const reset = () => {
    recoveryManager.reset();
  };

  const hasMaxFailures = recoveryManager.hasReconnectionFailed();

  return {
    ...state,
    reset,
    hasMaxFailures,
  };
}
