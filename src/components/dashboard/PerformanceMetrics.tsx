/**
 * PerformanceMetrics Component
 *
 * Displays trading performance metrics including:
 * - Total return percentage
 * - Sharpe ratio
 * - Maximum drawdown percentage
 * - Win rate percentage
 * - Total trades count
 * - Average trade duration
 * - Profit factor
 * - Benchmark comparison
 *
 * Features:
 * - Date range selector (today, week, month, all)
 * - Loading skeleton
 * - Error state with retry
 * - Auto-refresh every 30 seconds
 * - Uses Card and MetricCard components
 */

"use client";

import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { Award, TrendingUp, TrendingDown, RefreshCw, AlertCircle, Clock } from "lucide-react";
import { usePerformanceMetrics } from "@/hooks/usePerformanceMetrics";
import type { DateRange } from "@/types/performance";

/**
 * Loading skeleton for PerformanceMetrics
 */
function PerformanceMetricsSkeleton() {
  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Skeleton className="w-5 h-5 rounded" />
          <Skeleton className="h-6 w-40" />
        </div>
        <Skeleton className="h-8 w-24" />
      </div>

      <div className="space-y-6">
        <div className="space-y-2">
          <div className="flex justify-between">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-6 w-16" />
          </div>
          <Skeleton className="h-2 w-full" />
          <div className="flex justify-between">
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-3 w-16" />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="p-3 bg-muted/50 rounded-lg border border-border space-y-2">
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-6 w-20" />
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

/**
 * Error state for PerformanceMetrics
 */
interface PerformanceMetricsErrorProps {
  message: string;
  onRetry: () => void;
}

function PerformanceMetricsError({ message, onRetry }: PerformanceMetricsErrorProps) {
  return (
    <Card className="p-6">
      <div className="flex flex-col items-center justify-center py-8 space-y-4">
        <AlertCircle className="w-12 h-12 text-loss" />
        <div className="text-center space-y-2">
          <p className="text-lg font-semibold text-foreground">Failed to load performance metrics</p>
          <p className="text-sm text-muted-foreground">{message}</p>
        </div>
        <Button onClick={onRetry} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Retry
        </Button>
      </div>
    </Card>
  );
}

/**
 * Date range selector component
 */
interface DateRangeSelectorProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
}

function DateRangeSelector({ value, onChange }: DateRangeSelectorProps) {
  const ranges: { value: DateRange; label: string }[] = [
    { value: 'today', label: 'Today' },
    { value: 'week', label: 'Week' },
    { value: 'month', label: 'Month' },
    { value: 'all', label: 'All' },
  ];

  return (
    <div className="flex items-center gap-1 bg-muted/50 rounded-lg p-1">
      {ranges.map((range) => (
        <Button
          key={range.value}
          variant={value === range.value ? 'default' : 'ghost'}
          size="sm"
          onClick={() => onChange(range.value)}
          className="h-7 text-xs"
        >
          {range.label}
        </Button>
      ))}
    </div>
  );
}

/**
 * PerformanceMetrics component
 */
export function PerformanceMetrics() {
  const {
    metrics,
    isLoading,
    error,
    dateRange,
    setDateRange,
    retry,
  } = usePerformanceMetrics('all', 30000);

  // Show loading skeleton
  if (isLoading && !metrics) {
    return <PerformanceMetricsSkeleton />;
  }

  // Show error state
  if (error && !metrics) {
    return <PerformanceMetricsError message={error} onRetry={retry} />;
  }

  // Show empty state if no metrics
  if (!metrics) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center py-8">
          <p className="text-muted-foreground">No performance metrics available</p>
        </div>
      </Card>
    );
  }

  // Format duration in hours/days
  function formatDuration(minutes: number): string {
    if (minutes < 60) {
      return `${Math.round(minutes)}m`;
    } else if (minutes < 1440) {
      const hours = Math.floor(minutes / 60);
      const mins = Math.round(minutes % 60);
      return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`;
    } else {
      const days = Math.floor(minutes / 1440);
      const hours = Math.round((minutes % 1440) / 60);
      return hours > 0 ? `${days}d ${hours}h` : `${days}d`;
    }
  }

  const benchmarkDiff = metrics.benchmarkReturnPercent !== undefined
    ? metrics.totalReturnPercent - metrics.benchmarkReturnPercent
    : null;

  return (
    <Card className="p-4 sm:p-6">
      <CardHeader className="p-0 mb-6">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Award className="w-5 h-5 text-primary" />
            <span className="text-xl">Performance Metrics</span>
          </CardTitle>
          <DateRangeSelector value={dateRange} onChange={setDateRange} />
        </div>
      </CardHeader>

      <CardContent className="p-0 space-y-6">
        {/* Total Return */}
        <div className="p-4 bg-muted/50 rounded-lg border border-border">
          <div className="flex items-center justify-between">
            <span className="text-sm text-muted-foreground">Total Return</span>
            <div className="text-right">
              <p className={`text-2xl font-bold ${metrics.totalReturnPercent >= 0 ? 'text-profit' : 'text-loss'}`}>
                {metrics.totalReturnPercent >= 0 ? '+' : ''}{metrics.totalReturnPercent.toFixed(2)}%
              </p>
              <p className="text-xs text-muted-foreground">
                ${metrics.totalReturn.toFixed(2)}
              </p>
            </div>
          </div>
        </div>

        {/* Win Rate */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Win Rate</span>
            <span className="text-lg font-bold text-profit">{metrics.winRatePercent.toFixed(1)}%</span>
          </div>
          <Progress value={metrics.winRatePercent} className="h-2" />
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>{metrics.winRate} wins</span>
            <span>{metrics.totalTrades - metrics.winRate} losses</span>
          </div>
        </div>

        {/* Statistics Grid */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1">Sharpe Ratio</p>
            <p className="text-xl font-bold text-primary">{metrics.sharpeRatio.toFixed(2)}</p>
          </div>

          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1">Max Drawdown</p>
            <p className="text-xl font-bold text-loss">{metrics.maxDrawdownPercent.toFixed(1)}%</p>
          </div>

          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1">Profit Factor</p>
            <p className="text-xl font-bold text-primary">{metrics.profitFactor.toFixed(2)}</p>
          </div>

          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <div className="flex items-center gap-1 mb-1">
              <Clock className="w-3 h-3 text-muted-foreground" />
              <p className="text-xs text-muted-foreground">Avg Duration</p>
            </div>
            <p className="text-xl font-bold">{formatDuration(metrics.averageTradeDuration)}</p>
          </div>

          <div className="p-3 bg-muted/50 rounded-lg border border-border col-span-2">
            <p className="text-xs text-muted-foreground mb-1">Total Trades</p>
            <p className="text-xl font-bold">{metrics.totalTrades}</p>
          </div>
        </div>

        {/* Benchmark Comparison */}
        {metrics.benchmarkReturnPercent !== undefined && benchmarkDiff !== null && (
          <div className="pt-4 border-t border-border">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-muted-foreground">Benchmark (S&P 500)</p>
                <p className="text-sm font-medium">{metrics.benchmarkReturnPercent >= 0 ? '+' : ''}{metrics.benchmarkReturnPercent.toFixed(2)}%</p>
              </div>
              <div className="text-right">
                <p className="text-xs text-muted-foreground">vs Benchmark</p>
                <p className={`text-sm font-medium ${benchmarkDiff >= 0 ? 'text-profit' : 'text-loss'}`}>
                  {benchmarkDiff >= 0 ? '+' : ''}{benchmarkDiff.toFixed(2)}%
                </p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
