/**
 * MT5 Error Handler
 *
 * Handles MT5 errors with user-friendly toast notifications.
 * Provides error classification, toast display, and reconnection support.
 */

import { toast } from "sonner";
import { MT5ErrorCode, MT5Error, MT5ConnectionState } from "./types";
import { mt5Client } from "./client";

/**
 * Reconnection attempt result
 */
export interface ReconnectionResult {
  success: boolean;
  attempts: number;
  duration: number;
  error?: string;
}

/**
 * Reconnection statistics
 */
export interface ReconnectionStats {
  totalAttempts: number;
  successfulReconnections: number;
  failedReconnections: number;
  lastReconnectionTime?: Date;
  averageReconnectionTime?: number;
}

/**
 * Maximum reconnection attempts
 */
const MAX_RECONNECT_ATTEMPTS = 5;

/**
 * Reconnection statistics tracker
 */
const reconnectionStats: ReconnectionStats = {
  totalAttempts: 0,
  successfulReconnections: 0,
  failedReconnections: 0,
};

/**
 * Trading disabled state
 */
let isTradingDisabled = false;

/**
 * Get reconnection statistics
 */
export function getReconnectionStats(): ReconnectionStats {
  return { ...reconnectionStats };
}

/**
 * Check if trading is currently disabled
 */
export function isMT5TradingDisabled(): boolean {
  return isTradingDisabled;
}

/**
 * Enable trading (called after successful reconnection)
 */
export function enableMT5Trading(): void {
  if (isTradingDisabled) {
    isTradingDisabled = false;
    console.log('[MT5 Errors] Trading enabled');
  }
}

/**
 * Disable trading (called when MT5 disconnected)
 */
export function disableMT5Trading(): void {
  if (!isTradingDisabled) {
    isTradingDisabled = true;
    console.log('[MT5 Errors] Trading disabled due to MT5 disconnection');
  }
}

/**
 * Error message mappings for MT5 error codes
 */
const ERROR_MESSAGES: Record<MT5ErrorCode, { title: string; description: string }> = {
  [MT5ErrorCode.TERMINAL_NOT_FOUND]: {
    title: "MT5 Terminal Not Found",
    description: "MetaTrader 5 terminal is not running or not accessible",
  },
  [MT5ErrorCode.LOGIN_FAILED]: {
    title: "MT5 Login Failed",
    description: "Failed to authenticate with MT5 terminal. Check your account credentials",
  },
  [MT5ErrorCode.CONNECTION_LOST]: {
    title: "MT5 Connection Lost",
    description: "Connection to MT5 terminal has been lost",
  },
  [MT5ErrorCode.ORDER_REJECTED]: {
    title: "Order Rejected",
    description: "Order was rejected by MT5 terminal",
  },
  [MT5ErrorCode.NOT_ENOUGH_MONEY]: {
    title: "Insufficient Funds",
    description: "Not enough free margin to open this position",
  },
  [MT5ErrorCode.MARKET_CLOSED]: {
    title: "Market Closed",
    description: "Market is currently closed for trading",
  },
  [MT5ErrorCode.INVALID_PRICE]: {
    title: "Invalid Price",
    description: "The specified price is invalid or outdated",
  },
  [MT5ErrorCode.INVALID_VOLUME]: {
    title: "Invalid Volume",
    description: "The specified volume is invalid for this symbol",
  },
  [MT5ErrorCode.INVALID_PARAMETERS]: {
    title: "Invalid Parameters",
    description: "One or more order parameters are invalid",
  },
  [MT5ErrorCode.SERVER_BUSY]: {
    title: "MT5 Server Busy",
    description: "MT5 terminal is busy. Please try again",
  },
  [MT5ErrorCode.TRADE_DISABLED]: {
    title: "Trading Disabled",
    description: "Trading is disabled for this account or symbol",
  },
  [MT5ErrorCode.POSITION_NOT_FOUND]: {
    title: "Position Not Found",
    description: "The specified position does not exist",
  },
  [MT5ErrorCode.INVALID_TICKET]: {
    title: "Invalid Ticket",
    description: "The specified ticket number is invalid",
  },
  [MT5ErrorCode.UNKNOWN_ERROR]: {
    title: "MT5 Error",
    description: "An unknown error occurred in MT5 terminal",
  },
};

/**
 * Create an MT5Error object
 */
export function createMT5Error(
  code: MT5ErrorCode,
  message?: string,
  details?: string
): MT5Error {
  const errorInfo = ERROR_MESSAGES[code];
  return {
    code,
    message: message || errorInfo.description,
    details: details || errorInfo.description,
  };
}

/**
 * Handle MT5 error with appropriate toast notification
 *
 * Shows different toast messages based on error type:
 * - CONNECTION_LOST: Shows warning toast with reconnection status
 * - ORDER_REJECTED: Shows error toast with error reason
 * - NOT_ENOUGH_MONEY: Shows error toast about insufficient funds
 * - MARKET_CLOSED: Shows error toast about market closure
 * - Other errors: Shows default error toast
 *
 * @param error - The MT5Error to handle
 * @param context - Optional context information for the error
 */
export function handleMT5Error(error: MT5Error, context?: string): void {
  const errorMessage = ERROR_MESSAGES[error.code];
  const contextPrefix = context ? `[${context}] ` : "";

  console.error(`${contextPrefix}MT5 Error:`, error);

  switch (error.code) {
    case MT5ErrorCode.CONNECTION_LOST:
      toast.warning(`${errorMessage.title}`, {
        description: `${errorMessage.description}. Attempting to reconnect...`,
        duration: 5000,
        id: `mt5-connection-lost-${Date.now()}`,
      });
      break;

    case MT5ErrorCode.ORDER_REJECTED:
      toast.error(`${errorMessage.title}`, {
        description: error.details || error.message || errorMessage.description,
        duration: 6000,
      });
      break;

    case MT5ErrorCode.NOT_ENOUGH_MONEY:
      toast.error(`${errorMessage.title}`, {
        description: error.message || errorMessage.description,
        duration: 5000,
      });
      break;

    case MT5ErrorCode.MARKET_CLOSED:
      toast.error(`${errorMessage.title}`, {
        description: errorMessage.description,
        duration: 5000,
      });
      break;

    case MT5ErrorCode.TERMINAL_NOT_FOUND:
    case MT5ErrorCode.LOGIN_FAILED:
      toast.error(`${errorMessage.title}`, {
        description: error.details || errorMessage.description,
        duration: 7000,
      });
      break;

    default:
      toast.error(errorMessage.title, {
        description: error.message || errorMessage.description,
        duration: 5000,
      });
      break;
  }
}

/**
 * Handle MT5 API errors from HTTP responses
 *
 * Parses error responses from MT5 API endpoints and converts them to MT5Error objects.
 * Handles both structured error responses and generic HTTP errors.
 *
 * @param statusCode - HTTP status code
 * @param responseBody - Response body from API call
 * @param context - Optional context information for the error
 * @returns MT5Error object
 */
export function handleMT5ApiError(
  statusCode: number,
  responseBody: unknown,
  context?: string
): MT5Error {
  let errorCode = MT5ErrorCode.UNKNOWN_ERROR;
  let errorMessage = "Unknown error occurred";
  let errorDetails: string | undefined;

  if (statusCode === 404) {
    errorCode = MT5ErrorCode.TERMINAL_NOT_FOUND;
    errorMessage = "MT5 terminal not found or not running";
  } else if (statusCode === 401) {
    errorCode = MT5ErrorCode.LOGIN_FAILED;
    errorMessage = "MT5 authentication failed";
  } else if (statusCode === 503) {
    errorCode = MT5ErrorCode.CONNECTION_LOST;
    errorMessage = "MT5 connection lost";
  }

  if (typeof responseBody === "object" && responseBody !== null) {
    const body = responseBody as Record<string, unknown>;
    if (typeof body.error === "string") {
      errorMessage = body.error;
    }
    if (typeof body.code === "string") {
      const codeUpper = body.code.toUpperCase() as keyof typeof MT5ErrorCode;
      if (codeUpper in MT5ErrorCode) {
        errorCode = MT5ErrorCode[codeUpper];
      }
    }
    if (typeof body.details === "string") {
      errorDetails = body.details;
    }
  } else if (typeof responseBody === "string") {
    errorMessage = responseBody;
  }

  const error = createMT5Error(errorCode, errorMessage, errorDetails);
  handleMT5Error(error, context);
  return error;
}

/**
 * Get user-friendly error message for an MT5 error code
 *
 * @param code - MT5ErrorCode to get message for
 * @returns Object with title and description
 */
export function getErrorMessage(code: MT5ErrorCode): {
  title: string;
  description: string;
} {
  return ERROR_MESSAGES[code];
}

/**
 * Check if an error is retryable
 *
 * Returns true for errors that may be resolved by retrying the operation.
 *
 * @param error - MT5Error to check
 * @returns True if error is retryable
 */
export function isRetryableError(error: MT5Error): boolean {
  return [
    MT5ErrorCode.CONNECTION_LOST,
    MT5ErrorCode.SERVER_BUSY,
    MT5ErrorCode.INVALID_PRICE,
  ].includes(error.code);
}

/**
 * Check if an error should disable trading
 *
 * Returns true for errors that prevent trading operations.
 *
 * @param error - MT5Error to check
 * @returns True if trading should be disabled
 */
export function shouldDisableTrading(error: MT5Error): boolean {
  return [
    MT5ErrorCode.CONNECTION_LOST,
    MT5ErrorCode.TERMINAL_NOT_FOUND,
    MT5ErrorCode.LOGIN_FAILED,
    MT5ErrorCode.TRADE_DISABLED,
    MT5ErrorCode.MARKET_CLOSED,
  ].includes(error.code);
}

/**
 * Calculate exponential backoff delay
 *
 * Implements exponential backoff: 1s, 2s, 4s, 8s, 16s
 *
 * @param attemptNumber - Current attempt number (1-indexed)
 * @returns Delay in milliseconds
 */
function calculateBackoffDelay(attemptNumber: number): number {
  const baseDelay = 1000; // 1 second
  const maxDelay = 16000; // 16 seconds
  const delay = Math.min(baseDelay * Math.pow(2, attemptNumber - 1), maxDelay);
  return delay;
}

/**
 * Sleep for specified milliseconds
 *
 * @param ms - Milliseconds to sleep
 * @returns Promise that resolves after delay
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Attempt to reconnect to MT5 with exponential backoff
 *
 * Implements automatic reconnection with:
 * - Exponential backoff: 1s, 2s, 4s, 8s, 16s (5 attempts max)
 * - Toast notifications during reconnection attempts
 * - Success toast when reconnected
 * - Error toast after all attempts fail
 * - Trading disabled when MT5 disconnected
 * - Reconnection success rate tracking
 * - Detailed logging of all attempts
 *
 * @returns Promise with reconnection result
 */
export async function attemptMT5Reconnect(): Promise<ReconnectionResult> {
  const startTime = Date.now();
  let lastError: string | undefined;

  console.log('[MT5 Errors] Starting auto-reconnect sequence');
  reconnectionStats.totalAttempts++;

  // Disable trading when attempting to reconnect
  disableMT5Trading();

  for (let attempt = 1; attempt <= MAX_RECONNECT_ATTEMPTS; attempt++) {
    const delay = calculateBackoffDelay(attempt);

    console.log(`[MT5 Errors] Reconnection attempt ${attempt}/${MAX_RECONNECT_ATTEMPTS} after ${delay}ms delay`);

    // Show reconnection toast
    if (attempt === 1) {
      toast.info('Reconnecting to MT5...', {
        description: `Attempt 1 of ${MAX_RECONNECT_ATTEMPTS}. Please wait.`,
        duration: 3000,
        id: 'mt5-reconnecting',
      });
    }

    // Wait for backoff delay (skip delay on first attempt for faster response)
    if (attempt > 1) {
      await sleep(delay);
    }

    try {
      // Attempt to connect
      await mt5Client.connect();

      const duration = Date.now() - startTime;

      // Success!
      reconnectionStats.successfulReconnections++;
      reconnectionStats.lastReconnectionTime = new Date();

      // Update average reconnection time
      if (reconnectionStats.successfulReconnections === 1) {
        reconnectionStats.averageReconnectionTime = duration;
      } else {
        const total = (reconnectionStats.averageReconnectionTime || 0) * (reconnectionStats.successfulReconnections - 1);
        reconnectionStats.averageReconnectionTime = (total + duration) / reconnectionStats.successfulReconnections;
      }

      // Enable trading after successful reconnection
      enableMT5Trading();

      console.log(`[MT5 Errors] Reconnection successful after ${attempt} attempt(s) (${duration}ms)`);

      // Show success toast
      toast.success('MT5 Reconnected', {
        description: `Successfully reconnected to MT5 after ${attempt} attempt${attempt > 1 ? 's' : ''}`,
        duration: 5000,
        id: 'mt5-reconnect-success',
      });

      return {
        success: true,
        attempts: attempt,
        duration,
      };
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      lastError = errorMessage;

      console.error(`[MT5 Errors] Reconnection attempt ${attempt} failed:`, errorMessage);

      // Update toast with current attempt
      if (attempt < MAX_RECONNECT_ATTEMPTS) {
        toast.info('Reconnecting to MT5...', {
          description: `Attempt ${attempt + 1} of ${MAX_RECONNECT_ATTEMPTS}. Retrying...`,
          duration: 3000,
          id: 'mt5-reconnecting',
        });
      }
    }
  }

  // All attempts failed
  const duration = Date.now() - startTime;
  reconnectionStats.failedReconnections++;

  console.error(`[MT5 Errors] All ${MAX_RECONNECT_ATTEMPTS} reconnection attempts failed (${duration}ms)`);

  // Show error toast
  toast.error('MT5 Reconnection Failed', {
    description: `Failed to reconnect after ${MAX_RECONNECT_ATTEMPTS} attempts. ${lastError || 'Please check your connection and try manually.'}`,
    duration: 8000,
    id: 'mt5-reconnect-failed',
  });

  return {
    success: false,
    attempts: MAX_RECONNECT_ATTEMPTS,
    duration,
    error: lastError,
  };
}

/**
 * Reset reconnection statistics
 *
 * Call this after a successful manual connection to reset stats.
 */
export function resetReconnectionStats(): void {
  reconnectionStats.totalAttempts = 0;
  reconnectionStats.successfulReconnections = 0;
  reconnectionStats.failedReconnections = 0;
  reconnectionStats.lastReconnectionTime = undefined;
  reconnectionStats.averageReconnectionTime = undefined;
  console.log('[MT5 Errors] Reconnection statistics reset');
}
