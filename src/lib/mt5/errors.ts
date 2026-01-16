/**
 * MT5 Error Handler
 *
 * Handles MT5 errors with user-friendly toast notifications.
 * Provides error classification, toast display, and reconnection support.
 */

import { toast } from "sonner";
import { MT5ErrorCode, MT5Error, MT5ConnectionState } from "./types";

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
