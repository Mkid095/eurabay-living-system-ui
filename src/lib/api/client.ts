/**
 * API Client
 *
 * Core HTTP client for making API requests with error handling,
 * timeout support, auth interceptors, and consistent response formatting.
 */

import { API_CONFIG } from './config';
import { apiCache } from '../cache';

export interface ApiResponse<T> {
  data: T;
  status: number;
  ok: boolean;
}

export interface ApiError {
  message: string;
  status?: number;
  code?: string;
}

/**
 * Cache options for API requests
 */
export interface CacheOptions {
  /** Enable/disable caching (default: true for GET requests) */
  enabled?: boolean;
  /** Custom TTL in seconds (overrides default) */
  ttl?: number;
  /** Custom cache key (auto-generated if not provided) */
  key?: string;
}

/**
 * Default cache TTLs for different endpoint patterns
 */
const DEFAULT_CACHE_TTLS: Record<string, number> = {
  'system/status': 10,
  'system/health': 10,
  'config': 60,
  'markets/overview': 5,
  'markets': 5,
  'evolution/metrics': 10,
  'portfolio/metrics': 10,
};

/**
 * Generic API error class
 */
export class ApiRequestError extends Error implements ApiError {
  status?: number;
  code?: string;

  constructor(message: string, status?: number, code?: string) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
    this.code = code;
  }
}

/**
 * Auth token storage key
 */
const AUTH_TOKEN_KEY = 'auth_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

/**
 * Get stored auth token from localStorage
 */
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY);
  } catch {
    return null;
  }
}

/**
 * Clear auth tokens from localStorage (used on 401 errors)
 */
function clearAuthTokens(): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  } catch {
    // Ignore errors in localStorage access
  }
}

/**
 * Redirect to login page (used on 401 errors)
 */
function redirectToLogin(): void {
  if (typeof window === 'undefined') return;
  // Only redirect if not already on login page to avoid loops
  if (!window.location.pathname.includes('/login')) {
    window.location.href = '/login';
  }
}

/**
 * Request interceptor: Add auth token and common headers
 */
function applyRequestHeaders(options: RequestInit): RequestInit {
  const headers: Record<string, string> = {
    ...API_CONFIG.headers,
    ...(options.headers as Record<string, string>),
  };

  // Inject auth token from localStorage if available
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  return {
    ...options,
    headers,
  };
}

/**
 * Retry configuration for 5xx errors
 */
interface RetryConfig {
  maxRetries: number;
  retryDelay: number;
  retryableStatuses: number[];
}

const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxRetries: 3,
  retryDelay: 1000, // Start with 1 second
  retryableStatuses: [500, 502, 503, 504],
};

/**
 * Calculate exponential backoff delay
 */
function getRetryDelay(attemptNumber: number, baseDelay: number): number {
  // Exponential backoff: 1s, 2s, 4s, etc.
  return baseDelay * Math.pow(2, attemptNumber);
}

/**
 * Sleep utility for retry delays
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Generate cache key from URL and options
 */
function generateCacheKey(path: string, params?: Record<string, string | number | boolean | undefined>): string {
  const url = buildUrl(path, params);
  // Remove base URL to get relative path as cache key
  return url.replace(API_CONFIG.baseURL, '').replace(/^\//, '');
}

/**
 * Get default TTL for a given path
 */
function getDefaultTTL(path: string): number {
  const normalizedPath = path.toLowerCase();
  for (const [pattern, ttl] of Object.entries(DEFAULT_CACHE_TTLS)) {
    if (normalizedPath.includes(pattern)) {
      return ttl;
    }
  }
  return 0; // Default to no caching for unknown endpoints
}

/**
 * Build full URL from path and optional query parameters
 */
function buildUrl(path: string, params?: Record<string, string | number | boolean | undefined>): string {
  // Remove leading slash if present and join with base URL
  const cleanPath = path.startsWith('/') ? path.slice(1) : path;
  let url = `${API_CONFIG.baseURL}/${cleanPath}`;

  // Add query parameters if provided
  if (params && Object.keys(params).length > 0) {
    // Filter out undefined values
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        searchParams.append(key, String(value));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  return url;
}

/**
 * Core fetch wrapper with timeout, retry logic, and error handling
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: number = API_CONFIG.timeout,
  retryConfig: RetryConfig = DEFAULT_RETRY_CONFIG
): Promise<Response> {
  let lastError: Error | null = null;
  let attemptNumber = 0;

  // Retry loop for 5xx errors and network errors
  while (attemptNumber <= retryConfig.maxRetries) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    // Apply request interceptor (add auth headers and retry count)
    const interceptedOptions = applyRequestHeaders(options);

    // Add X-Retry-Count header to track retry attempts
    if (attemptNumber > 0) {
      (interceptedOptions.headers as Record<string, string>)['X-Retry-Count'] = String(attemptNumber);
    }

    try {
      const response = await fetch(url, {
        ...interceptedOptions,
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      // Check if response is retryable (5xx errors only - not 4xx)
      if (
        attemptNumber < retryConfig.maxRetries &&
        retryConfig.retryableStatuses.includes(response.status)
      ) {
        attemptNumber++;
        const delay = getRetryDelay(attemptNumber - 1, retryConfig.retryDelay);

        // Log retry attempt in development
        if (process.env.NODE_ENV === 'development') {
          console.warn(
            `API request failed with ${response.status}, retrying in ${delay}ms (attempt ${attemptNumber}/${retryConfig.maxRetries})`
          );
        }

        await sleep(delay);
        continue;
      }

      // Response interceptor: Handle specific status codes
      return response;
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error && error.name === 'AbortError') {
        throw new ApiRequestError('Request timeout', undefined, 'TIMEOUT');
      }

      // Network errors are retryable
      if (attemptNumber < retryConfig.maxRetries && error instanceof Error) {
        lastError = error;
        attemptNumber++;
        const delay = getRetryDelay(attemptNumber - 1, retryConfig.retryDelay);

        // Log retry attempt in development
        if (process.env.NODE_ENV === 'development') {
          console.warn(
            `Network error, retrying in ${delay}ms (attempt ${attemptNumber}/${retryConfig.maxRetries})`
          );
        }

        await sleep(delay);
        continue;
      }

      throw new ApiRequestError(
        error instanceof Error ? error.message : 'Network error',
        undefined,
        'NETWORK_ERROR'
      );
    }
  }

  // All retries exhausted
  throw new ApiRequestError(
    lastError?.message || 'Request failed after multiple retries',
    undefined,
    'MAX_RETRIES_EXCEEDED'
  );
}

/**
 * Response interceptor: Parse response and handle errors
 */
async function parseResponse<T>(response: Response): Promise<ApiResponse<T>> {
  const contentType = response.headers.get('content-type');
  const isJson = contentType?.includes('application/json');

  // Handle 401 Unauthorized - clear auth token and redirect to login
  if (response.status === 401) {
    clearAuthTokens();
    redirectToLogin();
    throw new ApiRequestError(
      'Authentication failed. Please log in again.',
      401,
      'UNAUTHORIZED'
    );
  }

  // Handle 403 Forbidden - permission error
  if (response.status === 403) {
    throw new ApiRequestError(
      'You do not have permission to perform this action.',
      403,
      'FORBIDDEN'
    );
  }

  // Handle other error responses
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;

    if (isJson) {
      try {
        const errorData = await response.json();
        errorMessage = errorData.message || errorData.error || errorMessage;
      } catch {
        // Use default error message if JSON parsing fails
      }
    }

    throw new ApiRequestError(errorMessage, response.status);
  }

  const data = isJson ? await response.json() : await response.text();

  return {
    data,
    status: response.status,
    ok: response.ok,
  };
}

/**
 * Invalidate related cache entries after write operations
 */
function invalidateRelatedCache(path: string): void {
  const normalizedPath = path.toLowerCase();

  // Invalidate all caches for system operations
  if (normalizedPath.includes('system')) {
    apiCache.invalidate('system/*');
  }

  // Invalidate config caches
  if (normalizedPath.includes('config')) {
    apiCache.invalidate('*config*');
  }

  // Invalidate evolution caches
  if (normalizedPath.includes('evolution')) {
    apiCache.invalidate('evolution/*');
  }

  // Invalidate portfolio caches
  if (normalizedPath.includes('portfolio') || normalizedPath.includes('trades')) {
    apiCache.invalidate('portfolio/*');
    apiCache.invalidate('trades/*');
  }

  // Invalidate markets caches
  if (normalizedPath.includes('markets')) {
    apiCache.invalidate('markets/*');
  }
}

/**
 * GET request with optional URL parameters and caching
 */
export async function get<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
  options?: RequestInit & { cache?: CacheOptions | boolean }
): Promise<ApiResponse<T>> {
  // Parse cache options
  const cacheEnabled = options?.cache === undefined || options?.cache === true
    ? (typeof options?.cache === 'object' ? options.cache.enabled !== false : true)
    : false;

  const cacheOpts: CacheOptions | undefined = typeof options?.cache === 'object' ? options.cache : undefined;
  const customTTL = cacheOpts?.ttl;
  const customKey = cacheOpts?.key;

  // Generate cache key
  const cacheKey = customKey ?? generateCacheKey(path, params);

  // Check cache if enabled
  if (cacheEnabled) {
    const cachedData = apiCache.get<T>(cacheKey);
    if (cachedData !== null) {
      if (process.env.NODE_ENV === 'development') {
        console.debug(`[API Cache HIT] ${cacheKey}`);
      }
      return {
        data: cachedData,
        status: 200,
        ok: true,
      };
    }

    if (process.env.NODE_ENV === 'development') {
      console.debug(`[API Cache MISS] ${cacheKey}`);
    }
  }

  // Make the actual request
  const url = buildUrl(path, params);
  const response = await fetchWithTimeout(url, { ...options, method: 'GET' });
  const result = await parseResponse<T>(response);

  // Cache successful responses if caching is enabled
  if (cacheEnabled && result.ok) {
    const ttl = customTTL ?? getDefaultTTL(path);
    if (ttl > 0) {
      apiCache.set(cacheKey, result.data, ttl);
      if (process.env.NODE_ENV === 'development') {
        console.debug(`[API Cache SET] ${cacheKey} (TTL: ${ttl}s)`);
      }
    }
  }

  return result;
}

/**
 * POST request
 */
export async function post<T>(
  path: string,
  body?: unknown,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  const url = buildUrl(path);
  const response = await fetchWithTimeout(url, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
    ...options,
  });
  const result = await parseResponse<T>(response);

  // Invalidate related cache entries after successful POST
  if (result.ok) {
    invalidateRelatedCache(path);
    if (process.env.NODE_ENV === 'development') {
      console.debug(`[API Cache] Invalidated related caches for POST ${path}`);
    }
  }

  return result;
}

/**
 * PUT request
 */
export async function put<T>(
  path: string,
  body?: unknown,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  const url = buildUrl(path);
  const response = await fetchWithTimeout(url, {
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined,
    ...options,
  });
  const result = await parseResponse<T>(response);

  // Invalidate related cache entries after successful PUT
  if (result.ok) {
    invalidateRelatedCache(path);
    if (process.env.NODE_ENV === 'development') {
      console.debug(`[API Cache] Invalidated related caches for PUT ${path}`);
    }
  }

  return result;
}

/**
 * DELETE request
 */
export async function del<T>(path: string, options?: RequestInit): Promise<ApiResponse<T>> {
  const url = buildUrl(path);
  const response = await fetchWithTimeout(url, { method: 'DELETE', ...options });
  const result = await parseResponse<T>(response);

  // Invalidate related cache entries after successful DELETE
  if (result.ok) {
    invalidateRelatedCache(path);
    if (process.env.NODE_ENV === 'development') {
      console.debug(`[API Cache] Invalidated related caches for DELETE ${path}`);
    }
  }

  return result;
}

/**
 * Export client object for convenience
 */
export const apiClient = {
  get,
  post,
  put,
  delete: del,
} as const;

/**
 * Export cache utilities for external use
 */
export const cacheUtils = {
  getStats: () => apiCache.getStats(),
  getHitRate: () => apiCache.getHitRate(),
  clear: () => apiCache.clear(),
  invalidate: (pattern: string) => apiCache.invalidate(pattern),
  logStats: () => {
    if (process.env.NODE_ENV === 'development') {
      const stats = apiCache.getStats();
      console.group('[API Cache Stats]');
      console.log(`Size: ${stats.size} entries`);
      console.log(`Hits: ${stats.hits}`);
      console.log(`Misses: ${stats.misses}`);
      console.log(`Hit rate: ${apiCache.getHitRate()}%`);
      console.log(`Keys:`, apiCache.keys());
      console.groupEnd();
    }
  },
} as const;

/**
 * Export auth utilities for use in auth components
 */
export const authUtils = {
  getAuthToken,
  clearAuthTokens,
  setAuthToken: (token: string): void => {
    if (typeof window === 'undefined') return;
    try {
      localStorage.setItem(AUTH_TOKEN_KEY, token);
    } catch {
      // Ignore errors in localStorage access
    }
  },
} as const;
