import { WSEvent } from './events';
import { EventSchemaMap } from './schemas';
import { z } from 'zod';

/**
 * WebSocket Connection States
 */
export type ConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'error';

/**
 * WebSocket Authentication Configuration
 */
export interface WSAuthConfig {
  getToken: () => string | null;
  onTokenRefresh?: () => Promise<string | null>;
  onAuthFailure?: () => void;
}

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
  auth?: WSAuthConfig;
}

/**
 * WebSocket Event Handler Type
 */
export type WSEventHandler<T = unknown> = (data: T, event: WSEvent<T>) => void;

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
  private authFailureCallbacks: Set<() => void> = new Set();
  private currentToken: string | null = null;
  private tokenRefreshInProgress: boolean = false;
  private eventHandlers: Map<string, Set<WSEventHandler>> = new Map();
  private lastPingTime: number = 0;
  private currentLatency: number | null = null;
  private latencyChangeCallbacks: Set<(latency: number | null) => void> = new Set();

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
      auth: config.auth ?? {
        getToken: () => localStorage.getItem('auth_token'),
      },
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
   * Subscribe to authentication failure events
   */
  onAuthFailure(callback: () => void): () => void {
    this.authFailureCallbacks.add(callback);
    return () => this.authFailureCallbacks.delete(callback);
  }

  /**
   * Subscribe to latency changes
   */
  onLatencyChange(callback: (latency: number | null) => void): () => void {
    this.latencyChangeCallbacks.add(callback);
    return () => this.latencyChangeCallbacks.delete(callback);
  }

  /**
   * Get current latency in milliseconds
   */
  getLatency(): number | null {
    return this.currentLatency;
  }

  /**
   * Register an event handler for a specific event type
   * @param event - The event type to listen for
   * @param handler - The callback function to execute when the event is received
   * @returns Unsubscribe function to remove the handler
   */
  on<T = unknown>(event: string, handler: WSEventHandler<T>): () => void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler as WSEventHandler);

    if (process.env.NODE_ENV === 'development') {
      console.log(`[WS] Registered handler for event: ${event}`);
    }

    return () => this.off(event, handler as WSEventHandler);
  }

  /**
   * Unregister an event handler for a specific event type
   * @param event - The event type
   * @param handler - The callback function to remove
   */
  off<T = unknown>(event: string, handler: WSEventHandler<T>): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.delete(handler as WSEventHandler);

      if (handlers.size === 0) {
        this.eventHandlers.delete(event);
      }

      if (process.env.NODE_ENV === 'development') {
        console.log(`[WS] Unregistered handler for event: ${event}`);
      }
    }
  }

  /**
   * Emit an event to the server
   * @param event - The event type to send
   * @param data - The data payload to send
   */
  emit<T = unknown>(event: string, data: T): void {
    const message: WSEvent<T> = {
      event: event as any,
      data,
      timestamp: Date.now(),
    };

    const jsonString = JSON.stringify(message);

    try {
      this.send(jsonString);

      if (process.env.NODE_ENV === 'development') {
        console.log(`[WS] Emitting event: ${event}`, data);
      }
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error(`[WS] Failed to emit event: ${event}`, error);
      }
      throw error;
    }
  }

  /**
   * Clear auth token (called on logout)
   */
  clearAuthToken(): void {
    this.currentToken = null;
    localStorage.removeItem('auth_token');
    this.disconnect();

    if (process.env.NODE_ENV === 'development') {
      console.log('[WS] Auth token cleared');
    }
  }

  /**
   * Get WebSocket URL with auth token
   */
  private getAuthUrl(): string {
    const token = this.config.auth.getToken();
    this.currentToken = token;

    if (!token) {
      return this.config.url;
    }

    // Add token as query parameter
    const url = new URL(this.config.url);
    url.searchParams.set('token', token);
    return url.toString();
  }

  /**
   * Handle authentication failure
   */
  private handleAuthFailure(reason: string): void {
    if (process.env.NODE_ENV === 'development') {
      console.error(`[WS] Authentication failed: ${reason}`);
    }

    // Notify all auth failure callbacks
    this.authFailureCallbacks.forEach(callback => {
      try {
        callback();
      } catch (error) {
        console.error('[WS] Error in auth failure callback:', error);
      }
    });

    // Call configured auth failure handler
    if (this.config.auth.onAuthFailure) {
      try {
        this.config.auth.onAuthFailure();
      } catch (error) {
        console.error('[WS] Error in configured auth failure handler:', error);
      }
    }

    // Disconnect and don't auto-reconnect on auth failure
    this.manuallyDisconnected = true;
    this.disconnect();
  }

  /**
   * Attempt to refresh auth token and reconnect
   */
  private async attemptTokenRefresh(): Promise<boolean> {
    if (!this.config.auth.onTokenRefresh || this.tokenRefreshInProgress) {
      return false;
    }

    this.tokenRefreshInProgress = true;

    try {
      if (process.env.NODE_ENV === 'development') {
        console.log('[WS] Attempting token refresh');
      }

      const newToken = await this.config.auth.onTokenRefresh();

      if (newToken) {
        this.currentToken = newToken;

        if (process.env.NODE_ENV === 'development') {
          console.log('[WS] Token refreshed successfully');
        }

        return true;
      }

      return false;
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[WS] Token refresh failed:', error);
      }
      return false;
    } finally {
      this.tokenRefreshInProgress = false;
    }
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
      const wsUrl = this.getAuthUrl();
      this.ws = new WebSocket(wsUrl);

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
        this.setLatency(null); // Reset latency on new connection
      };

      // Connection closed
      this.ws.onclose = (event: CloseEvent) => {
        this.clearConnectionTimeout();

        // Check for authentication-related close codes
        // 4008: Authentication timeout
        // 4003: Invalid token or authentication failed
        if (event.code === 4003 || event.code === 4008) {
          this.handleAuthFailure(`Authentication failed with close code: ${event.code} (${event.reason})`);
          return;
        }

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

      // Handle authentication failure
      if (message.type === 'auth_error' || message.type === 'authentication_failed') {
        this.handleAuthFailure(message.reason || 'Server rejected authentication');
        return;
      }

      // Handle token expiry
      if (message.type === 'token_expired') {
        this.handleTokenExpired();
        return;
      }

      // Handle pong response
      if (message.type === 'pong') {
        this.handlePong();
        return;
      }

      // Dispatch to event handlers for all other messages
      this.dispatchMessage(message);
    } catch (error) {
      if (process.env.NODE_ENV === 'development') {
        console.error('[WS] Failed to parse message:', error);
      }
    }
  }

  /**
   * Dispatch incoming message to appropriate event handlers
   * Validates messages using Zod schemas before dispatching
   */
  private dispatchMessage(message: unknown): void {
    // Validate message has event property
    if (!message || typeof message !== 'object') {
      if (process.env.NODE_ENV === 'development') {
        console.warn('[WS] Received invalid message format (not an object):', message);
      }
      return;
    }

    const msg = message as Record<string, unknown>;
    const eventType = msg.event;

    if (!eventType || typeof eventType !== 'string') {
      if (process.env.NODE_ENV === 'development') {
        console.warn('[WS] Received message without valid event type:', message);
      }
      return;
    }

    // Get the schema for this event type
    const schema = EventSchemaMap[eventType as keyof typeof EventSchemaMap];

    // Validate the event data if a schema exists
    if (schema) {
      const validationResult = schema.safeParse(msg.data);

      if (!validationResult.success) {
        // Log validation errors with full message details
        if (process.env.NODE_ENV === 'development') {
          console.warn(
            `[WS] Validation failed for event '${eventType}':`,
            {
              errors: validationResult.error.issues,
              data: msg.data,
              fullMessage: message,
            }
          );
        }
        // Discard invalid messages
        return;
      }

      // Use the validated data (with safe defaults applied)
      msg.data = validationResult.data;
    } else {
      // No schema exists for this event type - handle gracefully
      if (process.env.NODE_ENV === 'development') {
        console.log(`[WS] No validation schema for event type: ${eventType}, using raw data`);
      }
    }

    // Construct WSEvent object
    const wsEvent: WSEvent = {
      event: eventType as any,
      data: msg.data,
      timestamp: typeof msg.timestamp === 'number' ? msg.timestamp : Date.now(),
      correlationId: typeof msg.correlationId === 'string' ? msg.correlationId : undefined,
    };

    // Get handlers for this event type
    const handlers = this.eventHandlers.get(eventType);

    if (handlers && handlers.size > 0) {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[WS] Dispatching event '${eventType}' to ${handlers.size} handler(s)`);
      }

      handlers.forEach(handler => {
        try {
          handler(wsEvent.data, wsEvent);
        } catch (error) {
          if (process.env.NODE_ENV === 'development') {
            console.error(`[WS] Error in handler for event '${eventType}':`, error);
          }
        }
      });
    } else {
      if (process.env.NODE_ENV === 'development') {
        console.log(`[WS] No handlers registered for event: ${eventType}`);
      }
    }
  }

  /**
   * Handle token expiry message from server
   */
  private async handleTokenExpired(): Promise<void> {
    if (process.env.NODE_ENV === 'development') {
      console.log('[WS] Token expired, attempting refresh');
    }

    const refreshed = await this.attemptTokenRefresh();

    if (refreshed) {
      // Reconnect with new token
      this.reconnect();
    } else {
      // Token refresh failed, handle auth failure
      this.handleAuthFailure('Token expired and refresh failed');
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
    this.lastPingTime = Date.now();
    const pingMessage = JSON.stringify({ type: 'ping', timestamp: this.lastPingTime });

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

    // Calculate latency
    if (this.lastPingTime > 0) {
      const newLatency = Date.now() - this.lastPingTime;
      this.setLatency(newLatency);
    }

    if (process.env.NODE_ENV === 'development') {
      console.log('[WS] Pong received');
    }
  }

  /**
   * Update latency and notify listeners
   */
  private setLatency(latency: number | null): void {
    if (this.currentLatency !== latency) {
      this.currentLatency = latency;
      this.latencyChangeCallbacks.forEach(callback => {
        try {
          callback(latency);
        } catch (error) {
          console.error('[WS] Error in latency change callback:', error);
        }
      });
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
    this.eventHandlers.clear();
    this.latencyChangeCallbacks.clear();
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

      // Notify recovery manager about reconnection failure
      // Import dynamically to avoid circular dependencies
      import('./recovery').then(({ recoveryManager }) => {
        if (recoveryManager && (recoveryManager as any).handleReconnectionFailure) {
          (recoveryManager as any).handleReconnectionFailure();
        }
      });

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

    // Notify recovery manager about reconnection start
    // Import dynamically to avoid circular dependencies
    import('./recovery').then(({ recoveryManager }) => {
      if (recoveryManager && (recoveryManager as any).startReconnection) {
        (recoveryManager as any).startReconnection(this.reconnectAttemptCount, delay);
      }
    });

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
  // Check if WebSocket is disabled (for frontend-only testing)
  const wsDisabled = process.env.NEXT_PUBLIC_WS_DISABLED === 'true';

  if (wsDisabled) {
    if (process.env.NODE_ENV === 'development') {
      console.log('[WS] WebSocket is disabled via NEXT_PUBLIC_WS_DISABLED=true');
    }

    // Create client with invalid URL to prevent connection attempts
    return new WSClient({
      url: 'ws://disabled',
      connectionTimeout: 1000,
      reconnectOnClose: false,
      enableAutoReconnect: false, // Disable auto-reconnect when WS is disabled
      maxReconnectAttempts: 0,
      initialReconnectDelay: 1000,
      maxReconnectDelay: 30000,
      pingInterval: 30000,
      pongTimeout: 60000,
    });
  }

  // Default to localhost for development, configurable via env var
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';

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
