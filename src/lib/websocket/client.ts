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
  enableAutoReconnect?: boolean;
  maxReconnectAttempts?: number;
  initialReconnectDelay?: number;
  maxReconnectDelay?: number;
  pingInterval?: number;
  pongTimeout?: number;
}

/**
 * WebSocket Client for managing real-time connections
 */
export class WSClient {
  private ws: WebSocket | null = null;
  private state: ConnectionState = 'disconnected';
  private connectionAttemptCount: number = 0;
  private reconnectAttemptCount: number = 0;
  private connectionTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private reconnectTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private pingIntervalId: ReturnType<typeof setInterval> | null = null;
  private pongTimeoutId: ReturnType<typeof setTimeout> | null = null;
  private config: Required<WSClientConfig>;
  private stateChangeCallbacks: Set<(state: ConnectionState) => void> = new Set();
  private manuallyDisconnected: boolean = false;

  constructor(config: WSClientConfig) {
    this.config = {
      url: config.url,
      connectionTimeout: config.connectionTimeout ?? 10000,
      reconnectOnClose: config.reconnectOnClose ?? false,
      enableAutoReconnect: config.enableAutoReconnect ?? true,
      maxReconnectAttempts: config.maxReconnectAttempts ?? Number.POSITIVE_INFINITY,
      initialReconnectDelay: config.initialReconnectDelay ?? 1000,
      maxReconnectDelay: config.maxReconnectDelay ?? 30000,
      pingInterval: config.pingInterval ?? 30000, // Send ping every 30 seconds
      pongTimeout: config.pongTimeout ?? 60000, // Expect pong within 60 seconds
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
   * Get reconnect attempt count
   */
  getReconnectAttemptCount(): number {
    return this.reconnectAttemptCount;
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

    // Clear any pending reconnect timer when manually connecting
    this.clearReconnectTimer();
    this.manuallyDisconnected = false;

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
        this.clearReconnectTimer();
        this.reconnectAttemptCount = 0; // Reset reconnect count on successful connection
        this.startPingInterval();
        this.setState('connected');
      };

      // Connection closed
      this.ws.onclose = (event: CloseEvent) => {
        this.clearConnectionTimeout();

        if (this.state !== 'disconnected' && !this.manuallyDisconnected) {
          // Trigger auto-reconnect if enabled and connection was lost
          if (this.config.enableAutoReconnect) {
            this.setState('error');
            this.scheduleReconnect();
          } else {
            this.setState('disconnected');
          }
        } else {
          this.setState('disconnected');
        }
      };

      // Connection error
      this.ws.onerror = (error: Event) => {
        this.clearConnectionTimeout();
        this.setState('error');
      };

      // Message received
      this.ws.onmessage = (event: MessageEvent) => {
        this.handleMessage(event.data);
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
    this.clearReconnectTimer();
    this.clearPingInterval();
    this.clearPongTimeout();
    this.manuallyDisconnected = true;

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
   * Handle incoming WebSocket message
   */
  private handleMessage(data: string): void {
    if (process.env.NODE_ENV === 'development') {
      console.log('[WS] Raw message received:', data);
    }

    try {
      const message = JSON.parse(data);

      // Handle pong response
      if (message.type === 'pong') {
        this.handlePong();
        return;
      }

      // Other event handling will be added in US-006
    } catch (error) {
      // Ignore non-JSON messages
    }
  }

  /**
   * Start ping interval
   */
  private startPingInterval(): void {
    this.clearPingInterval();

    this.pingIntervalId = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.sendPing();
      }
    }, this.config.pingInterval);
  }

  /**
   * Clear ping interval
   */
  private clearPingInterval(): void {
    if (this.pingIntervalId !== null) {
      clearInterval(this.pingIntervalId);
      this.pingIntervalId = null;
    }
  }

  /**
   * Send ping message to server
   */
  private sendPing(): void {
    const pingMessage = JSON.stringify({ type: 'ping', timestamp: Date.now() });

    try {
      this.ws?.send(pingMessage);

      if (process.env.NODE_ENV === 'development') {
        console.log('[WS] Ping sent');
      }

      // Start waiting for pong response
      this.startPongTimeout();
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[WS] Failed to send ping:', error);
      }
    }
  }

  /**
   * Start pong timeout
   */
  private startPongTimeout(): void {
    this.clearPongTimeout();

    this.pongTimeoutId = setTimeout(() => {
      if (process.env.NODE_ENV === 'development') {
        console.error('[WS] Pong timeout - closing connection and reconnecting');
      }

      // Close connection to trigger reconnect
      if (this.ws) {
        this.ws.close(1000, 'Pong timeout');
      }
    }, this.config.pongTimeout);
  }

  /**
   * Clear pong timeout
   */
  private clearPongTimeout(): void {
    if (this.pongTimeoutId !== null) {
      clearTimeout(this.pongTimeoutId);
      this.pongTimeoutId = null;
    }
  }

  /**
   * Handle pong response from server
   */
  private handlePong(): void {
    this.clearPongTimeout();

    if (process.env.NODE_ENV === 'development') {
      console.log('[WS] Pong received');
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
    this.clearPingInterval();
    this.clearPongTimeout();
    this.stateChangeCallbacks.clear();
  }

  /**
   * Calculate exponential backoff delay
   */
  private calculateReconnectDelay(): number {
    // Calculate exponential backoff: 1s, 2s, 4s, 8s, 16s, 32s...
    const exponentialDelay = this.config.initialReconnectDelay * Math.pow(2, this.reconnectAttemptCount);

    // Cap at max reconnect delay (default 30s)
    return Math.min(exponentialDelay, this.config.maxReconnectDelay);
  }

  /**
   * Schedule reconnect with exponential backoff
   */
  private scheduleReconnect(): void {
    // Check if we've exceeded max reconnect attempts
    if (this.reconnectAttemptCount >= this.config.maxReconnectAttempts) {
      if (process.env.NODE_ENV === 'development') {
        console.error(
          `[WS] Max reconnect attempts (${this.config.maxReconnectAttempts}) reached. Stopping auto-reconnect.`
        );
      }
      this.setState('disconnected');
      return;
    }

    // Calculate delay using exponential backoff
    const delay = this.calculateReconnectDelay();
    this.reconnectAttemptCount++;

    const timestamp = new Date().toISOString();
    if (process.env.NODE_ENV === 'development') {
      console.log(
        `[WS] Scheduling reconnect attempt ${this.reconnectAttemptCount}/${this.config.maxReconnectAttempts} in ${delay}ms (${timestamp})`
      );
    }

    this.reconnectTimeoutId = setTimeout(() => {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[WS] Executing reconnect attempt ${this.reconnectAttemptCount}`);
      }
      this.connect();
    }, delay);
  }

  /**
   * Clear reconnect timer
   */
  private clearReconnectTimer(): void {
    if (this.reconnectTimeoutId !== null) {
      clearTimeout(this.reconnectTimeoutId);
      this.reconnectTimeoutId = null;
    }
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
    reconnectOnClose: false,
    enableAutoReconnect: true,
    maxReconnectAttempts: Number.POSITIVE_INFINITY, // Infinite reconnect attempts
    initialReconnectDelay: 1000, // Start with 1 second
    maxReconnectDelay: 30000, // Max 30 seconds
    pingInterval: 30000, // Send ping every 30 seconds
    pongTimeout: 60000, // Expect pong within 60 seconds
  });
};

/**
 * Export singleton instance
 */
export const wsClient = createDefaultClient();
