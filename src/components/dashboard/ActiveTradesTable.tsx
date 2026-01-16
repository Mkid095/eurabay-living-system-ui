"use client";

import { Card } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useRealTimeTrades } from "@/hooks/useRealTimeTrades";
import type { EvolvedTrade } from "@/types/evolution";

interface ActiveTradesTableProps {
  initialTrades?: EvolvedTrade[];
  initialRecentTrades?: EvolvedTrade[];
}

export function ActiveTradesTable({
  initialTrades = [],
  initialRecentTrades = []
}: ActiveTradesTableProps) {
  const {
    activeTrades,
    isFlashing,
  } = useRealTimeTrades(initialTrades, initialRecentTrades, {
    enableFlash: true,
    enableToasts: true,
    pnlChangeThreshold: 10,
  });
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
            {activeTrades.map((trade) => (
              <tr
                key={trade.ticket}
                className={cn(
                  "border-b border-border/50 transition-colors",
                  isFlashing(trade.ticket) && "bg-muted/80",
                  !isFlashing(trade.ticket) && "hover:bg-muted/50"
                )}
              >
                <td className="py-4 font-medium">{trade.symbol}</td>
                <td className="py-4">
                  <span className={cn(
                    "px-2 py-1 rounded text-xs font-medium",
                    trade.action === 'BUY'
                      ? "bg-profit/20 text-profit"
                      : "bg-loss/20 text-loss"
                  )}>
                    {trade.action}
                  </span>
                </td>
                <td className="py-4 text-sm">{trade.entryPrice.toFixed(5)}</td>
                <td className="py-4 text-sm">{trade.currentPrice?.toFixed(5) || '-'}</td>
                <td className="py-4 text-sm">{formatCurrency(trade.volume)}</td>
                <td className="py-4">
                  <div className={cn(
                    "flex items-center gap-1 font-medium",
                    (trade.pnl ?? 0) >= 0 ? "text-profit" : "text-loss"
                  )}>
                    {(trade.pnl ?? 0) >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                    <span>{formatCurrency(trade.pnl ?? 0)}</span>
                    <span className="text-xs">({(trade.pnlPercent ?? 0).toFixed(2)}%)</span>
                  </div>
                </td>
                <td className="py-4 text-sm text-muted-foreground">{formatTime(new Date(trade.openTime))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile Cards */}
      <div className="md:hidden space-y-3">
        {activeTrades.map((trade) => (
          <div
            key={trade.ticket}
            className={cn(
              "p-4 bg-card border border-border rounded-lg transition-colors",
              isFlashing(trade.ticket) && "bg-muted/80"
            )}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <span className="font-bold">{trade.symbol}</span>
                <span className={cn(
                  "px-2 py-0.5 rounded text-xs font-medium",
                  trade.action === 'BUY'
                    ? "bg-profit/20 text-profit"
                    : "bg-loss/20 text-loss"
                )}>
                  {trade.action}
                </span>
              </div>
              <div className={cn(
                "font-bold",
                (trade.pnl ?? 0) >= 0 ? "text-profit" : "text-loss"
              )}>
                {formatCurrency(trade.pnl ?? 0)}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <span className="text-muted-foreground">Entry:</span>
                <span className="ml-1 font-medium">{trade.entryPrice.toFixed(5)}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Current:</span>
                <span className="ml-1 font-medium">{trade.currentPrice?.toFixed(5) || '-'}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Amount:</span>
                <span className="ml-1 font-medium">{formatCurrency(trade.volume)}</span>
              </div>
              <div>
                <span className="text-muted-foreground">P&L:</span>
                <span className={cn(
                  "ml-1 font-medium",
                  (trade.pnl ?? 0) >= 0 ? "text-profit" : "text-loss"
                )}>
                  {(trade.pnlPercent ?? 0).toFixed(2)}%
                </span>
              </div>
            </div>
            <div className="mt-2 text-xs text-muted-foreground">{formatTime(new Date(trade.openTime))}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}
