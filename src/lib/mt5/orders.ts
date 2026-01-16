/**
 * MT5 Order Execution Functions
 *
 * Functions for executing market and pending orders through MetaTrader 5 terminal.
 */

import { post } from '../api/client';
import type {
  MT5OrderRequest,
  MT5OrderResult,
  MT5Error,
  MT5ErrorCode,
} from './types';

/**
 * Default magic number for system identification
 * Used to distinguish orders placed by this trading system
 */
export const DEFAULT_MAGIC_NUMBER = 123456;

/**
 * Maximum number of order retry attempts
 */
const MAX_ORDER_RETRIES = 3;

/**
 * Delay between retry attempts in milliseconds
 */
const RETRY_DELAY_MS = 1000;

/**
 * Sleep utility for retry delays
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Convert HTTP error status to MT5 error code
 */
function getMT5ErrorCodeFromStatus(status?: number, message?: string): MT5ErrorCode {
  if (status === 400) return 'INVALID_PARAMETERS';
  if (status === 401) return 'LOGIN_FAILED';
  if (status === 403) return 'TRADE_DISABLED';
  if (status === 404) return 'TERMINAL_NOT_FOUND';
  if (status === 409) return 'SERVER_BUSY';
  if (status === 422) return 'INVALID_VOLUME';
  if (status === 423) return 'INVALID_PRICE';
  if (status === 502) return 'CONNECTION_LOST';
  if (status === 503) return 'SERVER_BUSY';

  if (message) {
    const lowerMessage = message.toLowerCase();
    if (lowerMessage.includes('not enough money') || lowerMessage.includes('insufficient funds')) {
      return 'NOT_ENOUGH_MONEY';
    }
    if (lowerMessage.includes('market closed') || lowerMessage.includes('market is closed')) {
      return 'MARKET_CLOSED';
    }
    if (lowerMessage.includes('invalid price')) {
      return 'INVALID_PRICE';
    }
    if (lowerMessage.includes('invalid volume') || lowerMessage.includes('invalid lots')) {
      return 'INVALID_VOLUME';
    }
    if (lowerMessage.includes('order rejected') || lowerMessage.includes('rejected')) {
      return 'ORDER_REJECTED';
    }
    if (lowerMessage.includes('trade disabled') || lowerMessage.includes('trading disabled')) {
      return 'TRADE_DISABLED';
    }
  }

  return 'UNKNOWN_ERROR';
}

/**
 * Create MT5 error object
 */
function createMT5Error(code: MT5ErrorCode, message: string, details?: string): MT5Error {
  return {
    code,
    message,
    details,
  };
}

/**
 * Log order attempt
 */
function logOrderAttempt(
  action: string,
  request: MT5OrderRequest,
  attempt: number,
  maxAttempts: number
): void {
  const logPrefix = `[MT5 Order] ${action} (Attempt ${attempt}/${maxAttempts})`;
  const logData = {
    symbol: request.symbol,
    orderType: request.orderType,
    volume: request.volume,
    price: request.price,
    stopLoss: request.stopLoss,
    takeProfit: request.takeProfit,
    magic: request.magic,
    comment: request.comment,
  };

  console.log(logPrefix, logData);
}

/**
 * Log order result
 */
function logOrderResult(
  action: string,
  result: MT5OrderResult,
  duration: number
): void {
  if (result.success) {
    console.log(`[MT5 Order] ${action} SUCCESS`, {
      ticket: result.ticket,
      executionPrice: result.executionPrice,
      executionTime: result.executionTime,
      duration: `${duration}ms`,
    });
  } else {
    console.error(`[MT5 Order] ${action} FAILED`, {
      error: result.error,
      duration: `${duration}ms`,
    });
  }
}

/**
 * Execute an MT5 order with retry logic
 *
 * @param request - Order request parameters
 * @param evolutionGeneration - Current evolution generation number (included in comment)
 * @param retries - Number of retry attempts (default: MAX_ORDER_RETRIES)
 * @returns Promise<MT5OrderResult> - Order execution result
 *
 * @example
 * ```typescript
 * const result = await executeMT5Order(
 *   {
 *     symbol: 'V10',
 *     volume: 0.01,
 *     orderType: 'BUY',
 *     stopLoss: 12345.5,
 *     takeProfit: 12346.5,
 *   },
 *   42
 * );
 *
 * if (result.success) {
 *   console.log(`Order placed: ${result.ticket}`);
 * } else {
 *   console.error(`Order failed: ${result.error?.message}`);
 * }
 * ```
 */
export async function executeMT5Order(
  request: MT5OrderRequest,
  evolutionGeneration: number,
  retries: number = MAX_ORDER_RETRIES
): Promise<MT5OrderResult> {
  const startTime = Date.now();

  // Set default magic number if not provided
  const orderRequest: MT5OrderRequest = {
    ...request,
    magic: request.magic ?? DEFAULT_MAGIC_NUMBER,
  };

  // Add evolution generation to comment
  const evolutionComment = orderRequest.comment
    ? `${orderRequest.comment} | Gen:${evolutionGeneration}`
    : `Gen:${evolutionGeneration}`;

  orderRequest.comment = evolutionComment;

  // Validate order request
  const validationError = validateOrderRequest(orderRequest);
  if (validationError) {
    const duration = Date.now() - startTime;
    const result: MT5OrderResult = {
      success: false,
      error: validationError,
    };
    logOrderResult('executeMT5Order', result, duration);
    return result;
  }

  // Retry loop
  for (let attempt = 1; attempt <= retries; attempt++) {
    logOrderAttempt('executeMT5Order', orderRequest, attempt, retries);

    try {
      // Call POST /mt5/orders/execute endpoint
      const response = await post<{ ticket?: number; executionPrice?: number; message?: string }>(
        '/mt5/orders/execute',
        orderRequest
      );

      const duration = Date.now() - startTime;

      // Success response
      if (response.ok && response.data.ticket) {
        const result: MT5OrderResult = {
          success: true,
          ticket: response.data.ticket,
          executionPrice: response.data.executionPrice,
          executionTime: new Date(),
          comment: orderRequest.comment,
        };
        logOrderResult('executeMT5Order', result, duration);
        return result;
      }

      // Error response from backend
      if (!response.ok) {
        const errorCode = getMT5ErrorCodeFromStatus(response.status, response.data.message);
        const error = createMT5Error(
          errorCode,
          response.data.message || 'Order execution failed',
          response.status ? `HTTP ${response.status}` : undefined
        );

        // Don't retry on certain errors
        if (shouldNotRetry(errorCode)) {
          const result: MT5OrderResult = {
            success: false,
            error,
          };
          logOrderResult('executeMT5Order', result, duration);
          return result;
        }

        // Retry on other errors
        if (attempt < retries) {
          console.warn(`[MT5 Order] Retry ${attempt}/${retries} after error: ${error.message}`);
          await sleep(RETRY_DELAY_MS * attempt); // Exponential backoff
          continue;
        }

        const result: MT5OrderResult = {
          success: false,
          error,
        };
        logOrderResult('executeMT5Order', result, duration);
        return result;
      }

    } catch (error) {
      const duration = Date.now() - startTime;

      // Network or unexpected error
      const mt5Error = createMT5Error(
        'UNKNOWN_ERROR',
        error instanceof Error ? error.message : 'Unknown error occurred',
        error instanceof Error ? error.stack : undefined
      );

      if (attempt < retries) {
        console.warn(`[MT5 Order] Retry ${attempt}/${retries} after error: ${mt5Error.message}`);
        await sleep(RETRY_DELAY_MS * attempt);
        continue;
      }

      const result: MT5OrderResult = {
        success: false,
        error: mt5Error,
      };
      logOrderResult('executeMT5Order', result, duration);
      return result;
    }
  }

  // Should never reach here, but handle gracefully
  const duration = Date.now() - startTime;
  const result: MT5OrderResult = {
    success: false,
    error: createMT5Error('UNKNOWN_ERROR', 'Order execution failed after all retries'),
  };
  logOrderResult('executeMT5Order', result, duration);
  return result;
}

/**
 * Execute a market order (instant execution)
 *
 * Convenience function for market orders. Market orders are executed
 * immediately at the current market price.
 *
 * @param symbol - Trading symbol (e.g., 'V10', 'V25')
 * @param direction - Order direction ('BUY' or 'SELL')
 * @param volume - Order volume in lots
 * @param stopLoss - Optional stop loss price
 * @param takeProfit - Optional take profit price
 * @param evolutionGeneration - Current evolution generation number
 * @param magic - Optional magic number (defaults to DEFAULT_MAGIC_NUMBER)
 * @returns Promise<MT5OrderResult> - Order execution result
 *
 * @example
 * ```typescript
 * const result = await executeMarketOrder(
 *   'V10',
 *   'BUY',
 *   0.01,
 *   12345.5,
 *   12346.5,
 *   42
 * );
 * ```
 */
export async function executeMarketOrder(
  symbol: string,
  direction: 'BUY' | 'SELL',
  volume: number,
  stopLoss?: number,
  takeProfit?: number,
  evolutionGeneration?: number,
  magic?: number
): Promise<MT5OrderResult> {
  return executeMT5Order(
    {
      symbol,
      volume,
      orderType: direction,
      stopLoss,
      takeProfit,
      magic,
    },
    evolutionGeneration ?? 0
  );
}

/**
 * Execute a pending order (limit or stop)
 *
 * Convenience function for pending orders. Pending orders are executed
 * when the price reaches the specified level.
 *
 * @param symbol - Trading symbol (e.g., 'V10', 'V25')
 * @param orderType - Order type ('BUY_LIMIT', 'SELL_LIMIT', 'BUY_STOP', 'SELL_STOP')
 * @param volume - Order volume in lots
 * @param price - Target price for order execution
 * @param stopLoss - Optional stop loss price
 * @param takeProfit - Optional take profit price
 * @param expiration - Optional order expiration date
 * @param evolutionGeneration - Current evolution generation number
 * @param magic - Optional magic number (defaults to DEFAULT_MAGIC_NUMBER)
 * @returns Promise<MT5OrderResult> - Order execution result
 *
 * @example
 * ```typescript
 * const result = await executePendingOrder(
 *   'V10',
 *   'BUY_LIMIT',
 *   0.01,
 *   12344.0,
 *   12345.5,
 *   12346.5,
 *   new Date(Date.now() + 3600000), // 1 hour from now
 *   42
 * );
 * ```
 */
export async function executePendingOrder(
  symbol: string,
  orderType: 'BUY_LIMIT' | 'SELL_LIMIT' | 'BUY_STOP' | 'SELL_STOP',
  volume: number,
  price: number,
  stopLoss?: number,
  takeProfit?: number,
  expiration?: Date,
  evolutionGeneration?: number,
  magic?: number
): Promise<MT5OrderResult> {
  return executeMT5Order(
    {
      symbol,
      volume,
      orderType,
      price,
      stopLoss,
      takeProfit,
      expiration,
      magic,
    },
    evolutionGeneration ?? 0
  );
}

/**
 * Validate order request parameters
 *
 * Checks for common errors before sending the order to MT5.
 */
function validateOrderRequest(request: MT5OrderRequest): MT5Error | null {
  // Check symbol
  if (!request.symbol || typeof request.symbol !== 'string' || request.symbol.trim().length === 0) {
    return createMT5Error('INVALID_PARAMETERS', 'Symbol is required and must be a non-empty string');
  }

  // Check volume
  if (!request.volume || request.volume <= 0) {
    return createMT5Error('INVALID_VOLUME', 'Volume must be greater than 0');
  }
  if (request.volume > 100) {
    return createMT5Error('INVALID_VOLUME', 'Volume exceeds maximum allowed (100 lots)');
  }

  // Check order type
  const validOrderTypes = ['BUY', 'SELL', 'BUY_LIMIT', 'SELL_LIMIT', 'BUY_STOP', 'SELL_STOP'];
  if (!validOrderTypes.includes(request.orderType)) {
    return createMT5Error('INVALID_PARAMETERS', `Invalid order type: ${request.orderType}`);
  }

  // Check price for pending orders
  if (['BUY_LIMIT', 'SELL_LIMIT', 'BUY_STOP', 'SELL_STOP'].includes(request.orderType)) {
    if (!request.price || request.price <= 0) {
      return createMT5Error('INVALID_PRICE', 'Price is required for pending orders and must be greater than 0');
    }
  }

  // Check stop loss and take profit
  if (request.stopLoss !== undefined && request.stopLoss <= 0) {
    return createMT5Error('INVALID_PRICE', 'Stop loss must be greater than 0');
  }
  if (request.takeProfit !== undefined && request.takeProfit <= 0) {
    return createMT5Error('INVALID_PRICE', 'Take profit must be greater than 0');
  }

  // Check magic number
  if (request.magic !== undefined && (request.magic < 0 || request.magic > 2147483647)) {
    return createMT5Error('INVALID_PARAMETERS', 'Magic number must be between 0 and 2147483647');
  }

  return null;
}

/**
 * Determine if an error should not be retried
 *
 * Certain errors should not be retried as they will fail again.
 */
function shouldNotRetry(errorCode: MT5ErrorCode): boolean {
  const noRetryErrors: MT5ErrorCode[] = [
    'INVALID_PARAMETERS',
    'INVALID_VOLUME',
    'INVALID_PRICE',
    'NOT_ENOUGH_MONEY',
    'MARKET_CLOSED',
    'TRADE_DISABLED',
    'LOGIN_FAILED',
  ];

  return noRetryErrors.includes(errorCode);
}
