/**
 * useMT5Indicators Hook
 *
 * Provides access to MT5 technical indicator values.
 * Auto-refreshes indicators every 10 seconds.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import type {
  IndicatorRequest,
  RSIResult,
  MACDResult,
  MAResult,
  BollingerBandsResult,
  ATRResult,
  MT5Timeframe,
} from '@/lib/mt5/types';
import {
  getRSI,
  getMACD,
  getMovingAverage,
  getBollingerBands,
  getATR,
} from '@/lib/mt5/indicators';

export interface IndicatorData<T> {
  value: T | null;
  isLoading: boolean;
  error: Error | null;
}

export interface UseMT5IndicatorsReturn {
  rsi: IndicatorData<number>;
  macd: IndicatorData<{ macd: number; signal: number; histogram: number }>;
  ma: IndicatorData<number>;
  bollingerBands: IndicatorData<{ upper: number; middle: number; lower: number }>;
  atr: IndicatorData<number>;
  refreshIndicators: () => Promise<void>;
}

/**
 * Hook to access MT5 technical indicators
 *
 * @param symbol - Trading symbol (e.g., 'V10', 'V25')
 * @param timeframe - Chart timeframe (M1, M5, M15, M30, H1, H4, D1, W1, MN)
 * @param period - Indicator period (number of bars/candles)
 *
 * Auto-refreshes indicators every 10 seconds
 */
export function useMT5Indicators(
  symbol: string,
  timeframe: MT5Timeframe = 'H1',
  period: number = 14
): UseMT5IndicatorsReturn {
  // RSI state
  const [rsi, setRSI] = useState<number | null>(null);
  const [rsiLoading, setRSILoading] = useState(false);
  const [rsiError, setRSIError] = useState<Error | null>(null);

  // MACD state
  const [macd, setMACD] = useState<{ macd: number; signal: number; histogram: number } | null>(null);
  const [macdLoading, setMACDLoading] = useState(false);
  const [macdError, setMACDError] = useState<Error | null>(null);

  // MA state
  const [ma, setMA] = useState<number | null>(null);
  const [maLoading, setMALoading] = useState(false);
  const [maError, setMAError] = useState<Error | null>(null);

  // Bollinger Bands state
  const [bollingerBands, setBollingerBands] = useState<{ upper: number; middle: number; lower: number } | null>(null);
  const [bollingerLoading, setBollingerLoading] = useState(false);
  const [bollingerError, setBollingerError] = useState<Error | null>(null);

  // ATR state
  const [atr, setATR] = useState<number | null>(null);
  const [atrLoading, setATRLoading] = useState(false);
  const [atrError, setATRError] = useState<Error | null>(null);

  // Use ref to track mounted state
  const isMounted = useRef(true);

  // Create request object
  const request: IndicatorRequest = {
    symbol,
    timeframe,
    period,
  };

  /**
   * Refresh all indicators from MT5 terminal
   */
  const refreshIndicators = useCallback(async () => {
    if (!isMounted.current) return;

    // Fetch RSI
    if (isMounted.current) {
      setRSILoading(true);
      setRSIError(null);
    }
    try {
      const rsiResult = await getRSI(request);
      if (isMounted.current) {
        setRSI(rsiResult.value);
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to fetch RSI');
        setRSIError(errorObj);
        console.error('[useMT5Indicators] RSI fetch failed:', errorObj);
      }
    } finally {
      if (isMounted.current) {
        setRSILoading(false);
      }
    }

    // Fetch MACD
    if (isMounted.current) {
      setMACDLoading(true);
      setMACDError(null);
    }
    try {
      const macdResult = await getMACD(request);
      if (isMounted.current) {
        setMACD({
          macd: macdResult.macd,
          signal: macdResult.signal,
          histogram: macdResult.histogram,
        });
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to fetch MACD');
        setMACDError(errorObj);
        console.error('[useMT5Indicators] MACD fetch failed:', errorObj);
      }
    } finally {
      if (isMounted.current) {
        setMACDLoading(false);
      }
    }

    // Fetch MA
    if (isMounted.current) {
      setMALoading(true);
      setMAError(null);
    }
    try {
      const maResult = await getMovingAverage(request);
      if (isMounted.current) {
        setMA(maResult.value);
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to fetch MA');
        setMAError(errorObj);
        console.error('[useMT5Indicators] MA fetch failed:', errorObj);
      }
    } finally {
      if (isMounted.current) {
        setMALoading(false);
      }
    }

    // Fetch Bollinger Bands
    if (isMounted.current) {
      setBollingerLoading(true);
      setBollingerError(null);
    }
    try {
      const bollingerResult = await getBollingerBands(request);
      if (isMounted.current) {
        setBollingerBands({
          upper: bollingerResult.upper,
          middle: bollingerResult.middle,
          lower: bollingerResult.lower,
        });
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to fetch Bollinger Bands');
        setBollingerError(errorObj);
        console.error('[useMT5Indicators] Bollinger Bands fetch failed:', errorObj);
      }
    } finally {
      if (isMounted.current) {
        setBollingerLoading(false);
      }
    }

    // Fetch ATR
    if (isMounted.current) {
      setATRLoading(true);
      setATRError(null);
    }
    try {
      const atrResult = await getATR(request);
      if (isMounted.current) {
        setATR(atrResult.value);
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to fetch ATR');
        setATRError(errorObj);
        console.error('[useMT5Indicators] ATR fetch failed:', errorObj);
      }
    } finally {
      if (isMounted.current) {
        setATRLoading(false);
      }
    }
  }, [request]);

  // Auto-refresh indicators every 10 seconds
  useEffect(() => {
    const intervalId = setInterval(() => {
      refreshIndicators();
    }, 10000);

    return () => {
      clearInterval(intervalId);
    };
  }, [refreshIndicators]);

  // Initial fetch on mount
  useEffect(() => {
    isMounted.current = true;

    // Fetch indicators immediately on mount
    refreshIndicators();

    return () => {
      isMounted.current = false;
    };
  }, [refreshIndicators]);

  return {
    rsi: {
      value: rsi,
      isLoading: rsiLoading,
      error: rsiError,
    },
    macd: {
      value: macd,
      isLoading: macdLoading,
      error: macdError,
    },
    ma: {
      value: ma,
      isLoading: maLoading,
      error: maError,
    },
    bollingerBands: {
      value: bollingerBands,
      isLoading: bollingerLoading,
      error: bollingerError,
    },
    atr: {
      value: atr,
      isLoading: atrLoading,
      error: atrError,
    },
    refreshIndicators,
  };
}
