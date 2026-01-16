/**
 * MT5 Technical Indicators
 *
 * Functions for calculating and retrieving technical indicators
 * from MetaTrader 5 terminal with built-in caching.
 */

import { apiClient } from '@/lib/api/client';
import type {
  IndicatorRequest,
  RSIResult,
  MACDResult,
  MAResult,
  BollingerBandsResult,
  ATRResult,
  MT5Timeframe,
  MT5Error,
  MT5ErrorCode,
} from './types';

/**
 * Cache entry for indicator values
 */
interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

/**
 * In-memory cache for indicator values (30 second TTL)
 */
class IndicatorCache {
  private cache: Map<string, CacheEntry<unknown>> = new Map();
  private readonly TTL = 30000; // 30 seconds

  /**
   * Generate cache key from request parameters
   */
  private generateKey(endpoint: string, request: IndicatorRequest): string {
    return `${endpoint}:${request.symbol}:${request.timeframe}:${request.period}`;
  }

  /**
   * Get cached value if available and not expired
   */
  get<T>(endpoint: string, request: IndicatorRequest): T | null {
    const key = this.generateKey(endpoint, request);
    const entry = this.cache.get(key);

    if (!entry) {
      return null;
    }

    const now = Date.now();
    if (now > entry.expiresAt) {
      this.cache.delete(key);
      return null;
    }

    console.log(`[IndicatorCache] Cache hit for ${key}`);
    return entry.data as T;
  }

  /**
   * Set cached value with expiration
   */
  set<T>(endpoint: string, request: IndicatorRequest, data: T): void {
    const key = this.generateKey(endpoint, request);
    const now = Date.now();

    const entry: CacheEntry<T> = {
      data,
      timestamp: now,
      expiresAt: now + this.TTL,
    };

    this.cache.set(key, entry as CacheEntry<unknown>);
    console.log(`[IndicatorCache] Cached ${key} for ${this.TTL}ms`);
  }

  /**
   * Clear all cache entries
   */
  clear(): void {
    this.cache.clear();
    console.log('[IndicatorCache] Cache cleared');
  }

  /**
   * Clear cache for specific symbol
   */
  clearSymbol(symbol: string): void {
    const keysToDelete: string[] = [];

    for (const key of this.cache.keys()) {
      if (key.includes(`:${symbol}:`)) {
        keysToDelete.push(key);
      }
    }

    keysToDelete.forEach(key => this.cache.delete(key));
    console.log(`[IndicatorCache] Cleared ${keysToDelete.length} entries for ${symbol}`);
  }

  /**
   * Get cache statistics
   */
  getStats(): { size: number; keys: string[] } {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys()),
    };
  }
}

/**
 * Global indicator cache instance
 */
const indicatorCache = new IndicatorCache();

/**
 * Parse API error to MT5Error
 */
function parseError(error: unknown): MT5Error {
  if (error instanceof Error) {
    return {
      code: MT5ErrorCode.UNKNOWN_ERROR,
      message: error.message,
      details: error.stack,
    };
  }

  return {
    code: MT5ErrorCode.UNKNOWN_ERROR,
    message: 'Unknown error occurred',
    details: String(error),
  };
}

/**
 * Validate timeframe
 */
function isValidTimeframe(timeframe: MT5Timeframe): boolean {
  const validTimeframes: MT5Timeframe[] = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'W1', 'MN'];
  return validTimeframes.includes(timeframe);
}

/**
 * Validate indicator request
 */
function validateIndicatorRequest(request: IndicatorRequest): void {
  if (!request.symbol || typeof request.symbol !== 'string') {
    throw new Error('Invalid symbol: must be a non-empty string');
  }

  if (!isValidTimeframe(request.timeframe)) {
    throw new Error(`Invalid timeframe: ${request.timeframe}. Must be one of M1, M5, M15, M30, H1, H4, D1, W1, MN`);
  }

  if (!request.period || typeof request.period !== 'number' || request.period < 1) {
    throw new Error('Invalid period: must be a positive number');
  }
}

/**
 * Calculate RSI (Relative Strength Index)
 *
 * @param request - Indicator request with symbol, timeframe, and period
 * @returns RSI value with timestamp
 */
export async function getRSI(request: IndicatorRequest): Promise<RSIResult> {
  validateIndicatorRequest(request);

  console.log(`[MT5Indicators] Calculating RSI for ${request.symbol} ${request.timeframe} period=${request.period}`);

  // Check cache first
  const cached = indicatorCache.get<RSIResult>('rsi', request);
  if (cached) {
    return cached;
  }

  try {
    const response = await apiClient.post<{ result: RSIResult }>(
      'mt5/indicators/rsi',
      request
    );

    if (!response.data?.result) {
      throw new Error('Invalid RSI response from server');
    }

    const result = response.data.result;

    // Cache the result
    indicatorCache.set('rsi', request, result);

    console.log(`[MT5Indicators] RSI calculated: ${result.value}`);

    return result;
  } catch (error) {
    console.error('[MT5Indicators] RSI calculation failed:', error);
    throw parseError(error);
  }
}

/**
 * Calculate MACD (Moving Average Convergence Divergence)
 *
 * @param request - Indicator request with symbol, timeframe, and period
 * @returns MACD values (macd, signal, histogram) with timestamp
 */
export async function getMACD(request: IndicatorRequest): Promise<MACDResult> {
  validateIndicatorRequest(request);

  console.log(`[MT5Indicators] Calculating MACD for ${request.symbol} ${request.timeframe} period=${request.period}`);

  // Check cache first
  const cached = indicatorCache.get<MACDResult>('macd', request);
  if (cached) {
    return cached;
  }

  try {
    const response = await apiClient.post<{ result: MACDResult }>(
      'mt5/indicators/macd',
      request
    );

    if (!response.data?.result) {
      throw new Error('Invalid MACD response from server');
    }

    const result = response.data.result;

    // Cache the result
    indicatorCache.set('macd', request, result);

    console.log(`[MT5Indicators] MACD calculated: macd=${result.macd}, signal=${result.signal}, histogram=${result.histogram}`);

    return result;
  } catch (error) {
    console.error('[MT5Indicators] MACD calculation failed:', error);
    throw parseError(error);
  }
}

/**
 * Calculate Moving Average (MA)
 *
 * @param request - Indicator request with symbol, timeframe, and period
 * @returns MA value with timestamp
 */
export async function getMovingAverage(request: IndicatorRequest): Promise<MAResult> {
  validateIndicatorRequest(request);

  console.log(`[MT5Indicators] Calculating MA for ${request.symbol} ${request.timeframe} period=${request.period}`);

  // Check cache first
  const cached = indicatorCache.get<MAResult>('ma', request);
  if (cached) {
    return cached;
  }

  try {
    const response = await apiClient.post<{ result: MAResult }>(
      'mt5/indicators/ma',
      request
    );

    if (!response.data?.result) {
      throw new Error('Invalid MA response from server');
    }

    const result = response.data.result;

    // Cache the result
    indicatorCache.set('ma', request, result);

    console.log(`[MT5Indicators] MA calculated: ${result.value}`);

    return result;
  } catch (error) {
    console.error('[MT5Indicators] MA calculation failed:', error);
    throw parseError(error);
  }
}

/**
 * Calculate Bollinger Bands
 *
 * @param request - Indicator request with symbol, timeframe, and period
 * @returns Bollinger Bands (upper, middle, lower) with timestamp
 */
export async function getBollingerBands(request: IndicatorRequest): Promise<BollingerBandsResult> {
  validateIndicatorRequest(request);

  console.log(`[MT5Indicators] Calculating Bollinger Bands for ${request.symbol} ${request.timeframe} period=${request.period}`);

  // Check cache first
  const cached = indicatorCache.get<BollingerBandsResult>('bollinger', request);
  if (cached) {
    return cached;
  }

  try {
    const response = await apiClient.post<{ result: BollingerBandsResult }>(
      'mt5/indicators/bollinger',
      request
    );

    if (!response.data?.result) {
      throw new Error('Invalid Bollinger Bands response from server');
    }

    const result = response.data.result;

    // Cache the result
    indicatorCache.set('bollinger', request, result);

    console.log(`[MT5Indicators] Bollinger Bands calculated: upper=${result.upper}, middle=${result.middle}, lower=${result.lower}`);

    return result;
  } catch (error) {
    console.error('[MT5Indicators] Bollinger Bands calculation failed:', error);
    throw parseError(error);
  }
}

/**
 * Calculate ATR (Average True Range)
 *
 * @param request - Indicator request with symbol, timeframe, and period
 * @returns ATR value with timestamp
 */
export async function getATR(request: IndicatorRequest): Promise<ATRResult> {
  validateIndicatorRequest(request);

  console.log(`[MT5Indicators] Calculating ATR for ${request.symbol} ${request.timeframe} period=${request.period}`);

  // Check cache first
  const cached = indicatorCache.get<ATRResult>('atr', request);
  if (cached) {
    return cached;
  }

  try {
    const response = await apiClient.post<{ result: ATRResult }>(
      'mt5/indicators/atr',
      request
    );

    if (!response.data?.result) {
      throw new Error('Invalid ATR response from server');
    }

    const result = response.data.result;

    // Cache the result
    indicatorCache.set('atr', request, result);

    console.log(`[MT5Indicators] ATR calculated: ${result.value}`);

    return result;
  } catch (error) {
    console.error('[MT5Indicators] ATR calculation failed:', error);
    throw parseError(error);
  }
}

/**
 * Calculate multiple indicators at once
 *
 * @param request - Base indicator request
 * @param indicators - Array of indicator names to calculate
 * @returns Object with calculated indicator values
 */
export async function getMultipleIndicators(
  request: IndicatorRequest,
  indicators: Array<'rsi' | 'macd' | 'ma' | 'bollinger' | 'atr'>
): Promise<{
  rsi?: RSIResult;
  macd?: MACDResult;
  ma?: MAResult;
  bollinger?: BollingerBandsResult;
  atr?: ATRResult;
}> {
  console.log(`[MT5Indicators] Calculating multiple indicators: ${indicators.join(', ')}`);

  const results: {
    rsi?: RSIResult;
    macd?: MACDResult;
    ma?: MAResult;
    bollinger?: BollingerBandsResult;
    atr?: ATRResult;
  } = {};

  // Calculate indicators in parallel
  await Promise.all(
    indicators.map(async (indicator) => {
      switch (indicator) {
        case 'rsi':
          results.rsi = await getRSI(request);
          break;
        case 'macd':
          results.macd = await getMACD(request);
          break;
        case 'ma':
          results.ma = await getMovingAverage(request);
          break;
        case 'bollinger':
          results.bollinger = await getBollingerBands(request);
          break;
        case 'atr':
          results.atr = await getATR(request);
          break;
      }
    })
  );

  return results;
}

/**
 * Clear indicator cache for specific symbol
 *
 * @param symbol - Symbol to clear cache for
 */
export function clearIndicatorCache(symbol?: string): void {
  if (symbol) {
    indicatorCache.clearSymbol(symbol);
  } else {
    indicatorCache.clear();
  }
}

/**
 * Get indicator cache statistics
 */
export function getIndicatorCacheStats(): { size: number; keys: string[] } {
  return indicatorCache.getStats();
}
