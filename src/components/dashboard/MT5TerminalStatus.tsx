"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardSkeleton } from "@/components/ui/loading-skeleton";
import { CompactErrorState } from "@/components/ui/error-state";
import { useMT5TerminalStatus } from "@/hooks/useMT5TerminalStatus";
import {
  Terminal,
  Activity,
  Clock,
  Network,
  Shield,
  ShieldAlert,
  RefreshCw,
  Power,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Zap,
  HardDrive,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";

/**
 * MT5TerminalStatus Component
 *
 * Displays comprehensive MT5 terminal status information including:
 * - Terminal path and build version
 * - Connection status with colored badge
 * - Ping latency and last heartbeat time
 * - Data buffers status for each symbol (V10-V100)
 * - Trade allowed flag and trade context info
 * - Test Connection and Restart Connection buttons
 * - MT5 error log with timestamps
 * - Auto-refresh every 5 seconds
 */
export function MT5TerminalStatus() {
  const {
    terminalStatus,
    isLoading,
    error,
    refreshStatus,
    testConnection,
    restartConnection,
  } = useMT5TerminalStatus();

  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [isRestartingConnection, setIsRestartingConnection] = useState(false);
  const [showErrors, setShowErrors] = useState(true);

  const handleTestConnection = async () => {
    setIsTestingConnection(true);
    try {
      await testConnection();
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleRestartConnection = async () => {
    setIsRestartingConnection(true);
    try {
      await restartConnection();
    } finally {
      setIsRestartingConnection(false);
    }
  };

  // Show loading skeleton
  if (isLoading || !terminalStatus) {
    return (
      <Card className="p-6">
        <div className="mb-4">
          <h3 className="text-lg font-semibold">MT5 Terminal Status</h3>
          <p className="text-sm text-muted-foreground">Loading terminal information...</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <CardSkeleton showIcon={false} />
          <CardSkeleton showIcon={false} />
          <CardSkeleton showIcon={false} />
          <CardSkeleton showIcon={false} />
          <CardSkeleton showIcon={false} />
          <CardSkeleton showIcon={false} />
        </div>
      </Card>
    );
  }

  // Show error state
  if (error) {
    return (
      <Card className="p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">MT5 Terminal Status</h3>
            <p className="text-sm text-muted-foreground">Unable to load terminal information</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={refreshStatus}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </Button>
        </div>
        <CompactErrorState
          error={error}
          onRetry={refreshStatus}
        />
      </Card>
    );
  }

  // Get connection status badge
  const getConnectionBadge = () => {
    switch (terminalStatus.connectionState) {
      case "connected":
        return (
          <Badge className="bg-green-600 dark:bg-green-500">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Connected
          </Badge>
        );
      case "disconnected":
        return (
          <Badge variant="destructive">
            <XCircle className="h-3 w-3 mr-1" />
            Disconnected
          </Badge>
        );
      case "error":
        return (
          <Badge className="bg-red-600 dark:bg-red-500">
            <AlertTriangle className="h-3 w-3 mr-1" />
            Error
          </Badge>
        );
      default:
        return (
          <Badge variant="outline">
            <Info className="h-3 w-3 mr-1" />
            Unknown
          </Badge>
        );
    }
  };

  // Format date for display
  const formatDate = (date: Date): string => {
    return new Intl.DateTimeFormat("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    }).format(date);
  };

  // Get data buffer color based on usage
  const getBufferColor = (usage: number): string => {
    if (usage > 80) return "text-red-600 dark:text-red-500";
    if (usage > 50) return "text-yellow-600 dark:text-yellow-500";
    return "text-green-600 dark:text-green-500";
  };

  // Get data buffer background
  const getBufferBg = (usage: number): string => {
    if (usage > 80) return "bg-red-500/10";
    if (usage > 50) return "bg-yellow-500/10";
    return "bg-green-500/10";
  };

  return (
    <Card className="p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">MT5 Terminal Status</h3>
          <div className="flex items-center gap-2 mt-1">
            {getConnectionBadge()}
            {terminalStatus.ping > 0 && (
              <span className="text-xs text-muted-foreground">
                {terminalStatus.ping}ms
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleTestConnection}
            disabled={isTestingConnection}
            className="gap-2"
          >
            <Activity className="h-4 w-4" />
            {isTestingConnection ? "Testing..." : "Test Connection"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRestartConnection}
            disabled={isRestartingConnection}
            className="gap-2"
          >
            <Power className="h-4 w-4" />
            {isRestartingConnection ? "Restarting..." : "Restart"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={refreshStatus}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Terminal Info Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Terminal Path */}
        <div className="flex items-start gap-3 p-4 rounded-lg border bg-card sm:col-span-2">
          <div className="p-2 rounded-lg bg-blue-500/10">
            <Terminal className="h-5 w-5 text-blue-600 dark:text-blue-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-1">Terminal Path</p>
            <p className="text-sm font-mono truncate">
              {terminalStatus.terminalPath || "N/A"}
            </p>
          </div>
        </div>

        {/* Build Version */}
        <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
          <div className="p-2 rounded-lg bg-purple-500/10">
            <Info className="h-5 w-5 text-purple-600 dark:text-purple-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-1">Build Version</p>
            <p className="text-lg font-semibold">
              {terminalStatus.buildVersion || "N/A"}
            </p>
          </div>
        </div>

        {/* Connection State */}
        <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
          <div className="p-2 rounded-lg bg-green-500/10">
            <Network className="h-5 w-5 text-green-600 dark:text-green-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-1">Connection State</p>
            <p className="text-lg font-semibold capitalize">
              {terminalStatus.connectionState}
            </p>
          </div>
        </div>

        {/* Ping/Latency */}
        <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
          <div className="p-2 rounded-lg bg-cyan-500/10">
            <Activity className="h-5 w-5 text-cyan-600 dark:text-cyan-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-1">Ping</p>
            <p className="text-lg font-semibold tabular-nums">
              {terminalStatus.ping}ms
            </p>
          </div>
        </div>

        {/* Last Heartbeat */}
        <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
          <div className="p-2 rounded-lg bg-orange-500/10">
            <Clock className="h-5 w-5 text-orange-600 dark:text-orange-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-1">Last Heartbeat</p>
            <p className="text-sm font-medium">
              {formatDate(terminalStatus.lastHeartbeat)}
            </p>
          </div>
        </div>

        {/* Trade Allowed */}
        <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
          <div className={cn(
            "p-2 rounded-lg",
            terminalStatus.tradeAllowed ? "bg-green-500/10" : "bg-red-500/10"
          )}>
            {terminalStatus.tradeAllowed ? (
              <Shield className="h-5 w-5 text-green-600 dark:text-green-500" />
            ) : (
              <ShieldAlert className="h-5 w-5 text-red-600 dark:text-red-500" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-1">Trading Allowed</p>
            <p className={cn(
              "text-lg font-semibold",
              terminalStatus.tradeAllowed
                ? "text-green-600 dark:text-green-500"
                : "text-red-600 dark:text-red-500"
            )}>
              {terminalStatus.tradeAllowed ? "Yes" : "No"}
            </p>
          </div>
        </div>

        {/* Trade Context Busy */}
        <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
          <div className={cn(
            "p-2 rounded-lg",
            !terminalStatus.tradeContextBusy ? "bg-green-500/10" : "bg-yellow-500/10"
          )}>
            <Zap className={cn(
              "h-5 w-5",
              !terminalStatus.tradeContextBusy
                ? "text-green-600 dark:text-green-500"
                : "text-yellow-600 dark:text-yellow-500"
            )} />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-1">Trade Context</p>
            <p className={cn(
              "text-lg font-semibold",
              !terminalStatus.tradeContextBusy
                ? "text-green-600 dark:text-green-500"
                : "text-yellow-600 dark:text-yellow-500"
            )}>
              {terminalStatus.tradeContextBusy ? "Busy" : "Available"}
            </p>
          </div>
        </div>
      </div>

      {/* Data Buffers Section */}
      {Object.keys(terminalStatus.dataBuffers || {}).length > 0 && (
        <div className="mt-6">
          <h4 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <HardDrive className="h-4 w-4" />
            Data Buffers
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {Object.entries(terminalStatus.dataBuffers).map(([symbol, usage]) => (
              <div
                key={symbol}
                className={cn(
                  "p-3 rounded-lg border",
                  getBufferBg(usage as number)
                )}
              >
                <p className="text-xs text-muted-foreground mb-1">{symbol}</p>
                <p className={cn(
                  "text-lg font-semibold tabular-nums",
                  getBufferColor(usage as number)
                )}>
                  {usage}%
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Error Log Section */}
      {terminalStatus.errors && terminalStatus.errors.length > 0 && (
        <div className="mt-6">
          <Collapsible open={showErrors} onOpenChange={setShowErrors}>
            <CollapsibleTrigger asChild>
              <Button
                variant="ghost"
                size="sm"
                className="w-full justify-start mb-3 gap-2"
              >
                <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-500" />
                <span className="text-sm font-semibold">
                  Error Log ({terminalStatus.errors.length})
                </span>
                <span className="text-xs text-muted-foreground ml-auto">
                  {showErrors ? "Hide" : "Show"}
                </span>
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {terminalStatus.errors.map((err, index) => (
                  <div
                    key={index}
                    className="p-3 rounded-lg border bg-destructive/10 border-destructive/20"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <Badge variant="destructive" className="text-xs">
                        {err.code}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {formatDate(err.timestamp)}
                      </span>
                    </div>
                    <p className="text-sm font-medium">{err.message}</p>
                    {err.details && (
                      <p className="text-xs text-muted-foreground mt-1">
                        {err.details}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </CollapsibleContent>
          </Collapsible>
        </div>
      )}

      {/* Footer with last update */}
      <div className="mt-4 pt-4 border-t flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          Auto-refreshing every 5 seconds
        </span>
        {terminalStatus.lastHeartbeat && (
          <span className="text-muted-foreground">
            Last updated: {formatDate(terminalStatus.lastHeartbeat)}
          </span>
        )}
      </div>
    </Card>
  );
}
