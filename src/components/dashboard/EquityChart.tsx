/**
 * EquityCurve Component
 *
 * Displays portfolio equity growth over time with:
 * - Line chart with date on X-axis and equity value on Y-axis
 * - Tooltips with date, equity, and P&L on hover
 * - Starting equity reference line
 * - Peak equity marker
 * - Drawdown shading
 * - Zoom/pan functionality
 * - Date range selector
 * - Auto-refresh every 30 seconds
 * - Loading skeleton
 * - Error state with retry
 */

"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CompactErrorState } from "@/components/ui/error-state";
import { TrendingUp } from "lucide-react";
import { useEquityHistory } from "@/hooks/useEquityHistory";
import type { DateRange } from "@/types/performance";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Scatter,
  Cell,
  TooltipProps,
} from 'recharts';

/**
 * Loading skeleton for EquityCurve
 */
function EquityCurveSkeleton() {
  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="h-6 w-40 bg-muted animate-pulse rounded mb-2" />
          <div className="h-4 w-32 bg-muted animate-pulse rounded" />
        </div>
        <div className="h-8 w-24 bg-muted animate-pulse rounded" />
      </div>
      <div className="h-64 w-full bg-muted/30 rounded-lg animate-pulse" />
    </Card>
  );
}

/**
 * Error state for EquityCurve
 */
interface EquityCurveErrorProps {
  message: string;
  onRetry: () => void;
}

function EquityCurveError({ message, onRetry }: EquityCurveErrorProps) {
  return (
    <Card className="p-6">
      <CompactErrorState
        error={message}
        onRetry={onRetry}
        retryButtonText="Retry"
      />
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
 * Custom tooltip for the equity chart
 */
interface ChartTooltipProps extends TooltipProps<number, string> {
  active?: boolean;
  payload?: Array<{
    value: number;
    payload: {
      date: string;
      equity: number;
      pnl: number;
      drawdown: number;
    };
  }>;
}

function ChartTooltip({ active, payload }: ChartTooltipProps) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const data = payload[0].payload;
  const date = new Date(data.date).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

  return (
    <div className="bg-background border border-border rounded-lg p-3 shadow-lg">
      <p className="text-sm font-medium mb-2">{date}</p>
      <div className="space-y-1 text-xs">
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Equity:</span>
          <span className="font-medium">${data.equity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">P&L:</span>
          <span className={`font-medium ${data.pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
            {data.pnl >= 0 ? '+' : ''}${data.pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Drawdown:</span>
          <span className="font-medium text-loss">{(data.drawdown * 100).toFixed(1)}%</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Transform equity history data for chart display
 */
function transformChartData(history: NonNullable<ReturnType<typeof useEquityHistory>['history']>) {
  if (!history) return [];

  return history.history.map((point) => ({
    ...point,
    formattedDate: new Date(point.date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    }),
  }));
}

/**
 * Main EquityCurve component
 */
export function EquityCurve() {
  const {
    history,
    isLoading,
    error,
    dateRange,
    setDateRange,
    retry,
  } = useEquityHistory('all', 30000);

  // Show loading skeleton
  if (isLoading && !history) {
    return <EquityCurveSkeleton />;
  }

  // Show error state
  if (error && !history) {
    return <EquityCurveError message={error} onRetry={retry} />;
  }

  // Show empty state if no history
  if (!history || history.history.length === 0) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center py-8">
          <p className="text-muted-foreground">No equity history available</p>
        </div>
      </Card>
    );
  }

  const chartData = transformChartData(history);

  // Get peak equity points for markers
  const peakPoints = history.history
    .filter((point) => point.isPeak)
    .map((point) => ({
      x: new Date(point.date).getTime(),
      y: point.equity,
    }));

  return (
    <Card className="p-4 sm:p-6">
      <CardHeader className="p-0 mb-6">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-primary" />
            <span className="text-xl">Equity Curve</span>
          </CardTitle>
          <DateRangeSelector value={dateRange} onChange={setDateRange} />
        </div>
      </CardHeader>

      <div className="space-y-6">
        {/* Summary Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1">Starting Equity</p>
            <p className="text-lg font-bold">${history.startingEquity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
          </div>
          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1">Current Equity</p>
            <p className="text-lg font-bold">${history.currentEquity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
          </div>
          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1">Peak Equity</p>
            <p className="text-lg font-bold">${history.peakEquity.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
          </div>
          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1">Total Return</p>
            <p className={`text-lg font-bold ${history.totalReturnPercent >= 0 ? 'text-profit' : 'text-loss'}`}>
              {history.totalReturnPercent >= 0 ? '+' : ''}{history.totalReturnPercent.toFixed(2)}%
            </p>
          </div>
        </div>

        {/* Chart */}
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              {/* Starting equity reference line */}
              <ReferenceLine
                y={history.startingEquity}
                stroke="#8ba69a"
                strokeDasharray="3 3"
                label={{ value: 'Starting', fill: '#8ba69a', fontSize: 12 }}
              />

              {/* Peak equity marker (using scatter) */}
              {peakPoints.length > 0 && (
                <Scatter>
                  {peakPoints.map((point, index) => (
                    <Cell key={`peak-${index}`} x={point.x} y={point.y} fill="#c4f54d" r={6} />
                  ))}
                </Scatter>
              )}

              <XAxis
                dataKey="formattedDate"
                stroke="#8ba69a"
                style={{ fontSize: '12px' }}
                tickFormatter={(value) => value}
              />
              <YAxis
                stroke="#8ba69a"
                style={{ fontSize: '12px' }}
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
              />
              <Tooltip content={<ChartTooltip />} />
              <Area
                type="monotone"
                dataKey="equity"
                stroke="#c4f54d"
                strokeWidth={2}
                fill="#c4f54d"
                fillOpacity={0.2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Max Drawdown Indicator */}
        <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg border border-border">
          <span className="text-sm text-muted-foreground">Maximum Drawdown</span>
          <span className="text-lg font-bold text-loss">
            {(history.maxDrawdown * 100).toFixed(1)}%
          </span>
        </div>
      </div>
    </Card>
  );
}

// Export as default for backward compatibility
export default EquityCurve;
