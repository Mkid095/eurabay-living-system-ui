/**
 * Cache Statistics Logger
 *
 * Provides logging and monitoring utilities for cache statistics.
 * Can be integrated into monitoring systems or used for debugging.
 */

import { cacheManager } from './cache';
import { CacheStatistics } from './cache';

/**
 * Log level enum
 */
export enum LogLevel {
  ERROR = 0,
  WARN = 1,
  INFO = 2,
  DEBUG = 3,
}

/**
 * Logger configuration
 */
interface LoggerConfig {
  /** Minimum log level to output */
  minLevel: LogLevel;
  /** Whether to include timestamps */
  timestamps: boolean;
  /** Whether to log cache statistics periodically */
  periodicStats: boolean;
  /** Interval for periodic statistics logging (milliseconds) */
  statsInterval: number;
}

/**
 * Default logger configuration
 */
const DEFAULT_CONFIG: LoggerConfig = {
  minLevel: process.env.NODE_ENV === 'development' ? LogLevel.DEBUG : LogLevel.INFO,
  timestamps: true,
  periodicStats: process.env.NODE_ENV === 'development',
  statsInterval: 60000, // 1 minute
};

/**
 * Cache Logger class
 */
export class CacheLogger {
  private config: LoggerConfig;
  private statsInterval: ReturnType<typeof setInterval> | null = null;

  constructor(config: Partial<LoggerConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };

    if (this.config.periodicStats) {
      this.startPeriodicLogging();
    }
  }

  /**
   * Log cache statistics to console
   */
  logStatistics(): void {
    const stats = cacheManager.getStatistics();
    this.log('info', 'Cache Statistics', this.formatStatistics(stats));
  }

  /**
   * Format cache statistics for logging
   */
  private formatStatistics(stats: CacheStatistics): Record<string, string> {
    return {
      'Size': stats.size.toString(),
      'Hits': stats.hits.toString(),
      'Misses': stats.misses.toString(),
      'Hit Rate': `${(stats.hitRate * 100).toFixed(2)}%`,
      'Miss Rate': `${(stats.missRate * 100).toFixed(2)}%`,
      'Total Entries': stats.totalEntries.toString(),
      'Expired Entries': stats.expiredEntries.toString(),
      'Invalidations': stats.invalidations.toString(),
    };
  }

  /**
   * Log a message with specified level
   */
  private log(level: 'error' | 'warn' | 'info' | 'debug', message: string, data?: Record<string, unknown>): void {
    const logLevel = this.levelFromString(level);

    if (logLevel < this.config.minLevel) {
      return;
    }

    const timestamp = this.config.timestamps ? `[${new Date().toISOString()}] ` : '';
    const prefix = `${timestamp}[Cache] [${level.toUpperCase()}]`;
    const dataStr = data ? ` ${JSON.stringify(data)}` : '';

    console[level === 'debug' ? 'debug' : level](`${prefix} ${message}${dataStr}`);
  }

  /**
   * Convert string level to LogLevel enum
   */
  private levelFromString(level: string): LogLevel {
    switch (level) {
      case 'error':
        return LogLevel.ERROR;
      case 'warn':
        return LogLevel.WARN;
      case 'info':
        return LogLevel.INFO;
      case 'debug':
        return LogLevel.DEBUG;
      default:
        return LogLevel.INFO;
    }
  }

  /**
   * Start periodic statistics logging
   */
  private startPeriodicLogging(): void {
    this.statsInterval = setInterval(() => {
      this.logStatistics();
    }, this.config.statsInterval);
  }

  /**
   * Stop periodic statistics logging
   */
  stopPeriodicLogging(): void {
    if (this.statsInterval) {
      clearInterval(this.statsInterval);
      this.statsInterval = null;
    }
  }

  /**
   * Get current cache statistics as an object
   */
  getStatistics(): CacheStatistics {
    return cacheManager.getStatistics();
  }

  /**
   * Get cache statistics as a formatted string
   */
  getStatisticsString(): string {
    const stats = cacheManager.getStatistics();
    const lines: string[] = [
      '=== Cache Statistics ===',
      `Size: ${stats.size}`,
      `Hits: ${stats.hits}`,
      `Misses: ${stats.misses}`,
      `Hit Rate: ${(stats.hitRate * 100).toFixed(2)}%`,
      `Miss Rate: ${(stats.missRate * 100).toFixed(2)}%`,
      `Total Entries: ${stats.totalEntries}`,
      `Expired Entries: ${stats.expiredEntries}`,
      `Invalidations: ${stats.invalidations}`,
      '========================',
    ];
    return lines.join('\n');
  }

  /**
   * Reset cache statistics
   */
  resetStatistics(): void {
    cacheManager.resetStatistics();
    this.log('info', 'Cache statistics reset');
  }

  /**
   * Log cache health check
   */
  logHealthCheck(): void {
    const stats = cacheManager.getStatistics();
    const health = {
      status: 'healthy',
      issues: [] as string[],
    };

    // Check if cache is too large
    if (stats.size > 1000) {
      health.status = 'warning';
      health.issues.push(`Cache size is large: ${stats.size} entries`);
    }

    // Check if hit rate is low
    if (stats.hitRate < 0.5 && stats.hits + stats.misses > 100) {
      health.status = 'warning';
      health.issues.push(`Low hit rate: ${(stats.hitRate * 100).toFixed(2)}%`);
    }

    // Check if expiration rate is high
    if (stats.expiredEntries > stats.totalEntries * 0.5 && stats.totalEntries > 100) {
      health.status = 'warning';
      health.issues.push(`High expiration rate: ${stats.expiredEntries}/${stats.totalEntries}`);
    }

    this.log('info', `Cache health check: ${health.status}`, health.issues.length > 0 ? { issues: health.issues } : undefined);
  }

  /**
   * Destroy logger and cleanup
   */
  destroy(): void {
    this.stopPeriodicLogging();
  }
}

/**
 * Singleton cache logger instance
 */
export const cacheLogger = new CacheLogger();

/**
 * Export cache statistics utilities
 */
export const cacheStats = {
  /**
   * Log current cache statistics to console
   */
  log: (): void => cacheLogger.logStatistics(),

  /**
   * Get cache statistics as an object
   */
  get: (): CacheStatistics => cacheLogger.getStatistics(),

  /**
   * Get cache statistics as a formatted string
   */
  getString: (): string => cacheLogger.getStatisticsString(),

  /**
   * Reset cache statistics
   */
  reset: (): void => cacheLogger.resetStatistics(),

  /**
   * Perform cache health check
   */
  healthCheck: (): void => cacheLogger.logHealthCheck(),

  /**
   * Log cache statistics in development mode
   */
  logIfDev: (): void => {
    if (process.env.NODE_ENV === 'development') {
      cacheLogger.logStatistics();
    }
  },
};
