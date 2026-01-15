/**
 * API Client
 *
 * Core HTTP client for making API requests with error handling,
 * timeout support, and consistent response formatting.
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
 * Core fetch wrapper with timeout and error handling
 */
async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeout: number = API_CONFIG.timeout
): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...API_CONFIG.headers,
        ...options.headers,
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    return response;
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof Error && error.name === 'AbortError') {
      throw new ApiRequestError('Request timeout', undefined, 'TIMEOUT');
    }

    throw new ApiRequestError(
      error instanceof Error ? error.message : 'Network error',
      undefined,
      'NETWORK_ERROR'
    );
  }
}

/**
 * Parse response and handle errors
 */
async function parseResponse<T>(response: Response): Promise<ApiResponse<T>> {
  const contentType = response.headers.get('content-type');
  const isJson = contentType?.includes('application/json');

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
    ...options,
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
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
    ...options,
    method: 'PUT',
    body: body ? JSON.stringify(body) : undefined,
  });
  return parseResponse<T>(response);
}

/**
 * DELETE request
 */
export async function del<T>(path: string, options?: RequestInit): Promise<ApiResponse<T>> {
  const url = buildUrl(path);
  const response = await fetchWithTimeout(url, { ...options, method: 'DELETE' });
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
