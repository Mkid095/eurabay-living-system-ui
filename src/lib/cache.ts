/**
 * In-memory API cache with TTL support
 * Provides caching functionality for API responses to reduce redundant requests
 */

interface CacheItem<T> {
  data: T;
  expiresAt: number;
}

interface CacheStats {
  hits: number;
  misses: number;
  size: number;
}

/**
 * APICache - In-memory cache with TTL (Time To Live) support
 * @example
 * const cache = apiCache;
 * cache.set('user:123', userData, 60); // Cache for 60 seconds
 * const data = cache.get('user:123'); // Returns userData if not expired
 */
class APICache {
  private cache: Map<string, CacheItem<unknown>>;
  private stats: CacheStats;

  constructor() {
    this.cache = new Map();
    this.stats = {
      hits: 0,
      misses: 0,
      size: 0,
    };
  }

  /**
   * Get cached data by key
   * Returns null if key doesn't exist or item has expired
   * @param key - Cache key
   * @returns Cached data or null if not found/expired
   */
  get<T>(key: string): T | null {
    const item = this.cache.get(key);

    if (!item) {
      this.stats.misses++;
      return null;
    }

    // Check if item has expired
    if (Date.now() > item.expiresAt) {
      this.cache.delete(key);
      this.stats.misses++;
      this.stats.size = this.cache.size;
      return null;
    }

    this.stats.hits++;
    return item.data as T;
  }

  /**
   * Set cached data with TTL
   * @param key - Cache key
   * @param data - Data to cache
   * @param ttl - Time to live in seconds
   */
  set<T>(key: string, data: T, ttl: number): void {
    const expiresAt = Date.now() + ttl * 1000;
    const item: CacheItem<T> = {
      data,
      expiresAt,
    };

    this.cache.set(key, item as CacheItem<unknown>);
    this.stats.size = this.cache.size;
  }

  /**
   * Invalidate cache entries matching a pattern
   * Supports wildcard patterns with *
   * @param pattern - Pattern to match (supports * wildcard)
   * @example
   * invalidate('user:*') // Clears all user cache entries
   * invalidate('*') // Clears all cache
   */
  invalidate(pattern: string): void {
    if (pattern === '*') {
      this.clear();
      return;
    }

    const regex = new RegExp(
      '^' + pattern.replace(/\*/g, '.*').replace(/\?/g, '.') + '$'
    );

    for (const key of this.cache.keys()) {
      if (regex.test(key)) {
        this.cache.delete(key);
      }
    }

    this.stats.size = this.cache.size;
  }

  /**
   * Clear all cache entries
   */
  clear(): void {
    this.cache.clear();
    this.stats.size = 0;
  }

  /**
   * Get cache statistics
   * @returns Cache stats including hits, misses, and size
   */
  getStats(): CacheStats {
    return { ...this.stats };
  }

  /**
   * Reset cache statistics
   */
  resetStats(): void {
    this.stats = {
      hits: 0,
      misses: 0,
      size: this.cache.size,
    };
  }

  /**
   * Get cache hit rate
   * @returns Hit rate as a percentage (0-100)
   */
  getHitRate(): number {
    const total = this.stats.hits + this.stats.misses;
    if (total === 0) return 0;
    return Math.round((this.stats.hits / total) * 100);
  }

  /**
   * Check if a key exists and is not expired
   * @param key - Cache key
   * @returns true if key exists and is not expired
   */
  has(key: string): boolean {
    const item = this.cache.get(key);
    if (!item) return false;
    if (Date.now() > item.expiresAt) {
      this.cache.delete(key);
      this.stats.size = this.cache.size;
      return false;
    }
    return true;
  }

  /**
   * Get all cache keys
   * @returns Array of all cache keys
   */
  keys(): string[] {
    return Array.from(this.cache.keys());
  }

  /**
   * Clean up expired entries
   * Useful for maintenance to free memory
   */
  cleanup(): void {
    const now = Date.now();
    for (const [key, item] of this.cache.entries()) {
      if (now > item.expiresAt) {
        this.cache.delete(key);
      }
    }
    this.stats.size = this.cache.size;
  }
}

// Export singleton instance
export const apiCache = new APICache();

// Export class for testing
export { APICache };
export type { CacheItem, CacheStats };
