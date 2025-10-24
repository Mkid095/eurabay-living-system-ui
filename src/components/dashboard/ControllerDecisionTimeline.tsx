"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Brain } from "lucide-react";
import type { ControllerDecisionHistory } from "@/types/evolution";

interface ControllerDecisionTimelineProps {
  data: ControllerDecisionHistory[];
}

export const ControllerDecisionTimeline = ({ data }: ControllerDecisionTimelineProps) => {
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

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case 'STABLE':
        return '✓';
      case 'EVOLVE_CONSERVATIVE':
        return '→';
      case 'EVOLVE_MODERATE':
        return '↗';
      case 'EVOLVE_AGGRESSIVE':
        return '⇈';
      default:
        return '•';
    }
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">Controller Decision History</h3>
          <p className="text-sm text-muted-foreground">Evolution strategy timeline</p>
        </div>
        <Brain className="w-5 h-5 text-primary" />
      </div>

      <div className="space-y-4 max-h-[400px] overflow-y-auto">
        {data.map((item, index) => (
          <div key={index} className="relative pl-8 pb-4 border-l-2 border-border last:border-l-0">
            <div className="absolute left-[-9px] top-0 w-4 h-4 rounded-full bg-primary border-2 border-background flex items-center justify-center">
              <span className="text-[10px]">{getDecisionIcon(item.decision)}</span>
            </div>
            
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Badge className={getDecisionColor(item.decision)}>
                  {item.decision.replace(/_/g, ' ')}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {new Date(item.timestamp).toLocaleString()}
                </span>
              </div>
              
              <div className="flex items-center gap-4 text-sm">
                <span className="text-muted-foreground">Performance:</span>
                <span className="font-semibold">{item.performance.toFixed(2)}%</span>
              </div>
              
              {item.reason && (
                <p className="text-xs text-muted-foreground italic">{item.reason}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};
