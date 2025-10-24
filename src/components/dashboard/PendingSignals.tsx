"use client";

import { Card } from "@/components/ui/card";
import { Trade } from "@/hooks/useDashboardData";
import { Button } from "@/components/ui/button";
import { Check, X, Clock } from "lucide-react";
import { cn } from "@/lib/utils";

interface PendingSignalsProps {
  signals: Trade[];
}

export function PendingSignals({ signals }: PendingSignalsProps) {
  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-4">
        <Clock className="w-5 h-5 text-primary" />
        <h2 className="text-xl font-bold">Pending Signals</h2>
        <span className="ml-auto bg-primary/20 text-primary px-2 py-1 rounded text-sm font-medium">
          {signals.length}
        </span>
      </div>

      <div className="space-y-3">
        {signals.map((signal) => (
          <div key={signal.id} className="p-4 bg-muted/50 border border-border rounded-lg">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-bold text-lg">{signal.pair}</span>
                  <span className={cn(
                    "px-2 py-0.5 rounded text-xs font-medium",
                    signal.type === 'BUY' 
                      ? "bg-profit/20 text-profit" 
                      : "bg-loss/20 text-loss"
                  )}>
                    {signal.type}
                  </span>
                </div>
                <p className="text-sm text-muted-foreground">
                  Entry: {signal.entryPrice.toFixed(4)} • Amount: ${signal.amount.toLocaleString()}
                </p>
              </div>
            </div>

            <div className="flex gap-2">
              <Button size="sm" className="flex-1 bg-profit hover:bg-profit/90 text-white">
                <Check className="w-4 h-4 mr-1" />
                Execute
              </Button>
              <Button size="sm" variant="outline" className="flex-1 border-loss text-loss hover:bg-loss/10">
                <X className="w-4 h-4 mr-1" />
                Reject
              </Button>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
