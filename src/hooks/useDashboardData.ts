"use client";

import { useState, useEffect, useCallback, useRef } from 'react';
import { portfolioApi } from '@/lib/api/endpoints/portfolio-endpoints';
import { tradesApi } from '@/lib/api/endpoints/trades';
import { performanceApi } from '@/lib/api/endpoints/performance-endpoints';
import { systemApi } from '@/lib/api/endpoints/system';
import type {
  PortfolioMetrics,
  EvolvedTrade,
  ClosedTrade,
  PendingSignal,
  PerformanceMetrics,
  EquityHistory,
  PnLHistory,
  SystemHealth,
  SystemStatus,
} from '@/lib/api/types';

// ============================================================================
// LOCAL TYPES FOR COMPATIBILITY
// ============================================================================

/**
 * Chart data point for visualizations
 */
export interface ChartDataPoint {
  time: string;
  value: number;
}

/**
 * Combined hook state including loading and error states
 */
export interface DashboardDataState {
  // Data states
  portfolioMetrics: PortfolioMetrics;
  systemHealth: SystemHealth;
  systemStatus: SystemStatus;
  activeTrades: EvolvedTrade[];
  pendingSignals: PendingSignal[];
  recentTrades: ClosedTrade[];
  equityChart: ChartDataPoint[];
  pnlChart: ChartDataPoint[];
  performanceMetrics: PerformanceMetrics;

  // UI states
  loading: boolean;
  error: Error | null;

  // Actions
  refetch: () => Promise<void>;
}

// ============================================================================
// INITIAL STATES
// ============================================================================

const INITIAL_PORTFOLIO_METRICS: PortfolioMetrics = {
  totalValue: 0,
  totalPnL: 0,
  totalPnLPercent: 0,
  activeTrades: 0,
  winRate: 0,
};

const INITIAL_SYSTEM_HEALTH: SystemHealth = {
  health: 'healthy',
  cpuUsage: 0,
  memoryUsage: 0,
  availableMemory: 0,
  totalMemory: 0,
  latency: 0,
  activeConnections: 0,
  uptime: '0s',
  lastCheck: new Date().toISOString(),
};

const INITIAL_SYSTEM_STATUS: SystemStatus = {
  status: 'stopped',
  generation: 0,
  uptime: '0s',
  startTime: new Date().toISOString(),
  lastUpdate: new Date().toISOString(),
  version: '0.0.0',
};

const INITIAL_PERFORMANCE_METRICS: PerformanceMetrics = {
  totalReturn: 0,
  totalReturnPercent: 0,
  sharpeRatio: 0,
  maxDrawdown: 0,
  maxDrawdownPercent: 0,
  winRate: 0,
  winRatePercent: 0,
  totalTrades: 0,
  averageTradeDuration: 0,
  profitFactor: 0,
};

// ============================================================================
// CONVERSION UTILITIES
// ============================================================================

/**
 * Convert equity history to chart data points
 */
function convertEquityHistoryToChartData(equityHistory: EquityHistory): ChartDataPoint[] {
  return equityHistory.history.map(point => ({
    time: new Date(point.date).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    }),
    value: point.equity,
  }));
}

/**
 * Convert P&L history to chart data points
 */
function convertPnLHistoryToChartData(pnlHistory: PnLHistory): ChartDataPoint[] {
  return pnlHistory.history.map(point => ({
    time: new Date(point.date).toLocaleDateString('en-US', {
      weekday: 'short',
    }),
    value: point.pnl,
  }));
}

// ============================================================================
// MAIN HOOK
// ============================================================================

/**
 * Dashboard data hook
 *
 * Fetches and manages all dashboard data using real API calls.
 * Implements automatic polling, error handling, and fallback to last known good data.
 *
 * @returns DashboardDataState
 */
export function useDashboardData(): DashboardDataState {
  // Data states - initialize with default values for backward compatibility
  const [portfolioMetrics, setPortfolioMetrics] = useState<PortfolioMetrics>(INITIAL_PORTFOLIO_METRICS);
  const [systemHealth, setSystemHealth] = useState<SystemHealth>(INITIAL_SYSTEM_HEALTH);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>(INITIAL_SYSTEM_STATUS);
  const [activeTrades, setActiveTrades] = useState<EvolvedTrade[]>([]);
  const [pendingSignals, setPendingSignals] = useState<PendingSignal[]>([]);
  const [recentTrades, setRecentTrades] = useState<ClosedTrade[]>([]);
  const [equityChart, setEquityChart] = useState<ChartDataPoint[]>([]);
  const [pnlChart, setPnlChart] = useState<ChartDataPoint[]>([]);
  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics>(INITIAL_PERFORMANCE_METRICS);

  // UI states
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  // Track if component is mounted
  const isMountedRef = useRef<boolean>(true);

  // Track last known good data for fallback
  const lastKnownDataRef = useRef<{
    portfolioMetrics: PortfolioMetrics;
    systemHealth: SystemHealth;
    systemStatus: SystemStatus;
    activeTrades: EvolvedTrade[];
    pendingSignals: PendingSignal[];
    recentTrades: ClosedTrade[];
    equityChart: ChartDataPoint[];
    pnlChart: ChartDataPoint[];
    performanceMetrics: PerformanceMetrics;
  }>({
    portfolioMetrics: INITIAL_PORTFOLIO_METRICS,
    systemHealth: INITIAL_SYSTEM_HEALTH,
    systemStatus: INITIAL_SYSTEM_STATUS,
    activeTrades: [],
    pendingSignals: [],
    recentTrades: [],
    equityChart: [],
    pnlChart: [],
    performanceMetrics: INITIAL_PERFORMANCE_METRICS,
  });

  /**
   * Fetch all dashboard data in parallel
   */
  const fetchDashboardData = useCallback(async (isInitialLoad: boolean = false) => {
    try {
      // Set loading state for initial load only
      if (isInitialLoad && isMountedRef.current) {
        setLoading(true);
        setError(null);
      }

      // Fetch all data in parallel using Promise.all
      const [
        portfolioData,
        healthData,
        statusData,
        tradesData,
        signalsData,
        recentTradesData,
        equityHistoryData,
        pnlHistoryData,
        perfMetricsData,
      ] = await Promise.all([
        // Portfolio data
        portfolioApi.getMetrics().catch(err => {
          console.error('Failed to fetch portfolio metrics:', err);
          return lastKnownDataRef.current.portfolioMetrics;
        }),

        // System health
        systemApi.getHealth().catch(err => {
          console.error('Failed to fetch system health:', err);
          return lastKnownDataRef.current.systemHealth;
        }),

        // System status
        systemApi.getStatus().catch(err => {
          console.error('Failed to fetch system status:', err);
          return lastKnownDataRef.current.systemStatus;
        }),

        // Active trades
        tradesApi.getActiveTrades().catch(err => {
          console.error('Failed to fetch active trades:', err);
          return lastKnownDataRef.current.activeTrades;
        }),

        // Pending signals
        tradesApi.getPendingSignals().catch(err => {
          console.error('Failed to fetch pending signals:', err);
          return lastKnownDataRef.current.pendingSignals;
        }),

        // Recent trades (last 20)
        tradesApi.getRecentTrades({ limit: 20 }).catch(err => {
          console.error('Failed to fetch recent trades:', err);
          return lastKnownDataRef.current.recentTrades;
        }),

        // Equity history (last 7 days)
        portfolioApi.getEquityHistory('week').catch(err => {
          console.error('Failed to fetch equity history:', err);
          // Return empty equity history on error
          return {
            startingEquity: 0,
            currentEquity: 0,
            peakEquity: 0,
            maxDrawdown: 0,
            totalReturn: 0,
            totalReturnPercent: 0,
            history: [],
          };
        }),

        // P&L history (last 7 days)
        portfolioApi.getPnlHistory('week').catch(err => {
          console.error('Failed to fetch P&L history:', err);
          // Return empty P&L history on error
          return {
            totalPnl: 0,
            totalPnlPercent: 0,
            winningPeriods: 0,
            losingPeriods: 0,
            history: [],
          };
        }),

        // Performance metrics
        performanceApi.getMetrics().catch(err => {
          console.error('Failed to fetch performance metrics:', err);
          return lastKnownDataRef.current.performanceMetrics;
        }),
      ]);

      // Only update state if component is still mounted
      if (isMountedRef.current) {
        setPortfolioMetrics(portfolioData);
        setSystemHealth(healthData);
        setSystemStatus(statusData);
        setActiveTrades(tradesData);
        setPendingSignals(signalsData);
        setRecentTrades(recentTradesData);

        // Convert history data to chart format
        setEquityChart(convertEquityHistoryToChartData(equityHistoryData));
        setPnlChart(convertPnLHistoryToChartData(pnlHistoryData));

        setPerformanceMetrics(perfMetricsData);

        // Update last known good data
        lastKnownDataRef.current = {
          portfolioMetrics: portfolioData,
          systemHealth: healthData,
          systemStatus: statusData,
          activeTrades: tradesData,
          pendingSignals: signalsData,
          recentTrades: recentTradesData,
          equityChart: convertEquityHistoryToChartData(equityHistoryData),
          pnlChart: convertPnLHistoryToChartData(pnlHistoryData),
          performanceMetrics: perfMetricsData,
        };

        // Clear any previous error on successful fetch
        setError(null);
      }
    } catch (err) {
      // Handle any unexpected errors
      if (isMountedRef.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to fetch dashboard data');
        console.error('Dashboard data fetch error:', errorObj);

        // Only set error state on initial load
        if (isInitialLoad) {
          setError(errorObj);
        }

        // Fallback to last known good data (already set in state)
        console.warn('Using last known good data due to error');
      }
    } finally {
      if (isInitialLoad && isMountedRef.current) {
        setLoading(false);
      }
    }
  }, []); // Empty deps - we read refs directly inside

  /**
   * Manual refetch function
   */
  const refetch = useCallback(async () => {
    await fetchDashboardData(false);
  }, [fetchDashboardData]);

  // ============================================================================
  // EFFECTS
  // ============================================================================

  // Initial data fetch
  useEffect(() => {
    isMountedRef.current = true;
    fetchDashboardData(true);

    return () => {
      isMountedRef.current = false;
    };
  }, []); // Empty dependency array - only run on mount

  // Automatic polling every 3 seconds
  useEffect(() => {
    const pollingInterval = setInterval(() => {
      fetchDashboardData(false);
    }, 3000);

    return () => {
      clearInterval(pollingInterval);
    };
  }, [fetchDashboardData]);

  // ============================================================================
  // RETURN STATE
  // ============================================================================

  return {
    portfolioMetrics,
    systemHealth,
    systemStatus,
    activeTrades,
    pendingSignals,
    recentTrades,
    equityChart,
    pnlChart,
    performanceMetrics,
    loading,
    error,
    refetch,
  };
}
