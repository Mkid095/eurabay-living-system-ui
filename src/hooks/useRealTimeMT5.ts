/**
 * useRealTimeMT5 Hook
 *
 * Manages real-time MT5 (MetaTrader 5) event notifications via WebSocket.
 * Subscribes to mt5_connected, mt5_disconnected, mt5_order_opened,
 * mt5_order_closed, mt5_position_modified, and mt5_error events.
 * Updates MT5 connection status, shows toast notifications for orders,
 * updates positions when modified, and displays error messages.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';
import { wsClient } from '@/lib/websocket/client';
import {
  type MT5ConnectedEvent,
  type MT5DisconnectedEvent,
  type MT5OrderOpenedEvent,
  type MT5OrderClosedEvent,
  type MT5PositionModifiedEvent,
  type MT5ErrorEvent,
  MT5ErrorSeverity,
  OrderSide,
} from '@/lib/websocket/events';
import type { EvolvedTrade } from '@/types/evolution';

export interface UseRealTimeMT5Options {
  /**
   * Enable toast notifications for MT5 events
   * @default true
   */
  enableToasts?: boolean;

  /**
   * Enable automatic position updates
   * @default true
   */
  enablePositionUpdates?: boolean;
}

export interface MT5ConnectionState {
  /**
   * Whether MT5 is connected
   */
  connected: boolean;

  /**
   * MT5 account ID
   */
  accountId: string | null;

  /**
   * MT5 server name
   */
  server: string | null;

  /**
   * Connection type
   */
  connectionType: string | null;

  /**
   * Disconnection reason (if disconnected)
   */
  disconnectReason: string | null;
}

export interface UseRealTimeMT5Return {
  /**
   * MT5 connection state
   */
  mt5Connection: MT5ConnectionState;

  /**
   * Array of active trades updated by MT5 events
   */
  positions: EvolvedTrade[];

  /**
   * Recent MT5 errors
   */
  recentErrors: MT5ErrorEvent[];

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
   * Refresh all MT5 data from API
   */
  refresh: () => Promise<void>;

  /**
   * Manually reconnect to MT5
   */
  reconnect: () => void;
}

const DEFAULT_MAX_ERRORS = 50;
const TOAST_THROTTLE_MS = 3000;

/**
 * Create initial MT5 connection state
 */
function createInitialConnectionState(): MT5ConnectionState {
  return {
    connected: false,
    accountId: null,
    server: null,
    connectionType: null,
    disconnectReason: null,
  };
}

/**
 * Hook to manage real-time MT5 events
 */
export function useRealTimeMT5(
  initialPositions: EvolvedTrade[] = [],
  options: UseRealTimeMT5Options = {}
): UseRealTimeMT5Return {
  const {
    enableToasts = true,
    enablePositionUpdates = true,
  } = options;

  const [mt5Connection, setMt5Connection] = useState<MT5ConnectionState>(createInitialConnectionState);
  const [positions, setPositions] = useState<EvolvedTrade[]>(initialPositions);
  const [recentErrors, setRecentErrors] = useState<MT5ErrorEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const isMounted = useRef(true);
  const toastShownRef = useRef<Map<string, number>>(new Map());
  const wsHandlersRef = useRef<Array<() => void>>([]);

  /**
   * Check if toast should be throttled
   */
  const shouldThrottleToast = useCallback((key: string): boolean => {
    const lastShown = toastShownRef.current.get(key);
    const now = Date.now();

    if (lastShown && now - lastShown < TOAST_THROTTLE_MS) {
      return true;
    }

    toastShownRef.current.set(key, now);

    // Clean up old entries
    setTimeout(() => {
      toastShownRef.current.delete(key);
    }, TOAST_THROTTLE_MS * 2);

    return false;
  }, []);

  /**
   * Show toast with throttle check
   */
  const showThrottledToast = useCallback((
    title: string,
    message: string,
    type: 'success' | 'info' | 'warning' | 'error',
    throttleKey?: string
  ) => {
    if (!enableToasts) return;

    if (throttleKey && shouldThrottleToast(throttleKey)) {
      return;
    }

    if (type === 'success') {
      toast.success(title, { description: message });
    } else if (type === 'warning') {
      toast.warning(title, { description: message });
    } else if (type === 'error') {
      toast.error(title, { description: message });
    } else {
      toast.info(title, { description: message });
    }
  }, [enableToasts, shouldThrottleToast]);

  /**
   * Handle mt5_connected event from WebSocket
   */
  const handleMT5Connected = useCallback((event: MT5ConnectedEvent) => {
    if (!isMounted.current) return;

    if (process.env.NODE_ENV === 'development') {
      console.log('[useRealTimeMT5] MT5 connected:', event);
    }

    setMt5Connection({
      connected: true,
      accountId: event.accountId,
      server: event.server,
      connectionType: event.connectionType,
      disconnectReason: null,
    });

    showThrottledToast(
      'MT5 Connected',
      `Connected to ${event.server} (Account: ${event.accountId})`,
      'success',
      'mt5-connected'
    );
  }, [showThrottledToast]);

  /**
   * Handle mt5_disconnected event from WebSocket
   */
  const handleMT5Disconnected = useCallback((event: MT5DisconnectedEvent) => {
    if (!isMounted.current) return;

    if (process.env.NODE_ENV === 'development') {
      console.log('[useRealTimeMT5] MT5 disconnected:', event);
    }

    setMt5Connection((prev) => ({
      connected: false,
      accountId: prev.accountId,
      server: prev.server,
      connectionType: prev.connectionType,
      disconnectReason: event.reason ?? 'Unknown reason',
    }));

    showThrottledToast(
      'MT5 Disconnected',
      event.reason ?? 'Connection to MT5 terminal lost',
      'warning',
      'mt5-disconnected'
    );
  }, [showThrottledToast]);

  /**
   * Handle mt5_order_opened event from WebSocket
   */
  const handleMT5OrderOpened = useCallback((event: MT5OrderOpenedEvent) => {
    if (!isMounted.current) return;

    if (process.env.NODE_ENV === 'development') {
      console.log('[useRealTimeMT5] MT5 order opened:', event);
    }

    const sideText = event.side === OrderSide.BUY ? 'BUY' : 'SELL';
    const toastKey = `order-opened-${event.orderId}`;

    showThrottledToast(
      'Order Opened',
      `${sideText} ${event.lots} ${event.symbol} at ${event.price.toFixed(event.symbol.includes('JPY') ? 2 : 4)}`,
      'info',
      toastKey
    );
  }, [showThrottledToast]);

  /**
   * Handle mt5_order_closed event from WebSocket
   */
  const handleMT5OrderClosed = useCallback((event: MT5OrderClosedEvent) => {
    if (!isMounted.current) return;

    if (process.env.NODE_ENV === 'development') {
      console.log('[useRealTimeMT5] MT5 order closed:', event);
    }

    const sideText = event.side === OrderSide.BUY ? 'BUY' : 'SELL';
    const profitText = event.netProfit >= 0 ? `+$${event.netProfit.toFixed(2)}` : `-$${Math.abs(event.netProfit).toFixed(2)}`;
    const toastKey = `order-closed-${event.orderId}`;

    showThrottledToast(
      event.netProfit >= 0 ? 'Order Closed - Profit' : 'Order Closed - Loss',
      `${sideText} ${event.lots} ${event.symbol}: ${profitText}`,
      event.netProfit >= 0 ? 'success' : 'error',
      toastKey
    );

    // If position updates are enabled and we have a matching position, update it
    if (enablePositionUpdates) {
      setPositions((prevPositions) => {
        const positionIndex = prevPositions.findIndex(p => p.ticket === String(event.orderId));

        if (positionIndex !== -1) {
          const updatedPosition = { ...prevPositions[positionIndex] };
          // Update position status based on the close event
          return prevPositions.map((p, i) =>
            i === positionIndex
              ? { ...p, status: 'closed' as const, pnl: event.netProfit }
              : p
          );
        }

        return prevPositions;
      });
    }
  }, [showThrottledToast, enablePositionUpdates]);

  /**
   * Handle mt5_position_modified event from WebSocket
   */
  const handleMT5PositionModified = useCallback((event: MT5PositionModifiedEvent) => {
    if (!isMounted.current) return;

    if (process.env.NODE_ENV === 'development') {
      console.log('[useRealTimeMT5] MT5 position modified:', event);
    }

    // Update position when modified
    if (enablePositionUpdates) {
      setPositions((prevPositions) => {
        return prevPositions.map((position) => {
          if (position.ticket === String(event.positionId)) {
            const updatedPosition = { ...position };

            // Update stop loss
            if (event.modificationType === 'stop_loss' || event.modificationType === 'both') {
              if (event.newStopLoss !== undefined) {
                updatedPosition.stopLoss = event.newStopLoss;
              }
            }

            // Update take profit
            if (event.modificationType === 'take_profit' || event.modificationType === 'both') {
              if (event.newTakeProfit !== undefined) {
                updatedPosition.takeProfit = event.newTakeProfit;
              }
            }

            return updatedPosition;
          }

          return position;
        });
      });
    }

    // Show toast for position modifications
    const modificationDetails: string[] = [];
    if (event.newStopLoss !== undefined) {
      modificationDetails.push(`SL: ${event.newStopLoss.toFixed(4)}`);
    }
    if (event.newTakeProfit !== undefined) {
      modificationDetails.push(`TP: ${event.newTakeProfit.toFixed(4)}`);
    }

    showThrottledToast(
      'Position Modified',
      `${event.symbol}: ${modificationDetails.join(', ')}`,
      'info',
      `position-modified-${event.positionId}`
    );
  }, [showThrottledToast, enablePositionUpdates]);

  /**
   * Handle mt5_error event from WebSocket
   */
  const handleMT5Error = useCallback((event: MT5ErrorEvent) => {
    if (!isMounted.current) return;

    if (process.env.NODE_ENV === 'development') {
      console.log('[useRealTimeMT5] MT5 error:', event);
    }

    // Add to recent errors
    setRecentErrors((prevErrors) => {
      const newErrors = [event, ...prevErrors];

      // Trim to max errors
      if (newErrors.length > DEFAULT_MAX_ERRORS) {
        return newErrors.slice(0, DEFAULT_MAX_ERRORS);
      }

      return newErrors;
    });

    // Display error message based on severity
    const contextInfo = event.context
      ? ` ${event.context.operation ?? ''}${event.context.symbol ? ` on ${event.context.symbol}` : ''}`
      : '';

    if (event.severity === MT5ErrorSeverity.CRITICAL) {
      showThrottledToast(
        'MT5 Critical Error',
        `Error ${event.errorCode}: ${event.errorMessage}${contextInfo}`,
        'error',
        `mt5-critical-${event.errorCode}`
      );
    } else if (event.severity === MT5ErrorSeverity.ERROR) {
      showThrottledToast(
        'MT5 Error',
        `Error ${event.errorCode}: ${event.errorMessage}${contextInfo}`,
        'error',
        `mt5-error-${event.errorCode}`
      );
    } else {
      showThrottledToast(
        'MT5 Warning',
        `Warning ${event.errorCode}: ${event.errorMessage}${contextInfo}`,
        'warning',
        `mt5-warning-${event.errorCode}`
      );
    }
  }, [showThrottledToast]);

  /**
   * Manually reconnect to MT5
   */
  const reconnect = useCallback(() => {
    wsClient.reconnect();
  }, []);

  /**
   * Refresh MT5 data from API
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
        const errorObj = err instanceof Error ? err : new Error('Failed to refresh MT5 data');
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
   * Subscribe to MT5 events
   */
  useEffect(() => {
    const unsubscribeConnected = wsClient.on<MT5ConnectedEvent>(
      'mt5_connected',
      handleMT5Connected
    );

    const unsubscribeDisconnected = wsClient.on<MT5DisconnectedEvent>(
      'mt5_disconnected',
      handleMT5Disconnected
    );

    const unsubscribeOrderOpened = wsClient.on<MT5OrderOpenedEvent>(
      'mt5_order_opened',
      handleMT5OrderOpened
    );

    const unsubscribeOrderClosed = wsClient.on<MT5OrderClosedEvent>(
      'mt5_order_closed',
      handleMT5OrderClosed
    );

    const unsubscribePositionModified = wsClient.on<MT5PositionModifiedEvent>(
      'mt5_position_modified',
      handleMT5PositionModified
    );

    const unsubscribeError = wsClient.on<MT5ErrorEvent>(
      'mt5_error',
      handleMT5Error
    );

    wsHandlersRef.current = [
      unsubscribeConnected,
      unsubscribeDisconnected,
      unsubscribeOrderOpened,
      unsubscribeOrderClosed,
      unsubscribePositionModified,
      unsubscribeError,
    ];

    if (process.env.NODE_ENV === 'development') {
      console.log('[useRealTimeMT5] Subscribed to MT5 events');
    }

    return () => {
      wsHandlersRef.current.forEach(unsubscribe => unsubscribe?.());

      if (process.env.NODE_ENV === 'development') {
        console.log('[useRealTimeMT5] Unsubscribed from MT5 events');
      }
    };
  }, [
    handleMT5Connected,
    handleMT5Disconnected,
    handleMT5OrderOpened,
    handleMT5OrderClosed,
    handleMT5PositionModified,
    handleMT5Error,
  ]);

  /**
   * Update positions when initial data changes
   */
  useEffect(() => {
    setPositions(initialPositions);
  }, [initialPositions]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    isMounted.current = true;

    return () => {
      isMounted.current = false;
      toastShownRef.current.clear();
    };
  }, []);

  return {
    mt5Connection,
    positions,
    recentErrors,
    isConnected,
    isLoading,
    error,
    refresh,
    reconnect,
  };
}
