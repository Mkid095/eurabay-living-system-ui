/**
 * PnLHistory Component
 *
 * Displays portfolio profit and loss over time with:
 * - Bar chart with date on X-axis and P&L amount on Y-axis
 * - Color-coded bars (green=profit, red=loss)
 * - Tooltips with date, P&L, and trades count on hover
 * - Cumulative P&L line overlay
 * - Breakeven reference line
 * - Date range selector
 * - Symbol filter
 * - Auto-refresh every 30 seconds
 * - Loading skeleton
 * - Error state with retry
 */

"use client";

import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { CompactErrorState } from "@/components/ui/error-state";
import { BarChart3, Search, X } from "lucide-react";
import { usePnlHistory } from "@/hooks/usePnlHistory";
import type { DateRange } from "@/types/performance";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
  TooltipProps,
  CartesianGrid,
} from 'recharts';

/**
 * Loading skeleton for PnLHistory
 */
function PnLHistorySkeleton() {
  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="h-6 w-40 bg-muted animate-pulse rounded mb-2" />
          <div className="h-4 w-32 bg-muted animate-pulse rounded" />
        </div>
        <div className="flex items-center gap-2">
          <div className="h-8 w-24 bg-muted animate-pulse rounded" />
          <div className="h-8 w-32 bg-muted animate-pulse rounded" />
        </div>
      </div>
      <div className="h-64 w-full bg-muted/30 rounded-lg animate-pulse" />
    </Card>
  );
}

/**
 * Error state for PnLHistory
 */
interface PnLHistoryErrorProps {
  message: string;
  onRetry: () => void;
}

function PnLHistoryError({ message, onRetry }: PnLHistoryErrorProps) {
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
 * Symbol filter component
 */
interface SymbolFilterProps {
  value: string | undefined;
  onChange: (symbol: string | undefined) => void;
}

function SymbolFilter({ value, onChange }: SymbolFilterProps) {
  return (
    <div className="relative w-40">
      <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
      <Input
        type="text"
        placeholder="Filter symbol..."
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value || undefined)}
        className="pl-8 pr-8 h-7 text-sm"
      />
      {value && (
        <button
          onClick={() => onChange(undefined)}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </div>
  );
}

/**
 * Custom tooltip for the P&L chart
 */
interface ChartTooltipProps extends TooltipProps<number, string> {
  active?: boolean;
  payload?: Array<{
    value: number;
    name: string;
    payload: {
      date: string;
      pnl: number;
      cumulativePnl: number;
      tradesCount: number;
      symbol?: string;
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
          <span className="text-muted-foreground">P&L:</span>
          <span className={`font-medium ${data.pnl >= 0 ? 'text-profit' : 'text-loss'}`}>
            {data.pnl >= 0 ? '+' : ''}${data.pnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Cumulative:</span>
          <span className={`font-medium ${data.cumulativePnl >= 0 ? 'text-profit' : 'text-loss'}`}>
            {data.cumulativePnl >= 0 ? '+' : ''}${data.cumulativePnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>
        <div className="flex justify-between gap-4">
          <span className="text-muted-foreground">Trades:</span>
          <span className="font-medium">{data.tradesCount}</span>
        </div>
        {data.symbol && (
          <div className="flex justify-between gap-4">
            <span className="text-muted-foreground">Symbol:</span>
            <span className="font-medium">{data.symbol}</span>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Transform P&L history data for chart display
 */
function transformChartData(history: NonNullable<ReturnType<typeof usePnlHistory>['history']>) {
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
 * Main PnLHistory component
 */
export function PnLHistory() {
  const {
    history,
    isLoading,
    error,
    dateRange,
    setDateRange,
    symbol,
    setSymbol,
    retry,
  } = usePnlHistory('all', 30000);

  // Show loading skeleton
  if (isLoading && !history) {
    return <PnLHistorySkeleton />;
  }

  // Show error state
  if (error && !history) {
    return <PnLHistoryError message={error} onRetry={retry} />;
  }

  // Show empty state if no history
  if (!history || history.history.length === 0) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center py-8">
          <p className="text-muted-foreground">No P&L history available</p>
        </div>
      </Card>
    );
  }

  const chartData = transformChartData(history);

  return (
    <Card className="p-4 sm:p-6">
      <CardHeader className="p-0 mb-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-primary" />
            <span className="text-xl">P&L History</span>
          </CardTitle>
          <div className="flex items-center gap-2">
            <SymbolFilter value={symbol} onChange={setSymbol} />
            <DateRangeSelector value={dateRange} onChange={setDateRange} />
          </div>
        </div>
      </CardHeader>

      <div className="space-y-6">
        {/* Summary Stats */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1">Total P&L</p>
            <p className={`text-lg font-bold ${history.totalPnl >= 0 ? 'text-profit' : 'text-loss'}`}>
              {history.totalPnl >= 0 ? '+' : ''}${history.totalPnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </p>
          </div>
          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1">Total P&L %</p>
            <p className={`text-lg font-bold ${history.totalPnlPercent >= 0 ? 'text-profit' : 'text-loss'}`}>
              {history.totalPnlPercent >= 0 ? '+' : ''}{history.totalPnlPercent.toFixed(2)}%
            </p>
          </div>
          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1">Winning Periods</p>
            <p className="text-lg font-bold text-profit">{history.winningPeriods}</p>
          </div>
          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1">Losing Periods</p>
            <p className="text-lg font-bold text-loss">{history.losingPeriods}</p>
          </div>
        </div>

        {/* Chart */}
        <div className="h-80 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#3a5555" opacity={0.3} />

              {/* Breakeven reference line */}
              <ReferenceLine
                y={0}
                stroke="#8ba69a"
                strokeDasharray="3 3"
              />

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

              {/* Bar chart for daily P&L */}
              <Bar dataKey="pnl" radius={[4, 4, 0, 0]}>
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.pnl >= 0 ? '#66bb6a' : '#ef5350'}
                    fillOpacity={0.8}
                  />
                ))}
              </Bar>

              {/* Cumulative P&L line overlay */}
              <Line
                type="monotone"
                dataKey="cumulativePnl"
                stroke="#c4f54d"
                strokeWidth={2}
                dot={false}
                yAxisId={0}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </Card>
  );
}

/**
 * Legacy PnLChart component for backward compatibility
 * Accepts data prop and displays a simple bar chart
 */
interface ChartDataPoint {
  time: string;
  value: number;
}

interface PnLChartProps {
  data: ChartDataPoint[];
}

export function PnLChart({ data }: PnLChartProps) {
  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 className="w-5 h-5 text-primary" />
        <h2 className="text-xl font-bold">Daily P&L</h2>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <XAxis
              dataKey="time"
              stroke="#8ba69a"
              style={{ fontSize: '12px' }}
            />
            <YAxis
              stroke="#8ba69a"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `$${value}`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#233d3d',
                border: '1px solid #3a5555',
                borderRadius: '8px',
                color: '#e8f5e9',
              }}
              formatter={(value?: number) => value !== undefined ? [`$${value.toLocaleString()}`, 'P&L'] : ['', 'P&L']}
            />
            <Bar dataKey="value" radius={[8, 8, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.value >= 0 ? '#66bb6a' : '#ef5350'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}

// Export as default
export default PnLHistory;
