/**
 * useDerivPriceSync Hook
 *
 * Automatically syncs Deriv.com price data to MetaTrader 5 terminal.
 * Fetches market overview prices and syncs them to MT5 every 1 second.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { mt5Client, MT5ConnectionState } from '@/lib/mt5/client';
import { syncDerivToMT5 } from '@/lib/mt5/sync';
import { fetchMarketsOverview } from '@/lib/api/markets';
import type { DerivPriceData, PriceSyncResult } from '@/lib/mt5/types';
import type { MarketsOverviewResponse, MarketOverviewData } from '@/types/market';

/**
 * Price sync status
 */
export type PriceSyncStatus = 'idle' | 'syncing' | 'success' | 'error';

/**
 * Price sync data interface
 */
export interface PriceSyncData {
  status: PriceSyncStatus;
  lastSyncTime: Date | null;
  lastSyncResult: PriceSyncResult | null;
  consecutiveErrors: number;
  isSyncing: boolean;
}

/**
 * useDerivPriceSync return interface
 */
export interface UseDerivPriceSyncReturn extends PriceSyncData {
  startSync: () => void;
  stopSync: () => void;
  manualSync: () => Promise<void>;
}

/**
 * Convert MarketsOverviewResponse to DerivPriceData array
 *
 * @param marketsData - Markets overview response
 * @returns Array of DerivPriceData objects
 */
function convertToDerivPriceData(marketsData: MarketsOverviewResponse): DerivPriceData[] {
  return marketsData.markets
    .filter((market: MarketOverviewData) => {
      // Only sync volatility indices (V10, V25, V50, V75, V100)
      const volIndices = ['V10', 'V25', 'V50', 'V75', 'V100'];
      return volIndices.includes(market.symbol);
    })
    .map((market: MarketOverviewData) => ({
      symbol: market.symbol,
      price: market.price,
      timestamp: new Date(market.timestamp),
      // bid and ask are optional - will be calculated from price if not provided
      bid: market.price,
      ask: market.price,
    }));
}

/**
 * Hook to automatically sync Deriv prices to MT5
 *
 * This hook:
 * - Fetches Deriv market overview prices
 * - Syncs prices to MT5 every 1 second
 * - Shows sync status indicator (syncing, error, success)
 * - Handles sync errors with retry
 * - Stops sync when MT5 is disconnected
 * - Cleans up interval on unmount
 *
 * @returns UseDerivPriceSyncReturn - Sync state and control functions
 */
export function useDerivPriceSync(): UseDerivPriceSyncReturn {
  const [status, setStatus] = useState<PriceSyncStatus>('idle');
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);
  const [lastSyncResult, setLastSyncResult] = useState<PriceSyncResult | null>(null);
  const [consecutiveErrors, setConsecutiveErrors] = useState(0);
  const [isSyncing, setIsSyncing] = useState(false);

  // Use refs to track mounted state and sync state
  const isMounted = useRef(true);
  const isSyncActive = useRef(false);
  const syncIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  /**
   * Perform price sync from Deriv to MT5
   */
  const performSync = useCallback(async (): Promise<void> => {
    // Check if MT5 is connected
    const mt5State = mt5Client.getState();
    if (mt5State !== 'connected') {
      console.log('[useDerivPriceSync] MT5 not connected, skipping sync');
      setStatus('idle');
      return;
    }

    if (!isMounted.current) {
      return;
    }

    setIsSyncing(true);
    setStatus('syncing');

    try {
      // Fetch Deriv market overview prices
      const marketsData = await fetchMarketsOverview();

      if (!isMounted.current) {
        return;
      }

      // Convert to DerivPriceData format
      const priceData = convertToDerivPriceData(marketsData);

      if (priceData.length === 0) {
        console.warn('[useDerivPriceSync] No volatility indices found in market data');
        setStatus('idle');
        setConsecutiveErrors(0);
        return;
      }

      // Sync to MT5
      const syncResult = await syncDerivToMT5(priceData);

      if (!isMounted.current) {
        return;
      }

      // Update state based on sync result
      setLastSyncTime(new Date());
      setLastSyncResult(syncResult);

      if (syncResult.success) {
        setStatus('success');
        setConsecutiveErrors(0);
        console.log('[useDerivPriceSync] Sync completed successfully', {
          synced: syncResult.synced,
          failed: syncResult.failed,
        });
      } else {
        setStatus('error');
        setConsecutiveErrors((prev) => prev + 1);
        console.error('[useDerivPriceSync] Sync failed', {
          errors: syncResult.errors,
          consecutiveErrors: consecutiveErrors + 1,
        });
      }

    } catch (error) {
      if (!isMounted.current) {
        return;
      }

      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      console.error('[useDerivPriceSync] Sync error:', errorMessage);

      setStatus('error');
      setConsecutiveErrors((prev) => prev + 1);
      setLastSyncTime(new Date());
      setLastSyncResult({
        success: false,
        synced: 0,
        failed: 0,
        errors: [errorMessage],
      });

    } finally {
      if (isMounted.current) {
        setIsSyncing(false);
      }
    }
  }, [consecutiveErrors]);

  /**
   * Manual sync trigger
   */
  const manualSync = useCallback(async (): Promise<void> => {
    await performSync();
  }, [performSync]);

  /**
   * Start automatic price sync
   */
  const startSync = useCallback(() => {
    if (isSyncActive.current) {
      console.log('[useDerivPriceSync] Sync already active');
      return;
    }

    console.log('[useDerivPriceSync] Starting price sync');
    isSyncActive.current = true;

    // Clear any existing intervals
    if (syncIntervalRef.current) {
      clearInterval(syncIntervalRef.current);
      syncIntervalRef.current = null;
    }

    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }

    // Perform initial sync immediately
    performSync();

    // Set up sync interval (every 1 second)
    syncIntervalRef.current = setInterval(() => {
      performSync();
    }, 1000);
  }, [performSync]);

  /**
   * Stop automatic price sync
   */
  const stopSync = useCallback(() => {
    if (!isSyncActive.current) {
      console.log('[useDerivPriceSync] Sync not active');
      return;
    }

    console.log('[useDerivPriceSync] Stopping price sync');
    isSyncActive.current = false;

    // Clear intervals
    if (syncIntervalRef.current) {
      clearInterval(syncIntervalRef.current);
      syncIntervalRef.current = null;
    }

    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }

    setStatus('idle');
    setIsSyncing(false);
  }, []);

  // Monitor MT5 connection state and auto-stop sync when disconnected
  useEffect(() => {
    const unsubscribe = mt5Client.onStateChange((newState) => {
      if (newState !== 'connected' && isSyncActive.current) {
        console.log('[useDerivPriceSync] MT5 disconnected, stopping sync');
        stopSync();
      }
    });

    return unsubscribe;
  }, [stopSync]);

  // Cleanup on unmount
  useEffect(() => {
    isMounted.current = true;

    return () => {
      isMounted.current = false;

      // Clear all intervals and timeouts
      if (syncIntervalRef.current) {
        clearInterval(syncIntervalRef.current);
      }

      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
      }

      // Stop sync if active
      if (isSyncActive.current) {
        isSyncActive.current = false;
      }
    };
  }, []);

  return {
    status,
    lastSyncTime,
    lastSyncResult,
    consecutiveErrors,
    isSyncing,
    startSync,
    stopSync,
    manualSync,
  };
}
