/**
 * API Client
 *
 * Core HTTP client for making API requests with error handling,
 * timeout support, auth interceptors, Zod validation, logging, and consistent response formatting.
 */

import { z } from 'zod';
import { API_CONFIG } from './config';
import { apiCache } from '../cache';
import { apiLogger, type RequestLogEntry, type ResponseLogEntry, type ErrorLogEntry } from './logger';

/**
 * Validation options for API requests
 */
export interface ValidationOptions {
  /** Zod schema to validate the response against */
  schema?: z.ZodType;
  /** Disable validation (useful for development/debugging) */
  disable?: boolean;
  /** Return safe default values on validation failure instead of throwing */
  returnSafeDefaults?: boolean;
  /** Custom safe default value when validation fails */
  safeDefault?: unknown;
}

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
 * Validation error class for Zod validation failures
 */
export class ValidationError extends Error {
  /** Zod error details */
  public readonly zodError: z.ZodError;
  /** The response data that failed validation */
  public readonly responseData: unknown;
  /** The path of the API request that failed */
  public readonly path: string;

  constructor(zodError: z.ZodError, responseData: unknown, path: string) {
    const formattedErrors = zodError.errors
      .map(e => `${e.path.join('.')}: ${e.message}`)
      .join(', ');
    super(`API response validation failed for ${path}: ${formattedErrors}`);
    this.name = 'ValidationError';
    this.zodError = zodError;
    this.responseData = responseData;
    this.path = path;
  }

  /**
   * Get formatted validation errors
   */
  getErrors(): Array<{ path: string[]; message: string }> {
    return this.zodError.errors.map(e => ({
      path: e.path,
      message: e.message,
    }));
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
 * Core fetch wrapper with timeout, retry logic, error handling, and logging
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: number = API_CONFIG.timeout,
  retryConfig: RetryConfig = DEFAULT_RETRY_CONFIG,
  correlationId?: string
): Promise<{ response: Response; startTime: number; attemptNumber: number }> {
  let lastError: Error | null = null;
  let attemptNumber = 0;

  // Generate correlation ID if not provided
  const cid = correlationId ?? apiLogger.generateCorrelationId();

  // Extract method and body for logging
  const method = (options.method as string) || 'GET';
  const body = options.body ? JSON.parse(options.body as string) : undefined;

  // Log the request
  apiLogger.logRequest(cid, {
    method,
    url,
    headers: options.headers as Record<string, string>,
    params: undefined, // Already in URL
    body,
  } as RequestLogEntry);

  // Retry loop for 5xx errors and network errors
  while (attemptNumber <= retryConfig.maxRetries) {
    const startTime = Date.now();
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

        // Log retry attempt using logger
        apiLogger.logRetry(cid, attemptNumber, retryConfig.maxRetries, delay);

        await sleep(delay);
        continue;
      }

      // Response interceptor: Handle specific status codes
      return { response, startTime, attemptNumber };
    } catch (error) {
      clearTimeout(timeoutId);

      if (error instanceof Error && error.name === 'AbortError') {
        const timeoutError = new ApiRequestError('Request timeout', undefined, 'TIMEOUT');

        // Log timeout error
        apiLogger.logError(cid, {
          message: timeoutError.message,
          code: 'TIMEOUT',
          request: { method, url },
        } as ErrorLogEntry);

        throw timeoutError;
      }

      // Network errors are retryable
      if (attemptNumber < retryConfig.maxRetries && error instanceof Error) {
        lastError = error;
        attemptNumber++;
        const delay = getRetryDelay(attemptNumber - 1, retryConfig.retryDelay);

        // Log retry attempt using logger
        apiLogger.logRetry(cid, attemptNumber, retryConfig.maxRetries, delay);

        await sleep(delay);
        continue;
      }

      // Log final network error
      const networkError = new ApiRequestError(
        error instanceof Error ? error.message : 'Network error',
        undefined,
        'NETWORK_ERROR'
      );

      apiLogger.logError(cid, {
        message: networkError.message,
        code: 'NETWORK_ERROR',
        stack: error instanceof Error ? error.stack : undefined,
        request: { method, url },
      } as ErrorLogEntry);

      throw networkError;
    }
  }

  // All retries exhausted - log error
  const maxRetriesError = new ApiRequestError(
    lastError?.message || 'Request failed after multiple retries',
    undefined,
    'MAX_RETRIES_EXCEEDED'
  );

  apiLogger.logError(cid, {
    message: maxRetriesError.message,
    code: 'MAX_RETRIES_EXCEEDED',
    request: { method, url },
  } as ErrorLogEntry);

  throw maxRetriesError;
}

/**
 * Validate response data using Zod schema
 */
function validateResponse<T>(
  data: unknown,
  schema: z.ZodType<T>,
  path: string,
  options: ValidationOptions,
  correlationId: string
): T {
  // Skip validation if disabled
  if (options.disable) {
    return data as T;
  }

  try {
    return schema.parse(data);
  } catch (error) {
    if (error instanceof z.ZodError) {
      // Log validation error using logger
      apiLogger.logValidationError(correlationId, path, error.errors);

      // Return safe default if configured
      if (options.returnSafeDefaults) {
        return (options.safeDefault as T) ?? ({} as T);
      }

      // Throw validation error
      throw new ValidationError(error, data, path);
    }

    // Re-throw non-Zod errors
    throw error;
  }
}

/**
 * Response interceptor: Parse response and handle errors
 */
async function parseResponse<T>(
  fetchResult: { response: Response; startTime: number; attemptNumber: number },
  validationOptions?: ValidationOptions,
  requestPath?: string,
  correlationId?: string
): Promise<ApiResponse<T>> {
  const { response, startTime, attemptNumber } = fetchResult;
  const cid = correlationId ?? apiLogger.generateCorrelationId();
  const duration = Date.now() - startTime;

  const contentType = response.headers.get('content-type');
  const isJson = contentType?.includes('application/json');

  // Handle 401 Unauthorized - clear auth token and redirect to login
  if (response.status === 401) {
    const authError = new ApiRequestError(
      'Authentication failed. Please log in again.',
      401,
      'UNAUTHORIZED'
    );

    apiLogger.logError(cid, {
      message: authError.message,
      code: 'UNAUTHORIZED',
      status: 401,
      response: { status: response.status, ok: response.ok, duration },
    } as ErrorLogEntry);

    clearAuthTokens();
    redirectToLogin();
    throw authError;
  }

  // Handle 403 Forbidden - permission error
  if (response.status === 403) {
    const forbiddenError = new ApiRequestError(
      'You do not have permission to perform this action.',
      403,
      'FORBIDDEN'
    );

    apiLogger.logError(cid, {
      message: forbiddenError.message,
      code: 'FORBIDDEN',
      status: 403,
      response: { status: response.status, ok: response.ok, duration },
    } as ErrorLogEntry);

    throw forbiddenError;
  }

  // Handle other error responses
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    let errorData: unknown;

    if (isJson) {
      try {
        errorData = await response.clone().json();
        errorMessage = (errorData as { message?: string; error?: string }).message ??
                       (errorData as { message?: string; error?: string }).error ??
                       errorMessage;
      } catch {
        // Use default error message if JSON parsing fails
      }
    }

    const httpError = new ApiRequestError(errorMessage, response.status);

    apiLogger.logError(cid, {
      message: httpError.message,
      status: response.status,
      response: { status: response.status, ok: response.ok, duration },
      ...(errorData && { data: errorData }),
    } as ErrorLogEntry);

    throw httpError;
  }

  const rawData = isJson ? await response.json() : await response.text();

  // Validate response if schema provided
  let data: T = rawData as T;
  if (validationOptions?.schema && isJson) {
    data = validateResponse<T>(
      rawData,
      validationOptions.schema,
      requestPath || response.url,
      validationOptions,
      cid
    );
  }

  // Log the response
  apiLogger.logResponse(cid, {
    status: response.status,
    ok: response.ok,
    duration,
    ...(isJson && { data: rawData }),
  } as ResponseLogEntry);

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
 * GET request with optional URL parameters, caching, and validation
 */
export async function get<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
  options?: RequestInit & {
    cache?: CacheOptions | boolean;
    validate?: ValidationOptions;
  }
): Promise<ApiResponse<T>> {
  // Generate correlation ID for this request
  const correlationId = apiLogger.generateCorrelationId();

  // Parse cache options
  const cacheEnabled = options?.cache === undefined || options?.cache === true
    ? (typeof options?.cache === 'object' ? options.cache.enabled !== false : true)
    : false;

  const cacheOpts: CacheOptions | undefined = typeof options?.cache === 'object' ? options.cache : undefined;
  const customTTL = cacheOpts?.ttl;
  const customKey = cacheOpts?.key;
  const validationOptions = options?.validate;

  // Generate cache key
  const cacheKey = customKey ?? generateCacheKey(path, params);

  // Check cache if enabled
  if (cacheEnabled) {
    const cachedData = apiCache.get<T>(cacheKey);
    if (cachedData !== null) {
      apiLogger.logCacheHit(correlationId, cacheKey);
      return {
        data: cachedData,
        status: 200,
        ok: true,
      };
    }

    apiLogger.logCacheMiss(correlationId, cacheKey);
  }

  // Make the actual request
  const url = buildUrl(path, params);
  const fetchResult = await fetchWithTimeout(url, { ...options, method: 'GET' }, API_CONFIG.timeout, DEFAULT_RETRY_CONFIG, correlationId);
  const result = await parseResponse<T>(fetchResult, validationOptions, path, correlationId);

  // Cache successful responses if caching is enabled
  if (cacheEnabled && result.ok) {
    const ttl = customTTL ?? getDefaultTTL(path);
    if (ttl > 0) {
      apiCache.set(cacheKey, result.data, ttl);
      apiLogger.logCacheSet(correlationId, cacheKey, ttl);
    }
  }

  return result;
}

/**
 * POST request with optional validation
 */
export async function post<T>(
  path: string,
  body?: unknown,
  options?: RequestInit & {
    validate?: ValidationOptions;
  }
): Promise<ApiResponse<T>> {
  const correlationId = apiLogger.generateCorrelationId();
  const url = buildUrl(path);
  const fetchResult = await fetchWithTimeout(url, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
    ...options,
  }, API_CONFIG.timeout, DEFAULT_RETRY_CONFIG, correlationId);
  const validationOptions = options?.validate;
  const result = await parseResponse<T>(fetchResult, validationOptions, path, correlationId);

  // Invalidate related cache entries after successful POST
  if (result.ok) {
    invalidateRelatedCache(path);
  }

  return result;
}

/**
 * PUT request with optional validation
 */
export async function put<T>(
  path: string,
  body?: unknown,
  options?: RequestInit & {
    validate?: ValidationOptions;
  }
): Promise<ApiResponse<T>> {
  const correlationId = apiLogger.generateCorrelationId();
  const url = buildUrl(path);
  const fetchResult = await fetchWithTimeout(url, {
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined,
    ...options,
  }, API_CONFIG.timeout, DEFAULT_RETRY_CONFIG, correlationId);
  const validationOptions = options?.validate;
  const result = await parseResponse<T>(fetchResult, validationOptions, path, correlationId);

  // Invalidate related cache entries after successful PUT
  if (result.ok) {
    invalidateRelatedCache(path);
  }

  return result;
}

/**
 * DELETE request with optional validation
 */
export async function del<T>(
  path: string,
  options?: RequestInit & {
    validate?: ValidationOptions;
  }
): Promise<ApiResponse<T>> {
  const correlationId = apiLogger.generateCorrelationId();
  const url = buildUrl(path);
  const fetchResult = await fetchWithTimeout(url, { method: 'DELETE', ...options }, API_CONFIG.timeout, DEFAULT_RETRY_CONFIG, correlationId);
  const validationOptions = options?.validate;
  const result = await parseResponse<T>(fetchResult, validationOptions, path, correlationId);

  // Invalidate related cache entries after successful DELETE
  if (result.ok) {
    invalidateRelatedCache(path);
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

/**
 * Export logger utilities for external use
 */
export const loggerUtils = {
  setConfig: (config: Parameters<typeof apiLogger.setConfig>[0]) => apiLogger.setConfig(config),
  setMinLevel: (level: Parameters<typeof apiLogger.setMinLevel>[0]) => apiLogger.setMinLevel(level),
  generateCorrelationId: () => apiLogger.generateCorrelationId(),
  logRequest: (correlationId: string, request: Parameters<typeof apiLogger.logRequest>[1]) =>
    apiLogger.logRequest(correlationId, request),
  logResponse: (correlationId: string, response: Parameters<typeof apiLogger.logResponse>[1]) =>
    apiLogger.logResponse(correlationId, response),
  logError: (correlationId: string, error: Parameters<typeof apiLogger.logError>[1]) =>
    apiLogger.logError(correlationId, error),
  debug: (correlationId: string, message: string, data?: unknown) =>
    apiLogger.debug(correlationId, message, data),
  info: (correlationId: string, message: string, data?: unknown) =>
    apiLogger.info(correlationId, message, data),
  warn: (correlationId: string, message: string, data?: unknown) =>
    apiLogger.warn(correlationId, message, data),
  error: (correlationId: string, message: string, data?: unknown) =>
    apiLogger.error(correlationId, message, data),
} as const;
