/**
 * MT5 Price Sync Functions
 *
 * Functions for syncing Deriv.com price data with MetaTrader 5 terminal
 * for analysis and trading operations.
 */

import { post } from '../api/client';
import type {
  DerivPriceData,
  PriceSyncResult,
  MT5Error,
  MT5ErrorCode,
} from './types';

/**
 * Symbol mapping from Deriv volatility indices to MT5 symbols
 *
 * Deriv.com uses volatility index symbols (V10, V25, V50, V75, V100)
 * which need to be mapped to corresponding MT5 symbol names.
 */
const DERIV_TO_MT5_SYMBOL_MAP: Record<string, string> = {
  'V10': 'Volatility 10 Index',
  'V25': 'Volatility 25 Index',
  'V50': 'Volatility 50 Index',
  'V75': 'Volatility 75 Index',
  'V100': 'Volatility 100 Index',
};

/**
 * Reverse mapping from MT5 symbols to Deriv symbols
 */
const MT5_TO_DERIV_SYMBOL_MAP: Record<string, string> = {
  'Volatility 10 Index': 'V10',
  'Volatility 25 Index': 'V25',
  'Volatility 50 Index': 'V50',
  'Volatility 75 Index': 'V75',
  'Volatility 100 Index': 'V100',
};

/**
 * Alternative MT5 symbol naming variations
 */
const ALTERNATIVE_MT5_SYMBOLS: Record<string, string[]> = {
  'V10': ['VOL10', 'Volatility10', 'VOLATILITY10'],
  'V25': ['VOL25', 'Volatility25', 'VOLATILITY25'],
  'V50': ['VOL50', 'Volatility50', 'VOLATILITY50'],
  'V75': ['VOL75', 'Volatility75', 'VOLATILITY75'],
  'V100': ['VOL100', 'Volatility100', 'VOLATILITY100'],
};

/**
 * Convert HTTP error status to MT5 error code
 */
function getMT5ErrorCodeFromStatus(status?: number, message?: string): MT5ErrorCode {
  if (status === 400) return 'INVALID_PARAMETERS';
  if (status === 401) return 'LOGIN_FAILED';
  if (status === 403) return 'TRADE_DISABLED';
  if (status === 404) return 'TERMINAL_NOT_FOUND';
  if (status === 409) return 'SERVER_BUSY';
  if (status === 502) return 'CONNECTION_LOST';
  if (status === 503) return 'SERVER_BUSY';

  if (message) {
    const lowerMessage = message.toLowerCase();
    if (lowerMessage.includes('connection lost') || lowerMessage.includes('not connected')) {
      return 'CONNECTION_LOST';
    }
    if (lowerMessage.includes('terminal not found') || lowerMessage.includes('mt5 not found')) {
      return 'TERMINAL_NOT_FOUND';
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
 * Map Deriv symbol to MT5 symbol
 *
 * @param derivSymbol - Deriv symbol (e.g., 'V10', 'V25')
 * @returns MT5 symbol name or undefined if no mapping exists
 */
export function mapDerivToMT5Symbol(derivSymbol: string): string | undefined {
  const normalizedSymbol = derivSymbol.toUpperCase().trim();
  return DERIV_TO_MT5_SYMBOL_MAP[normalizedSymbol];
}

/**
 * Map MT5 symbol to Deriv symbol
 *
 * @param mt5Symbol - MT5 symbol name
 * @returns Deriv symbol or undefined if no mapping exists
 */
export function mapMT5ToDerivSymbol(mt5Symbol: string): string | undefined {
  // Try exact match first
  if (MT5_TO_DERIV_SYMBOL_MAP[mt5Symbol]) {
    return MT5_TO_DERIV_SYMBOL_MAP[mt5Symbol];
  }

  // Try case-insensitive match
  const normalizedSymbol = mt5Symbol.toUpperCase().trim();
  for (const [mt5Key, derivKey] of Object.entries(MT5_TO_DERIV_SYMBOL_MAP)) {
    if (mt5Key.toUpperCase() === normalizedSymbol) {
      return derivKey;
    }
  }

  return undefined;
}

/**
 * Check if a symbol is a valid Deriv volatility index
 *
 * @param symbol - Symbol to check
 * @returns true if symbol is a valid Deriv volatility index
 */
export function isDerivVolatilityIndex(symbol: string): boolean {
  const normalizedSymbol = symbol.toUpperCase().trim();
  return Object.keys(DERIV_TO_MT5_SYMBOL_MAP).includes(normalizedSymbol);
}

/**
 * Convert Deriv price data to MT5 price data format
 *
 * @param derivData - Deriv price data
 * @returns MT5 price data object or null if conversion fails
 */
function convertToMT5PriceData(derivData: DerivPriceData): {
  symbol: string;
  bid: number;
  ask: number;
  timestamp: string;
} | null {
  const mt5Symbol = mapDerivToMT5Symbol(derivData.symbol);
  if (!mt5Symbol) {
    console.warn(`[MT5 Sync] No MT5 symbol mapping found for Deriv symbol: ${derivData.symbol}`);
    return null;
  }

  // Use bid/ask if available, otherwise calculate from price
  const bid = derivData.bid ?? derivData.price;
  const ask = derivData.ask ?? derivData.price;

  return {
    symbol: mt5Symbol,
    bid,
    ask,
    timestamp: derivData.timestamp instanceof Date
      ? derivData.timestamp.toISOString()
      : derivData.timestamp,
  };
}

/**
 * Log price sync attempt
 */
function logPriceSyncAttempt(priceCount: number): void {
  console.log(`[MT5 Sync] Syncing ${priceCount} price(s) to MT5...`);
}

/**
 * Log price sync result
 */
function logPriceSyncResult(result: PriceSyncResult, duration: number): void {
  if (result.success && result.failed === 0) {
    console.log(`[MT5 Sync] Sync SUCCESS`, {
      synced: result.synced,
      duration: `${duration}ms`,
    });
  } else if (result.synced > 0) {
    console.warn(`[MT5 Sync] Sync PARTIAL`, {
      synced: result.synced,
      failed: result.failed,
      errors: result.errors,
      duration: `${duration}ms`,
    });
  } else {
    console.error(`[MT5 Sync] Sync FAILED`, {
      synced: result.synced,
      failed: result.failed,
      errors: result.errors,
      duration: `${duration}ms`,
    });
  }
}

/**
 * Sync Deriv price data to MT5 terminal
 *
 * This function takes price data from Deriv.com and syncs it with the
 * MT5 terminal for analysis and trading operations. It maps Deriv symbols
 * to their corresponding MT5 symbol names and sends bid/ask prices.
 *
 * @param priceData - Array of Deriv price data objects
 * @returns Promise<PriceSyncResult> - Sync result with success status and counts
 *
 * @example
 * ```typescript
 * const result = await syncDerivToMT5([
 *   {
 *     symbol: 'V10',
 *     price: 12345.5,
 *     timestamp: new Date(),
 *     bid: 12345.4,
 *     ask: 12345.6,
 *   },
 *   {
 *     symbol: 'V25',
 *     price: 23456.7,
 *     timestamp: new Date(),
 *   },
 * ]);
 *
 * if (result.success) {
 *   console.log(`Synced ${result.synced} prices`);
 * } else {
 *   console.error(`Failed to sync ${result.failed} prices`);
 * }
 * ```
 */
export async function syncDerivToMT5(priceData: DerivPriceData[]): Promise<PriceSyncResult> {
  const startTime = Date.now();

  // Validate input
  if (!Array.isArray(priceData) || priceData.length === 0) {
    const duration = Date.now() - startTime;
    const result: PriceSyncResult = {
      success: false,
      synced: 0,
      failed: 0,
      errors: ['No price data provided'],
    };
    logPriceSyncResult(result, duration);
    return result;
  }

  logPriceSyncAttempt(priceData.length);

  // Convert Deriv price data to MT5 format
  const mt5Prices: Array<{
    symbol: string;
    bid: number;
    ask: number;
    timestamp: string;
  }> = [];
  const errors: string[] = [];

  for (const data of priceData) {
    const mt5Price = convertToMT5PriceData(data);
    if (mt5Price) {
      mt5Prices.push(mt5Price);
    } else {
      errors.push(`No MT5 mapping for symbol: ${data.symbol}`);
    }
  }

  // If no valid prices to sync, return failure
  if (mt5Prices.length === 0) {
    const duration = Date.now() - startTime;
    const result: PriceSyncResult = {
      success: false,
      synced: 0,
      failed: priceData.length,
      errors,
    };
    logPriceSyncResult(result, duration);
    return result;
  }

  // Call POST /mt5/sync/prices endpoint
  try {
    const response = await post<{ synced: number; failed: number; errors?: string[] }>(
      '/mt5/sync/prices',
      { prices: mt5Prices }
    );

    const duration = Date.now() - startTime;

    if (response.ok && response.data) {
      const result: PriceSyncResult = {
        success: response.data.synced > 0 || response.data.failed === 0,
        synced: response.data.synced,
        failed: response.data.failed + errors.length,
        errors: [...errors, ...(response.data.errors || [])],
      };
      logPriceSyncResult(result, duration);
      return result;
    }

    // Error response from backend
    const errorCode = getMT5ErrorCodeFromStatus(response.status);
    const errorMessage = response.data?.message || 'Price sync failed';
    errors.push(`API Error: ${errorMessage} (${errorCode})`);

    const result: PriceSyncResult = {
      success: false,
      synced: 0,
      failed: mt5Prices.length,
      errors,
    };
    logPriceSyncResult(result, duration);
    return result;

  } catch (error) {
    const duration = Date.now() - startTime;

    // Network or unexpected error
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    errors.push(`Network Error: ${errorMessage}`);

    // Handle sync failures gracefully - log error but don't crash
    console.error('[MT5 Sync] Sync failed with error:', errorMessage);

    const result: PriceSyncResult = {
      success: false,
      synced: 0,
      failed: mt5Prices.length,
      errors,
    };
    logPriceSyncResult(result, duration);
    return result;
  }
}

/**
 * Sync a single Deriv price to MT5
 *
 * Convenience function for syncing a single price update.
 *
 * @param symbol - Deriv symbol (e.g., 'V10', 'V25')
 * @param price - Current price
 * @param timestamp - Price timestamp
 * @param bid - Optional bid price
 * @param ask - Optional ask price
 * @returns Promise<PriceSyncResult> - Sync result
 *
 * @example
 * ```typescript
 * const result = await syncSingleDerivPrice(
 *   'V10',
 *   12345.5,
 *   new Date(),
 *   12345.4,
 *   12345.6
 * );
 * ```
 */
export async function syncSingleDerivPrice(
  symbol: string,
  price: number,
  timestamp: Date,
  bid?: number,
  ask?: number
): Promise<PriceSyncResult> {
  const priceData: DerivPriceData = {
    symbol,
    price,
    timestamp,
    bid,
    ask,
  };

  return syncDerivToMT5([priceData]);
}

/**
 * Get all supported Deriv volatility indices
 *
 * @returns Array of Deriv volatility index symbols
 */
export function getSupportedVolatilityIndices(): string[] {
  return Object.keys(DERIV_TO_MT5_SYMBOL_MAP);
}

/**
 * Get symbol mapping for display purposes
 *
 * @returns Object mapping Deriv symbols to MT5 symbols
 */
export function getSymbolMapping(): Record<string, string> {
  return { ...DERIV_TO_MT5_SYMBOL_MAP };
}
