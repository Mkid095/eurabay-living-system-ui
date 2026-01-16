"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  AlertTriangle,
  Shield,
  Pause,
  Play,
  XCircle,
  Ban,
  CheckCircle2
} from "lucide-react";
import { cn } from "@/lib/utils";
import { post } from "@/lib/api/client";
import { toast } from "sonner";
import { RoleGuard } from "@/components/auth/RoleGuard";

type OverrideStatus = "enabled" | "disabled";

interface OverrideStateResponse {
  status: OverrideStatus;
  enabledAt?: string;
  evolutionPaused?: boolean;
}

export function ManualOverride() {
  const [overrideStatus, setOverrideStatus] = useState<OverrideStatus>("disabled");
  const [evolutionPaused, setEvolutionPaused] = useState(false);
  const [isTogglingOverride, setIsTogglingOverride] = useState(false);
  const [isPausingEvolution, setIsPausingEvolution] = useState(false);
  const [isForcingApproval, setIsForcingApproval] = useState(false);
  const [isClosingPositions, setIsClosingPositions] = useState(false);
  const [isCancellingSignals, setIsCancellingSignals] = useState(false);
  const [enabledAt, setEnabledAt] = useState<string>("");

  // Dialog states
  const [showPauseDialog, setShowPauseDialog] = useState(false);
  const [showClosePositionsDialog, setShowClosePositionsDialog] = useState(false);
  const [showCancelSignalsDialog, setShowCancelSignalsDialog] = useState(false);

  // Fetch override status on mount
  useEffect(() => {
    const fetchOverrideStatus = async () => {
      try {
        const response = await post<OverrideStateResponse>("/system/override/status");
        if (response.data) {
          setOverrideStatus(response.data.status);
          setEvolutionPaused(response.data.evolutionPaused || false);
          setEnabledAt(response.data.enabledAt || "");
        }
      } catch {
        // Default to disabled if API fails
        setOverrideStatus("disabled");
      }
    };

    fetchOverrideStatus();
  }, []);

  // Format date string
  const formatDate = (dateString: string): string => {
    if (!dateString) return "Never";
    return new Date(dateString).toLocaleString();
  };

  // Handle toggle override
  const handleToggleOverride = async (checked: boolean) => {
    setIsTogglingOverride(true);

    try {
      const response = await post<{ status: OverrideStatus; enabledAt?: string }>("/system/override", {
        enabled: checked,
      });

      if (response.data) {
        setOverrideStatus(response.data.status);
        if (response.data.enabledAt) {
          setEnabledAt(response.data.enabledAt);
        }
        toast.success(
          checked
            ? "Manual override enabled"
            : "Manual override disabled"
        );
      }
    } catch {
      toast.error("Failed to toggle manual override");
    } finally {
      setIsTogglingOverride(false);
    }
  };

  // Handle pause evolution
  const handlePauseEvolution = async () => {
    setShowPauseDialog(false);
    setIsPausingEvolution(true);

    try {
      const response = await post<{ success: boolean }>("/system/pause-evolution");

      if (response.data?.success) {
        setEvolutionPaused(true);
        toast.success("Evolution paused successfully");
      } else {
        toast.error("Failed to pause evolution");
      }
    } catch {
      toast.error("Failed to pause evolution");
    } finally {
      setIsPausingEvolution(false);
    }
  };

  // Handle force trade approval
  const handleForceApproval = async () => {
    setIsForcingApproval(true);

    try {
      const response = await post<{ success: boolean }>("/system/force-approval");

      if (response.data?.success) {
        toast.success("Trade approval forced successfully");
      } else {
        toast.error("Failed to force trade approval");
      }
    } catch {
      toast.error("Failed to force trade approval");
    } finally {
      setIsForcingApproval(false);
    }
  };

  // Handle close all positions
  const handleCloseAllPositions = async () => {
    setShowClosePositionsDialog(false);
    setIsClosingPositions(true);

    try {
      const response = await post<{ success: boolean; closedCount?: number }>("/system/close-all-positions");

      if (response.data?.success) {
        const count = response.data.closedCount || 0;
        toast.success(`Closed ${count} position${count !== 1 ? "s" : ""} successfully`);
      } else {
        toast.error("Failed to close all positions");
      }
    } catch {
      toast.error("Failed to close all positions");
    } finally {
      setIsClosingPositions(false);
    }
  };

  // Handle cancel all pending signals
  const handleCancelAllSignals = async () => {
    setShowCancelSignalsDialog(false);
    setIsCancellingSignals(true);

    try {
      const response = await post<{ success: boolean; cancelledCount?: number }>("/system/cancel-pending-signals");

      if (response.data?.success) {
        const count = response.data.cancelledCount || 0;
        toast.success(`Cancelled ${count} signal${count !== 1 ? "s" : ""} successfully`);
      } else {
        toast.error("Failed to cancel pending signals");
      }
    } catch {
      toast.error("Failed to cancel pending signals");
    } finally {
      setIsCancellingSignals(false);
    }
  };

  const isOverrideEnabled = overrideStatus === "enabled";

  return (
    <RoleGuard allowedRoles={["admin"]}>
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary" />
            <h2 className="text-xl font-bold">Manual Override</h2>
          </div>
          <Badge
            variant={isOverrideEnabled ? "destructive" : "secondary"}
            className="text-sm px-3 py-1"
          >
            {isOverrideEnabled ? "Enabled" : "Disabled"}
          </Badge>
        </div>

        <div className="space-y-6">
          {/* Warning Banner when override is enabled */}
          {isOverrideEnabled && (
            <Alert variant="destructive">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>Manual Override Active</AlertTitle>
              <AlertDescription>
                Manual override is currently enabled. The system will not execute automated trades until disabled.
                Enabled since {formatDate(enabledAt)}.
              </AlertDescription>
            </Alert>
          )}

          {/* Override Toggle */}
          <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border border-border">
            <div className="space-y-0.5">
              <p className="font-medium">Enable Manual Override</p>
              <p className="text-sm text-muted-foreground">
                Take manual control of the trading system
              </p>
            </div>
            <Switch
              checked={isOverrideEnabled}
              onCheckedChange={handleToggleOverride}
              disabled={isTogglingOverride}
            />
          </div>

          {/* Action Buttons - only enabled when override is active */}
          <div className={cn(
            "space-y-3 transition-opacity",
            !isOverrideEnabled && "opacity-50 pointer-events-none"
          )}>
            <p className="text-sm font-medium text-muted-foreground">
              Override Actions (requires override enabled)
            </p>

            {/* Pause Evolution */}
            <div className="flex items-center justify-between p-4 bg-card border border-border rounded-lg">
              <div className="flex items-center gap-3">
                <div className={cn(
                  "w-10 h-10 rounded-lg flex items-center justify-center",
                  evolutionPaused ? "bg-amber-500/20" : "bg-blue-500/20"
                )}>
                  {evolutionPaused ? (
                    <Pause className="w-5 h-5 text-amber-600" />
                  ) : (
                    <Play className="w-5 h-5 text-blue-600" />
                  )}
                </div>
                <div>
                  <p className="font-medium">
                    {evolutionPaused ? "Resume Evolution" : "Pause Evolution"}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {evolutionPaused
                      ? "Resume automatic strategy evolution"
                      : "Temporarily pause strategy evolution"}
                  </p>
                </div>
              </div>
              <Button
                variant={evolutionPaused ? "default" : "outline"}
                onClick={() => setShowPauseDialog(true)}
                disabled={isPausingEvolution}
              >
                {isPausingEvolution
                  ? "Processing..."
                  : evolutionPaused
                    ? "Resume"
                    : "Pause"}
              </Button>
            </div>

            {/* Force Trade Approval */}
            <div className="flex items-center justify-between p-4 bg-card border border-border rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-green-500/20 flex items-center justify-center">
                  <CheckCircle2 className="w-5 h-5 text-green-600" />
                </div>
                <div>
                  <p className="font-medium">Force Trade Approval</p>
                  <p className="text-sm text-muted-foreground">
                    Manually approve pending trade signals
                  </p>
                </div>
              </div>
              <Button
                onClick={handleForceApproval}
                disabled={isForcingApproval}
              >
                {isForcingApproval ? "Processing..." : "Approve"}
              </Button>
            </div>

            {/* Cancel All Pending Signals */}
            <div className="flex items-center justify-between p-4 bg-card border border-border rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-amber-500/20 flex items-center justify-center">
                  <Ban className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <p className="font-medium">Cancel All Pending Signals</p>
                  <p className="text-sm text-muted-foreground">
                    Cancel all signals awaiting approval
                  </p>
                </div>
              </div>
              <Button
                variant="outline"
                onClick={() => setShowCancelSignalsDialog(true)}
                disabled={isCancellingSignals}
              >
                {isCancellingSignals ? "Cancelling..." : "Cancel All"}
              </Button>
            </div>

            {/* Close All Positions - DANGER */}
            <div className="flex items-center justify-between p-4 bg-red-500/5 border border-red-500/20 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-red-500/20 flex items-center justify-center">
                  <XCircle className="w-5 h-5 text-red-600" />
                </div>
                <div>
                  <p className="font-medium text-red-900">Close All Positions</p>
                  <p className="text-sm text-red-700">
                    Immediately close all open positions
                  </p>
                </div>
              </div>
              <Button
                variant="destructive"
                onClick={() => setShowClosePositionsDialog(true)}
                disabled={isClosingPositions}
              >
                {isClosingPositions ? "Closing..." : "Close All"}
              </Button>
            </div>
          </div>

          {/* Disabled State Message */}
          {!isOverrideEnabled && (
            <div className="flex items-center justify-center p-8 bg-muted/30 rounded-lg border border-dashed border-border">
              <div className="text-center">
                <Shield className="w-12 h-12 text-muted-foreground mx-auto mb-3" />
                <p className="text-sm text-muted-foreground">
                  Enable manual override to access control actions
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Pause Evolution Confirmation Dialog */}
        <AlertDialog open={showPauseDialog} onOpenChange={setShowPauseDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>
                {evolutionPaused ? "Resume Evolution" : "Pause Evolution"}
              </AlertDialogTitle>
              <AlertDialogDescription>
                {evolutionPaused
                  ? "Are you sure you want to resume automatic strategy evolution? The system will continue optimizing trading strategies."
                  : "Are you sure you want to pause evolution? The system will stop optimizing trading strategies until resumed."}
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handlePauseEvolution}
                className={evolutionPaused ? "bg-primary" : "bg-amber-600 text-white hover:bg-amber-700"}
              >
                {evolutionPaused ? "Resume" : "Pause"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        {/* Close All Positions Confirmation Dialog */}
        <AlertDialog open={showClosePositionsDialog} onOpenChange={setShowClosePositionsDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Close All Positions</AlertDialogTitle>
              <AlertDialogDescription>
                This is a dangerous action that will immediately close all open positions. This may result in significant losses depending on current market conditions. Are you absolutely sure?
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleCloseAllPositions}
                className="bg-destructive text-white hover:bg-destructive/90"
              >
                Close All Positions
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>

        {/* Cancel All Signals Confirmation Dialog */}
        <AlertDialog open={showCancelSignalsDialog} onOpenChange={setShowCancelSignalsDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Cancel All Pending Signals</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to cancel all pending signals? Any signals awaiting approval will be discarded.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction
                onClick={handleCancelAllSignals}
                className="bg-amber-600 text-white hover:bg-amber-700"
              >
                Cancel All Signals
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </Card>
    </RoleGuard>
  );
}
