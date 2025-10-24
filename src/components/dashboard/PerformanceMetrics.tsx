"use client";

import { Card } from "@/components/ui/card";
import { PerformanceMetrics as Metrics } from "@/hooks/useDashboardData";
import { Award, TrendingUp, TrendingDown } from "lucide-react";
import { Progress } from "@/components/ui/progress";

interface PerformanceMetricsProps {
  metrics: Metrics;
}

export function PerformanceMetrics({ metrics }: PerformanceMetricsProps) {
  const winRate = (metrics.winningTrades / metrics.totalTrades) * 100;

  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-6">
        <Award className="w-5 h-5 text-primary" />
        <h2 className="text-xl font-bold">Performance Metrics</h2>
      </div>

      <div className="space-y-6">
        {/* Win Rate */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Win Rate</span>
            <span className="text-lg font-bold text-profit">{winRate.toFixed(1)}%</span>
          </div>
          <Progress value={winRate} className="h-2" />
          <div className="flex justify-between text-xs text-muted-foreground mt-1">
            <span>{metrics.winningTrades} wins</span>
            <span>{metrics.losingTrades} losses</span>
          </div>
        </div>

        {/* Statistics Grid */}
        <div className="grid grid-cols-2 gap-4">
          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <div className="flex items-center gap-2 text-profit mb-1">
              <TrendingUp className="w-4 h-4" />
              <span className="text-xs font-medium">Avg Win</span>
            </div>
            <p className="text-xl font-bold">${metrics.avgWin.toFixed(2)}</p>
          </div>

          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <div className="flex items-center gap-2 text-loss mb-1">
              <TrendingDown className="w-4 h-4" />
              <span className="text-xs font-medium">Avg Loss</span>
            </div>
            <p className="text-xl font-bold">${Math.abs(metrics.avgLoss).toFixed(2)}</p>
          </div>

          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1">Sharpe Ratio</p>
            <p className="text-xl font-bold text-primary">{metrics.sharpeRatio.toFixed(2)}</p>
          </div>

          <div className="p-3 bg-muted/50 rounded-lg border border-border">
            <p className="text-xs text-muted-foreground mb-1">Max Drawdown</p>
            <p className="text-xl font-bold text-loss">{metrics.maxDrawdown.toFixed(1)}%</p>
          </div>
        </div>

        {/* Total Trades */}
        <div className="pt-4 border-t border-border">
          <div className="flex justify-between items-center">
            <span className="text-sm text-muted-foreground">Total Trades</span>
            <span className="text-2xl font-bold">{metrics.totalTrades}</span>
          </div>
        </div>
      </div>
    </Card>
  );
}
