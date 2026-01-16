"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Shield, Save, RotateCcw, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { post, put } from "@/lib/api/client";
import { RoleGuard } from "@/components/auth/RoleGuard";

interface RiskParametersResponse {
  maxPositionSize: number;
  maxDailyLoss: number;
  maxConcurrentTrades: number;
  riskPerTrade: number;
  allowAggressiveEvolution: boolean;
  autoApproveSignals: boolean;
}

const DEFAULT_PARAMS = {
  maxPositionSize: [0.1],
  maxDailyLoss: [1000],
  maxConcurrentTrades: [3],
  riskPerTrade: [2],
  allowAggressiveEvolution: false,
  autoApproveSignals: false,
};

export function RiskParameterControls() {
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [riskParams, setRiskParams] = useState(DEFAULT_PARAMS);
  const [hasChanges, setHasChanges] = useState(false);
  const [showWarning, setShowWarning] = useState(false);

  // Fetch current parameters on mount
  useEffect(() => {
    const fetchParameters = async () => {
      setIsLoading(true);
      try {
        const response = await post<RiskParametersResponse>("/config/risk");
        if (response.data) {
          setRiskParams({
            maxPositionSize: [response.data.maxPositionSize],
            maxDailyLoss: [response.data.maxDailyLoss],
            maxConcurrentTrades: [response.data.maxConcurrentTrades],
            riskPerTrade: [response.data.riskPerTrade],
            allowAggressiveEvolution: response.data.allowAggressiveEvolution,
            autoApproveSignals: response.data.autoApproveSignals,
          });
        }
      } catch {
        // Use defaults if API fails
        toast.error("Failed to fetch risk parameters, using defaults");
      } finally {
        setIsLoading(false);
      }
    };

    fetchParameters();
  }, []);

  // Check for extreme values and show warning
  useEffect(() => {
    const isExtreme =
      riskParams.riskPerTrade[0] > 7 ||
      riskParams.maxDailyLoss[0] > 8000 ||
      riskParams.maxConcurrentTrades[0] > 7 ||
      riskParams.maxPositionSize[0] > 0.7;
    setShowWarning(isExtreme);
  }, [riskParams]);

  // Update parameter value
  const updateParam = <K extends keyof typeof riskParams>(
    key: K,
    value: (typeof riskParams)[K]
  ) => {
    setRiskParams((prev) => {
      const updated = { ...prev, [key]: value };
      setHasChanges(true);
      return updated;
    });
  };

  // Handle save
  const handleSave = async () => {
    setIsSaving(true);
    try {
      const response = await put("/config/risk", {
        maxPositionSize: riskParams.maxPositionSize[0],
        maxDailyLoss: riskParams.maxDailyLoss[0],
        maxConcurrentTrades: riskParams.maxConcurrentTrades[0],
        riskPerTrade: riskParams.riskPerTrade[0],
        allowAggressiveEvolution: riskParams.allowAggressiveEvolution,
        autoApproveSignals: riskParams.autoApproveSignals,
      });

      if (response.ok) {
        toast.success("Risk parameters saved successfully");
        setHasChanges(false);
      } else {
        toast.error("Failed to save risk parameters");
      }
    } catch {
      toast.error("Failed to save risk parameters");
    } finally {
      setIsSaving(false);
    }
  };

  // Handle reset to defaults
  const handleReset = () => {
    setRiskParams(DEFAULT_PARAMS);
    setHasChanges(true);
    toast.info("Parameters reset to defaults");
  };

  return (
    <RoleGuard allowedRoles={["admin"]}>
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary" />
            <h2 className="text-xl font-bold">Risk Parameter Controls</h2>
          </div>
          {hasChanges && (
            <span className="text-sm text-muted-foreground">Unsaved changes</span>
          )}
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-muted-foreground">Loading parameters...</div>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Warning Banner */}
            {showWarning && (
              <div className="flex items-start gap-3 p-4 bg-amber-500/10 border border-amber-500/20 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="font-medium text-amber-900">High Risk Settings Detected</p>
                  <p className="text-sm text-amber-800">
                    Some parameters are set to extreme values. This may result in significant losses.
                  </p>
                </div>
              </div>
            )}

            {/* Max Position Size */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="maxPositionSize">Max Position Size (lots)</Label>
                <span className="text-sm font-medium text-primary">
                  {riskParams.maxPositionSize[0].toFixed(2)}
                </span>
              </div>
              <Slider
                id="maxPositionSize"
                value={riskParams.maxPositionSize}
                onValueChange={(value) => updateParam("maxPositionSize", value)}
                min={0.01}
                max={1.0}
                step={0.01}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>0.01 lots</span>
                <span>1.0 lots</span>
              </div>
            </div>

            {/* Max Daily Loss Limit */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="maxDailyLoss">Max Daily Loss Limit</Label>
                <span className="text-sm font-medium text-primary">
                  ${riskParams.maxDailyLoss[0].toLocaleString()}
                </span>
              </div>
              <Slider
                id="maxDailyLoss"
                value={riskParams.maxDailyLoss}
                onValueChange={(value) => updateParam("maxDailyLoss", value)}
                min={100}
                max={10000}
                step={100}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>$100</span>
                <span>$10,000</span>
              </div>
            </div>

            {/* Max Concurrent Trades */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="maxConcurrentTrades">Max Concurrent Trades</Label>
                <span className="text-sm font-medium text-primary">
                  {riskParams.maxConcurrentTrades[0]}
                </span>
              </div>
              <Slider
                id="maxConcurrentTrades"
                value={riskParams.maxConcurrentTrades}
                onValueChange={(value) => updateParam("maxConcurrentTrades", value)}
                min={1}
                max={10}
                step={1}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>1 trade</span>
                <span>10 trades</span>
              </div>
            </div>

            {/* Risk Per Trade */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label htmlFor="riskPerTrade">Risk Per Trade</Label>
                <span className="text-sm font-medium text-primary">
                  {riskParams.riskPerTrade[0]}%
                </span>
              </div>
              <Slider
                id="riskPerTrade"
                value={riskParams.riskPerTrade}
                onValueChange={(value) => updateParam("riskPerTrade", value)}
                min={1}
                max={10}
                step={0.5}
                className="w-full"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>1%</span>
                <span>10%</span>
              </div>
            </div>

            {/* Boolean Switches */}
            <div className="space-y-4 pt-4 border-t border-border">
              {/* Allow Aggressive Evolution */}
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="aggressiveEvolution">Allow Aggressive Evolution</Label>
                  <p className="text-xs text-muted-foreground">
                    Enable higher-risk evolution strategies
                  </p>
                </div>
                <Switch
                  id="aggressiveEvolution"
                  checked={riskParams.allowAggressiveEvolution}
                  onCheckedChange={(checked) =>
                    updateParam("allowAggressiveEvolution", checked)
                  }
                />
              </div>

              {/* Auto-approve Signals */}
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="autoApprove">Auto-approve Signals</Label>
                  <p className="text-xs text-muted-foreground">
                    Automatically approve trading signals
                  </p>
                </div>
                <Switch
                  id="autoApprove"
                  checked={riskParams.autoApproveSignals}
                  onCheckedChange={(checked) =>
                    updateParam("autoApproveSignals", checked)
                  }
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-3 pt-4">
              <Button
                onClick={handleSave}
                disabled={isSaving || !hasChanges}
                className="flex-1"
              >
                <Save className="w-4 h-4 mr-2" />
                {isSaving ? "Saving..." : "Save Parameters"}
              </Button>
              <Button
                onClick={handleReset}
                variant="outline"
                disabled={isLoading}
              >
                <RotateCcw className="w-4 h-4 mr-2" />
                Reset
              </Button>
            </div>
          </div>
        )}
      </Card>
    </RoleGuard>
  );
}
