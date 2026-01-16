/**
 * API Client
 *
 * Core HTTP client for making API requests with error handling,
 * timeout support, auth interceptors, and consistent response formatting.
 */

import { API_CONFIG } from './config';

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
 * GET request with optional URL parameters
 */
export async function get<T>(
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  const url = buildUrl(path, params);
  const response = await fetchWithTimeout(url, { ...options, method: 'GET' });
  return parseResponse<T>(response);
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
  return parseResponse<T>(response);
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
  return parseResponse<T>(response);
}

/**
 * DELETE request
 */
export async function del<T>(path: string, options?: RequestInit): Promise<ApiResponse<T>> {
  const url = buildUrl(path);
  const response = await fetchWithTimeout(url, { method: 'DELETE', ...options });
  return parseResponse<T>(response);
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
