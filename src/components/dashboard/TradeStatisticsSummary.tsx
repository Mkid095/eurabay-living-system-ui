"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  TrendingUp,
  TrendingDown,
  Activity,
  DollarSign,
  Award,
  ShieldAlert,
  Target,
  Clock,
  Star,
  AlertCircle,
  RefreshCw,
} from "lucide-react";
import { useTradeStatistics, type StatisticsDateRange } from "@/hooks/useTradeStatistics";
import { MetricCard } from "./MetricCard";
import { cn } from "@/lib/utils";

const DATE_RANGE_OPTIONS: Array<{ value: StatisticsDateRange; label: string }> = [
  { value: 'today', label: 'Today' },
  { value: 'week', label: 'This Week' },
  { value: 'month', label: 'This Month' },
  { value: 'all', label: 'All Time' },
];

/**
 * Loading skeleton component for statistics cards
 */
function StatisticsSkeleton() {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((i) => (
        <Card key={i} className="p-4 sm:p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <Skeleton className="h-4 w-24 mb-2" />
              <Skeleton className="h-8 w-32 mb-2" />
              <Skeleton className="h-4 w-20" />
            </div>
            <Skeleton className="h-12 w-12 rounded-lg" />
          </div>
        </Card>
      ))}
    </div>
  );
}

/**
 * Error state component with retry functionality
 */
function StatisticsError({ error, onRetry }: { error: Error; onRetry: () => void }) {
  return (
    <Card className="p-12">
      <div className="flex flex-col items-center justify-center text-center space-y-4">
        <div className="p-4 rounded-full bg-destructive/10">
          <AlertCircle className="w-12 h-12 text-destructive" />
        </div>
        <div>
          <h3 className="text-lg font-semibold mb-1">Failed to Load Statistics</h3>
          <p className="text-sm text-muted-foreground mb-4">{error.message}</p>
        </div>
        <Button onClick={onRetry} variant="outline" className="gap-2">
          <RefreshCw className="w-4 h-4" />
          Retry
        </Button>
      </div>
    </Card>
  );
}

/**
 * Trade Statistics Summary Component
 *
 * Displays comprehensive trading performance metrics including:
 * - Total trades count
 * - Win rate percentage
 * - Total profit/loss
 * - Average win/loss amounts
 * - Profit factor
 * - Largest winning/losing trades
 * - Average trade duration
 * - Best/worst performing symbols
 */
export function TradeStatisticsSummary() {
  const [dateRange, setDateRange] = useState<StatisticsDateRange>('all');
  const [isRefreshing, setIsRefreshing] = useState(false);

  const {
    statistics,
    isLoading,
    error,
    lastUpdated,
    refreshStatistics,
  } = useTradeStatistics({
    dateRange,
    autoRefresh: true,
    refreshInterval: 30000, // 30 seconds
  });

  /**
   * Format currency value with proper decimal places
   */
  const formatCurrency = useCallback((value: number): string => {
    if (Math.abs(value) >= 1000) {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }).format(value);
    }
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  }, []);

  /**
   * Format percentage value
   */
  const formatPercentage = useCallback((value: number): string => {
    return `${value.toFixed(2)}%`;
  }, []);

  /**
   * Handle manual refresh
   */
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    try {
      await refreshStatistics();
    } finally {
      setIsRefreshing(false);
    }
  }, [refreshStatistics]);

  /**
   * Determine trend based on P&L
   */
  const getTrend = useCallback((value: number): 'up' | 'down' | 'neutral' => {
    if (value > 0) return 'up';
    if (value < 0) return 'down';
    return 'neutral';
  }, []);

  /**
   * Calculate win rate color
   */
  const getWinRateColor = useCallback((winRate: number): string => {
    if (winRate >= 60) return 'text-profit';
    if (winRate >= 50) return 'text-yellow-600';
    return 'text-loss';
  }, []);

  /**
   * Calculate profit factor color
   */
  const getProfitFactorColor = useCallback((profitFactor: number): string => {
    if (profitFactor >= 2) return 'text-profit';
    if (profitFactor >= 1) return 'text-yellow-600';
    return 'text-loss';
  }, []);

  /**
   * Memoized formatted data to prevent unnecessary recalculations
   */
  const formattedData = useMemo(() => {
    if (!statistics) return null;

    return {
      totalTrades: statistics.totalTrades.toString(),
      winRate: formatPercentage(statistics.winRate),
      totalProfitLoss: formatCurrency(statistics.totalProfitLoss),
      averageWin: formatCurrency(statistics.averageWin),
      averageLoss: formatCurrency(Math.abs(statistics.averageLoss)),
      profitFactor: statistics.profitFactor.toFixed(2),
      largestWin: formatCurrency(statistics.largestWinningTrade),
      largestLoss: formatCurrency(Math.abs(statistics.largestLosingTrade)),
      bestSymbol: statistics.bestPerformingSymbol || 'N/A',
      worstSymbol: statistics.worstPerformingSymbol || 'N/A',
    };
  }, [statistics, formatCurrency, formatPercentage]);

  /**
   * Memoized last updated time
   */
  const lastUpdatedTime = useMemo(() => {
    if (!lastUpdated) return null;
    return new Intl.TimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(lastUpdated);
  }, [lastUpdated]);

  if (isLoading) {
    return <StatisticsSkeleton />;
  }

  if (error) {
    return <StatisticsError error={error} onRetry={refreshStatistics} />;
  }

  if (!statistics || !formattedData) {
    return (
      <Card className="p-12">
        <div className="flex flex-col items-center justify-center text-center space-y-4">
          <Activity className="w-12 h-12 text-muted-foreground" />
          <div>
            <h3 className="text-lg font-semibold mb-1">No Statistics Available</h3>
            <p className="text-sm text-muted-foreground">
              Trade statistics will appear here once you have completed trades.
            </p>
          </div>
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with date range selector and refresh button */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold">Trade Statistics</h2>
          {lastUpdatedTime && (
            <p className="text-sm text-muted-foreground mt-1">
              Last updated: {lastUpdatedTime}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Select value={dateRange} onValueChange={(value) => setDateRange(value as StatisticsDateRange)}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Date Range" />
            </SelectTrigger>
            <SelectContent>
              {DATE_RANGE_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="icon"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="shrink-0"
          >
            <RefreshCw className={cn("w-4 h-4", isRefreshing && "animate-spin")} />
          </Button>
        </div>
      </div>

      {/* Statistics grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {/* Total Trades */}
        <MetricCard
          title="Total Trades"
          value={formattedData.totalTrades}
          icon={Activity}
          iconColor="text-primary"
        />

        {/* Win Rate */}
        <MetricCard
          title="Win Rate"
          value={formattedData.winRate}
          icon={TrendingUp}
          iconColor={getWinRateColor(statistics.winRate)}
        />

        {/* Total Profit/Loss */}
        <MetricCard
          title="Total P&L"
          value={formattedData.totalProfitLoss}
          icon={DollarSign}
          iconColor={getTrend(statistics.totalProfitLoss) === 'up' ? 'text-profit' : getTrend(statistics.totalProfitLoss) === 'down' ? 'text-loss' : 'text-primary'}
          trend={getTrend(statistics.totalProfitLoss)}
        />

        {/* Average Win */}
        <MetricCard
          title="Average Win"
          value={formattedData.averageWin}
          icon={Award}
          iconColor="text-profit"
        />

        {/* Average Loss */}
        <MetricCard
          title="Average Loss"
          value={formattedData.averageLoss}
          icon={ShieldAlert}
          iconColor="text-loss"
        />

        {/* Profit Factor */}
        <MetricCard
          title="Profit Factor"
          value={formattedData.profitFactor}
          icon={Target}
          iconColor={getProfitFactorColor(statistics.profitFactor)}
        />

        {/* Largest Winning Trade */}
        <MetricCard
          title="Largest Win"
          value={formattedData.largestWin}
          icon={TrendingUp}
          iconColor="text-profit"
        />

        {/* Largest Losing Trade */}
        <MetricCard
          title="Largest Loss"
          value={formattedData.largestLoss}
          icon={TrendingDown}
          iconColor="text-loss"
        />

        {/* Average Trade Duration */}
        <MetricCard
          title="Avg Duration"
          value={statistics.averageTradeDuration}
          icon={Clock}
          iconColor="text-primary"
        />

        {/* Best Performing Symbol */}
        <MetricCard
          title="Best Symbol"
          value={formattedData.bestSymbol}
          icon={Star}
          iconColor="text-profit"
        />

        {/* Worst Performing Symbol */}
        <MetricCard
          title="Worst Symbol"
          value={formattedData.worstSymbol}
          icon={AlertCircle}
          iconColor="text-loss"
        />
      </div>
    </div>
  );
}
