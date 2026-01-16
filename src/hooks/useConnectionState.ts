"use client"

import { useState, useEffect } from 'react';
import { wsClient, ConnectionState } from '@/lib/websocket/client';

/**
 * Connection state interface returned by useConnectionState hook
 */
export interface ConnectionStateReturn {
  state: ConnectionState;
  latency: number | null;
  reconnectAttemptCount: number;
  reconnect: () => void;
}

/**
 * Hook to access WebSocket connection state
 * Subscribes to connection state changes and provides connection metrics
 */
export function useConnectionState(): ConnectionStateReturn {
  const [state, setState] = useState<ConnectionState>(wsClient.getState());
  const [latency, setLatency] = useState<number | null>(wsClient.getLatency());
  const [reconnectAttemptCount, setReconnectAttemptCount] = useState<number>(
    wsClient.getReconnectAttemptCount()
  );

  useEffect(() => {
    // Subscribe to connection state changes
    const unsubscribeState = wsClient.onStateChange((newState: ConnectionState) => {
      setState(newState);
      setReconnectAttemptCount(wsClient.getReconnectAttemptCount());
    });

    // Subscribe to latency changes
    const unsubscribeLatency = wsClient.onLatencyChange((newLatency: number | null) => {
      setLatency(newLatency);
    });

    return () => {
      unsubscribeState();
      unsubscribeLatency();
    };
  }, []);

  const reconnect = () => {
    wsClient.reconnect();
  };

  return {
    state,
    latency,
    reconnectAttemptCount,
    reconnect,
  };
}
