"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Activity, Dna, TrendingUp, TrendingDown } from "lucide-react";
import type { EvolutionLog } from "@/types/evolution";

interface EvolutionLogViewerProps {
  logs: EvolutionLog[];
}

export const EvolutionLogViewer = ({ logs }: EvolutionLogViewerProps) => {
  const getLogTypeColor = (type: string) => {
    switch (type) {
      case 'EVOLUTION_CYCLE':
        return 'bg-primary/20 text-primary border-primary/30';
      case 'MUTATION':
        return 'bg-info/20 text-info border-info/30';
      case 'FEATURE_SUCCESS':
        return 'bg-profit/20 text-profit border-profit/30';
      case 'FEATURE_FAILURE':
        return 'bg-loss/20 text-loss border-loss/30';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  const getLogIcon = (type: string) => {
    switch (type) {
      case 'EVOLUTION_CYCLE':
        return <Dna className="w-4 h-4" />;
      case 'MUTATION':
        return <Activity className="w-4 h-4" />;
      case 'FEATURE_SUCCESS':
        return <TrendingUp className="w-4 h-4" />;
      case 'FEATURE_FAILURE':
        return <TrendingDown className="w-4 h-4" />;
      default:
        return <Activity className="w-4 h-4" />;
    }
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">Evolution Log</h3>
          <p className="text-sm text-muted-foreground">Real-time evolution events</p>
        </div>
        <Dna className="w-5 h-5 text-primary" />
      </div>

      <ScrollArea className="h-[400px]">
        <div className="space-y-3">
          {logs.map((log, index) => (
            <div key={index} className="p-3 rounded-lg bg-card border border-border hover:bg-accent/5 transition-colors">
              <div className="flex items-start gap-3">
                <div className={`mt-0.5 ${getLogTypeColor(log.type).split(' ')[1]}`}>
                  {getLogIcon(log.type)}
                </div>
                
                <div className="flex-1 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <Badge className={getLogTypeColor(log.type)}>
                      {log.type.replace(/_/g, ' ')}
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      Gen #{log.generation}
                    </span>
                  </div>
                  
                  <p className="text-sm">{log.message}</p>
                  
                  {log.details && Object.keys(log.details).length > 0 && (
                    <div className="text-xs text-muted-foreground font-mono bg-muted/30 p-2 rounded">
                      {JSON.stringify(log.details, null, 2)}
                    </div>
                  )}
                  
                  <span className="text-xs text-muted-foreground">
                    {new Date(log.timestamp).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </Card>
  );
};
