/**
 * MT5 Trade History Functions
 *
 * Functions for accessing and exporting MetaTrader 5 trade history.
 * Supports fetching history by date range and symbol, with CSV export functionality.
 */

import { get } from '../api/client';
import type {
  MT5TradeHistory,
  MT5Error,
  MT5ErrorCode,
} from './types';

/**
 * Trade history request parameters
 */
export interface MT5TradeHistoryRequest {
  /** Optional start date filter (ISO date string) */
  startDate?: string;
  /** Optional end date filter (ISO date string) */
  endDate?: string;
  /** Optional symbol filter (e.g., 'V10', 'V25') */
  symbol?: string;
}

/**
 * Trade history response
 */
export interface MT5TradeHistoryResponse {
  /** Array of completed trades */
  trades: MT5TradeHistory[];
  /** Total number of trades */
  totalCount: number;
}

/**
 * Convert HTTP error status to MT5 error code
 */
function getMT5ErrorCodeFromStatus(status?: number, message?: string): MT5ErrorCode {
  if (status === 400) return 'INVALID_PARAMETERS';
  if (status === 401) return 'LOGIN_FAILED';
  if (status === 403) return 'TRADE_DISABLED';
  if (status === 502) return 'CONNECTION_LOST';
  if (status === 503) return 'SERVER_BUSY';

  if (message) {
    const lowerMessage = message.toLowerCase();
    if (lowerMessage.includes('connection lost') || lowerMessage.includes('not connected')) {
      return 'CONNECTION_LOST';
    }
    if (lowerMessage.includes('invalid parameters') || lowerMessage.includes('invalid date')) {
      return 'INVALID_PARAMETERS';
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
 * Validate trade history request parameters
 */
function validateHistoryRequest(request: MT5TradeHistoryRequest): MT5Error | null {
  if (request.startDate) {
    const startDate = new Date(request.startDate);
    if (isNaN(startDate.getTime())) {
      return createMT5Error('INVALID_PARAMETERS', 'Invalid start date format. Use ISO date string (e.g., "2024-01-01")');
    }
  }

  if (request.endDate) {
    const endDate = new Date(request.endDate);
    if (isNaN(endDate.getTime())) {
      return createMT5Error('INVALID_PARAMETERS', 'Invalid end date format. Use ISO date string (e.g., "2024-12-31")');
    }
  }

  if (request.startDate && request.endDate) {
    const startDate = new Date(request.startDate);
    const endDate = new Date(request.endDate);
    if (startDate > endDate) {
      return createMT5Error('INVALID_PARAMETERS', 'Start date cannot be after end date');
    }
  }

  if (request.symbol && request.symbol.trim().length === 0) {
    return createMT5Error('INVALID_PARAMETERS', 'Symbol cannot be empty');
  }

  return null;
}

/**
 * Log history request attempt
 */
function logHistoryAttempt(action: string, details?: Record<string, unknown>): void {
  const logPrefix = `[MT5 History] ${action}`;
  console.log(logPrefix, details || {});
}

/**
 * Log history request result
 */
function logHistoryResult(
  action: string,
  result: { success: boolean; count?: number; error?: MT5Error },
  duration: number
): void {
  if (result.success) {
    console.log(`[MT5 History] ${action} SUCCESS`, {
      count: result.count,
      duration: `${duration}ms`,
    });
  } else {
    console.error(`[MT5 History] ${action} FAILED`, {
      error: result.error,
      duration: `${duration}ms`,
    });
  }
}

/**
 * Get MT5 trade history
 *
 * Fetches the complete trade history from MT5 terminal with optional filters.
 * Returns an array of MT5TradeHistory objects containing completed trade details.
 *
 * @param request - Optional filters for startDate, endDate, and symbol
 * @returns Promise<MT5TradeHistory[]> - Array of completed trades
 *
 * @example
 * ```typescript
 * // Get all trade history
 * const allTrades = await getMT5TradeHistory();
 *
 * // Get trades for specific date range
 * const recentTrades = await getMT5TradeHistory({
 *   startDate: '2024-01-01',
 *   endDate: '2024-12-31',
 * });
 *
 * // Get trades for specific symbol
 * const v10Trades = await getMT5TradeHistory({ symbol: 'V10' });
 * ```
 */
export async function getMT5TradeHistory(
  request: MT5TradeHistoryRequest = {}
): Promise<MT5TradeHistory[]> {
  const startTime = Date.now();

  // Validate request parameters
  const validationError = validateHistoryRequest(request);
  if (validationError) {
    logHistoryResult('getMT5TradeHistory', {
      success: false,
      error: validationError,
    }, Date.now() - startTime);
    throw validationError;
  }

  logHistoryAttempt('getMT5TradeHistory', request);

  try {
    // Build query parameters
    const params: Record<string, string | undefined> = {};
    if (request.startDate) params.startDate = request.startDate;
    if (request.endDate) params.endDate = request.endDate;
    if (request.symbol) params.symbol = request.symbol;

    const response = await get<{ trades: MT5TradeHistory[]; totalCount?: number }>(
      '/mt5/history/trades',
      params
    );

    const duration = Date.now() - startTime;

    if (response.ok && response.data.trades) {
      logHistoryResult('getMT5TradeHistory', {
        success: true,
        count: response.data.trades.length,
      }, duration);

      // Convert date strings to Date objects
      const trades = response.data.trades.map((trade) => ({
        ...trade,
        openTime: new Date(trade.openTime),
        closeTime: new Date(trade.closeTime),
      }));

      return trades;
    }

    // Return empty array on error
    const error = createMT5Error(
      'UNKNOWN_ERROR',
      'Failed to fetch trade history from MT5',
      response.status ? `HTTP ${response.status}` : undefined
    );

    logHistoryResult('getMT5TradeHistory', {
      success: false,
      error,
    }, duration);

    return [];

  } catch (error) {
    const duration = Date.now() - startTime;

    // Network or unexpected error
    const mt5Error = createMT5Error(
      'UNKNOWN_ERROR',
      error instanceof Error ? error.message : 'Failed to fetch trade history',
      error instanceof Error ? error.stack : undefined
    );

    logHistoryResult('getMT5TradeHistory', {
      success: false,
      error: mt5Error,
    }, duration);

    // Return empty array instead of throwing
    return [];
  }
}

/**
 * Convert trade history array to CSV format
 *
 * Converts MT5TradeHistory array to CSV string with proper escaping
 * for special characters and commas.
 *
 * @param trades - Array of trade history objects
 * @returns string - CSV formatted string
 *
 * @example
 * ```typescript
 * const trades = await getMT5TradeHistory();
 * const csv = convertToCSV(trades);
 * console.log(csv);
 * ```
 */
export function convertToCSV(trades: MT5TradeHistory[]): string {
  if (trades.length === 0) {
    return '';
  }

  // CSV headers
  const headers = [
    'Ticket',
    'Symbol',
    'Direction',
    'Lots',
    'Open Price',
    'Close Price',
    'Open Time',
    'Close Time',
    'Profit',
    'Commission',
    'Swap',
    'Comment',
    'Magic Number',
  ];

  // Build CSV rows
  const rows = trades.map((trade) => {
    return [
      trade.ticket,
      trade.symbol,
      trade.direction,
      trade.lots,
      trade.openPrice,
      trade.closePrice,
      trade.openTime.toISOString(),
      trade.closeTime.toISOString(),
      trade.profit,
      trade.commission,
      trade.swap,
      trade.comment,
      trade.magic,
    ].map((value) => {
      // Convert to string and escape if contains comma, quote, or newline
      const stringValue = String(value);
      if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
        return `"${stringValue.replace(/"/g, '""')}"`;
      }
      return stringValue;
    }).join(',');
  });

  // Combine headers and rows
  return [headers.join(','), ...rows].join('\n');
}

/**
 * Download file to browser
 *
 * Creates a temporary download link and triggers browser download
 * for the given content with specified filename.
 *
 * @param content - File content as string
 * @param filename - Name of the file to download
 * @param mimeType - MIME type of the file (default: text/csv)
 *
 * @example
 * ```typescript
 * const csv = convertToCSV(trades);
 * downloadFile(csv, 'mt5-trades-2024.csv');
 * ```
 */
export function downloadFile(content: string, filename: string, mimeType: string = 'text/csv'): void {
  if (typeof window === 'undefined') {
    console.warn('[MT5 History] downloadFile called in non-browser environment');
    return;
  }

  try {
    // Create blob with content
    const blob = new Blob([content], { type: mimeType });

    // Create temporary download link
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;

    // Append to document, click, and cleanup
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    // Revoke object URL to free memory
    window.URL.revokeObjectURL(url);

    console.log(`[MT5 History] File downloaded: ${filename}`);
  } catch (error) {
    console.error('[MT5 History] Download failed:', error);
    throw new Error(
      error instanceof Error
        ? error.message
        : 'Failed to download file'
    );
  }
}

/**
 * Export MT5 trade history to CSV file
 *
 * Fetches trade history with optional filters and exports to CSV file.
 * Automatically generates filename with timestamp.
 *
 * @param request - Optional filters for startDate, endDate, and symbol
 * @returns Promise<void> - Downloads CSV file to browser
 *
 * @example
 * ```typescript
 * // Export all trade history
 * await exportMT5HistoryToCSV();
 *
 * // Export trades for specific date range
 * await exportMT5HistoryToCSV({
 *   startDate: '2024-01-01',
 *   endDate: '2024-12-31',
 * });
 *
 * // Export trades for specific symbol
 * await exportMT5HistoryToCSV({ symbol: 'V10' });
 * ```
 */
export async function exportMT5HistoryToCSV(
  request: MT5TradeHistoryRequest = {}
): Promise<void> {
  logHistoryAttempt('exportMT5HistoryToCSV', request);

  try {
    // Fetch trade history
    const trades = await getMT5TradeHistory(request);

    if (trades.length === 0) {
      console.warn('[MT5 History] No trades found for export');
      return;
    }

    // Convert to CSV
    const csv = convertToCSV(trades);

    // Generate filename with timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
    const symbolSuffix = request.symbol ? `-${request.symbol}` : '';
    const filename = `mt5-trades${symbolSuffix}-${timestamp}.csv`;

    // Download file
    downloadFile(csv, filename);

    logHistoryResult('exportMT5HistoryToCSV', {
      success: true,
      count: trades.length,
    }, Date.now());

  } catch (error) {
    const mt5Error = createMT5Error(
      'UNKNOWN_ERROR',
      error instanceof Error ? error.message : 'Failed to export trade history',
      error instanceof Error ? error.stack : undefined
    );

    logHistoryResult('exportMT5HistoryToCSV', {
      success: false,
      error: mt5Error,
    }, Date.now());

    throw mt5Error;
  }
}
