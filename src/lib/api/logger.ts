/**
 * API Logger
 *
 * Comprehensive logging system for API requests and responses with
 * request timing, correlation IDs, log level filtering, and sensitive data sanitization.
 */

/**
 * Log levels for filtering and categorization
 */
export enum LogLevel {
  ERROR = 0,
  WARN = 1,
  INFO = 2,
  DEBUG = 3,
}

/**
 * Log entry metadata
 */
interface LogMetadata {
  /** Correlation ID for request tracking */
  correlationId: string;
  /** Timestamp of the log entry */
  timestamp: string;
  /** Log level */
  level: LogLevel;
}

/**
 * Request log entry
 */
export interface RequestLogEntry {
  method: string;
  url: string;
  headers?: Record<string, string>;
  params?: Record<string, string | number | boolean>;
  body?: unknown;
}

/**
 * Response log entry
 */
export interface ResponseLogEntry {
  status: number;
  ok: boolean;
  headers?: Record<string, string>;
  data?: unknown;
  duration: number;
}

/**
 * Error log entry
 */
export interface ErrorLogEntry {
  message: string;
  code?: string;
  status?: number;
  stack?: string;
  request?: RequestLogEntry;
  response?: ResponseLogEntry;
}

/**
 * Logger configuration
 */
interface LoggerConfig {
  /** Minimum log level to output */
  minLevel: LogLevel;
  /** Whether to enable verbose logging in development */
  verbose: boolean;
  /** Whether to include request/response body in logs */
  includeBody: boolean;
  /** Whether to include headers in logs */
  includeHeaders: boolean;
}

/**
 * Default logger configuration
 */
const DEFAULT_CONFIG: LoggerConfig = {
  minLevel: process.env.NODE_ENV === 'development' ? LogLevel.DEBUG : LogLevel.INFO,
  verbose: process.env.NODE_ENV === 'development',
  includeBody: process.env.NODE_ENV === 'development',
  includeHeaders: false,
};

/**
 * Patterns for detecting sensitive data that should be sanitized
 */
const SENSITIVE_PATTERNS = [
  /password/i,
  /token/i,
  /secret/i,
  /authorization/i,
  /apikey/i,
  /api_key/i,
  /session/i,
  /credit/i,
  /ssn/i,
  /bearer/i,
];

/**
 * Recursively sanitize sensitive data from an object
 */
function sanitizeData(data: unknown): unknown {
  if (data === null || data === undefined) {
    return data;
  }

  if (typeof data === 'string') {
    // Check if key suggests sensitive data
    return '[REDACTED]';
  }

  if (typeof data === 'number' || typeof data === 'boolean') {
    return data;
  }

  if (Array.isArray(data)) {
    return data.map(sanitizeData);
  }

  if (typeof data === 'object') {
    const sanitized: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      // Check if key matches any sensitive pattern
      const isSensitive = SENSITIVE_PATTERNS.some(pattern => pattern.test(key));

      if (isSensitive) {
        sanitized[key] = '[REDACTED]';
      } else {
        sanitized[key] = sanitizeData(value);
      }
    }
    return sanitized;
  }

  return data;
}

/**
 * Sanitize headers to remove sensitive information
 */
function sanitizeHeaders(headers: Record<string, string>): Record<string, string> {
  const sanitized: Record<string, string> = {};

  for (const [key, value] of Object.entries(headers)) {
    const lowerKey = key.toLowerCase();

    // Redact authorization headers
    if (lowerKey === 'authorization' || lowerKey === 'cookie') {
      sanitized[key] = '[REDACTED]';
    } else {
      sanitized[key] = value;
    }
  }

  return sanitized;
}

/**
 * Get log level name as string
 */
function getLevelName(level: LogLevel): string {
  switch (level) {
    case LogLevel.ERROR:
      return 'ERROR';
    case LogLevel.WARN:
      return 'WARN';
    case LogLevel.INFO:
      return 'INFO';
    case LogLevel.DEBUG:
      return 'DEBUG';
    default:
      return 'UNKNOWN';
  }
}

/**
 * Get console method for log level
 */
function getConsoleMethod(level: LogLevel): (...args: unknown[]) => void {
  switch (level) {
    case LogLevel.ERROR:
      return console.error;
    case LogLevel.WARN:
      return console.warn;
    case LogLevel.INFO:
      return console.info;
    case LogLevel.DEBUG:
      return console.debug;
    default:
      return console.log;
  }
}

/**
 * API Logger class for logging API requests and responses
 */
export class APILogger {
  private config: LoggerConfig;
  private correlationIdCounter = 0;

  constructor(config: Partial<LoggerConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
  }

  /**
   * Update logger configuration
   */
  setConfig(config: Partial<LoggerConfig>): void {
    this.config = { ...this.config, ...config };
  }

  /**
   * Set minimum log level
   */
  setMinLevel(level: LogLevel): void {
    this.config.minLevel = level;
  }

  /**
   * Generate a unique correlation ID for request tracking
   */
  generateCorrelationId(): string {
    const timestamp = Date.now().toString(36);
    const counter = (this.correlationIdCounter++).toString(36).padStart(4, '0');
    return `req_${timestamp}_${counter}`;
  }

  /**
   * Check if a log level should be output based on min level
   */
  private shouldLog(level: LogLevel): boolean {
    return level <= this.config.minLevel;
  }

  /**
   * Format log entry for output
   */
  private formatLogEntry(
    level: LogLevel,
    correlationId: string,
    message: string,
    data?: unknown
  ): string {
    const timestamp = new Date().toISOString();
    const levelName = getLevelName(level);
    const dataStr = data ? `\n  ${JSON.stringify(data, null, 2).split('\n').join('\n  ')}` : '';
    return `[${timestamp}] [${levelName}] [${correlationId}] ${message}${dataStr}`;
  }

  /**
   * Log an entry at the specified level
   */
  private log(level: LogLevel, correlationId: string, message: string, data?: unknown): void {
    if (!this.shouldLog(level)) {
      return;
    }

    const formatted = this.formatLogEntry(level, correlationId, message, data);
    const consoleMethod = getConsoleMethod(level);

    consoleMethod(formatted);
  }

  /**
   * Log an API request
   */
  logRequest(correlationId: string, request: RequestLogEntry): void {
    const sanitizedHeaders = this.config.includeHeaders && request.headers
      ? sanitizeHeaders(request.headers)
      : undefined;

    const sanitizedBody = this.config.includeBody && request.body
      ? sanitizeData(request.body)
      : undefined;

    const logData: Partial<RequestLogEntry> = {
      method: request.method,
      url: this.sanitizeUrl(request.url),
    };

    if (sanitizedHeaders) {
      logData.headers = sanitizedHeaders;
    }

    if (sanitizedBody !== undefined) {
      logData.body = sanitizedBody;
    }

    if (request.params) {
      logData.params = request.params;
    }

    this.log(
      LogLevel.INFO,
      correlationId,
      `API Request: ${request.method} ${request.url}`,
      this.config.verbose ? logData : undefined
    );
  }

  /**
   * Log an API response
   */
  logResponse(correlationId: string, response: ResponseLogEntry): void {
    const sanitizedHeaders = this.config.includeHeaders && response.headers
      ? sanitizeHeaders(response.headers)
      : undefined;

    const sanitizedBody = this.config.includeBody && response.data
      ? sanitizeData(response.data)
      : undefined;

    const logData: Partial<ResponseLogEntry> = {
      status: response.status,
      ok: response.ok,
      duration: `${response.duration}ms`,
    };

    if (sanitizedHeaders) {
      logData.headers = sanitizedHeaders;
    }

    if (sanitizedBody !== undefined) {
      logData.data = sanitizedBody;
    }

    const level = response.ok ? LogLevel.INFO : LogLevel.WARN;

    this.log(
      level,
      correlationId,
      `API Response: ${response.status} ${response.ok ? 'OK' : 'ERROR'} (${response.duration}ms)`,
      this.config.verbose ? logData : undefined
    );
  }

  /**
   * Log an API error
   */
  logError(correlationId: string, error: ErrorLogEntry): void {
    const logData: Partial<ErrorLogEntry> = {
      message: error.message,
      code: error.code,
      status: error.status,
    };

    if (this.config.verbose && error.stack) {
      logData.stack = error.stack;
    }

    if (this.config.verbose && error.request) {
      logData.request = {
        method: error.request.method,
        url: this.sanitizeUrl(error.request.url),
      };
    }

    if (this.config.verbose && error.response) {
      logData.response = {
        status: error.response.status,
        ok: error.response.ok,
        duration: `${error.response.duration}ms`,
      };
    }

    this.log(
      LogLevel.ERROR,
      correlationId,
      `API Error: ${error.message}${error.status ? ` (${error.status})` : ''}`,
      this.config.verbose ? logData : undefined
    );
  }

  /**
   * Log a debug message
   */
  debug(correlationId: string, message: string, data?: unknown): void {
    this.log(LogLevel.DEBUG, correlationId, message, data);
  }

  /**
   * Log an info message
   */
  info(correlationId: string, message: string, data?: unknown): void {
    this.log(LogLevel.INFO, correlationId, message, data);
  }

  /**
   * Log a warning message
   */
  warn(correlationId: string, message: string, data?: unknown): void {
    this.log(LogLevel.WARN, correlationId, message, data);
  }

  /**
   * Log an error message
   */
  error(correlationId: string, message: string, data?: unknown): void {
    this.log(LogLevel.ERROR, correlationId, message, data);
  }

  /**
   * Sanitize URL to remove sensitive query parameters
   */
  private sanitizeUrl(url: string): string {
    try {
      const urlObj = new URL(url);
      const params = urlObj.searchParams;

      // Sanitize sensitive query parameters
      for (const key of params.keys()) {
        if (SENSITIVE_PATTERNS.some(pattern => pattern.test(key))) {
          params.set(key, '[REDACTED]');
        }
      }

      return urlObj.toString();
    } catch {
      // If URL parsing fails, return original
      return url;
    }
  }

  /**
   * Log retry attempt
   */
  logRetry(correlationId: string, attemptNumber: number, maxRetries: number, delay: number): void {
    this.log(
      LogLevel.WARN,
      correlationId,
      `Retry attempt ${attemptNumber}/${maxRetries} after ${delay}ms delay`
    );
  }

  /**
   * Log cache hit
   */
  logCacheHit(correlationId: string, cacheKey: string): void {
    this.log(LogLevel.DEBUG, correlationId, `Cache HIT: ${cacheKey}`);
  }

  /**
   * Log cache miss
   */
  logCacheMiss(correlationId: string, cacheKey: string): void {
    this.log(LogLevel.DEBUG, correlationId, `Cache MISS: ${cacheKey}`);
  }

  /**
   * Log cache set
   */
  logCacheSet(correlationId: string, cacheKey: string, ttl: number): void {
    this.log(LogLevel.DEBUG, correlationId, `Cache SET: ${cacheKey} (TTL: ${ttl}s)`);
  }

  /**
   * Log validation error
   */
  logValidationError(correlationId: string, path: string, errors: unknown): void {
    this.log(LogLevel.ERROR, correlationId, `Validation error for ${path}`, errors);
  }
}

/**
 * Default API logger instance
 */
export const apiLogger = new APILogger();

/**
 * Export log levels for external use
 */
export { LogLevel as ApiLogLevel };
