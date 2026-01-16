"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import { Power, Play, Pause, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import { post } from "@/lib/api/client";
import { toast } from "sonner";
import { RoleGuard } from "@/components/auth/RoleGuard";

type SystemStatus = "running" | "stopped" | "error";

interface SystemStateResponse {
  status: SystemStatus;
  uptime?: number;
  lastStartTime?: string;
  lastStopTime?: string;
}

export function SystemControlPanel() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus>("stopped");
  const [uptime, setUptime] = useState<number>(0);
  const [lastStartTime, setLastStartTime] = useState<string>("");
  const [lastStopTime, setLastStopTime] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [isTransitioning, setIsTransitioning] = useState(false);
  const [showStopDialog, setShowStopDialog] = useState(false);

  // Fetch system status on mount
  useEffect(() => {
    const fetchSystemStatus = async () => {
      try {
        const response = await post<SystemStateResponse>("/system/status");
        if (response.data) {
          setSystemStatus(response.data.status);
          setUptime(response.data.uptime || 0);
          setLastStartTime(response.data.lastStartTime || "");
          setLastStopTime(response.data.lastStopTime || "");
        }
      } catch {
        // Default to stopped if API fails
        setSystemStatus("stopped");
      }
    };

    fetchSystemStatus();
  }, []);

  // Update uptime counter when running
  useEffect(() => {
    if (systemStatus === "running") {
      const interval = setInterval(() => {
        setUptime((prev) => prev + 1);
      }, 1000);
      return () => clearInterval(interval);
    }
  }, [systemStatus]);

  // Format uptime to readable string
  const formatUptime = (seconds: number): string => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    if (hours > 0) {
      return `${hours}h ${minutes}m ${secs}s`;
    }
    if (minutes > 0) {
      return `${minutes}m ${secs}s`;
    }
    return `${secs}s`;
  };

  // Format date string
  const formatDate = (dateString: string): string => {
    if (!dateString) return "Never";
    return new Date(dateString).toLocaleString();
  };

  // Get status badge variant
  const getStatusBadge = (): { variant: "default" | "destructive" | "secondary"; label: string } => {
    switch (systemStatus) {
      case "running":
        return { variant: "default", label: "Running" };
      case "stopped":
        return { variant: "secondary", label: "Stopped" };
      case "error":
        return { variant: "destructive", label: "Error" };
      default:
        return { variant: "secondary", label: "Unknown" };
    }
  };

  // Get status color class
  const getStatusColor = (): string => {
    switch (systemStatus) {
      case "running":
        return "bg-green-500";
      case "stopped":
        return "bg-red-500";
      case "error":
        return "bg-yellow-500";
      default:
        return "bg-gray-500";
    }
  };

  // Handle start system
  const handleStart = async () => {
    setIsLoading(true);
    setIsTransitioning(true);

    try {
      const response = await post<{ status: SystemStatus; uptime: number }>("/system/start");

      if (response.data) {
        setSystemStatus(response.data.status);
        setUptime(response.data.uptime || 0);
        setLastStartTime(new Date().toISOString());
        toast.success("System started successfully");
      }
    } catch {
      setSystemStatus("error");
      toast.error("Failed to start system");
    } finally {
      setIsLoading(false);
      setIsTransitioning(false);
    }
  };

  // Handle stop system
  const handleStop = async () => {
    setShowStopDialog(false);
    setIsLoading(true);
    setIsTransitioning(true);

    try {
      const response = await post<{ status: SystemStatus }>("/system/stop");

      if (response.data) {
        setSystemStatus(response.data.status);
        setLastStopTime(new Date().toISOString());
        toast.success("System stopped successfully");
      }
    } catch {
      setSystemStatus("error");
      toast.error("Failed to stop system");
    } finally {
      setIsLoading(false);
      setIsTransitioning(false);
    }
  };

  const statusBadge = getStatusBadge();

  return (
    <RoleGuard allowedRoles={["admin"]}>
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold">System Control Panel</h2>
            <p className="text-sm text-muted-foreground">Start and stop the trading system</p>
          </div>
          <Badge variant={statusBadge.variant} className="text-sm px-3 py-1">
            <span className={cn("w-2 h-2 rounded-full mr-2", getStatusColor())} />
            {statusBadge.label}
          </Badge>
        </div>

        {/* Status and Controls */}
        <div className="flex items-center justify-between p-4 bg-muted/50 rounded-lg border border-border mb-6">
          <div className="flex items-center gap-4">
            <div className={cn(
              "w-16 h-16 rounded-full flex items-center justify-center",
              systemStatus === "running" ? "bg-green-500/20" : "bg-muted"
            )}>
              <Power className={cn(
                "w-8 h-8",
                systemStatus === "running" ? "text-green-600" : "text-muted-foreground"
              )} />
            </div>
            <div>
              <p className="font-bold text-lg">
                System {systemStatus === "running" ? "Running" : systemStatus === "stopped" ? "Stopped" : "Error"}
              </p>
              <p className="text-sm text-muted-foreground">
                {systemStatus === "running" ? "All systems operational" : "Trading paused"}
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            {systemStatus !== "running" ? (
              <Button
                size="lg"
                onClick={handleStart}
                disabled={isLoading || isTransitioning}
                className="bg-green-600 hover:bg-green-700 text-white"
              >
                {isLoading ? (
                  <>Starting...</>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    Start System
                  </>
                )}
              </Button>
            ) : (
              <Button
                size="lg"
                onClick={() => setShowStopDialog(true)}
                disabled={isLoading || isTransitioning}
                variant="destructive"
              >
                {isLoading ? (
                  <>Stopping...</>
                ) : (
                  <>
                    <Pause className="w-4 h-4 mr-2" />
                    Stop System
                  </>
                )}
              </Button>
            )}
          </div>
        </div>

        {/* System Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Uptime Counter */}
          <div className="p-4 bg-card border border-border rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-4 h-4 text-muted-foreground" />
              <p className="text-sm font-medium">Uptime</p>
            </div>
            <p className="text-2xl font-bold">
              {systemStatus === "running" ? formatUptime(uptime) : "0s"}
            </p>
          </div>

          {/* Last Start Time */}
          <div className="p-4 bg-card border border-border rounded-lg">
            <p className="text-sm font-medium mb-2">Last Start</p>
            <p className="text-sm text-muted-foreground">{formatDate(lastStartTime)}</p>
          </div>

          {/* Last Stop Time */}
          <div className="p-4 bg-card border border-border rounded-lg md:col-span-2">
            <p className="text-sm font-medium mb-2">Last Stop</p>
            <p className="text-sm text-muted-foreground">{formatDate(lastStopTime)}</p>
          </div>
        </div>

        {/* Stop Confirmation Dialog */}
        <AlertDialog open={showStopDialog} onOpenChange={setShowStopDialog}>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Stop System</AlertDialogTitle>
              <AlertDialogDescription>
                Are you sure you want to stop the trading system? This will halt all automated trading activities.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleStop} className="bg-destructive text-white hover:bg-destructive/90">
                Stop System
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </Card>
    </RoleGuard>
  );
}
