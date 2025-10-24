"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, Dna, Zap, Clock } from "lucide-react";
import type { EvolutionMetrics as EvolutionMetricsType } from "@/types/evolution";

interface EvolutionMetricsProps {
  metrics: EvolutionMetricsType;
}

export const EvolutionMetrics = ({ metrics }: EvolutionMetricsProps) => {
  const getDecisionColor = (decision: string) => {
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
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">Evolution Status</h3>
          <p className="text-sm text-muted-foreground">Living System Metrics</p>
        </div>
        <Dna className="w-8 h-8 text-primary" />
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
          <p className="text-sm font-mono">{metrics.uptime}</p>
        </div>

        <div className="space-y-1 sm:col-span-2">
          <p className="text-xs text-muted-foreground">Version: {metrics.systemVersion}</p>
          <p className="text-xs text-muted-foreground">Birth: {new Date(metrics.birthTime).toLocaleString()}</p>
        </div>
      </div>
    </Card>
  );
};
