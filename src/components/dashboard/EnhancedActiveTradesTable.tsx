"use client";

import { useState, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { DataTableSkeleton } from "@/components/ui/loading-skeleton";
import { CompactErrorState } from "@/components/ui/error-state";
import {
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Clock,
  Target,
  Shield,
  ExternalLink,
} from "lucide-react";
import { useActiveTrades } from "@/hooks/useActiveTrades";
import { TradeDetailModal } from "./TradeDetailModal";
import { ModifySLTPDialog } from "./ModifySLTPDialog";
import type { EvolvedTrade } from "@/types/evolution";

export function EnhancedActiveTradesTable() {
  const {
    trades,
    isLoading,
    error,
    isConnected,
    refreshTrades,
    isFlashing,
  } = useActiveTrades();

  const [selectedTrade, setSelectedTrade] = useState<EvolvedTrade | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modifyTradeTicket, setModifyTradeTicket] = useState<string | null>(null);
  const [isModifyDialogOpen, setIsModifyDialogOpen] = useState(false);

  const handleRowClick = useCallback((trade: EvolvedTrade) => {
    setSelectedTrade(trade);
    setIsModalOpen(true);
  }, []);

  const handleCloseTrade = useCallback(async (ticket: string) => {
    try {
      const response = await fetch(`/api/trades/${ticket}/close`, {
        method: "POST",
      });
      if (response.ok) {
        await refreshTrades();
      }
    } catch (error) {
      console.error("Failed to close trade:", error);
    }
  }, [refreshTrades]);

  const handleModifySLTP = useCallback((ticket: string) => {
    setModifyTradeTicket(ticket);
    setIsModifyDialogOpen(true);
  }, []);

  const handleSaveSLTP = useCallback(async (
    ticket: string,
    stopLoss?: number,
    takeProfit?: number
  ) => {
    try {
      const response = await fetch(`/api/trades/${ticket}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          stopLoss,
          takeProfit,
        }),
      });
      if (response.ok) {
        await refreshTrades();
      }
    } catch (error) {
      console.error("Failed to modify SL/TP:", error);
      throw error;
    }
  }, [refreshTrades]);

  const formatDuration = (entryTime: string): string => {
    const entry = new Date(entryTime);
    const now = new Date();
    const diffMs = now.getTime() - entry.getTime();
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));
    return `${hours}h ${minutes}m`;
  };

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="mb-6">
          <h3 className="text-lg font-semibold">Active Trades</h3>
          <p className="text-sm text-muted-foreground">Loading trades...</p>
        </div>
        <DataTableSkeleton rowCount={5} columnCount={13} />
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <CompactErrorState
          error={error}
          onRetry={refreshTrades}
          retryButtonText="Retry"
        />
      </Card>
    );
  }

  return (
    <>
      <Card className="p-6">
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">Active Trades</h3>
            <p className="text-sm text-muted-foreground">
              Real-time trade monitoring {isConnected && "(Connected)"}
            </p>
          </div>
          <Button onClick={refreshTrades} variant="outline" size="sm">
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </Button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                  System Ticket
                </th>
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                  MT5 Ticket
                </th>
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                  Symbol
                </th>
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                  Side
                </th>
                <th className="text-right py-3 px-2 text-sm font-medium text-muted-foreground">
                  Lots
                </th>
                <th className="text-right py-3 px-2 text-sm font-medium text-muted-foreground">
                  Entry
                </th>
                <th className="text-right py-3 px-2 text-sm font-medium text-muted-foreground">
                  Current
                </th>
                <th className="text-right py-3 px-2 text-sm font-medium text-muted-foreground">
                  P&L
                </th>
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                  SL/TP
                </th>
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                  Duration
                </th>
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                  Context
                </th>
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                  Features
                </th>
                <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                  Confidence
                </th>
              </tr>
            </thead>
            <tbody>
              {trades.length === 0 ? (
                <tr>
                  <td colSpan={13} className="text-center py-8 text-muted-foreground">
                    No active trades
                  </td>
                </tr>
              ) : (
                trades.map((trade) => (
                  <tr
                    key={trade.ticket}
                    className={`border-b border-border hover:bg-accent/5 cursor-pointer transition-colors ${
                      isFlashing(trade.ticket) ? "bg-accent/20" : ""
                    }`}
                    onClick={() => handleRowClick(trade)}
                  >
                    <td className="py-3 px-2">
                      <span className="font-mono text-sm">{trade.ticket}</span>
                    </td>
                    <td className="py-3 px-2">
                      {trade.mt5Ticket ? (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <div className="flex items-center gap-1 cursor-help">
                                <span className="font-mono text-sm text-blue-600">
                                  {trade.mt5Ticket}
                                </span>
                                <ExternalLink className="w-3 h-3 text-blue-600" />
                              </div>
                            </TooltipTrigger>
                            <TooltipContent>
                              <p className="text-xs">
                                {trade.mt5Comment || `MT5 Position #${trade.mt5Ticket}`}
                              </p>
                              {trade.generation && (
                                <p className="text-xs text-muted-foreground">
                                  Generation: {trade.generation}
                                </p>
                              )}
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      ) : (
                        <span className="text-xs text-muted-foreground">-</span>
                      )}
                    </td>
                    <td className="py-3 px-2">
                      <span className="font-medium">{trade.symbol}</span>
                    </td>
                    <td className="py-3 px-2">
                      <Badge
                        className={
                          trade.side === "BUY"
                            ? "bg-profit/20 text-profit"
                            : "bg-loss/20 text-loss"
                        }
                      >
                        {trade.side === "BUY" ? (
                          <TrendingUp className="w-3 h-3 mr-1" />
                        ) : (
                          <TrendingDown className="w-3 h-3 mr-1" />
                        )}
                        {trade.side}
                      </Badge>
                    </td>
                    <td className="py-3 px-2 text-right font-medium text-sm">
                      {trade.lots}
                    </td>
                    <td className="py-3 px-2 text-right font-mono text-sm">
                      {trade.entryPrice.toFixed(5)}
                    </td>
                    <td className="py-3 px-2 text-right font-mono text-sm">
                      {trade.currentPrice.toFixed(5)}
                    </td>
                    <td className="py-3 px-2 text-right">
                      <div className="space-y-1">
                        <span
                          className={
                            trade.pnl >= 0
                              ? "text-profit font-semibold"
                              : "text-loss font-semibold"
                          }
                        >
                          {trade.pnl >= 0 ? "+" : ""}
                          ${trade.pnl.toFixed(2)}
                        </span>
                        {trade.pnlPercent && (
                          <div className="text-xs text-muted-foreground">
                            ({trade.pnlPercent >= 0 ? "+" : ""}
                            {trade.pnlPercent.toFixed(2)}%)
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-2">
                      <div className="flex gap-1">
                        {trade.stopLoss && (
                          <div
                            className="flex items-center gap-1 text-xs text-loss"
                            title="Stop Loss"
                          >
                            <Shield className="w-3 h-3" />
                            {trade.stopLoss.toFixed(5)}
                          </div>
                        )}
                        {trade.takeProfit && (
                          <div
                            className="flex items-center gap-1 text-xs text-profit"
                            title="Take Profit"
                          >
                            <Target className="w-3 h-3" />
                            {trade.takeProfit.toFixed(5)}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-2">
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="w-3 h-3" />
                        {trade.duration || formatDuration(trade.entryTime)}
                      </div>
                    </td>
                    <td className="py-3 px-2">
                      <div className="space-y-1">
                        <div className="text-xs">
                          <span className="text-muted-foreground">HTF:</span>{" "}
                          <span className="font-medium">{trade.htfContext}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-muted-foreground">LTF:</span>{" "}
                          <span className="font-medium">{trade.ltfContext}</span>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-2">
                      <div className="flex flex-wrap gap-1 max-w-[150px]">
                        {trade.featuresUsed.slice(0, 2).map((feature, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">
                            {feature}
                          </Badge>
                        ))}
                        {trade.featuresUsed.length > 2 && (
                          <Badge variant="outline" className="text-xs">
                            +{trade.featuresUsed.length - 2}
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-2">
                      <div className="w-16">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-muted-foreground">
                            {(trade.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <Progress value={trade.confidence * 100} className="h-1" />
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <TradeDetailModal
        trade={selectedTrade}
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
        onCloseTrade={handleCloseTrade}
        onModifySLTP={handleModifySLTP}
      />

      <ModifySLTPDialog
        trade={trades.find((t) => t.ticket === modifyTradeTicket) || null}
        open={isModifyDialogOpen}
        onOpenChange={setIsModifyDialogOpen}
        onSave={handleSaveSLTP}
      />
    </>
  );
}
