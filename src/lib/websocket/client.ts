/**
 * WebSocket Connection States
 */
export type ConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'error';

/**
 * WebSocket Client Configuration
 */
export interface WSClientConfig {
  url: string;
  connectionTimeout?: number;
  reconnectOnClose?: boolean;
}

/**
 * WebSocket Client for managing real-time connections
 */
export class WSClient {
  private ws: WebSocket | null = null;
  private state: ConnectionState = 'disconnected';
  private connectionAttemptCount: number = 0;
  private connectionTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private config: Required<WSClientConfig>;
  private stateChangeCallbacks: Set<(state: ConnectionState) => void> = new Set();

  constructor(config: WSClientConfig) {
    this.config = {
      url: config.url,
      connectionTimeout: config.connectionTimeout ?? 10000,
      reconnectOnClose: config.reconnectOnClose ?? false,
    };
  }

  /**
   * Get current connection state
   */
  getState(): ConnectionState {
    return this.state;
  }

  /**
   * Get connection attempt count
   */
  getConnectionAttemptCount(): number {
    return this.connectionAttemptCount;
  }

  /**
   * Subscribe to connection state changes
   */
  onStateChange(callback: (state: ConnectionState) => void): () => void {
    this.stateChangeCallbacks.add(callback);
    return () => this.stateChangeCallbacks.delete(callback);
  }

  /**
   * Establish WebSocket connection
   */
  connect(): void {
    if (this.state === 'connected' || this.state === 'connecting') {
      return;
    }

    this.setState('connecting');
    this.connectionAttemptCount++;

    try {
      this.ws = new WebSocket(this.config.url);

      // Set up connection timeout
      this.connectionTimeoutId = setTimeout(() => {
        if (this.state === 'connecting') {
          this.ws?.close();
          this.setState('error');
        }
      }, this.config.connectionTimeout);

      // Connection opened
      this.ws.onopen = () => {
        this.clearConnectionTimeout();
        this.setState('connected');
      };

      // Connection closed
      this.ws.onclose = (event: CloseEvent) => {
        this.clearConnectionTimeout();

        if (this.state !== 'disconnected') {
          // Only reconnect if it wasn't a manual disconnect
          if (this.config.reconnectOnClose && !event.wasClean) {
            // Auto-reconnect will be handled by separate logic in US-002
            this.setState('error');
          } else {
            this.setState('disconnected');
          }
        }
      };

      // Connection error
      this.ws.onerror = (error: Event) => {
        this.clearConnectionTimeout();
        this.setState('error');
      };

      // Message received
      this.ws.onmessage = (event: MessageEvent) => {
        // Message handling will be added in US-006
        if (process.env.NODE_ENV === 'development') {
          console.log('[WS] Raw message received:', event.data);
        }
      };
    } catch (error) {
      this.clearConnectionTimeout();
      this.setState('error');
      if (process.env.NODE_ENV === 'development') {
        console.error('[WS] Connection error:', error);
      }
    }
  }

  /**
   * Close WebSocket connection cleanly
   */
  disconnect(): void {
    this.clearConnectionTimeout();

    if (this.ws) {
      // Remove onclose handler to prevent state change
      this.ws.onclose = null;
      this.ws.onerror = null;
      this.ws.onmessage = null;
      this.ws.onopen = null;

      if (this.ws.readyState === WebSocket.OPEN ||
          this.ws.readyState === WebSocket.CONNECTING) {
        this.ws.close(1000, 'Client disconnect');
      }

      this.ws = null;
    }

    this.setState('disconnected');
  }

  /**
   * Manual reconnection
   */
  reconnect(): void {
    this.disconnect();
    this.connect();
  }

  /**
   * Send data through WebSocket
   */
  send(data: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    } else {
      throw new Error('WebSocket is not connected');
    }
  }

  /**
   * Update connection state and notify listeners
   */
  private setState(newState: ConnectionState): void {
    if (this.state !== newState) {
      const oldState = this.state;
      this.state = newState;

      if (process.env.NODE_ENV === 'development') {
        console.log(`[WS] State changed: ${oldState} -> ${newState}`);
      }

      this.stateChangeCallbacks.forEach(callback => callback(newState));
    }
  }

  /**
   * Clear connection timeout
   */
  private clearConnectionTimeout(): void {
    if (this.connectionTimeoutId !== null) {
      clearTimeout(this.connectionTimeoutId);
      this.connectionTimeoutId = null;
    }
  }

  /**
   * Clean up resources
   */
  destroy(): void {
    this.disconnect();
    this.stateChangeCallbacks.clear();
  }
}

/**
 * Create default WebSocket client instance
 * URL will be configured from environment variable or default value
 */
const createDefaultClient = (): WSClient => {
  // Default to localhost for development, configurable via env var
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:3001';

  return new WSClient({
    url: wsUrl,
    connectionTimeout: 10000,
    reconnectOnClose: false, // Will be enabled in US-002 with auto-reconnect
  });
};

/**
 * Export singleton instance
 */
export const wsClient = createDefaultClient();
