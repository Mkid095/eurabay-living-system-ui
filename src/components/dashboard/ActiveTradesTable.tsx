"use client";

import { Card } from "@/components/ui/card";
import { Trade } from "@/hooks/useDashboardData";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ActiveTradesTableProps {
  trades: Trade[];
}

export function ActiveTradesTable({ trades }: ActiveTradesTableProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatTime = (date: Date) => {
    const diff = Date.now() - date.getTime();
    const hours = Math.floor(diff / 3600000);
    const minutes = Math.floor((diff % 3600000) / 60000);
    return `${hours}h ${minutes}m ago`;
  };

  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold">Active Trades</h2>
        <Button variant="outline" size="sm" className="text-primary border-primary">
          View All
        </Button>
      </div>

      {/* Desktop Table */}
      <div className="hidden md:block overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border text-left text-sm text-muted-foreground">
              <th className="pb-3 font-medium">Pair</th>
              <th className="pb-3 font-medium">Type</th>
              <th className="pb-3 font-medium">Entry</th>
              <th className="pb-3 font-medium">Current</th>
              <th className="pb-3 font-medium">Amount</th>
              <th className="pb-3 font-medium">P&L</th>
              <th className="pb-3 font-medium">Time</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((trade) => (
              <tr key={trade.id} className="border-b border-border/50 hover:bg-muted/50 transition-colors">
                <td className="py-4 font-medium">{trade.pair}</td>
                <td className="py-4">
                  <span className={cn(
                    "px-2 py-1 rounded text-xs font-medium",
                    trade.type === 'BUY' 
                      ? "bg-profit/20 text-profit" 
                      : "bg-loss/20 text-loss"
                  )}>
                    {trade.type}
                  </span>
                </td>
                <td className="py-4 text-sm">{trade.entryPrice.toFixed(4)}</td>
                <td className="py-4 text-sm">{trade.currentPrice.toFixed(4)}</td>
                <td className="py-4 text-sm">{formatCurrency(trade.amount)}</td>
                <td className="py-4">
                  <div className={cn(
                    "flex items-center gap-1 font-medium",
                    trade.pnl >= 0 ? "text-profit" : "text-loss"
                  )}>
                    {trade.pnl >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                    <span>{formatCurrency(trade.pnl)}</span>
                    <span className="text-xs">({trade.pnlPercent.toFixed(2)}%)</span>
                  </div>
                </td>
                <td className="py-4 text-sm text-muted-foreground">{formatTime(trade.timestamp)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Cards */}
      <div className="md:hidden space-y-3">
        {trades.map((trade) => (
          <div key={trade.id} className="p-4 bg-card border border-border rounded-lg">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="font-bold">{trade.pair}</span>
                <span className={cn(
                  "px-2 py-0.5 rounded text-xs font-medium",
                  trade.type === 'BUY' 
                    ? "bg-profit/20 text-profit" 
                    : "bg-loss/20 text-loss"
                )}>
                  {trade.type}
                </span>
              </div>
              <div className={cn(
                "font-bold",
                trade.pnl >= 0 ? "text-profit" : "text-loss"
              )}>
                {formatCurrency(trade.pnl)}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-muted-foreground">Entry:</span>
                <span className="ml-1 font-medium">{trade.entryPrice.toFixed(4)}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Current:</span>
                <span className="ml-1 font-medium">{trade.currentPrice.toFixed(4)}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Amount:</span>
                <span className="ml-1 font-medium">{formatCurrency(trade.amount)}</span>
              </div>
              <div>
                <span className="text-muted-foreground">P&L:</span>
                <span className={cn(
                  "ml-1 font-medium",
                  trade.pnl >= 0 ? "text-profit" : "text-loss"
                )}>
                  {trade.pnlPercent.toFixed(2)}%
                </span>
              </div>
            </div>
            <div className="mt-2 text-xs text-muted-foreground">{formatTime(trade.timestamp)}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}
