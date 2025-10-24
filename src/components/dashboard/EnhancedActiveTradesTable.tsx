"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, TrendingDown } from "lucide-react";
import type { EvolvedTrade } from "@/types/evolution";

interface EnhancedActiveTradesTableProps {
  trades: EvolvedTrade[];
}

export const EnhancedActiveTradesTable = ({ trades }: EnhancedActiveTradesTableProps) => {
  return (
    <Card className="p-6">
      <div className="mb-6">
        <h3 className="text-lg font-semibold">Active Trades (Enhanced)</h3>
        <p className="text-sm text-muted-foreground">Trades with evolved features</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">Symbol</th>
              <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">Side</th>
              <th className="text-right py-3 px-2 text-sm font-medium text-muted-foreground">Entry</th>
              <th className="text-right py-3 px-2 text-sm font-medium text-muted-foreground">Current</th>
              <th className="text-right py-3 px-2 text-sm font-medium text-muted-foreground">P&L</th>
              <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">Context</th>
              <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">Features</th>
            </tr>
          </thead>
          <tbody>
            {trades.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-muted-foreground">
                  No active trades
                </td>
              </tr>
            ) : (
              trades.map((trade) => (
                <tr key={trade.ticket} className="border-b border-border hover:bg-accent/5">
                  <td className="py-3 px-2">
                    <span className="font-medium">{trade.symbol}</span>
                  </td>
                  <td className="py-3 px-2">
                    <Badge className={trade.side === 'BUY' ? 'bg-profit/20 text-profit' : 'bg-loss/20 text-loss'}>
                      {trade.side === 'BUY' ? (
                        <TrendingUp className="w-3 h-3 mr-1" />
                      ) : (
                        <TrendingDown className="w-3 h-3 mr-1" />
                      )}
                      {trade.side}
                    </Badge>
                  </td>
                  <td className="py-3 px-2 text-right font-mono text-sm">
                    {trade.entryPrice.toFixed(5)}
                  </td>
                  <td className="py-3 px-2 text-right font-mono text-sm">
                    {trade.currentPrice.toFixed(5)}
                  </td>
                  <td className="py-3 px-2 text-right">
                    <span className={trade.pnl >= 0 ? 'text-profit font-semibold' : 'text-loss font-semibold'}>
                      ${trade.pnl.toFixed(2)}
                    </span>
                  </td>
                  <td className="py-3 px-2">
                    <div className="space-y-1">
                      <div className="text-xs">
                        <span className="text-muted-foreground">LTF:</span>{' '}
                        <span className="font-medium">{trade.ltfContext}</span>
                      </div>
                      <div className="text-xs">
                        <span className="text-muted-foreground">HTF:</span>{' '}
                        <span className="font-medium">{trade.htfContext}</span>
                      </div>
                      <div className="text-xs">
                        <span className="text-muted-foreground">Conf:</span>{' '}
                        <span className="font-medium">{(trade.confidence * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-2">
                    <div className="flex flex-wrap gap-1">
                      {trade.featuresUsed.map((feature, idx) => (
                        <Badge key={idx} variant="outline" className="text-xs">
                          {feature}
                        </Badge>
                      ))}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
};
