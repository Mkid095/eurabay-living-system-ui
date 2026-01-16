"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CompactErrorState } from "@/components/ui/error-state";
import { Activity, Dna, Zap, Clock, RefreshCw } from "lucide-react";
import type { EvolutionMetrics as EvolutionMetricsType } from "@/types/evolution";
import { useEvolutionData } from "@/hooks/useEvolutionData";
import { useRealTimeEvolution } from "@/hooks/useRealTimeEvolution";
import type { EvolutionLog } from "@/types/evolution";

/**
 * Format uptime duration from milliseconds to HH:MM:SS
 */
function formatUptime(birthTime: string): string {
  const birth = new Date(birthTime).getTime();
  const now = Date.now();
  const diff = now - birth;

  const hours = Math.floor(diff / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((diff % (1000 * 60)) / 1000);

  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

/**
 * Get color class for controller decision
 */
function getDecisionColor(decision: string) {
  switch (decision) {
    case 'STABLE':
      return 'bg-profit/20 text-profit border-profit/30';
    case 'EVOLVE_CONSERVATIVE':
      return 'bg-info/20 text-info border-info/30';
    case 'EVOLVE_MODERATE':
      return 'bg-warning/20 text-warning border-warning/30';
    case 'EVOLVE_AGGRESSIVE':
      return 'bg-loss/20 text-loss border-loss/30';
    default:
      return 'bg-muted text-muted-foreground';
  }
}

/**
 * Loading skeleton for EvolutionMetrics
 */
function EvolutionMetricsSkeleton() {
  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="h-6 w-40 bg-muted animate-pulse rounded mb-2" />
          <div className="h-4 w-48 bg-muted animate-pulse rounded" />
        </div>
        <div className="w-8 h-8 rounded-full bg-muted animate-pulse" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="space-y-2">
            <div className="h-4 w-24 bg-muted animate-pulse rounded" />
            <div className="h-8 w-32 bg-muted animate-pulse rounded" />
          </div>
        ))}
      </div>
    </Card>
  );
}

/**
 * Error state for EvolutionMetrics
 */
interface EvolutionMetricsErrorProps {
  message: string;
  onRetry: () => void;
}

function EvolutionMetricsError({ message, onRetry }: EvolutionMetricsErrorProps) {
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
 * EvolutionMetrics component props
 */
interface EvolutionMetricsProps {
  initialMetrics?: EvolutionMetricsType | null;
  initialEvolutionLog?: EvolutionLog[];
}

/**
 * EvolutionMetrics component
 *
 * Displays current evolution status and metrics including:
 * - Current generation number
 * - Controller decision with color-coded badge
 * - Cycles completed
 * - System version
 * - Birth time
 * - Uptime counter
 *
 * Features:
 * - Real-time updates via WebSocket
 * - Auto-refresh every 5 seconds
 * - Manual refresh button
 * - Loading skeleton
 * - Error state with retry
 */
export const EvolutionMetrics = ({
  initialMetrics,
  initialEvolutionLog = []
}: EvolutionMetricsProps) => {
  // Use real-time hook for WebSocket updates
  const {
    metrics: realtimeMetrics,
    isConnected,
  } = useRealTimeEvolution(initialMetrics, initialEvolutionLog, {
    enableToasts: true,
    maxLogSize: 100,
    enableAutoScroll: true,
  });

  // Use hook if metrics are not provided as props
  const { evolutionMetrics: hookMetrics, loading, error, refetchMetrics } = useEvolutionData({
    refreshInterval: 5000,
    enableAutoRefresh: !initialMetrics,
  });

  const metrics = realtimeMetrics || hookMetrics;

  // Show loading skeleton
  if (loading.metrics && !metrics) {
    return <EvolutionMetricsSkeleton />;
  }

  // Show error state
  if (error.metrics && !metrics) {
    return <EvolutionMetricsError message={error.metrics} onRetry={refetchMetrics} />;
  }

  // Show empty state if no metrics
  if (!metrics) {
    return (
      <Card className="p-6">
        <div className="flex items-center justify-center py-8">
          <p className="text-muted-foreground">No evolution metrics available</p>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">Evolution Status</h3>
          <p className="text-sm text-muted-foreground">Living System Metrics</p>
        </div>
        <div className="flex items-center gap-2">
          {!initialMetrics && (
            <Button
              variant="ghost"
              size="icon"
              onClick={refetchMetrics}
              disabled={loading.metrics}
              className="h-8 w-8"
            >
              <RefreshCw className={`w-4 h-4 ${loading.metrics ? 'animate-spin' : ''}`} />
            </Button>
          )}
          <Dna className="w-8 h-8 text-primary" />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-primary" />
            <span className="text-sm text-muted-foreground">Generation</span>
          </div>
          <p className="text-2xl font-bold text-primary">#{metrics.currentGeneration}</p>
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            <span className="text-sm text-muted-foreground">Cycles</span>
          </div>
          <p className="text-2xl font-bold">{metrics.cyclesCompleted}</p>
        </div>

        <div className="space-y-2 sm:col-span-2">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">Controller Decision</span>
          </div>
          <Badge className={getDecisionColor(metrics.controllerDecision)}>
            {metrics.controllerDecision.replace(/_/g, ' ')}
          </Badge>
        </div>

        <div className="space-y-2 sm:col-span-2">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-muted-foreground" />
            <span className="text-sm text-muted-foreground">System Uptime</span>
          </div>
          <p className="text-sm font-mono">{formatUptime(metrics.birthTime)}</p>
        </div>

        <div className="space-y-1 sm:col-span-2">
          <p className="text-xs text-muted-foreground">Version: {metrics.systemVersion}</p>
          <p className="text-xs text-muted-foreground">Birth: {new Date(metrics.birthTime).toLocaleString()}</p>
        </div>
      </div>
    </Card>
  );
};
