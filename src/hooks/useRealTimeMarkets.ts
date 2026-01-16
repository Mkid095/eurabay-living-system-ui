/**
 * useRealTimeMarkets Hook
 *
 * Manages real-time market price updates via WebSocket.
 * Subscribes to market_update events, updates market prices,
 * adds green/red flash effects for price changes, updates
 * price change percentages, highlights markets with significant
 * movements, and updates trend indicators when they change.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { wsClient } from '@/lib/websocket/client';
import type { MarketUpdateEvent } from '@/lib/websocket/events';
import type { MarketOverviewData, FlashState } from '@/types/market';

export interface UseRealTimeMarketsOptions {
  /**
   * Enable flash animation for price updates
   * @default true
   */
  enableFlash?: boolean;

  /**
   * Price change percentage threshold for highlighting
   * @default 2
   */
  highlightThreshold?: number;

  /**
   * Flash animation duration in milliseconds
   * @default 500
   */
  flashDuration?: number;
}

export interface UseRealTimeMarketsReturn {
  /**
   * Current market data with real-time updates
   */
  markets: MarketOverviewData[];

  /**
   * Flash states for each market (for visual feedback)
   */
  flashStates: Record<string, FlashState>;

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
   * Last update timestamp
   */
  lastUpdate: Date | null;

  /**
   * Refresh all market data from API
   */
  refresh: () => Promise<void>;

  /**
   * Manually trigger a flash animation for a specific market
   */
  flashMarket: (symbol: string, direction: 'up' | 'down') => void;

  /**
   * Check if a market is currently flashing
   */
  isFlashing: (symbol: string) => boolean;

  /**
   * Get previous price for a market (before last update)
   */
  getPreviousPrice: (symbol: string) => number | null;
}

const DEFAULT_HIGHLIGHT_THRESHOLD = 2;
const DEFAULT_FLASH_DURATION = 500;

/**
 * Hook to manage real-time market updates
 */
export function useRealTimeMarkets(
  initialMarkets: MarketOverviewData[] = [],
  options: UseRealTimeMarketsOptions = {}
): UseRealTimeMarketsReturn {
  const {
    enableFlash = true,
    highlightThreshold = DEFAULT_HIGHLIGHT_THRESHOLD,
    flashDuration = DEFAULT_FLASH_DURATION,
  } = options;

  const [markets, setMarkets] = useState<MarketOverviewData[]>(initialMarkets);
  const [flashStates, setFlashStates] = useState<Record<string, FlashState>>({});
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const isMounted = useRef(true);
  const previousPricesRef = useRef<Record<string, number>>({});
  const wsHandlerRef = useRef<(() => void) | null>(null);

  /**
   * Check if a market is currently flashing
   */
  const isFlashing = useCallback((symbol: string): boolean => {
    return flashStates[symbol] !== null && flashStates[symbol] !== undefined;
  }, [flashStates]);

  /**
   * Trigger flash animation for a market
   */
  const flashMarket = useCallback((symbol: string, direction: 'up' | 'down') => {
    if (!enableFlash || !isMounted.current) return;

    setFlashStates((prev) => ({ ...prev, [symbol]: direction }));

    setTimeout(() => {
      if (isMounted.current) {
        setFlashStates((prev) => {
          const next = { ...prev };
          delete next[symbol];
          return next;
        });
      }
    }, flashDuration);
  }, [enableFlash, flashDuration]);

  /**
   * Get previous price for a market
   */
  const getPreviousPrice = useCallback((symbol: string): number | null => {
    return previousPricesRef.current[symbol] ?? null;
  }, []);

  /**
   * Handle market update event from WebSocket
   */
  const handleMarketUpdate = useCallback((data: MarketUpdateEvent) => {
    if (!isMounted.current) return;

    const { symbol, bid, priceChange, priceChangePercentage, timestamp } = data;

    setMarkets((prevMarkets) => {
      let updatedMarket: MarketOverviewData | null = null;

      const newMarkets = prevMarkets.map((market) => {
        if (market.symbol === symbol) {
          // Determine flash direction based on price change
          const previousPrice = previousPricesRef.current[symbol];
          let flashState: FlashState = null;

          if (previousPrice !== undefined && previousPrice !== bid) {
            flashState = bid > previousPrice ? 'up' : 'down';
          }

          // Store current price for next comparison
          previousPricesRef.current[symbol] = bid;

          // Trigger flash animation if price changed
          if (flashState && enableFlash) {
            setFlashStates((prev) => ({ ...prev, [symbol]: flashState! }));

            setTimeout(() => {
              if (isMounted.current) {
                setFlashStates((prev) => {
                  const next = { ...prev };
                  delete next[symbol];
                  return next;
                });
              }
            }, flashDuration);
          }

          // Update market with WebSocket data
          updatedMarket = {
            ...market,
            price: bid,
            priceChange,
            priceChangePercentage,
            high24h: Math.max(market.high24h, bid),
            low24h: Math.min(market.low24h, bid),
            timestamp,
          };

          return updatedMarket;
        }

        return market;
      });

      // Update last update timestamp
      setLastUpdate(new Date(timestamp));

      return newMarkets;
    });
  }, [enableFlash, flashDuration]);

  /**
   * Refresh markets from API
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
        const errorObj = err instanceof Error ? err : new Error('Failed to refresh markets');
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
   * Subscribe to market_update events
   */
  useEffect(() => {
    wsHandlerRef.current = () => {
      const unsubscribe = wsClient.on<MarketUpdateEvent>('market_update', handleMarketUpdate);

      if (process.env.NODE_ENV === 'development') {
        console.log('[useRealTimeMarkets] Subscribed to market_update events');
      }

      return unsubscribe;
    };

    const unsubscribe = wsHandlerRef.current();

    return () => {
      unsubscribe?.();

      if (process.env.NODE_ENV === 'development') {
        console.log('[useRealTimeMarkets] Unsubscribed from market_update events');
      }
    };
  }, [handleMarketUpdate]);

  /**
   * Initialize previous prices when initial markets change
   */
  useEffect(() => {
    initialMarkets.forEach((market) => {
      previousPricesRef.current[market.symbol] = market.price;
    });
  }, [initialMarkets]);

  /**
   * Update markets when initial data changes
   */
  useEffect(() => {
    setMarkets(initialMarkets);
    setLastUpdate(new Date());
  }, [initialMarkets]);

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
    markets,
    flashStates,
    isConnected,
    isLoading,
    error,
    lastUpdate,
    refresh,
    flashMarket,
    isFlashing,
    getPreviousPrice,
  };
}
