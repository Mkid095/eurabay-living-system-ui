"use client";

import { useState, useEffect, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, TrendingUp, RefreshCw, Calendar } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
  Brush
} from "recharts";
import type { GenerationHistory } from "@/types/evolution";

type DateRange = 7 | 30 | 90 | 'all';

interface GenerationHistoryChartProps {
  data: GenerationHistory[];
  loading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  onDateRangeChange?: (days: DateRange) => void;
}

const DATE_RANGE_OPTIONS: { value: DateRange; label: string }[] = [
  { value: 7, label: '7 Days' },
  { value: 30, label: '30 Days' },
  { value: 90, label: '90 Days' },
  { value: 'all', label: 'All' },
];

/**
 * Format a timestamp to a readable date string
 */
function formatTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  });
}

/**
 * Format a timestamp to a full datetime string for tooltips
 */
function formatFullTimestamp(timestamp: string): string {
  return new Date(timestamp).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Calculate fitness improvement percentage from first to last generation
 */
function calculateFitnessImprovement(data: GenerationHistory[]): number {
  if (data.length < 2) return 0;

  const firstFitness = data[0].fitness;
  const lastFitness = data[data.length - 1].fitness;

  if (firstFitness === 0) return 0;

  return ((lastFitness - firstFitness) / firstFitness) * 100;
}

export const GenerationHistoryChart = ({
  data,
  loading = false,
  error = null,
  onRefresh,
  onDateRangeChange,
}: GenerationHistoryChartProps) => {
  const [selectedRange, setSelectedRange] = useState<DateRange>('all');
  const [autoRefreshInterval, setAutoRefreshInterval] = useState<ReturnType<typeof setInterval> | null>(null);

  /**
   * Handle date range change
   */
  const handleRangeChange = useCallback((range: DateRange) => {
    setSelectedRange(range);
    if (onDateRangeChange) {
      onDateRangeChange(range);
    }
  }, [onDateRangeChange]);

  /**
   * Setup auto-refresh every 10 seconds
   */
  useEffect(() => {
    const interval = setInterval(() => {
      if (onRefresh) {
        onRefresh();
      }
    }, 10000);

    setAutoRefreshInterval(interval);

    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [onRefresh]);

  /**
   * Calculate derived metrics
   */
  const fitnessImprovement = calculateFitnessImprovement(data);
  const currentGeneration = data.length > 0 ? data[data.length - 1].generation : 0;
  const currentFitness = data.length > 0 ? data[data.length - 1].fitness : 0;

  /**
   * Loading state - show skeleton
   */
  if (loading) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <Skeleton className="h-6 w-48 mb-2" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Skeleton className="h-10 w-24" />
        </div>

        <div className="flex gap-2 mb-4">
          {DATE_RANGE_OPTIONS.map((option) => (
            <Skeleton key={option.value} className="h-8 w-16" />
          ))}
        </div>

        <Skeleton className="h-[300px] w-full" />
      </Card>
    );
  }

  /**
   * Error state - show error message with retry button
   */
  if (error) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold">Evolution History</h3>
            <p className="text-sm text-muted-foreground">Generation progression over time</p>
          </div>
          <TrendingUp className="w-5 h-5 text-primary" />
        </div>

        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>{error}</span>
            {onRefresh && (
              <Button
                variant="outline"
                size="sm"
                onClick={onRefresh}
                className="ml-4"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Retry
              </Button>
            )}
          </AlertDescription>
        </Alert>
      </Card>
    );
  }

  /**
   * Empty state - show message when no data available
   */
  if (data.length === 0) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold">Evolution History</h3>
            <p className="text-sm text-muted-foreground">Generation progression over time</p>
          </div>
          <TrendingUp className="w-5 h-5 text-primary" />
        </div>

        <div className="flex items-center justify-center h-[300px] text-muted-foreground">
          <p>No generation history data available</p>
        </div>
      </Card>
    );
  }

  /**
   * Main chart display
   */
  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-1">
            <h3 className="text-lg font-semibold">Evolution History</h3>
            <Badge variant="secondary" className="text-xs">
              Gen {currentGeneration}
            </Badge>
            <Badge
              variant="secondary"
              className={`text-xs ${
                fitnessImprovement > 0
                  ? "bg-profit/10 text-profit border-profit/20"
                  : fitnessImprovement < 0
                  ? "bg-loss/10 text-loss border-loss/20"
                  : ""
              }`}
            >
              {fitnessImprovement > 0 ? '+' : ''}
              {fitnessImprovement.toFixed(1)}% vs first
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Generation progression over time
          </p>
        </div>
        <div className="flex items-center gap-2">
          {onRefresh && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRefresh}
              className="gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </Button>
          )}
          <TrendingUp className="w-5 h-5 text-primary" />
        </div>
      </div>

      {/* Date Range Selector */}
      <div className="flex items-center gap-2 mb-4">
        <Calendar className="w-4 h-4 text-muted-foreground" />
        <div className="flex gap-1">
          {DATE_RANGE_OPTIONS.map((option) => (
            <Button
              key={option.value}
              variant={selectedRange === option.value ? "default" : "ghost"}
              size="sm"
              onClick={() => handleRangeChange(option.value)}
              className="h-8 text-xs"
            >
              {option.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Chart */}
      <div className="h-[350px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 5, right: 30, left: 20, bottom: 60 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              dataKey="generation"
              stroke="var(--muted-foreground)"
              fontSize={12}
              tickFormatter={(value) => `Gen ${value}`}
              label={{
                value: 'Generation Number',
                position: 'insideBottom',
                offset: -10,
                style: { fontSize: 12, fill: 'var(--muted-foreground)' },
              }}
            />
            <YAxis
              stroke="var(--muted-foreground)"
              fontSize={12}
              domain={[0, 1]}
              tickFormatter={(value) => (value * 100).toFixed(0) + '%'}
              label={{
                value: 'Fitness Score',
                angle: -90,
                position: 'insideLeft',
                style: { fontSize: 12, fill: 'var(--muted-foreground)' },
              }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--card)',
                border: '1px solid var(--border)',
                borderRadius: '0.5rem',
              }}
              formatter={(value: number | undefined, name: string) => {
                const numValue = typeof value === 'number' ? value : 0;
                if (name === 'Fitness Score') {
                  return [(numValue * 100).toFixed(2) + '%', name];
                }
                if (name === 'Avg Performance') {
                  return [(numValue * 100).toFixed(2) + '%', name];
                }
                return [numValue, name];
              }}
              labelFormatter={(value) => {
                const entry = data.find((d) => d.generation === value);
                if (!entry) return `Generation ${value}`;
                return `Generation ${value} - ${formatFullTimestamp(entry.timestamp)}`;
              }}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="fitness"
              stroke="var(--primary)"
              strokeWidth={2}
              name="Fitness Score"
              dot={{ fill: 'var(--primary)', r: 4 }}
              activeDot={{ r: 6, stroke: 'var(--primary)', strokeWidth: 2 }}
            />
            <Line
              type="monotone"
              dataKey="avgPerformance"
              stroke="var(--chart-2)"
              strokeWidth={2}
              name="Avg Performance"
              dot={{ fill: 'var(--chart-2)', r: 4 }}
              activeDot={{ r: 6, stroke: 'var(--chart-2)', strokeWidth: 2 }}
            />
            <Brush
              dataKey="generation"
              height={30}
              stroke="var(--border)"
              fill="var(--muted)"
              travellerWidth={10}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Current Stats */}
      <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-border">
        <div className="text-center">
          <p className="text-sm text-muted-foreground">Current Generation</p>
          <p className="text-2xl font-semibold">{currentGeneration}</p>
        </div>
        <div className="text-center">
          <p className="text-sm text-muted-foreground">Current Fitness</p>
          <p className="text-2xl font-semibold">{(currentFitness * 100).toFixed(1)}%</p>
        </div>
        <div className="text-center">
          <p className="text-sm text-muted-foreground">Total Generations</p>
          <p className="text-2xl font-semibold">{data.length}</p>
        </div>
      </div>
    </Card>
  );
};
