/**
 * Database Connection Pool Configuration
 *
 * Manages database connections with pooling, retry logic, and metrics tracking.
 * Supports both development (single connection) and production (connection pool) modes.
 */

import { createClient } from '@libsql/client';

/**
 * Connection pool metrics interface
 */
export interface PoolMetrics {
  /** Total number of connections created */
  totalConnections: number;
  /** Number of currently active connections */
  activeConnections: number;
  /** Number of idle connections available */
  idleConnections: number;
  /** Number of connection errors */
  connectionErrors: number;
  /** Number of successful retries */
  successfulRetries: number;
  /** Average connection acquisition time in milliseconds */
  avgAcquisitionTime: number;
}

/**
 * Connection pool configuration interface
 */
export interface PoolConfig {
  /** Maximum number of concurrent connections (default: 10) */
  maxConnections: number;
  /** Connection timeout in milliseconds (default: 30000ms = 30s) */
  connectionTimeout: number;
  /** Maximum number of retry attempts (default: 3) */
  maxRetries: number;
  /** Base delay for retry attempts in milliseconds (default: 1000ms) */
  retryDelay: number;
  /** Whether connection pooling is enabled */
  poolingEnabled: boolean;
  /** Whether to log detailed pool metrics */
  verboseLogging: boolean;
}

/**
 * Default pool configuration
 */
const DEFAULT_POOL_CONFIG: PoolConfig = {
  maxConnections: parseInt(process.env.DB_POOL_MAX || '10', 10),
  connectionTimeout: parseInt(process.env.DB_CONNECTION_TIMEOUT || '30000', 10),
  maxRetries: 3,
  retryDelay: 1000,
  poolingEnabled: process.env.NODE_ENV === 'production',
  verboseLogging: process.env.NODE_ENV === 'development',
};

/**
 * Connection wrapper to track connection state
 */
interface ConnectionWrapper {
  /** The actual libSQL client connection */
  client: ReturnType<typeof createClient>;
  /** Whether this connection is currently in use */
  inUse: boolean;
  /** Timestamp when this connection was created */
  createdAt: number;
  /** Timestamp when this connection was last acquired */
  lastAcquiredAt: number;
  /** Timestamp when this connection was last released */
  lastReleasedAt: number;
}

/**
 * Database Connection Pool Manager
 *
 * Manages a pool of database connections with automatic retry logic,
 * connection timeout handling, and metrics tracking.
 */
export class ConnectionPoolManager {
  private config: PoolConfig;
  private connections: ConnectionWrapper[] = [];
  private metrics: PoolMetrics = {
    totalConnections: 0,
    activeConnections: 0,
    idleConnections: 0,
    connectionErrors: 0,
    successfulRetries: 0,
    avgAcquisitionTime: 0,
  };
  private acquisitionTimes: number[] = [];
  private readonly maxAcquisitionSamples = 100;

  constructor(config: Partial<PoolConfig> = {}) {
    this.config = { ...DEFAULT_POOL_CONFIG, ...config };

    if (this.config.verboseLogging) {
      this.log('info', 'ConnectionPoolManager initialized', {
        maxConnections: this.config.maxConnections,
        connectionTimeout: this.config.connectionTimeout,
        poolingEnabled: this.config.poolingEnabled,
      });
    }

    // Create initial connection for development mode
    if (!this.config.poolingEnabled) {
      this.createInitialConnection();
    }
  }

  /**
   * Create the initial connection (for development mode)
   */
  private createInitialConnection(): void {
    const client = this.createConnectionClient();
    const wrapper: ConnectionWrapper = {
      client,
      inUse: false,
      createdAt: Date.now(),
      lastAcquiredAt: 0,
      lastReleasedAt: 0,
    };
    this.connections.push(wrapper);
    this.metrics.totalConnections++;
    this.metrics.idleConnections++;

    if (this.config.verboseLogging) {
      this.log('info', 'Initial connection created for development mode');
    }
  }

  /**
   * Create a new libSQL client connection
   */
  private createConnectionClient(): ReturnType<typeof createClient> {
    const databaseUrl = process.env.TURSO_DATABASE_URL || 'file:.local/db.sqlite';
    const clientConfig: { url: string; authToken?: string } = { url: databaseUrl };

    // Add auth token for production (Turso)
    if (process.env.TURSO_AUTH_TOKEN) {
      clientConfig.authToken = process.env.TURSO_AUTH_TOKEN;
    }

    return createClient(clientConfig);
  }

  /**
   * Acquire a connection from the pool
   * Returns a connection client that must be released back to the pool
   */
  async acquire(): Promise<ReturnType<typeof createClient>> {
    const startTime = Date.now();

    // In development mode (no pooling), return the single connection
    if (!this.config.poolingEnabled) {
      if (this.connections.length === 0) {
        this.createInitialConnection();
      }
      const wrapper = this.connections[0];

      // Wait if connection is in use
      if (wrapper.inUse) {
        await this.waitForConnectionRelease(wrapper);
      }

      wrapper.inUse = true;
      wrapper.lastAcquiredAt = Date.now();

      this.updateMetrics(startTime);
      return wrapper.client;
    }

    // Production mode with connection pooling
    // Try to find an idle connection
    let wrapper = this.connections.find(w => !w.inUse);

    if (!wrapper) {
      // No idle connections available
      if (this.connections.length < this.config.maxConnections) {
        // Create a new connection if under max limit
        wrapper = this.createConnection();
      } else {
        // Wait for an existing connection to become available
        wrapper = await this.waitForAvailableConnection();
      }
    }

    wrapper.inUse = true;
    wrapper.lastAcquiredAt = Date.now();

    this.updateMetrics(startTime);

    if (this.config.verboseLogging) {
      this.log('debug', 'Connection acquired', {
        activeConnections: this.metrics.activeConnections,
        idleConnections: this.metrics.idleConnections,
      });
    }

    return wrapper.client;
  }

  /**
   * Create a new connection and add it to the pool
   */
  private createConnection(): ConnectionWrapper {
    const client = this.createConnectionClient();
    const wrapper: ConnectionWrapper = {
      client,
      inUse: false,
      createdAt: Date.now(),
      lastAcquiredAt: 0,
      lastReleasedAt: 0,
    };
    this.connections.push(wrapper);
    this.metrics.totalConnections++;

    if (this.config.verboseLogging) {
      this.log('info', 'New connection added to pool', {
        totalConnections: this.connections.length,
        maxConnections: this.config.maxConnections,
      });
    }

    return wrapper;
  }

  /**
   * Wait for a connection to be released with timeout
   */
  private async waitForConnectionRelease(wrapper: ConnectionWrapper): Promise<void> {
    const timeout = this.config.connectionTimeout;
    const startTime = Date.now();

    return new Promise((resolve, reject) => {
      const checkInterval = setInterval(() => {
        if (!wrapper.inUse) {
          clearInterval(checkInterval);
          resolve();
          return;
        }

        if (Date.now() - startTime > timeout) {
          clearInterval(checkInterval);
          reject(new Error(`Connection acquisition timeout after ${timeout}ms`));
          return;
        }
      }, 50);
    });
  }

  /**
   * Wait for any connection to become available with timeout
   */
  private async waitForAvailableConnection(): Promise<ConnectionWrapper> {
    const timeout = this.config.connectionTimeout;
    const startTime = Date.now();

    return new Promise((resolve, reject) => {
      const checkInterval = setInterval(() => {
        const wrapper = this.connections.find(w => !w.inUse);
        if (wrapper) {
          clearInterval(checkInterval);
          resolve(wrapper);
          return;
        }

        if (Date.now() - startTime > timeout) {
          clearInterval(checkInterval);
          reject(new Error(`Connection pool exhausted - timeout after ${timeout}ms`));
          return;
        }
      }, 50);
    });
  }

  /**
   * Release a connection back to the pool
   */
  release(client: ReturnType<typeof createClient>): void {
    const wrapper = this.connections.find(w => w.client === client);
    if (!wrapper) {
      this.log('warn', 'Attempted to release unknown connection');
      return;
    }

    wrapper.inUse = false;
    wrapper.lastReleasedAt = Date.now();

    this.updateMetrics();

    if (this.config.verboseLogging) {
      this.log('debug', 'Connection released', {
        activeConnections: this.metrics.activeConnections,
        idleConnections: this.metrics.idleConnections,
      });
    }
  }

  /**
   * Execute a callback with automatic connection management and retry logic
   * This is the preferred way to use the connection pool
   */
  async execute<T>(
    callback: (client: ReturnType<typeof createClient>) => Promise<T>
  ): Promise<T> {
    let lastError: Error | undefined;
    let attempt = 0;

    while (attempt <= this.config.maxRetries) {
      try {
        const client = await this.acquire();

        try {
          const result = await callback(client);
          return result;
        } finally {
          this.release(client);
        }
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        // Don't retry on certain errors
        if (this.shouldNotRetry(lastError)) {
          this.metrics.connectionErrors++;
          throw lastError;
        }

        attempt++;

        if (attempt <= this.config.maxRetries) {
          const delay = this.config.retryDelay * attempt; // Exponential backoff

          if (this.config.verboseLogging) {
            this.log('warn', `Connection error, retrying... (attempt ${attempt}/${this.config.maxRetries})`, {
              error: lastError.message,
              delay: `${delay}ms`,
            });
          }

          await this.sleep(delay);
        } else {
          this.metrics.connectionErrors++;
          this.log('error', 'Connection error after all retries', {
            error: lastError.message,
            attempts: attempt,
          });
        }
      }
    }

    throw lastError;
  }

  /**
   * Determine if an error should not be retried
   */
  private shouldNotRetry(error: Error): boolean {
    const noRetryMessages = [
      'authentication failed',
      'unauthorized',
      'forbidden',
      'not found',
      'validation error',
      'syntax error',
    ];

    const lowerMessage = error.message.toLowerCase();
    return noRetryMessages.some(msg => lowerMessage.includes(msg));
  }

  /**
   * Sleep for a specified number of milliseconds
   */
  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Update pool metrics
   */
  private updateMetrics(acquisitionStartTime?: number): void {
    const active = this.connections.filter(w => w.inUse).length;
    const idle = this.connections.length - active;

    this.metrics.activeConnections = active;
    this.metrics.idleConnections = idle;

    if (acquisitionStartTime) {
      const acquisitionTime = Date.now() - acquisitionStartTime;
      this.acquisitionTimes.push(acquisitionTime);

      // Keep only the most recent samples
      if (this.acquisitionTimes.length > this.maxAcquisitionSamples) {
        this.acquisitionTimes.shift();
      }

      // Calculate average
      const sum = this.acquisitionTimes.reduce((a, b) => a + b, 0);
      this.metrics.avgAcquisitionTime = sum / this.acquisitionTimes.length;
    }
  }

  /**
   * Get current pool metrics
   */
  getMetrics(): PoolMetrics {
    return { ...this.metrics };
  }

  /**
   * Get pool configuration
   */
  getConfig(): PoolConfig {
    return { ...this.config };
  }

  /**
   * Log a message with pool context
   */
  private log(level: 'info' | 'warn' | 'error' | 'debug', message: string, data?: Record<string, unknown>): void {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [ConnectionPool] [${level.toUpperCase()}]`;
    const dataStr = data ? ` ${JSON.stringify(data)}` : '';
    console[level === 'debug' ? 'debug' : level](`${prefix} ${message}${dataStr}`);
  }

  /**
   * Close all connections in the pool
   */
  async closeAll(): Promise<void> {
    this.log('info', 'Closing all connections in pool');

    // libSQL client doesn't have an explicit close method
    // We just clear our references
    this.connections = [];
    this.metrics = {
      totalConnections: 0,
      activeConnections: 0,
      idleConnections: 0,
      connectionErrors: 0,
      successfulRetries: 0,
      avgAcquisitionTime: 0,
    };
    this.acquisitionTimes = [];

    this.log('info', 'All connections closed');
  }

  /**
   * Log current pool status
   */
  logStatus(): void {
    const metrics = this.getMetrics();
    const config = this.getConfig();

    this.log('info', 'Connection Pool Status', {
      config: {
        maxConnections: config.maxConnections,
        connectionTimeout: config.connectionTimeout,
        maxRetries: config.maxRetries,
        poolingEnabled: config.poolingEnabled,
      },
      metrics: {
        totalConnections: metrics.totalConnections,
        activeConnections: metrics.activeConnections,
        idleConnections: metrics.idleConnections,
        connectionErrors: metrics.connectionErrors,
        avgAcquisitionTime: `${metrics.avgAcquisitionTime.toFixed(2)}ms`,
      },
    });
  }
}

/**
 * Singleton instance of the connection pool manager
 */
export const connectionPool = new ConnectionPoolManager();

/**
 * Export the pool manager class for testing or custom instances
 */
export { ConnectionPoolManager };
