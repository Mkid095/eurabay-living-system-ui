/**
 * useActiveTrades Hook
 *
 * Fetches and manages active trades data from the API.
 * Includes real-time updates via WebSocket, loading states, and error handling.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { get } from '@/lib/api/client';
import { wsClient } from '@/lib/websocket/client';
import type { EvolvedTrade } from '@/types/evolution';

export interface UseActiveTradesReturn {
  trades: EvolvedTrade[];
  isLoading: boolean;
  error: Error | null;
  isConnected: boolean;
  refreshTrades: () => Promise<void>;
  retryCount: number;
  flashTrade: (ticket: string) => void;
  isFlashing: (ticket: string) => boolean;
}

export interface TradeUpdateData {
  tradeId: string;
  symbol: string;
  status: string;
  entryPrice: number;
  currentPrice?: number;
  pnl?: number;
  pnlPercentage?: number;
}

/**
 * MT5 Position Update Event Data
 */
export interface MT5PositionUpdateData {
  positionId: number;
  symbol: string;
  currentPrice: number;
  profit: number;
  profitPercentage?: number;
  timestamp: string;
}

/**
 * MT5 Position Closed Event Data
 */
export interface MT5PositionClosedData {
  positionId: number;
  symbol: string;
  lots: number;
  entryPrice: number;
  exitPrice: number;
  profit: number;
  commission: number;
  swap: number;
  closeTime: string;
  reason?: string;
}

/**
 * Hook to fetch and manage active trades with real-time updates
 */
export function useActiveTrades(): UseActiveTradesReturn {
  const [trades, setTrades] = useState<EvolvedTrade[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  const isMounted = useRef(true);
  const wsHandlerRef = useRef<(() => () => void) | null>(null);
  const wsMT5HandlerRef = useRef<(() => () => void) | null>(null);
  const wsMT5ClosedRef = useRef<(() => () => void) | null>(null);
  const flashingTradesRef = useRef<Set<string>>(new Set());

  /**
   * Fetch active trades from API
   */
  const fetchTrades = useCallback(async (): Promise<void> => {
    if (!isMounted.current) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await get<EvolvedTrade[]>('/trades/active');

      if (isMounted.current && response.ok) {
        setTrades(response.data);
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to fetch active trades');
        setError(errorObj);
        setRetryCount((prev) => prev + 1);
        console.error('[useActiveTrades] Fetch failed:', errorObj);
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, []);

  /**
   * Refresh trades (can be called manually)
   */
  const refreshTrades = useCallback(async () => {
    await fetchTrades();
  }, [fetchTrades]);

  /**
   * Check if a trade is currently flashing
   */
  const isFlashing = useCallback((ticket: string): boolean => {
    return flashingTradesRef.current.has(ticket);
  }, []);

  /**
   * Add a trade to the flashing set
   */
  const flashTrade = useCallback((ticket: string) => {
    flashingTradesRef.current.add(ticket);
    setTimeout(() => {
      flashingTradesRef.current.delete(ticket);
    }, 1000);
  }, []);

  /**
   * Handle trade update from WebSocket
   */
  const handleTradeUpdate = useCallback((data: TradeUpdateData) => {
    if (!isMounted.current) return;

    setTrades((prevTrades) => {
      const updatedTrades = prevTrades.map((trade) => {
        if (trade.ticket === data.tradeId) {
          return {
            ...trade,
            currentPrice: data.currentPrice ?? trade.currentPrice,
            pnl: data.pnl ?? trade.pnl,
            pnlPercent: data.pnlPercentage ?? trade.pnlPercent,
          };
        }
        return trade;
      });

      return updatedTrades;
    });

    flashTrade(data.tradeId);
  }, [flashTrade]);

  /**
   * Handle MT5 position update from WebSocket
   * Updates trade P&L and current price based on MT5 position data
   */
  const handleMT5PositionUpdate = useCallback((data: MT5PositionUpdateData) => {
    if (!isMounted.current) return;

    setTrades((prevTrades) => {
      const updatedTrades = prevTrades.map((trade) => {
        // Match trade by MT5 ticket number
        if (trade.mt5Ticket === data.positionId) {
          return {
            ...trade,
            currentPrice: data.currentPrice,
            pnl: data.profit,
            pnlPercent: data.profitPercentage,
          };
        }
        return trade;
      });

      return updatedTrades;
    });

    // Flash the trade with matching MT5 ticket
    setTrades((prevTrades) => {
      const matchingTrade = prevTrades.find(t => t.mt5Ticket === data.positionId);
      if (matchingTrade) {
        flashTrade(matchingTrade.ticket);
      }
      return prevTrades;
    });
  }, [flashTrade]);

  /**
   * Handle MT5 position closed event from WebSocket
   * Removes the trade from active trades list when MT5 position is closed
   */
  const handleMT5PositionClosed = useCallback((data: MT5PositionClosedData) => {
    if (!isMounted.current) return;

    setTrades((prevTrades) => {
      // Remove the trade that matches the closed MT5 position
      return prevTrades.filter((trade) => trade.mt5Ticket !== data.positionId);
    });

    console.log('[useActiveTrades] MT5 position closed:', data.positionId, data.symbol);
  }, []);

  /**
   * Subscribe to WebSocket connection state
   */
  useEffect(() => {
    const unsubscribeState = wsClient.onStateChange((state) => {
      if (isMounted.current) {
        setIsConnected(state === 'connected');
      }
    });

    return unsubscribeState;
  }, []);

  /**
   * Subscribe to trade update events
   */
  useEffect(() => {
    wsHandlerRef.current = () => {
      const unsubscribe = wsClient.on<TradeUpdateData>('trade_update', handleTradeUpdate);
      return unsubscribe;
    };

    const unsubscribe = wsHandlerRef.current();

    return () => {
      unsubscribe?.();
    };
  }, [handleTradeUpdate]);

  /**
   * Subscribe to MT5 position update events
   */
  useEffect(() => {
    wsMT5HandlerRef.current = () => {
      const unsubscribe = wsClient.on<MT5PositionUpdateData>('mt5_position_update', handleMT5PositionUpdate);
      return unsubscribe;
    };

    const unsubscribe = wsMT5HandlerRef.current();

    return () => {
      unsubscribe?.();
    };
  }, [handleMT5PositionUpdate]);

  /**
   * Subscribe to MT5 position closed events
   */
  useEffect(() => {
    wsMT5ClosedRef.current = () => {
      const unsubscribe = wsClient.on<MT5PositionClosedData>('mt5_position_closed', handleMT5PositionClosed);
      return unsubscribe;
    };

    const unsubscribe = wsMT5ClosedRef.current();

    return () => {
      unsubscribe?.();
    };
  }, [handleMT5PositionClosed]);

  /**
   * Initial fetch and auto-refresh interval
   */
  useEffect(() => {
    fetchTrades();

    const intervalId = setInterval(() => {
      fetchTrades();
    }, 30000);

    return () => {
      clearInterval(intervalId);
    };
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

  return {
    trades,
    isLoading,
    error,
    isConnected,
    refreshTrades,
    retryCount,
    flashTrade,
    isFlashing,
  };
}
