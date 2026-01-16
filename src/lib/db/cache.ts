/**
 * Database Cache Layer
 *
 * In-memory caching layer for frequently accessed data to reduce database load
 * and improve performance. Supports TTL-based expiration, cache invalidation,
 * warming, and statistics tracking.
 */

/**
 * Cache entry with value and expiration metadata
 */
interface CacheEntry<T = unknown> {
  /** Cached value */
  value: T;
  /** Expiration timestamp (milliseconds since epoch) */
  expiresAt: number;
  /** Time-to-live in seconds */
  ttl: number;
  /** Timestamp when this entry was created */
  createdAt: number;
  /** Timestamp when this entry was last accessed */
  lastAccessedAt: number;
  /** Number of times this entry has been accessed */
  accessCount: number;
}

/**
 * Cache statistics interface
 */
export interface CacheStatistics {
  /** Total number of cache hits */
  hits: number;
  /** Total number of cache misses */
  misses: number;
  /** Total number of entries currently in cache */
  size: number;
  /** Cache hit rate (0-1) */
  hitRate: number;
  /** Cache miss rate (0-1) */
  missRate: number;
  /** Total number of entries ever stored */
  totalEntries: number;
  /** Number of expired entries removed */
  expiredEntries: number;
  /** Number of manual invalidations */
  invalidations: number;
}

/**
 * Cache key patterns for different data types
 */
export const CacheKeys = {
  /** User session keys: user:session:{userId} */
  USER_SESSION: (userId: string) => `user:session:${userId}`,
  /** User by ID keys: user:id:{userId} */
  USER_ID: (userId: string) => `user:id:${userId}`,
  /** User by email keys: user:email:{email} */
  USER_EMAIL: (email: string) => `user:email:${email}`,
  /** System configuration keys: config:{configKey} */
  CONFIG: (key: string) => `config:${key}`,
  /** Active trades keys: trades:active */
  TRADES_ACTIVE: 'trades:active',
  /** Trades by symbol: trades:symbol:{symbol} */
  TRADES_SYMBOL: (symbol: string) => `trades:symbol:${symbol}`,
  /** Recent trades keys: trades:recent:{limit} */
  TRADES_RECENT: (limit: number) => `trades:recent:${limit}`,
  /** Evolution metrics keys: evolution:metrics */
  EVOLUTION_METRICS: 'evolution:metrics',
  /** Evolution generation: evolution:generation:{generationNumber} */
  EVOLUTION_GENERATION: (generationNumber: number) => `evolution:generation:${generationNumber}`,
  /** Evolution features: evolution:features */
  EVOLUTION_FEATURES: 'evolution:features',
  /** Evolution stats: evolution:stats */
  EVOLUTION_STATS: 'evolution:stats',
  /** Pending signals keys: signals:pending */
  SIGNALS_PENDING: 'signals:pending',
  /** System logs keys: logs:recent:{limit} */
  LOGS_RECENT: (limit: number) => `logs:recent:${limit}`,
} as const;

/**
 * Default TTL values for different cache types (in seconds)
 */
export const CacheTTL = {
  /** User sessions: 5 minutes */
  USER_SESSION: 5 * 60,
  /** User data: 5 minutes */
  USER_DATA: 5 * 60,
  /** System configuration: 10 minutes */
  CONFIG: 10 * 60,
  /** Active trades: 30 seconds */
  ACTIVE_TRADES: 30,
  /** Trade queries: 1 minute */
  TRADE_QUERY: 60,
  /** Evolution metrics: 1 minute */
  EVOLUTION_METRICS: 60,
  /** Evolution data: 2 minutes */
  EVOLUTION_DATA: 2 * 60,
  /** Signals: 30 seconds */
  SIGNALS: 30,
  /** System logs: 2 minutes */
  LOGS: 2 * 60,
} as const;

/**
 * Cache Manager class for handling in-memory caching
 */
export class CacheManager {
  private cache: Map<string, CacheEntry> = new Map();
  private stats: CacheStatistics = {
    hits: 0,
    misses: 0,
    size: 0,
    hitRate: 0,
    missRate: 0,
    totalEntries: 0,
    expiredEntries: 0,
    invalidations: 0,
  };
  private cleanupInterval: ReturnType<typeof setInterval> | null = null;

  constructor(autoCleanupEnabled = true) {
    if (autoCleanupEnabled) {
      // Start automatic cleanup of expired entries every minute
      this.cleanupInterval = setInterval(() => {
        this.cleanupExpired();
      }, 60 * 1000);
    }
  }

  /**
   * Get a value from cache by key
   * Returns null if key doesn't exist or entry has expired
   */
  get<T = unknown>(key: string): T | null {
    const entry = this.cache.get(key);

    if (!entry) {
      this.stats.misses++;
      this.updateRates();
      return null;
    }

    const now = Date.now();

    if (now > entry.expiresAt) {
      // Entry has expired
      this.cache.delete(key);
      this.stats.size--;
      this.stats.expiredEntries++;
      this.stats.misses++;
      this.updateRates();
      return null;
    }

    // Update access metadata
    entry.lastAccessedAt = now;
    entry.accessCount++;

    this.stats.hits++;
    this.updateRates();

    return entry.value as T;
  }

  /**
   * Set a value in cache with specified TTL
   */
  set<T = unknown>(key: string, value: T, ttl: number): void {
    const now = Date.now();
    const entry: CacheEntry<T> = {
      value,
      expiresAt: now + ttl * 1000,
      ttl,
      createdAt: now,
      lastAccessedAt: now,
      accessCount: 0,
    };

    const isNewEntry = !this.cache.has(key);
    this.cache.set(key, entry as CacheEntry);

    if (isNewEntry) {
      this.stats.size++;
      this.stats.totalEntries++;
    }
  }

  /**
   * Check if a key exists in cache and is not expired
   */
  has(key: string): boolean {
    const entry = this.cache.get(key);

    if (!entry) {
      return false;
    }

    if (Date.now() > entry.expiresAt) {
      this.cache.delete(key);
      this.stats.size--;
      this.stats.expiredEntries++;
      return false;
    }

    return true;
  }

  /**
   * Delete a specific key from cache
   */
  delete(key: string): boolean {
    const deleted = this.cache.delete(key);

    if (deleted) {
      this.stats.size--;
      this.stats.invalidations++;
    }

    return deleted;
  }

  /**
   * Invalidate cache entries matching a pattern
   * Supports wildcard patterns with *
   */
  invalidate(pattern: string): number {
    let invalidatedCount = 0;

    if (pattern.includes('*')) {
      // Wildcard pattern matching
      const regex = new RegExp(
        '^' + pattern.replace(/\*/g, '.*').replace(/\?/g, '.') + '$'
      );

      for (const key of this.cache.keys()) {
        if (regex.test(key)) {
          this.cache.delete(key);
          invalidatedCount++;
          this.stats.invalidations++;
        }
      }
    } else {
      // Exact match
      if (this.delete(pattern)) {
        invalidatedCount++;
      }
    }

    this.stats.size = this.cache.size;
    return invalidatedCount;
  }

  /**
   * Clear all entries from cache
   */
  clear(): void {
    const previousSize = this.cache.size;
    this.cache.clear();
    this.stats.size = 0;
    this.stats.invalidations += previousSize;
  }

  /**
   * Remove expired entries from cache
   */
  cleanupExpired(): number {
    const now = Date.now();
    let removedCount = 0;

    for (const [key, entry] of this.cache.entries()) {
      if (now > entry.expiresAt) {
        this.cache.delete(key);
        removedCount++;
        this.stats.expiredEntries++;
      }
    }

    this.stats.size = this.cache.size;
    return removedCount;
  }

  /**
   * Get all cache keys (for debugging/testing)
   */
  keys(): string[] {
    return Array.from(this.cache.keys());
  }

  /**
   * Get current cache statistics
   */
  getStatistics(): CacheStatistics {
    return { ...this.stats };
  }

  /**
   * Reset cache statistics counters
   */
  resetStatistics(): void {
    this.stats = {
      hits: 0,
      misses: 0,
      size: this.cache.size,
      hitRate: 0,
      missRate: 0,
      totalEntries: 0,
      expiredEntries: 0,
      invalidations: 0,
    };
  }

  /**
   * Update hit/miss rates
   */
  private updateRates(): void {
    const total = this.stats.hits + this.stats.misses;

    if (total > 0) {
      this.stats.hitRate = this.stats.hits / total;
      this.stats.missRate = this.stats.misses / total;
    } else {
      this.stats.hitRate = 0;
      this.stats.missRate = 0;
    }
  }

  /**
   * Get or set pattern - if key exists, return value; otherwise set and return
   */
  async getOrSet<T>(
    key: string,
    factory: () => Promise<T> | T,
    ttl: number
  ): Promise<T> {
    const cached = this.get<T>(key);

    if (cached !== null) {
      return cached;
    }

    const value = await factory();
    this.set(key, value, ttl);
    return value;
  }

  /**
   * Get multiple keys at once
   */
  getMany<T = unknown>(keys: string[]): Map<string, T> {
    const result = new Map<string, T>();

    for (const key of keys) {
      const value = this.get<T>(key);
      if (value !== null) {
        result.set(key, value);
      }
    }

    return result;
  }

  /**
   * Set multiple key-value pairs at once
   */
  setMany(entries: Array<{ key: string; value: unknown; ttl: number }>): void {
    for (const { key, value, ttl } of entries) {
      this.set(key, value, ttl);
    }
  }

  /**
   * Stop automatic cleanup interval
   */
  destroy(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
    this.clear();
  }

  /**
   * Log cache statistics to console
   */
  logStatistics(): void {
    console.log('[Cache Statistics]', {
      size: this.stats.size,
      hits: this.stats.hits,
      misses: this.stats.misses,
      hitRate: `${(this.stats.hitRate * 100).toFixed(2)}%`,
      missRate: `${(this.stats.missRate * 100).toFixed(2)}%`,
      totalEntries: this.stats.totalEntries,
      expiredEntries: this.stats.expiredEntries,
      invalidations: this.stats.invalidations,
    });
  }
}

/**
 * Domain-specific cache utilities
 */
export class DomainCache {
  constructor(private cache: CacheManager) {}

  /**
   * Cache user session data
   */
  cacheUserSession(userId: string, sessionData: unknown): void {
    const key = CacheKeys.USER_SESSION(userId);
    this.cache.set(key, sessionData, CacheTTL.USER_SESSION);
  }

  /**
   * Get cached user session
   */
  getUserSession<T = unknown>(userId: string): T | null {
    const key = CacheKeys.USER_SESSION(userId);
    return this.cache.get<T>(key);
  }

  /**
   * Cache user by ID
   */
  cacheUserById(userId: string, userData: unknown): void {
    const key = CacheKeys.USER_ID(userId);
    this.cache.set(key, userData, CacheTTL.USER_DATA);
  }

  /**
   * Get cached user by ID
   */
  getUserById<T = unknown>(userId: string): T | null {
    const key = CacheKeys.USER_ID(userId);
    return this.cache.get<T>(key);
  }

  /**
   * Invalidate all user-related cache entries
   */
  invalidateUser(userId: string): void {
    this.cache.invalidate(`user:*${userId}*`);
    this.cache.invalidate(`user:session:${userId}`);
    this.cache.invalidate(`user:id:${userId}`);
  }

  /**
   * Cache system configuration
   */
  cacheConfig(key: string, configData: unknown): void {
    const cacheKey = CacheKeys.CONFIG(key);
    this.cache.set(cacheKey, configData, CacheTTL.CONFIG);
  }

  /**
   * Get cached system configuration
   */
  getConfig<T = unknown>(key: string): T | null {
    const cacheKey = CacheKeys.CONFIG(key);
    return this.cache.get<T>(cacheKey);
  }

  /**
   * Invalidate all configuration cache
   */
  invalidateConfig(): void {
    this.cache.invalidate('config:*');
  }

  /**
   * Cache active trades
   */
  cacheActiveTrades(trades: unknown): void {
    this.cache.set(CacheKeys.TRADES_ACTIVE, trades, CacheTTL.ACTIVE_TRADES);
  }

  /**
   * Get cached active trades
   */
  getActiveTrades<T = unknown>(): T | null {
    return this.cache.get<T>(CacheKeys.TRADES_ACTIVE);
  }

  /**
   * Invalidate active trades cache
   */
  invalidateActiveTrades(): void {
    this.cache.delete(CacheKeys.TRADES_ACTIVE);
  }

  /**
   * Invalidate all trades cache
   */
  invalidateTrades(): void {
    this.cache.invalidate('trades:*');
  }

  /**
   * Cache evolution metrics
   */
  cacheEvolutionMetrics(metrics: unknown): void {
    this.cache.set(CacheKeys.EVOLUTION_METRICS, metrics, CacheTTL.EVOLUTION_METRICS);
  }

  /**
   * Get cached evolution metrics
   */
  getEvolutionMetrics<T = unknown>(): T | null {
    return this.cache.get<T>(CacheKeys.EVOLUTION_METRICS);
  }

  /**
   * Invalidate evolution metrics cache
   */
  invalidateEvolutionMetrics(): void {
    this.cache.delete(CacheKeys.EVOLUTION_METRICS);
  }

  /**
   * Invalidate all evolution cache
   */
  invalidateEvolution(): void {
    this.cache.invalidate('evolution:*');
  }

  /**
   * Invalidate all signals cache
   */
  invalidateSignals(): void {
    this.cache.invalidate('signals:*');
  }

  /**
   * Invalidate all cache (emergency use)
   */
  invalidateAll(): void {
    this.cache.clear();
  }
}

/**
 * Singleton cache manager instance
 */
export const cacheManager = new CacheManager();

/**
 * Domain-specific cache utilities instance
 */
export const domainCache = new DomainCache(cacheManager);

/**
 * Cache warming utilities
 */
export const cacheWarmer = {
  /**
   * Warm up cache with common data
   * This should be called on application startup
   */
  async warmUp(loaders: {
    /** Load active trades */
    loadActiveTrades?: () => Promise<unknown>;
    /** Load evolution metrics */
    loadEvolutionMetrics?: () => Promise<unknown>;
    /** Load system config */
    loadConfig?: (key: string) => Promise<unknown>;
    /** Load pending signals */
    loadPendingSignals?: () => Promise<unknown>;
  }): Promise<void> {
    const startTime = Date.now();

    try {
      const promises: Promise<void>[] = [];

      // Warm up active trades
      if (loaders.loadActiveTrades) {
        promises.push(
          (async () => {
            try {
              const trades = await loaders.loadActiveTrades();
              domainCache.cacheActiveTrades(trades);
            } catch (error) {
              console.warn('[Cache Warmer] Failed to load active trades:', error);
            }
          })()
        );
      }

      // Warm up evolution metrics
      if (loaders.loadEvolutionMetrics) {
        promises.push(
          (async () => {
            try {
              const metrics = await loaders.loadEvolutionMetrics();
              domainCache.cacheEvolutionMetrics(metrics);
            } catch (error) {
              console.warn('[Cache Warmer] Failed to load evolution metrics:', error);
            }
          })()
        );
      }

      // Warm up system config
      if (loaders.loadConfig) {
        promises.push(
          (async () => {
            try {
              const config = await loaders.loadConfig('system');
              domainCache.cacheConfig('system', config);
            } catch (error) {
              console.warn('[Cache Warmer] Failed to load system config:', error);
            }
          })()
        );
      }

      // Warm up pending signals
      if (loaders.loadPendingSignals) {
        promises.push(
          (async () => {
            try {
              const signals = await loaders.loadPendingSignals();
              cacheManager.set(CacheKeys.SIGNALS_PENDING, signals, CacheTTL.SIGNALS);
            } catch (error) {
              console.warn('[Cache Warmer] Failed to load pending signals:', error);
            }
          })()
        );
      }

      await Promise.all(promises);

      const duration = Date.now() - startTime;
      console.log(`[Cache Warmer] Completed in ${duration}ms`);
    } catch (error) {
      console.error('[Cache Warmer] Error during cache warm-up:', error);
    }
  },
};

/**
 * Cache invalidation helpers for repository operations
 */
export const cacheInvalidation = {
  /** Invalidate cache on user create/update/delete */
  onUserChange(userId: string): void {
    domainCache.invalidateUser(userId);
  },

  /** Invalidate cache on trade create/update/delete */
  onTradeChange(): void {
    domainCache.invalidateTrades();
  },

  /** Invalidate cache on evolution data change */
  onEvolutionChange(): void {
    domainCache.invalidateEvolution();
  },

  /** Invalidate cache on signal change */
  onSignalChange(): void {
    domainCache.invalidateSignals();
  },

  /** Invalidate cache on config change */
  onConfigChange(): void {
    domainCache.invalidateConfig();
  },
};

/**
 * Export cache utilities for easy access
 */
export const cacheUtils = {
  manager: cacheManager,
  domain: domainCache,
  warmer: cacheWarmer,
  invalidation: cacheInvalidation,
  keys: CacheKeys,
  ttl: CacheTTL,
};
