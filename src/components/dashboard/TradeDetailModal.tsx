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
import {
  TrendingUp,
  TrendingDown,
  Clock,
  Target,
  Shield,
  Settings,
  BarChart3,
  Info,
} from "lucide-react";
import type { EvolvedTrade, ClosedTrade } from "@/types/evolution";

type TradeData = EvolvedTrade | ClosedTrade;

interface TradeDetailModalProps {
  trade: TradeData | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCloseTrade?: (ticket: string) => Promise<void>;
  onModifySLTP?: (ticket: string) => void;
}

export function TradeDetailModal({
  trade,
  open,
  onOpenChange,
  onCloseTrade,
  onModifySLTP,
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

  const handleModifySLTP = () => {
    onOpenChange(false);
    onModifySLTP?.(trade.ticket);
  };

  // Helper function to explain HTF context
  const explainHTFContext = (context: string): string => {
    const parts = context.split(' ');
    const trend = parts[0];
    const timeframe = parts[1] || '';
    const rValue = parts[2] || '';

    const trendMeanings: Record<string, string> = {
      'BULLISH': 'Price is trending upward',
      'BEARISH': 'Price is trending downward',
      'RANGING': 'Price is moving sideways',
      'STRONG_BUY': 'Strong upward momentum',
      'STRONG_SELL': 'Strong downward momentum',
    };

    let explanation = trendMeanings[trend] || trend;

    if (timeframe) {
      explanation += ` on ${timeframe.replace('_', ' ')} timeframe`;
    }

    if (rValue.startsWith('R_')) {
      explanation += `. R-value: ${rValue} (risk level)`;
    }

    return explanation;
  };

  // Helper function to explain LTF context
  const explainLTFContext = (context: string): string => {
    const parts = context.split(' ');
    const signal = parts[0];
    const timeframe = parts[1] || '';

    const signalMeanings: Record<string, string> = {
      'STRONG_BUY': 'Strong buy signal',
      'BUY': 'Buy signal',
      'SELL': 'Sell signal',
      'STRONG_SELL': 'Strong sell signal',
    };

    let explanation = signalMeanings[signal] || signal;

    if (timeframe) {
      explanation += ` from ${timeframe.replace('_', ' ')} analysis`;
    }

    return explanation;
  };

  // Check if trade is a closed trade
  const isClosedTrade = (t: TradeData): t is ClosedTrade => {
    return 'exitPrice' in t && 'exitTime' in t;
  };

  const pnlColor = trade.pnl >= 0 ? "text-profit" : "text-loss";
  const bgColor = trade.pnl >= 0 ? "bg-profit/10" : "bg-loss/10";

  // Get display price based on trade type
  const displayPrice = isClosedTrade(trade) ? trade.exitPrice : trade.currentPrice;
  const priceLabel = isClosedTrade(trade) ? "Exit Price" : "Current Price";

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
            Ticket #{trade.ticket} · {trade.symbol} · {trade.lots} lots
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
                <p className="text-sm text-muted-foreground">{priceLabel}</p>
                <p className="text-lg font-mono font-semibold">
                  {displayPrice.toFixed(5)}
                </p>
              </div>
            </div>
          </div>

          {/* Trade Information */}
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Lots</p>
              <p className="font-semibold">{trade.lots}</p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">Entry Price</p>
              <p className="font-mono font-semibold">
                {trade.entryPrice.toFixed(5)}
              </p>
            </div>
            <div>
              <p className="text-sm text-muted-foreground mb-1">{priceLabel}</p>
              <p className="font-mono font-semibold">
                {displayPrice.toFixed(5)}
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
                      {isClosedTrade(trade) && trade.stopLossHit && (
                        <span className="ml-2 text-xs">Hit!</span>
                      )}
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
                      {isClosedTrade(trade) && trade.takeProfitHit && (
                        <span className="ml-2 text-xs">Hit!</span>
                      )}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Time Information */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-muted-foreground" />
              <div>
                <p className="text-xs text-muted-foreground">Entry Time</p>
                <p className="text-sm font-medium">
                  {new Date(trade.entryTime).toLocaleString()}
                </p>
              </div>
            </div>
            {isClosedTrade(trade) && (
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Exit Time</p>
                  <p className="text-sm font-medium">
                    {new Date(trade.exitTime).toLocaleString()}
                  </p>
                </div>
              </div>
            )}
            {trade.duration && (
              <p className="text-xs text-muted-foreground ml-6">
                Duration: {trade.duration}
              </p>
            )}
          </div>

          {/* Market Context with Explanations */}
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium mb-2">Market Context</p>
              <div className="space-y-3">
                <div className="p-3 bg-muted/50 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-muted-foreground">
                      Higher Timeframe:
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {trade.htfContext}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground flex items-start gap-1">
                    <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
                    {explainHTFContext(trade.htfContext)}
                  </p>
                </div>
                <div className="p-3 bg-muted/50 rounded-lg">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-muted-foreground">
                      Lower Timeframe:
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {trade.ltfContext}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground flex items-start gap-1">
                    <Info className="w-3 h-3 mt-0.5 flex-shrink-0" />
                    {explainLTFContext(trade.ltfContext)}
                  </p>
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
              {trade.confidenceBreakdown && (
                <div className="mt-3 grid grid-cols-3 gap-2">
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Technical</p>
                    <div className="flex items-center gap-1">
                      <Progress
                        value={trade.confidenceBreakdown.technical * 100}
                        className="h-1 flex-1"
                      />
                      <span className="text-xs font-medium">
                        {(trade.confidenceBreakdown.technical * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Fundamental</p>
                    <div className="flex items-center gap-1">
                      <Progress
                        value={trade.confidenceBreakdown.fundamental * 100}
                        className="h-1 flex-1"
                      />
                      <span className="text-xs font-medium">
                        {(trade.confidenceBreakdown.fundamental * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground mb-1">Sentiment</p>
                    <div className="flex items-center gap-1">
                      <Progress
                        value={trade.confidenceBreakdown.sentiment * 100}
                        className="h-1 flex-1"
                      />
                      <span className="text-xs font-medium">
                        {(trade.confidenceBreakdown.sentiment * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Features Used with Success Rates */}
            {trade.featuresUsed && trade.featuresUsed.length > 0 && (
              <div>
                <p className="text-sm font-medium mb-2">Evolved Features Used</p>
                <div className="space-y-2">
                  {trade.featuresUsed.map((feature, idx) => (
                    <div
                      key={idx}
                      className="flex items-center justify-between p-2 bg-muted/30 rounded"
                    >
                      <Badge variant="secondary" className="text-xs">
                        {feature}
                      </Badge>
                      {trade.featureSuccessRates?.[feature] !== undefined && (
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">
                            Success Rate:
                          </span>
                          <Badge
                            variant="outline"
                            className={
                              trade.featureSuccessRates[feature] >= 0.6
                                ? "text-profit"
                                : trade.featureSuccessRates[feature] >= 0.4
                                ? ""
                                : "text-loss"
                            }
                          >
                            {(trade.featureSuccessRates[feature] * 100).toFixed(0)}%
                          </Badge>
                        </div>
                      )}
                    </div>
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

          {/* Trade Chart Placeholder */}
          <div className="p-6 border border-dashed border-border rounded-lg bg-muted/20 flex flex-col items-center justify-center">
            <BarChart3 className="w-12 h-12 text-muted-foreground mb-3" />
            <p className="text-sm text-muted-foreground text-center">
              Trade Chart
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Chart visualization will be available when backend API is connected
            </p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          {onModifySLTP && !isClosedTrade(trade) && (
            <Button variant="outline" onClick={handleModifySLTP}>
              <Settings className="w-4 h-4 mr-2" />
              Modify SL/TP
            </Button>
          )}
          {onCloseTrade && !isClosedTrade(trade) && (
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
