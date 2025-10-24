"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { 
  Power, 
  Pause, 
  Play, 
  AlertTriangle,
  Settings2
} from "lucide-react";
import { cn } from "@/lib/utils";

export function SystemControls() {
  const [isSystemActive, setIsSystemActive] = useState(true);
  const [autoTrading, setAutoTrading] = useState(true);
  const [manualOverride, setManualOverride] = useState(false);
  const [riskManagement, setRiskManagement] = useState(true);

  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-6">
        <Settings2 className="w-5 h-5 text-primary" />
        <h2 className="text-xl font-bold">System Controls</h2>
      </div>

      {/* System Status */}
      <div className="mb-6">
        <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border border-border">
          <div className="flex items-center gap-3">
            <div className={cn(
              "w-12 h-12 rounded-full flex items-center justify-center",
              isSystemActive ? "bg-profit/20" : "bg-muted"
            )}>
              <Power className={cn(
                "w-6 h-6",
                isSystemActive ? "text-profit" : "text-muted-foreground"
              )} />
            </div>
            <div>
              <p className="font-bold text-lg">
                System {isSystemActive ? "Active" : "Inactive"}
              </p>
              <p className="text-sm text-muted-foreground">
                {isSystemActive ? "All systems operational" : "Trading paused"}
              </p>
            </div>
          </div>
          <Button
            size="lg"
            className={cn(
              isSystemActive 
                ? "bg-loss hover:bg-loss/90" 
                : "bg-profit hover:bg-profit/90",
              "text-white"
            )}
            onClick={() => setIsSystemActive(!isSystemActive)}
          >
            {isSystemActive ? (
              <>
                <Pause className="w-4 h-4 mr-2" />
                Stop
              </>
            ) : (
              <>
                <Play className="w-4 h-4 mr-2" />
                Start
              </>
            )}
          </Button>
        </div>
      </div>

      {/* Control Switches */}
      <div className="space-y-4">
        <div className="flex items-center justify-between p-3 bg-card border border-border rounded-lg">
          <div className="flex-1">
            <Label htmlFor="auto-trading" className="font-medium cursor-pointer">
              Auto Trading
            </Label>
            <p className="text-xs text-muted-foreground mt-1">
              Enable automated trade execution
            </p>
          </div>
          <Switch
            id="auto-trading"
            checked={autoTrading}
            onCheckedChange={setAutoTrading}
          />
        </div>

        <div className="flex items-center justify-between p-3 bg-card border border-border rounded-lg">
          <div className="flex-1">
            <Label htmlFor="manual-override" className="font-medium cursor-pointer">
              Manual Override
            </Label>
            <p className="text-xs text-muted-foreground mt-1">
              Allow manual trade intervention
            </p>
          </div>
          <Switch
            id="manual-override"
            checked={manualOverride}
            onCheckedChange={setManualOverride}
          />
        </div>

        <div className="flex items-center justify-between p-3 bg-card border border-border rounded-lg">
          <div className="flex-1">
            <Label htmlFor="risk-management" className="font-medium cursor-pointer">
              Risk Management
            </Label>
            <p className="text-xs text-muted-foreground mt-1">
              Enable automatic risk controls
            </p>
          </div>
          <Switch
            id="risk-management"
            checked={riskManagement}
            onCheckedChange={setRiskManagement}
          />
        </div>
      </div>

      {/* Warning */}
      {manualOverride && (
        <div className="mt-4 flex items-start gap-2 p-3 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <AlertTriangle className="w-5 h-5 text-yellow-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-yellow-500">Manual Override Active</p>
            <p className="text-xs text-yellow-500/80 mt-1">
              Automated safety features may be bypassed
            </p>
          </div>
        </div>
      )}
    </Card>
  );
}
