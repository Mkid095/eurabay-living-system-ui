/**
 * useMT5Positions Hook
 *
 * Provides access to MT5 positions data and position management functions.
 * Auto-refreshes positions every 3 seconds.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type { MT5Position } from '@/lib/mt5/types';
import {
  getMT5Positions,
  closeMT5Position,
  modifyMT5Position,
} from '@/lib/mt5/positions';
import type {
  CloseMT5PositionRequest,
  ModifyMT5PositionRequest,
} from '@/lib/mt5/positions';

export interface MT5PositionsData {
  positions: MT5Position[];
  isLoading: boolean;
  error: Error | null;
}

export interface UseMT5PositionsReturn extends MT5PositionsData {
  closePosition: (ticket: number, lots?: number) => Promise<boolean>;
  modifyPosition: (ticket: number, sl?: number, tp?: number) => Promise<boolean>;
  refreshPositions: () => Promise<void>;
}

/**
 * Hook to access and manage MT5 positions
 * Auto-refreshes positions every 3 seconds
 */
export function useMT5Positions(): UseMT5PositionsReturn {
  const [positions, setPositions] = useState<MT5Position[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  // Use ref to track mounted state
  const isMounted = useRef(true);

  /**
   * Refresh positions from MT5 terminal
   */
  const refreshPositions = useCallback(async () => {
    if (!isMounted.current) return;

    setIsLoading(true);
    setError(null);

    try {
      const fetchedPositions = await getMT5Positions();

      if (isMounted.current) {
        setPositions(fetchedPositions);
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to fetch MT5 positions');
        setError(errorObj);
        console.error('[useMT5Positions] Position refresh failed:', errorObj);
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, []);

  /**
   * Close a position (full or partial close)
   *
   * @param ticket - Position ticket number
   * @param lots - Optional lots for partial close (if not provided, closes full position)
   * @returns Promise<boolean> - True if position was closed successfully
   */
  const closePosition = useCallback(async (ticket: number, lots?: number): Promise<boolean> => {
    if (!isMounted.current) return false;

    setIsLoading(true);
    setError(null);

    try {
      const request: CloseMT5PositionRequest = { ticket, lots };
      const success = await closeMT5Position(request);

      if (success && isMounted.current) {
        // Refresh positions after successful close
        await refreshPositions();
      }

      return success;
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to close position');
        setError(errorObj);
        console.error('[useMT5Positions] Close position failed:', errorObj);
      }
      return false;
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, [refreshPositions]);

  /**
   * Modify a position (stop loss and/or take profit)
   *
   * @param ticket - Position ticket number
   * @param sl - New stop loss price (optional, set to 0 to remove)
   * @param tp - New take profit price (optional, set to 0 to remove)
   * @returns Promise<boolean> - True if position was modified successfully
   */
  const modifyPosition = useCallback(async (ticket: number, sl?: number, tp?: number): Promise<boolean> => {
    if (!isMounted.current) return false;

    setIsLoading(true);
    setError(null);

    try {
      const request: ModifyMT5PositionRequest = {
        ticket,
        stopLoss: sl,
        takeProfit: tp,
      };
      const success = await modifyMT5Position(request);

      if (success && isMounted.current) {
        // Refresh positions after successful modification
        await refreshPositions();
      }

      return success;
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to modify position');
        setError(errorObj);
        console.error('[useMT5Positions] Modify position failed:', errorObj);
      }
      return false;
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, [refreshPositions]);

  // Auto-refresh positions every 3 seconds
  useEffect(() => {
    const intervalId = setInterval(() => {
      refreshPositions();
    }, 3000);

    return () => {
      clearInterval(intervalId);
    };
  }, [refreshPositions]);

  // Initial fetch on mount
  useEffect(() => {
    isMounted.current = true;

    // Fetch positions immediately on mount
    refreshPositions();

    return () => {
      isMounted.current = false;
    };
  }, [refreshPositions]);

  return {
    positions,
    isLoading,
    error,
    closePosition,
    modifyPosition,
    refreshPositions,
  };
}
