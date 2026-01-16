/**
 * MT5 Position Management Functions
 *
 * Functions for managing open positions in MetaTrader 5 terminal.
 * Supports fetching, closing, and modifying positions with partial close support.
 */

import { get, post, put } from '../api/client';
import type {
  MT5Position,
  MT5Error,
  MT5ErrorCode,
} from './types';

/**
 * Close position request parameters
 */
export interface CloseMT5PositionRequest {
  /** Position ticket number (required) */
  ticket: number;
  /** Optional volume for partial close (if not specified, closes full position) */
  lots?: number;
}

/**
 * Modify position request parameters
 */
export interface ModifyMT5PositionRequest {
  /** Position ticket number (required) */
  ticket: number;
  /** New stop loss price (optional, set to 0 to remove) */
  stopLoss?: number;
  /** New take profit price (optional, set to 0 to remove) */
  takeProfit?: number;
}

/**
 * Position modification result
 */
export interface MT5PositionOperationResult {
  /** Operation success status */
  success: boolean;
  /** Position ticket number */
  ticket?: number;
  /** Error details if operation failed */
  error?: MT5Error;
  /** Operation message */
  message?: string;
}

/**
 * Convert HTTP error status to MT5 error code
 */
function getMT5ErrorCodeFromStatus(status?: number, message?: string): MT5ErrorCode {
  if (status === 400) return 'INVALID_PARAMETERS';
  if (status === 401) return 'LOGIN_FAILED';
  if (status === 403) return 'TRADE_DISABLED';
  if (status === 404) return 'POSITION_NOT_FOUND';
  if (status === 409) return 'SERVER_BUSY';
  if (status === 422) return 'INVALID_TICKET';
  if (status === 423) return 'INVALID_PRICE';
  if (status === 502) return 'CONNECTION_LOST';
  if (status === 503) return 'SERVER_BUSY';

  if (message) {
    const lowerMessage = message.toLowerCase();
    if (lowerMessage.includes('position not found') || lowerMessage.includes('invalid ticket')) {
      return 'POSITION_NOT_FOUND';
    }
    if (lowerMessage.includes('invalid price')) {
      return 'INVALID_PRICE';
    }
    if (lowerMessage.includes('trade disabled') || lowerMessage.includes('trading disabled')) {
      return 'TRADE_DISABLED';
    }
    if (lowerMessage.includes('market closed') || lowerMessage.includes('market is closed')) {
      return 'MARKET_CLOSED';
    }
    if (lowerMessage.includes('connection lost') || lowerMessage.includes('not connected')) {
      return 'CONNECTION_LOST';
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
 * Log position operation attempt
 */
function logPositionAttempt(
  action: string,
  ticket: number,
  details?: Record<string, unknown>
): void {
  const logPrefix = `[MT5 Position] ${action} (Ticket: ${ticket})`;
  console.log(logPrefix, details || {});
}

/**
 * Log position operation result
 */
function logPositionResult(
  action: string,
  result: MT5PositionOperationResult,
  duration: number
): void {
  if (result.success) {
    console.log(`[MT5 Position] ${action} SUCCESS`, {
      ticket: result.ticket,
      message: result.message,
      duration: `${duration}ms`,
    });
  } else {
    console.error(`[MT5 Position] ${action} FAILED`, {
      ticket: result.ticket,
      error: result.error,
      duration: `${duration}ms`,
    });
  }
}

/**
 * Validate ticket number
 */
function validateTicket(ticket: number): MT5Error | null {
  if (!ticket || ticket <= 0) {
    return createMT5Error('INVALID_TICKET', 'Ticket number must be greater than 0');
  }
  if (ticket > 2147483647) {
    return createMT5Error('INVALID_TICKET', 'Ticket number exceeds maximum allowed value');
  }
  return null;
}

/**
 * Validate lots value for partial close
 */
function validateLots(lots?: number): MT5Error | null {
  if (lots !== undefined) {
    if (lots <= 0) {
      return createMT5Error('INVALID_VOLUME', 'Lots must be greater than 0 for partial close');
    }
    if (lots > 100) {
      return createMT5Error('INVALID_VOLUME', 'Lots exceeds maximum allowed (100 lots)');
    }
  }
  return null;
}

/**
 * Validate stop loss and take profit values
 */
function validateStopLossTakeProfit(
  stopLoss?: number,
  takeProfit?: number
): MT5Error | null {
  if (stopLoss !== undefined && stopLoss < 0) {
    return createMT5Error('INVALID_PRICE', 'Stop loss cannot be negative');
  }
  if (takeProfit !== undefined && takeProfit < 0) {
    return createMT5Error('INVALID_PRICE', 'Take profit cannot be negative');
  }
  return null;
}

/**
 * Get all open MT5 positions
 *
 * Fetches the list of all currently open positions from MT5 terminal.
 * Returns an array of MT5Position objects containing position details.
 *
 * @returns Promise<MT5Position[]> - Array of open positions
 *
 * @example
 * ```typescript
 * const positions = await getMT5Positions();
 * console.log(`Found ${positions.length} open positions`);
 * positions.forEach(pos => {
 *   console.log(`${pos.symbol} ${pos.direction}: ${pos.volume} lots @ ${pos.openPrice}`);
 * });
 * ```
 */
export async function getMT5Positions(): Promise<MT5Position[]> {
  const startTime = Date.now();

  try {
    logPositionAttempt('getMT5Positions', 0, { action: 'fetch' });

    const response = await get<{ positions: MT5Position[] }>('/mt5/positions/open');

    const duration = Date.now() - startTime;

    if (response.ok && response.data.positions) {
      console.log(`[MT5 Position] getMT5Positions SUCCESS`, {
        count: response.data.positions.length,
        duration: `${duration}ms`,
      });
      return response.data.positions;
    }

    // Return empty array on error
    console.warn(`[MT5 Position] getMT5Positions returned empty result`, {
      duration: `${duration}ms`,
    });
    return [];

  } catch (error) {
    const duration = Date.now() - startTime;
    const mt5Error = createMT5Error(
      'UNKNOWN_ERROR',
      error instanceof Error ? error.message : 'Failed to fetch positions',
      error instanceof Error ? error.stack : undefined
    );

    console.error(`[MT5 Position] getMT5Positions FAILED`, {
      error: mt5Error,
      duration: `${duration}ms`,
    });

    // Return empty array instead of throwing
    return [];
  }
}

/**
 * Close an MT5 position (full or partial close)
 *
 * Closes the specified position. If lots parameter is provided,
 * performs a partial close. Otherwise, closes the full position.
 *
 * @param request - Close position request with ticket and optional lots
 * @returns Promise<boolean> - True if position was closed successfully
 *
 * @example
 * ```typescript
 * // Full position close
 * const closed = await closeMT5Position({ ticket: 123456 });
 *
 * // Partial close (close 0.5 lots of a 1.0 lot position)
 * const partialClosed = await closeMT5Position({ ticket: 123456, lots: 0.5 });
 * ```
 */
export async function closeMT5Position(
  request: CloseMT5PositionRequest
): Promise<boolean> {
  const startTime = Date.now();

  // Validate ticket
  const ticketError = validateTicket(request.ticket);
  if (ticketError) {
    logPositionResult('closeMT5Position', {
      success: false,
      ticket: request.ticket,
      error: ticketError,
    }, Date.now() - startTime);
    return false;
  }

  // Validate lots for partial close
  const lotsError = validateLots(request.lots);
  if (lotsError) {
    logPositionResult('closeMT5Position', {
      success: false,
      ticket: request.ticket,
      error: lotsError,
    }, Date.now() - startTime);
    return false;
  }

  logPositionAttempt('closeMT5Position', request.ticket, {
    lots: request.lots ?? 'full',
  });

  try {
    const response = await post<{ success: boolean; message?: string }>(
      '/mt5/positions/close',
      {
        ticket: request.ticket,
        lots: request.lots,
      }
    );

    const duration = Date.now() - startTime;

    if (response.ok && response.data.success) {
      logPositionResult('closeMT5Position', {
        success: true,
        ticket: request.ticket,
        message: response.data.message,
      }, duration);
      return true;
    }

    // Error response from backend
    const errorCode = getMT5ErrorCodeFromStatus(response.status, response.data.message);
    const error = createMT5Error(
      errorCode,
      response.data.message || 'Failed to close position',
      response.status ? `HTTP ${response.status}` : undefined
    );

    logPositionResult('closeMT5Position', {
      success: false,
      ticket: request.ticket,
      error,
    }, duration);

    return false;

  } catch (error) {
    const duration = Date.now() - startTime;

    // Network or unexpected error
    const mt5Error = createMT5Error(
      'UNKNOWN_ERROR',
      error instanceof Error ? error.message : 'Failed to close position',
      error instanceof Error ? error.stack : undefined
    );

    logPositionResult('closeMT5Position', {
      success: false,
      ticket: request.ticket,
      error: mt5Error,
    }, duration);

    return false;
  }
}

/**
 * Modify an MT5 position (stop loss and/or take profit)
 *
 * Updates the stop loss and/or take profit values for the specified position.
 * Set SL/TP to 0 to remove the existing stop loss or take profit.
 *
 * @param request - Modify position request with ticket and sl/tp values
 * @returns Promise<boolean> - True if position was modified successfully
 *
 * @example
 * ```typescript
 * // Update stop loss and take profit
 * const modified = await modifyMT5Position({
 *   ticket: 123456,
 *   stopLoss: 12345.5,
 *   takeProfit: 12350.0,
 * });
 *
 * // Remove stop loss (set to 0)
 * const noSL = await modifyMT5Position({
 *   ticket: 123456,
 *   stopLoss: 0,
 * });
 * ```
 */
export async function modifyMT5Position(
  request: ModifyMT5PositionRequest
): Promise<boolean> {
  const startTime = Date.now();

  // Validate ticket
  const ticketError = validateTicket(request.ticket);
  if (ticketError) {
    logPositionResult('modifyMT5Position', {
      success: false,
      ticket: request.ticket,
      error: ticketError,
    }, Date.now() - startTime);
    return false;
  }

  // Validate stop loss and take profit
  const sltpError = validateStopLossTakeProfit(request.stopLoss, request.takeProfit);
  if (sltpError) {
    logPositionResult('modifyMT5Position', {
      success: false,
      ticket: request.ticket,
      error: sltpError,
    }, Date.now() - startTime);
    return false;
  }

  // Check if at least one modification is provided
  if (request.stopLoss === undefined && request.takeProfit === undefined) {
    const error = createMT5Error(
      'INVALID_PARAMETERS',
      'At least one of stopLoss or takeProfit must be specified'
    );
    logPositionResult('modifyMT5Position', {
      success: false,
      ticket: request.ticket,
      error,
    }, Date.now() - startTime);
    return false;
  }

  logPositionAttempt('modifyMT5Position', request.ticket, {
    stopLoss: request.stopLoss,
    takeProfit: request.takeProfit,
  });

  try {
    const response = await put<{ success: boolean; message?: string }>(
      '/mt5/positions/modify',
      {
        ticket: request.ticket,
        stopLoss: request.stopLoss,
        takeProfit: request.takeProfit,
      }
    );

    const duration = Date.now() - startTime;

    if (response.ok && response.data.success) {
      logPositionResult('modifyMT5Position', {
        success: true,
        ticket: request.ticket,
        message: response.data.message,
      }, duration);
      return true;
    }

    // Error response from backend
    const errorCode = getMT5ErrorCodeFromStatus(response.status, response.data.message);
    const error = createMT5Error(
      errorCode,
      response.data.message || 'Failed to modify position',
      response.status ? `HTTP ${response.status}` : undefined
    );

    logPositionResult('modifyMT5Position', {
      success: false,
      ticket: request.ticket,
      error,
    }, duration);

    return false;

  } catch (error) {
    const duration = Date.now() - startTime;

    // Network or unexpected error
    const mt5Error = createMT5Error(
      'UNKNOWN_ERROR',
      error instanceof Error ? error.message : 'Failed to modify position',
      error instanceof Error ? error.stack : undefined
    );

    logPositionResult('modifyMT5Position', {
      success: false,
      ticket: request.ticket,
      error: mt5Error,
    }, duration);

    return false;
  }
}
