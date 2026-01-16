"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { toast } from "sonner";

interface WebSocketMessage {
  type: string;
  data: unknown;
}

interface UseWebSocketOptions {
  /**
   * Enable/disable WebSocket connection
   * @default true
   */
  enabled?: boolean;

  /**
   * Reconnection attempt delay in milliseconds
   * @default 3000 (3 seconds)
   */
  reconnectDelay?: number;

  /**
   * Maximum reconnection attempts
   * @default 10
   */
  maxReconnectAttempts?: number;

  /**
   * Message handler callback
   */
  onMessage?: (message: WebSocketMessage) => void;
}

interface UseWebSocketReturn {
  /**
   * WebSocket connection status
   */
  isConnected: boolean;

  /**
   * Whether the connection is currently attempting to reconnect
   */
  isReconnecting: boolean;

  /**
   * Connection error if any
   */
  error: string | null;

  /**
   * Send a message through the WebSocket
   */
  send: (message: Record<string, unknown>) => void;

  /**
   * Manually reconnect the WebSocket
   */
  reconnect: () => void;

  /**
   * Manually disconnect the WebSocket
   */
  disconnect: () => void;
}

/**
 * Custom hook for managing WebSocket connections
 * Provides automatic reconnection, error handling, and message handling
 */
export const useWebSocket = (
  messageType: string,
  options: UseWebSocketOptions = {}
): UseWebSocketReturn => {
  const {
    enabled = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 10,
    onMessage,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const isMountedRef = useRef(true);

  /**
   * Build WebSocket URL from environment variables
   */
  const getWebSocketUrl = useCallback(() => {
    const api_url = process.env.NEXT_PUBLIC_WS_URL;
    if (!api_url) {
      console.warn("NEXT_PUBLIC_WS_URL not set, using default");
      return "ws://localhost:8000/ws";
    }

    // Convert http(s) to ws(s)
    const wsUrl = api_url.replace(/^http/, "ws");
    return wsUrl;
  }, []);

  /**
   * Connect to WebSocket server
   */
  const connect = useCallback(() => {
    if (!enabled || !isMountedRef.current) return;

    // Close existing connection if any
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    try {
      const wsUrl = getWebSocketUrl();
      console.log(`[WebSocket] Connecting to ${wsUrl} for message type: ${messageType}`);

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (!isMountedRef.current) return;

        console.log(`[WebSocket] Connected for message type: ${messageType}`);
        setIsConnected(true);
        setIsReconnecting(false);
        setError(null);
        reconnectAttemptsRef.current = 0;

        // Subscribe to the specific message type
        ws.send(
          JSON.stringify({
            action: "subscribe",
            type: messageType,
          })
        );
      };

      ws.onmessage = (event) => {
        if (!isMountedRef.current) return;

        try {
          const message = JSON.parse(event.data) as WebSocketMessage;

          // Handle the message if it matches our type or is a broadcast
          if (message.type === messageType || message.type === "broadcast") {
            onMessage?.(message);
          }
        } catch (err) {
          console.error("[WebSocket] Failed to parse message:", err);
        }
      };

      ws.onerror = (event) => {
        if (!isMountedRef.current) return;
        console.error("[WebSocket] Error:", event);
        setError("WebSocket connection error");
      };

      ws.onclose = () => {
        if (!isMountedRef.current) return;

        console.log(`[WebSocket] Disconnected from ${messageType}`);
        setIsConnected(false);
        wsRef.current = null;

        // Attempt to reconnect if we haven't exceeded max attempts
        if (
          enabled &&
          reconnectAttemptsRef.current < maxReconnectAttempts
        ) {
          reconnectAttemptsRef.current++;
          setIsReconnecting(true);

          console.log(
            `[WebSocket] Reconnecting attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts}...`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        } else if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
          setError("Failed to reconnect after maximum attempts");
          setIsReconnecting(false);
          toast.error("WebSocket connection lost. Please refresh the page.");
        }
      };

      wsRef.current = ws;
    } catch (err) {
      console.error("[WebSocket] Failed to create connection:", err);
      setError("Failed to create WebSocket connection");
    }
  }, [enabled, messageType, onMessage, reconnectDelay, maxReconnectAttempts, getWebSocketUrl]);

  /**
   * Send a message through the WebSocket
   */
  const send = useCallback((message: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn("[WebSocket] Cannot send message, not connected");
    }
  }, []);

  /**
   * Manually reconnect the WebSocket
   */
  const reconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect]);

  /**
   * Manually disconnect the WebSocket
   */
  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setIsReconnecting(false);
  }, []);

  // Connect on mount and disconnect on unmount
  useEffect(() => {
    if (enabled) {
      connect();
    }

    return () => {
      isMountedRef.current = false;
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    isConnected,
    isReconnecting,
    error,
    send,
    reconnect,
    disconnect,
  };
};
