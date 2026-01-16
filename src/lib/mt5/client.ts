/**
 * MT5 Client
 *
 * Manages MetaTrader 5 terminal connection, health monitoring,
 * and connection state tracking.
 */

import { apiClient } from '@/lib/api/client';

/**
 * MT5 connection states
 */
export type MT5ConnectionState = 'connected' | 'disconnected' | 'error' | 'connecting';

/**
 * MT5 connection information
 */
export interface MT5ConnectionInfo {
  connected: boolean;
  accountNumber?: string;
  company?: string;
  server?: string;
  terminalPath?: string;
  lastHeartbeat?: string;
  latency?: number;
}

/**
 * MT5 account information
 */
export interface MT5AccountInfo {
  login: number;
  company: string;
  currency: string;
  balance: number;
  equity: number;
  margin: number;
  freeMargin: number;
  marginLevel: number;
  leverage: number;
}

/**
 * Connection state change listener
 */
type StateChangeListener = (state: MT5ConnectionState) => void;

/**
 * MT5 Client class for managing terminal connections
 */
export class MT5Client {
  private state: MT5ConnectionState = 'disconnected';
  private connectionInfo: MT5ConnectionInfo | null = null;
  private accountInfo: MT5AccountInfo | null = null;
  private connectionAttempts: number = 0;
  private healthCheckInterval: ReturnType<typeof setInterval> | null = null;
  private stateChangeListeners: Set<StateChangeListener> = new Set();

  /**
   * Get current connection state
   */
  getState(): MT5ConnectionState {
    return this.state;
  }

  /**
   * Get connection information
   */
  getConnectionInfo(): MT5ConnectionInfo | null {
    return this.connectionInfo;
  }

  /**
   * Get account information
   */
  getAccountInfo(): MT5AccountInfo | null {
    return this.accountInfo;
  }

  /**
   * Get connection attempt count
   */
  getConnectionAttempts(): number {
    return this.connectionAttempts;
  }

  /**
   * Subscribe to connection state changes
   * Returns unsubscribe function
   */
  onStateChange(listener: StateChangeListener): () => void {
    this.stateChangeListeners.add(listener);
    return () => {
      this.stateChangeListeners.delete(listener);
    };
  }

  /**
   * Update connection state and notify listeners
   */
  private setState(newState: MT5ConnectionState): void {
    if (this.state !== newState) {
      const oldState = this.state;
      this.state = newState;
      console.log(`[MT5Client] Connection state changed: ${oldState} -> ${newState}`);

      // Notify all listeners
      this.stateChangeListeners.forEach((listener) => {
        listener(newState);
      });
    }
  }

  /**
   * Connect to MT5 terminal
   */
  async connect(): Promise<MT5ConnectionInfo> {
    this.setState('connecting');
    this.connectionAttempts++;

    console.log(`[MT5Client] Connection attempt ${this.connectionAttempts}`);

    try {
      const response = await apiClient.post<{ connectionInfo: MT5ConnectionInfo; accountInfo: MT5AccountInfo }>(
        'mt5/connect',
        {}
      );

      if (!response.data?.connectionInfo) {
        throw new Error('Invalid connection response from server');
      }

      this.connectionInfo = response.data.connectionInfo;
      this.accountInfo = response.data.accountInfo || null;
      this.setState('connected');

      // Start health check
      this.startHealthCheck();

      console.log('[MT5Client] Connected successfully', {
        account: this.connectionInfo.accountNumber,
        server: this.connectionInfo.server,
      });

      return this.connectionInfo;
    } catch (error) {
      this.setState('error');
      const errorMessage = error instanceof Error ? error.message : 'Unknown connection error';
      console.error('[MT5Client] Connection failed:', errorMessage);
      throw error;
    }
  }

  /**
   * Disconnect from MT5 terminal
   */
  async disconnect(): Promise<void> {
    console.log('[MT5Client] Disconnecting...');

    try {
      await apiClient.post('mt5/disconnect', {});
    } catch (error) {
      console.error('[MT5Client] Disconnect error:', error);
    } finally {
      this.connectionInfo = null;
      this.accountInfo = null;
      this.setState('disconnected');
      this.stopHealthCheck();
      console.log('[MT5Client] Disconnected');
    }
  }

  /**
   * Check if connected to MT5
   */
  async isConnected(): Promise<boolean> {
    try {
      const response = await apiClient.get<{ connected: boolean }>('mt5/status');
      const connected = response.data?.connected ?? false;

      if (connected && this.state === 'disconnected') {
        this.setState('connected');
      } else if (!connected && this.state === 'connected') {
        this.setState('error');
      }

      return connected;
    } catch (error) {
      console.error('[MT5Client] Status check failed:', error);
      this.setState('error');
      return false;
    }
  }

  /**
   * Perform health check with ping
   */
  async healthCheck(): Promise<{ success: boolean; latency?: number }> {
    const startTime = Date.now();

    try {
      const response = await apiClient.get<{ connected: boolean; latency?: number }>('mt5/status');
      const success = response.data?.connected ?? false;

      if (!success) {
        this.setState('error');
      }

      const latency = response.data?.latency ?? (Date.now() - startTime);

      return { success, latency };
    } catch (error) {
      console.error('[MT5Client] Health check failed:', error);
      this.setState('error');
      return { success: false };
    }
  }

  /**
   * Start periodic health checks (every 30 seconds)
   */
  private startHealthCheck(): void {
    this.stopHealthCheck();

    this.healthCheckInterval = setInterval(async () => {
      if (this.state === 'connected') {
        await this.healthCheck();
      }
    }, 30000);

    console.log('[MT5Client] Health check started (30s interval)');
  }

  /**
   * Stop periodic health checks
   */
  private stopHealthCheck(): void {
    if (this.healthCheckInterval) {
      clearInterval(this.healthCheckInterval);
      this.healthCheckInterval = null;
      console.log('[MT5Client] Health check stopped');
    }
  }

  /**
   * Reset connection attempt counter
   */
  resetConnectionAttempts(): void {
    this.connectionAttempts = 0;
    console.log('[MT5Client] Connection attempts reset');
  }
}

/**
 * Global MT5 client instance
 */
export const mt5Client = new MT5Client();
