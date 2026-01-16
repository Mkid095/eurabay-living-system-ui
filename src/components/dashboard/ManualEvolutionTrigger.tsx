"use client";

import { useState, useEffect, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { Spinner } from "@/components/ui/spinner";
import { AdminGuard } from "@/components/auth/RoleGuard";
import { toast } from "sonner";
import { evolutionApi } from "@/lib/api";
import {
  Play,
  Zap,
  RotateCcw,
  Clock,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";

// Cooldown duration in milliseconds (60 seconds)
const COOLDOWN_DURATION = 60 * 1000;

// Local storage key for last evolution timestamp
const LAST_EVOLUTION_KEY = "last_evolution_timestamp";

type TriggerType = "normal" | "aggressive" | "reset";

/**
 * ManualEvolutionTrigger component
 *
 * Admin-only controls for manually triggering evolution cycles.
 * Provides three actions: Trigger Evolution, Force Aggressive Evolution, and Reset to Generation 1.
 */
export const ManualEvolutionTrigger = () => {
  const [lastEvolutionTime, setLastEvolutionTime] = useState<number | null>(null);
  const [isEvolving, setIsEvolving] = useState(false);
  const [evolutionProgress, setEvolutionProgress] = useState(0);
  const [triggerType, setTriggerType] = useState<TriggerType | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [pendingTriggerType, setPendingTriggerType] = useState<TriggerType | null>(null);

  /**
   * Load last evolution time from localStorage on mount
   */
  useEffect(() => {
    const savedTime = localStorage.getItem(LAST_EVOLUTION_KEY);
    if (savedTime) {
      setLastEvolutionTime(Number.parseInt(savedTime, 10));
    }
  }, []);

  /**
   * Calculate remaining cooldown time in seconds
   */
  const cooldownRemaining = lastEvolutionTime
    ? Math.max(0, COOLDOWN_DURATION - (Date.now() - lastEvolutionTime))
    : 0;

  const isOnCooldown = cooldownRemaining > 0;

  /**
   * Format cooldown time as MM:SS
   */
  const formatCooldown = (ms: number): string => {
    const seconds = Math.ceil(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  /**
   * Format timestamp as relative time (e.g., "2 minutes ago")
   */
  const formatLastEvolution = (timestamp: number): string => {
    const seconds = Math.floor((Date.now() - timestamp) / 1000);

    if (seconds < 60) return "Just now";
    if (seconds < 3600) {
      const minutes = Math.floor(seconds / 60);
      return `${minutes} minute${minutes > 1 ? "s" : ""} ago`;
    }
    const hours = Math.floor(seconds / 3600);
    return `${hours} hour${hours > 1 ? "s" : ""} ago`;
  };

  /**
   * Simulate evolution progress (placeholder for real progress from WebSocket)
   */
  const simulateProgress = useCallback(() => {
    setEvolutionProgress(0);
    const interval = setInterval(() => {
      setEvolutionProgress((prev) => {
        if (prev >= 95) {
          clearInterval(interval);
          return 95;
        }
        return prev + Math.random() * 15;
      });
    }, 500);
    return interval;
  }, []);

  /**
   * Handle evolution trigger with confirmation
   */
  const handleTrigger = useCallback(
    async (type: TriggerType) => {
      setPendingTriggerType(type);
      setIsDialogOpen(true);
    },
    []
  );

  /**
   * Confirm and execute evolution trigger
   */
  const confirmTrigger = useCallback(async () => {
    if (!pendingTriggerType) return;

    setIsEvolving(true);
    setTriggerType(pendingTriggerType);
    setIsDialogOpen(false);
    const progressInterval = simulateProgress();

    try {
      switch (pendingTriggerType) {
        case "normal":
          await evolutionApi.forceEvolution();
          toast.success("Evolution cycle triggered", {
            description: "A new evolution cycle has been initiated",
            icon: <CheckCircle2 className="w-4 h-4 text-success" />,
          });
          break;

        case "aggressive":
          await evolutionApi.forceAggressiveEvolution();
          toast.success("Aggressive evolution triggered", {
            description: "An aggressive evolution cycle has been initiated",
            icon: <Zap className="w-4 h-4 text-warning" />,
          });
          break;

        case "reset":
          await evolutionApi.resetToGeneration(1);
          toast.success("System reset to generation 1", {
            description: "The evolution system has been reset to the initial generation",
            icon: <RotateCcw className="w-4 h-4 text-destructive" />,
          });
          break;
      }

      // Update last evolution time
      const now = Date.now();
      setLastEvolutionTime(now);
      localStorage.setItem(LAST_EVOLUTION_KEY, now.toString());
    } catch (error) {
      toast.error("Failed to trigger evolution", {
        description:
          error instanceof Error ? error.message : "An unknown error occurred",
      });
    } finally {
      clearInterval(progressInterval);
      setEvolutionProgress(100);
      setTimeout(() => {
        setIsEvolving(false);
        setEvolutionProgress(0);
        setTriggerType(null);
      }, 1000);
    }
  }, [pendingTriggerType, simulateProgress]);

  /**
   * Get dialog content based on trigger type
   */
  const getDialogContent = useCallback((type: TriggerType) => {
    switch (type) {
      case "normal":
        return {
          title: "Trigger Evolution Cycle",
          description:
            "This will initiate a standard evolution cycle. The system will create a new generation based on current parameters and fitness scores.",
          confirmText: "Trigger Evolution",
          variant: "default" as const,
        };

      case "aggressive":
        return {
          title: "Force Aggressive Evolution",
          description:
            "This will trigger an aggressive evolution cycle with increased mutation rates and more radical changes. This action cannot be undone and may significantly alter the system's behavior.",
          confirmText: "Force Aggressive",
          variant: "warning" as const,
        };

      case "reset":
        return {
          title: "Reset to Generation 1",
          description:
            "This will reset the entire evolution system to generation 1. All evolved features, learned patterns, and progress will be permanently lost. This is a destructive action that cannot be undone.",
          confirmText: "Reset System",
          variant: "destructive" as const,
        };
    }
  }, []);

  return (
    <AdminGuard>
      <Card className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold">Manual Evolution Control</h3>
            <p className="text-sm text-muted-foreground">
              Manually trigger evolution cycles
            </p>
          </div>
          <Play className="w-5 h-5 text-primary" />
        </div>

        {/* Last Evolution Info */}
        <div className="mb-6 p-4 rounded-lg bg-muted/30">
          <div className="flex items-center gap-3">
            <Clock className="w-5 h-5 text-muted-foreground" />
            <div className="flex-1">
              <p className="text-sm font-medium">Last Evolution</p>
              <p className="text-xs text-muted-foreground">
                {lastEvolutionTime
                  ? formatLastEvolution(lastEvolutionTime)
                  : "Never"}
              </p>
            </div>
            {isOnCooldown && (
              <div className="text-right">
                <p className="text-sm font-medium text-warning">Cooldown</p>
                <p className="text-xs text-muted-foreground">
                  {formatCooldown(cooldownRemaining)}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Progress Indicator */}
        {isEvolving && (
          <div className="mb-6 p-4 rounded-lg bg-primary/5 border border-primary/20">
            <div className="flex items-center gap-3 mb-3">
              <Spinner className="w-5 h-5 text-primary" />
              <div className="flex-1">
                <p className="text-sm font-medium">
                  {triggerType === "aggressive"
                    ? "Aggressive Evolution"
                    : triggerType === "reset"
                      ? "Resetting System"
                      : "Evolution"}{" "}
                  in Progress
                </p>
                <p className="text-xs text-muted-foreground">
                  Please wait while the system processes this request
                </p>
              </div>
              <span className="text-sm font-mono font-medium">
                {Math.round(evolutionProgress)}%
              </span>
            </div>
            <Progress value={evolutionProgress} className="h-2" />
          </div>
        )}

        {/* Action Buttons */}
        <div className="space-y-3">
          {/* Trigger Evolution */}
          <Button
            onClick={() => handleTrigger("normal")}
            disabled={isEvolving || isOnCooldown}
            className="w-full"
            variant="default"
          >
            <Play className="w-4 h-4 mr-2" />
            Trigger Evolution
          </Button>

          {/* Force Aggressive Evolution */}
          <Button
            onClick={() => handleTrigger("aggressive")}
            disabled={isEvolving || isOnCooldown}
            className="w-full"
            variant="outline"
          >
            <Zap className="w-4 h-4 mr-2" />
            Force Aggressive Evolution
          </Button>

          {/* Reset to Generation 1 */}
          <Button
            onClick={() => handleTrigger("reset")}
            disabled={isEvolving || isOnCooldown}
            className="w-full"
            variant="destructive"
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset to Generation 1
          </Button>
        </div>

        {/* Cooldown Notice */}
        {isOnCooldown && !isEvolving && (
          <div className="mt-4 p-3 rounded-lg bg-warning/10 border border-warning/30 flex items-start gap-3">
            <Clock className="w-5 h-5 text-warning shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-warning">
                Cooldown Active
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Please wait {formatCooldown(cooldownRemaining)} before
                triggering another evolution cycle to maintain system stability.
              </p>
            </div>
          </div>
        )}

        {/* Warning Notice */}
        {!isOnCooldown && !isEvolving && (
          <div className="mt-4 p-3 rounded-lg bg-muted/50 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-warning shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium">Use with Caution</p>
              <p className="text-xs text-muted-foreground mt-1">
                Manual evolution triggers bypass the automatic controller and
                may affect system performance. Use only when necessary.
              </p>
            </div>
          </div>
        )}
      </Card>

      {/* Confirmation Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {pendingTriggerType && getDialogContent(pendingTriggerType).title}
            </DialogTitle>
            <DialogDescription>
              {pendingTriggerType &&
                getDialogContent(pendingTriggerType).description}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsDialogOpen(false)}
              disabled={isEvolving}
            >
              Cancel
            </Button>
            <Button
              onClick={confirmTrigger}
              variant={
                pendingTriggerType
                  ? getDialogContent(pendingTriggerType).variant
                  : "default"
              }
              disabled={isEvolving}
            >
              {pendingTriggerType && getDialogContent(pendingTriggerType).confirmText}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </AdminGuard>
  );
};
