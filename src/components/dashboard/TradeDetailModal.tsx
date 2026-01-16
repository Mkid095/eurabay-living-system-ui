"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { TrendingUp, TrendingDown, Clock, Target, Shield } from "lucide-react";
import type { EvolvedTrade } from "@/types/evolution";

interface TradeDetailModalProps {
  trade: EvolvedTrade | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCloseTrade?: (ticket: string) => Promise<void>;
}

export function TradeDetailModal({
  trade,
  open,
  onOpenChange,
  onCloseTrade,
}: TradeDetailModalProps) {
  const [isClosing, setIsClosing] = useState(false);

  if (!trade) return null;

  const handleCloseTrade = async () => {
    if (!onCloseTrade) return;

    setIsClosing(true);
    try {
      await onCloseTrade(trade.ticket);
      onOpenChange(false);
    } catch (error) {
      console.error("Failed to close trade:", error);
    } finally {
      setIsClosing(false);
    }
  };

  const pnlColor = trade.pnl >= 0 ? "text-profit" : "text-loss";
  const bgColor = trade.pnl >= 0 ? "bg-profit/10" : "bg-loss/10";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <span>Trade Details</span>
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
          </DialogTitle>
          <DialogDescription>
            Ticket #{trade.ticket} · {trade.symbol}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* P&L Summary */}
          <div className={`p-4 rounded-lg ${bgColor}`}>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Profit & Loss</p>
                <p className={`text-2xl font-bold ${pnlColor}`}>
                  {trade.pnl >= 0 ? "+" : ""}
                  ${trade.pnl.toFixed(2)}
                  {trade.pnlPercent && (
                    <span className="text-lg ml-2">
                      ({trade.pnlPercent >= 0 ? "+" : ""}
                      {trade.pnlPercent.toFixed(2)}%)
                    </span>
                  )}
                </p>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground">Current Price</p>
                <p className="text-lg font-mono font-semibold">
                  {trade.currentPrice.toFixed(5)}
                </p>
              </div>
            </div>
          </div>

          {/* Price Information */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Entry Price</p>
              <p className="font-mono font-semibold">
                {trade.entryPrice.toFixed(5)}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">Current Price</p>
              <p className="font-mono font-semibold">
                {trade.currentPrice.toFixed(5)}
              </p>
            </div>
          </div>

          {/* Stop Loss and Take Profit */}
          {(trade.stopLoss || trade.takeProfit) && (
            <div className="grid grid-cols-2 gap-4">
              {trade.stopLoss && (
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-loss" />
                  <div>
                    <p className="text-xs text-muted-foreground">Stop Loss</p>
                    <p className="font-mono font-semibold text-loss">
                      {trade.stopLoss.toFixed(5)}
                    </p>
                  </div>
                </div>
              )}
              {trade.takeProfit && (
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-profit" />
                  <div>
                    <p className="text-xs text-muted-foreground">Take Profit</p>
                    <p className="font-mono font-semibold text-profit">
                      {trade.takeProfit.toFixed(5)}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Time Information */}
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-muted-foreground" />
            <div>
              <p className="text-xs text-muted-foreground">Entry Time</p>
              <p className="text-sm font-medium">
                {new Date(trade.entryTime).toLocaleString()}
              </p>
              {trade.duration && (
                <p className="text-xs text-muted-foreground">
                  Duration: {trade.duration}
                </p>
              )}
            </div>
          </div>

          {/* Context Information */}
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium mb-2">Market Context</p>
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    Higher Timeframe:
                  </span>
                  <Badge variant="outline">{trade.htfContext}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">
                    Lower Timeframe:
                  </span>
                  <Badge variant="outline">{trade.ltfContext}</Badge>
                </div>
              </div>
            </div>

            {/* Confidence Score */}
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-sm font-medium">Confidence Score</p>
                <span className="text-sm font-semibold">
                  {(trade.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <Progress value={trade.confidence * 100} className="h-2" />
            </div>

            {/* Features Used */}
            {trade.featuresUsed && trade.featuresUsed.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-2">Evolved Features Used</p>
                <div className="flex flex-wrap gap-1">
                  {trade.featuresUsed.map((feature, idx) => (
                    <Badge key={idx} variant="secondary" className="text-xs">
                      {feature}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Generation */}
            {trade.generation && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">
                  Evolution Generation:
                </span>
                <Badge variant="outline">Gen {trade.generation}</Badge>
              </div>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          {onCloseTrade && (
            <Button
              variant="destructive"
              onClick={handleCloseTrade}
              disabled={isClosing}
            >
              {isClosing ? "Closing..." : "Close Trade"}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
