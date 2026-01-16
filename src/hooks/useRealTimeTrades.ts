/**
 * useRealTimeTrades Hook
 *
 * Manages real-time trade updates via WebSocket.
 * Subscribes to trade_update events, updates trades array,
 * adds flash animations, moves closed trades to recent,
 * and shows toast notifications for significant P&L changes.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { wsClient } from '@/lib/websocket/client';
import type { TradeUpdateEvent, TradeStatus } from '@/lib/websocket/events';
import type { EvolvedTrade, ClosedTrade } from '@/types/evolution';
import { showTradeClosedToast, showPnLChangeToast } from '@/lib/toast/notifications';

export interface UseRealTimeTradesOptions {
  /**
   * Enable toast notifications for large P&L changes
   * @default true
   */
  enableToasts?: boolean;

  /**
   * P&L change percentage threshold for showing toast
   * @default 10
   */
  pnlChangeThreshold?: number;

  /**
   * Enable flash animation for updated trades
   * @default true
   */
  enableFlash?: boolean;
}

export interface UseRealTimeTradesReturn {
  /**
   * Current active trades with real-time updates
   */
  activeTrades: EvolvedTrade[];

  /**
   * Recent closed trades updated in real-time
   */
  recentTrades: ClosedTrade[];

  /**
   * Whether the WebSocket is connected
   */
  isConnected: boolean;

  /**
   * Whether currently fetching initial data
   */
  isLoading: boolean;

  /**
   * Error from fetching or WebSocket
   */
  error: Error | null;

  /**
   * Refresh all trade data from API
   */
  refresh: () => Promise<void>;

  /**
   * Manually trigger a flash animation for a specific trade
   */
  flashTrade: (ticket: string) => void;

  /**
   * Check if a trade is currently flashing
   */
  isFlashing: (ticket: string) => boolean;

  /**
   * Get the previous P&L value for a trade (before last update)
   */
  getPreviousPnL: (ticket: string) => number | null;
}

const DEFAULT_PNL_THRESHOLD = 10;
const FLASH_DURATION_MS = 1000;

/**
 * Hook to manage real-time trade updates
 */
export function useRealTimeTrades(
  initialActiveTrades: EvolvedTrade[] = [],
  initialRecentTrades: ClosedTrade[] = [],
  options: UseRealTimeTradesOptions = {}
): UseRealTimeTradesReturn {
  const {
    enableToasts = true,
    pnlChangeThreshold = DEFAULT_PNL_THRESHOLD,
    enableFlash = true,
  } = options;

  const [activeTrades, setActiveTrades] = useState<EvolvedTrade[]>(initialActiveTrades);
  const [recentTrades, setRecentTrades] = useState<ClosedTrade[]>(initialRecentTrades);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const isMounted = useRef(true);
  const flashingTradesRef = useRef<Set<string>>(new Set());
  const previousPnLRef = useRef<Map<string, number>>(new Map());
  const toastShownRef = useRef<Set<string>>(new Set());
  const wsHandlerRef = useRef<(() => void) | null>(null);

  /**
   * Check if a trade is currently flashing
   */
  const isFlashing = useCallback((ticket: string): boolean => {
    return flashingTradesRef.current.has(ticket);
  }, []);

  /**
   * Trigger flash animation for a trade
   */
  const flashTrade = useCallback((ticket: string) => {
    if (!enableFlash || !isMounted.current) return;

    flashingTradesRef.current.add(ticket);

    setTimeout(() => {
      if (isMounted.current) {
        flashingTradesRef.current.delete(ticket);
      }
    }, FLASH_DURATION_MS);
  }, [enableFlash]);

  /**
   * Get previous P&L value for a trade
   */
  const getPreviousPnL = useCallback((ticket: string): number | null => {
    return previousPnLRef.current.get(ticket) ?? null;
  }, []);

  /**
   * Show toast for significant P&L change
   */
  const showPnLToast = useCallback((
    trade: EvolvedTrade | ClosedTrade,
    previousPnL: number | null
  ) => {
    if (!enableToasts) return;

    const currentPnL = trade.pnl;
    const previousPnLValue = previousPnL ?? 0;

    // Calculate P&L change percentage
    const pnlChange = Math.abs(currentPnL - previousPnLValue);
    const pnlChangePercent = previousPnLValue !== 0
      ? (pnlChange / Math.abs(previousPnLValue)) * 100
      : 0;

    // Only show toast if change exceeds threshold
    if (pnlChangePercent >= pnlChangeThreshold) {
      const toastKey = `pnl-${trade.ticket}-${Date.now()}`;

      // Avoid duplicate toasts for the same trade
      if (toastShownRef.current.has(toastKey)) return;
      toastShownRef.current.add(toastKey);

      // Clean up toast key after a delay
      setTimeout(() => {
        toastShownRef.current.delete(toastKey);
      }, 5000);

      // Show toast with View button (optional - can be extended)
      showPnLChangeToast(trade as EvolvedTrade, pnlChangePercent, undefined, toastKey);
    }
  }, [enableToasts, pnlChangeThreshold]);

  /**
   * Handle trade update event from WebSocket
   */
  const handleTradeUpdate = useCallback((data: TradeUpdateEvent) => {
    if (!isMounted.current) return;

    const { tradeId, status, pnl, pnlPercentage } = data;

    // Store previous P&L before updating
    const previousPnL = previousPnLRef.current.get(tradeId) ?? null;

    // Handle trade based on its status
    if (status === 'closed' || status === 'cancelled') {
      // Move trade from active to recent
      setActiveTrades((prevActive) => {
        const tradeToMove = prevActive.find(t => t.ticket === tradeId);

        if (tradeToMove) {
          // Create closed trade from active trade
          const closedTrade: ClosedTrade = {
            ...tradeToMove,
            exitPrice: data.exitPrice ?? tradeToMove.currentPrice,
            exitTime: data.closeTime ?? new Date().toISOString(),
            pnl: pnl ?? tradeToMove.pnl,
            pnlPercent: pnlPercentage ?? tradeToMove.pnlPercent ?? 0,
          };

          // Add to recent trades
          setRecentTrades((prevRecent) => {
            const filtered = prevRecent.filter(t => t.ticket !== tradeId);
            return [closedTrade, ...filtered];
          });

          // Remove from active trades
          return prevActive.filter(t => t.ticket !== tradeId);
        }

        return prevActive;
      });

      // Show toast for closed trade with View button
      if (enableToasts) {
        // Find the closed trade in recent trades to show toast
        setRecentTrades((prevRecent) => {
          const closedTrade = prevRecent.find(t => t.ticket === tradeId);
          if (closedTrade) {
            showTradeClosedToast(closedTrade, undefined, `trade-closed-${tradeId}`);
          }
          return prevRecent;
        });
      }

      // Clean up references for closed trades
      previousPnLRef.current.delete(tradeId);
    } else {
      // Update active trade
      setActiveTrades((prevTrades) => {
        let updatedTrade: EvolvedTrade | null = null;

        const newTrades = prevTrades.map((trade) => {
          if (trade.ticket === tradeId) {
            updatedTrade = {
              ...trade,
              currentPrice: data.currentPrice ?? trade.currentPrice,
              pnl: pnl ?? trade.pnl,
              pnlPercent: pnlPercentage ?? trade.pnlPercent,
            };

            // Store current P&L for next comparison
            if (updatedTrade.pnl !== undefined) {
              previousPnLRef.current.set(tradeId, updatedTrade.pnl);
            }

            return updatedTrade;
          }
          return trade;
        });

        // Show toast for significant P&L change
        if (updatedTrade) {
          showPnLToast(updatedTrade, previousPnL);
        }

        return newTrades;
      });

      // Flash the updated trade
      flashTrade(tradeId);
    }
  }, [flashTrade, showPnLToast]);

  /**
   * Refresh trades from API
   */
  const refresh = useCallback(async () => {
    if (!isMounted.current) return;

    setIsLoading(true);
    setError(null);

    try {
      // This would typically fetch from API
      // For now, we rely on the initial data passed in
      // The caller should refetch and pass new data
      await new Promise(resolve => setTimeout(resolve, 100));

      if (isMounted.current) {
        setIsLoading(false);
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to refresh trades');
        setError(errorObj);
        setIsLoading(false);
      }
    }
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

    // Set initial state
    setIsConnected(wsClient.getState() === 'connected');

    return unsubscribeState;
  }, []);

  /**
   * Subscribe to trade_update events
   */
  useEffect(() => {
    wsHandlerRef.current = () => {
      const unsubscribe = wsClient.on<TradeUpdateEvent>('trade_update', handleTradeUpdate);

      if (process.env.NODE_ENV === 'development') {
        console.log('[useRealTimeTrades] Subscribed to trade_update events');
      }

      return unsubscribe;
    };

    const unsubscribe = wsHandlerRef.current();

    return () => {
      unsubscribe?.();

      if (process.env.NODE_ENV === 'development') {
        console.log('[useRealTimeTrades] Unsubscribed from trade_update events');
      }
    };
  }, [handleTradeUpdate]);

  /**
   * Initialize previous P&L values when initial trades change
   */
  useEffect(() => {
    initialActiveTrades.forEach((trade) => {
      if (trade.pnl !== undefined) {
        previousPnLRef.current.set(trade.ticket, trade.pnl);
      }
    });

    initialRecentTrades.forEach((trade) => {
      if (trade.pnl !== undefined) {
        previousPnLRef.current.set(trade.ticket, trade.pnl);
      }
    });
  }, [initialActiveTrades, initialRecentTrades]);

  /**
   * Update active trades when initial data changes
   */
  useEffect(() => {
    setActiveTrades(initialActiveTrades);
  }, [initialActiveTrades]);

  /**
   * Update recent trades when initial data changes
   */
  useEffect(() => {
    setRecentTrades(initialRecentTrades);
  }, [initialRecentTrades]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    isMounted.current = true;

    return () => {
      isMounted.current = false;
      previousPnLRef.current.clear();
      toastShownRef.current.clear();
      flashingTradesRef.current.clear();
    };
  }, []);

  return {
    activeTrades,
    recentTrades,
    isConnected,
    isLoading,
    error,
    refresh,
    flashTrade,
    isFlashing,
    getPreviousPnL,
  };
}
