/**
 * Cache Warming Utility
 *
 * Preloads commonly accessed API endpoints into cache on app startup
 * to improve initial page load performance.
 */

import { apiClient } from './client';
import { apiCache } from '../cache';

/**
 * Cache warming configuration
 * Maps endpoint paths to their cache keys and warm-up priorities
 */
interface CacheWarmupEntry {
  path: string;
  key: string;
  priority: number; // Lower number = higher priority
  params?: Record<string, string | number | boolean | undefined>;
}

/**
 * Common endpoints to warm up on app startup
 * Ordered by priority (most frequently accessed first)
 */
const WARMUP_ENDPOINTS: CacheWarmupEntry[] = [
  // System status - highest priority
  { path: 'system/status', key: 'system/status', priority: 1 },
  { path: 'system/health', key: 'system/health', priority: 2 },

  // Market overview - high priority
  { path: 'markets/overview', key: 'markets/overview', priority: 3 },

  // Configuration
  { path: 'config', key: 'config', priority: 4 },

  // Evolution metrics - medium priority
  { path: 'evolution/metrics', key: 'evolution/metrics', priority: 5 },

  // Portfolio metrics - medium priority
  { path: 'portfolio/metrics', key: 'portfolio/metrics', priority: 6 },
];

/**
 * Warm up a single cache entry
 */
async function warmCacheEntry(entry: CacheWarmupEntry): Promise<void> {
  try {
    const response = await apiClient.get(entry.path, entry.params, {
      cache: { enabled: true, key: entry.key },
    });

    if (response.ok) {
      if (process.env.NODE_ENV === 'development') {
        console.debug(`[Cache Warmup] Warmed: ${entry.key}`);
      }
    }
  } catch (error) {
    // Silently fail - cache warming is optional
    if (process.env.NODE_ENV === 'development') {
      console.warn(`[Cache Warmup] Failed to warm: ${entry.key}`, error);
    }
  }
}

/**
 * Warm up all configured cache entries
 * Uses priority ordering to warm most important endpoints first
 *
 * @param options - Optional configuration
 * @param options.maxConcurrency - Maximum number of concurrent requests (default: 3)
 * @param options.timeout - Maximum time to wait for warmup in ms (default: 5000)
 */
export async function warmUpCache(options: {
  maxConcurrency?: number;
  timeout?: number;
} = {}): Promise<void> {
  const { maxConcurrency = 3, timeout = 5000 } = options;

  // Sort endpoints by priority
  const sortedEntries = [...WARMUP_ENDPOINTS].sort((a, b) => a.priority - b.priority);

  if (process.env.NODE_ENV === 'development') {
    console.debug('[Cache Warmup] Starting cache warmup...');
  }

  // Create a timeout promise
  const timeoutPromise = new Promise<void>((_, reject) => {
    setTimeout(() => reject(new Error('Cache warmup timeout')), timeout);
  });

  // Process entries in batches
  const warmupPromise = (async () => {
    for (let i = 0; i < sortedEntries.length; i += maxConcurrency) {
      const batch = sortedEntries.slice(i, i + maxConcurrency);
      await Promise.all(batch.map(warmCacheEntry));
    }
  })();

  // Race between warmup and timeout
  try {
    await Promise.race([warmupPromise, timeoutPromise]);

    if (process.env.NODE_ENV === 'development') {
      const stats = apiCache.getStats();
      console.debug(
        `[Cache Warmup] Complete. Size: ${stats.size}, Hit rate: ${apiCache.getHitRate()}%`
      );
    }
  } catch (error) {
    // Timeout or error is not critical - app can function without cache warming
    if (process.env.NODE_ENV === 'development') {
      console.warn('[Cache Warmup] Warmup incomplete or timed out');
    }
  }
}

/**
 * Manually trigger cache warming for specific endpoints
 *
 * @param paths - Array of endpoint paths to warm
 */
export async function warmCacheEntries(paths: string[]): Promise<void> {
  const entries = WARMUP_ENDPOINTS.filter(entry => paths.includes(entry.path));

  if (process.env.NODE_ENV === 'development') {
    console.debug(`[Cache Warmup] Warming ${entries.length} specific entries...`);
  }

  await Promise.all(entries.map(warmCacheEntry));
}
