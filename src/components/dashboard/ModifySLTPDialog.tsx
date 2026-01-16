"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Shield, Target, AlertTriangle } from "lucide-react";
import { Input } from "@/components/ui/input";
import type { EvolvedTrade } from "@/types/evolution";

interface ModifySLTPDialogProps {
  trade: EvolvedTrade | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (ticket: string, stopLoss?: number, takeProfit?: number) => Promise<void>;
}

export function ModifySLTPDialog({
  trade,
  open,
  onOpenChange,
  onSave,
}: ModifySLTPDialogProps) {
  const [stopLoss, setStopLoss] = useState<string>("");
  const [takeProfit, setTakeProfit] = useState<string>("");
  const [isSaving, setIsSaving] = useState(false);
  const [validationError, setValidationError] = useState<string>("");
  const [riskRewardRatio, setRiskRewardRatio] = useState<number | null>(null);

  // Initialize form values when trade changes
  useEffect(() => {
    if (trade) {
      setStopLoss(trade.stopLoss?.toString() ?? "");
      setTakeProfit(trade.takeProfit?.toString() ?? "");
      setValidationError("");
      setRiskRewardRatio(null);
    }
  }, [trade]);

  // Calculate risk/reward ratio and potential P&L
  useEffect(() => {
    if (!trade) return;

    const sl = stopLoss ? parseFloat(stopLoss) : null;
    const tp = takeProfit ? parseFloat(takeProfit) : null;

    if (sl && tp && trade.entryPrice) {
      const isBuy = trade.side === "BUY";

      // Calculate risk and reward
      const risk = isBuy
        ? Math.abs(trade.entryPrice - sl)
        : Math.abs(sl - trade.entryPrice);
      const reward = isBuy
        ? Math.abs(tp - trade.entryPrice)
        : Math.abs(trade.entryPrice - tp);

      if (risk > 0 && reward > 0) {
        setRiskRewardRatio(reward / risk);
      } else {
        setRiskRewardRatio(null);
      }
    } else {
      setRiskRewardRatio(null);
    }
  }, [stopLoss, takeProfit, trade]);

  // Validate inputs
  const validateInputs = (): boolean => {
    if (!trade) return false;

    const sl = stopLoss ? parseFloat(stopLoss) : null;
    const tp = takeProfit ? parseFloat(takeProfit) : null;

    // Check if at least one value is provided
    if (!sl && !tp) {
      setValidationError("Please enter at least Stop Loss or Take Profit");
      return false;
    }

    // Validate numeric values
    if ((sl && isNaN(sl)) || (tp && isNaN(tp))) {
      setValidationError("Please enter valid numeric values");
      return false;
    }

    // Validate against current price based on trade side
    const currentPrice = trade.currentPrice;

    if (trade.side === "BUY") {
      if (sl && sl >= currentPrice) {
        setValidationError("Stop Loss must be below current price for BUY orders");
        return false;
      }
      if (tp && tp <= currentPrice) {
        setValidationError("Take Profit must be above current price for BUY orders");
        return false;
      }
      if (sl && tp && sl >= tp) {
        setValidationError("Stop Loss must be below Take Profit for BUY orders");
        return false;
      }
    } else {
      // SELL order
      if (sl && sl <= currentPrice) {
        setValidationError("Stop Loss must be above current price for SELL orders");
        return false;
      }
      if (tp && tp >= currentPrice) {
        setValidationError("Take Profit must be below current price for SELL orders");
        return false;
      }
      if (sl && tp && sl <= tp) {
        setValidationError("Stop Loss must be above Take Profit for SELL orders");
        return false;
      }
    }

    setValidationError("");
    return true;
  };

  const handleSave = async () => {
    if (!trade || !validateInputs()) return;

    setIsSaving(true);
    try {
      const sl = stopLoss ? parseFloat(stopLoss) : undefined;
      const tp = takeProfit ? parseFloat(takeProfit) : undefined;

      await onSave(trade.ticket, sl, tp);
      onOpenChange(false);
    } catch (error) {
      console.error("Failed to modify SL/TP:", error);
      setValidationError("Failed to save changes. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  // Calculate potential P&L at new levels
  const calculatePotentialPnL = (price: number): number => {
    if (!trade) return 0;

    const isBuy = trade.side === "BUY";
    const priceDiff = isBuy ? price - trade.entryPrice : trade.entryPrice - price;
    const pipValue = trade.symbol.includes("JPY") ? 0.01 : 0.0001;
    const pips = priceDiff / pipValue;
    const pnlPerPip = 10; // Standard lot multiplier

    return pips * pnlPerPip * trade.lots;
  };

  if (!trade) return null;

  const sl = stopLoss ? parseFloat(stopLoss) : null;
  const tp = takeProfit ? parseFloat(takeProfit) : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Modify Stop Loss & Take Profit</DialogTitle>
          <DialogDescription>
            Ticket #{trade.ticket} · {trade.symbol} · {trade.side}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-6">
          {/* Current Price Reference */}
          <div className="p-3 bg-muted/50 rounded-lg">
            <p className="text-sm text-muted-foreground mb-1">Current Price</p>
            <p className="text-lg font-mono font-semibold">
              {trade.currentPrice.toFixed(5)}
            </p>
          </div>

          {/* Current Levels */}
          {(trade.stopLoss || trade.takeProfit) && (
            <div className="grid grid-cols-2 gap-4">
              {trade.stopLoss && (
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-loss" />
                  <div>
                    <p className="text-xs text-muted-foreground">Current SL</p>
                    <p className="font-mono text-sm text-loss">
                      {trade.stopLoss.toFixed(5)}
                    </p>
                  </div>
                </div>
              )}
              {trade.takeProfit && (
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-profit" />
                  <div>
                    <p className="text-xs text-muted-foreground">Current TP</p>
                    <p className="font-mono text-sm text-profit">
                      {trade.takeProfit.toFixed(5)}
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Input Fields */}
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="stopLoss">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-loss" />
                  Stop Loss
                </div>
              </Label>
              <Input
                id="stopLoss"
                type="number"
                step="0.00001"
                placeholder="Optional"
                value={stopLoss}
                onChange={(e) => setStopLoss(e.target.value)}
                className="font-mono"
              />
              {sl && (
                <p className="text-xs text-muted-foreground">
                  Potential Loss: ${Math.abs(calculatePotentialPnL(sl)).toFixed(2)}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="takeProfit">
                <div className="flex items-center gap-2">
                  <Target className="w-4 h-4 text-profit" />
                  Take Profit
                </div>
              </Label>
              <Input
                id="takeProfit"
                type="number"
                step="0.00001"
                placeholder="Optional"
                value={takeProfit}
                onChange={(e) => setTakeProfit(e.target.value)}
                className="font-mono"
              />
              {tp && (
                <p className="text-xs text-muted-foreground">
                  Potential Profit: ${calculatePotentialPnL(tp).toFixed(2)}
                </p>
              )}
            </div>
          </div>

          {/* Risk/Reward Ratio */}
          {riskRewardRatio !== null && (
            <div className="p-3 bg-muted/50 rounded-lg">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">Risk/Reward Ratio</span>
                <span className={`text-sm font-semibold ${
                  riskRewardRatio >= 2 ? "text-profit" : riskRewardRatio >= 1 ? "" : "text-loss"
                }`}>
                  1:{riskRewardRatio.toFixed(2)}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {riskRewardRatio >= 2
                  ? "Excellent risk/reward ratio"
                  : riskRewardRatio >= 1
                  ? "Acceptable risk/reward ratio"
                  : "Risk exceeds potential reward"}
              </p>
            </div>
          )}

          {/* Validation Error */}
          {validationError && (
            <div className="flex items-start gap-2 p-3 bg-destructive/10 border border-destructive/20 rounded-lg">
              <AlertTriangle className="w-4 h-4 text-destructive mt-0.5 flex-shrink-0" />
              <p className="text-sm text-destructive">{validationError}</p>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isSaving}
          >
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? "Saving..." : "Save Changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
