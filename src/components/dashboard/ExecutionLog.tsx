"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Terminal, Pause, Play, Trash2, Download, RefreshCw, AlertCircle, Filter, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useExecutionLog } from "@/hooks/useExecutionLog";
import { VOLATILITY_INDICES } from "@/types/market";
import type { ExecutionLogLevel } from "@/types/evolution";

const EVENT_TYPES: { value: ExecutionLogLevel; label: string; color: string }[] = [
  { value: 'info', label: 'Info', color: 'text-blue-500' },
  { value: 'success', label: 'Success', color: 'text-profit' },
  { value: 'warning', label: 'Warning', color: 'text-yellow-500' },
  { value: 'error', label: 'Error', color: 'text-loss' },
];

/**
 * Loading skeleton for ExecutionLog
 */
function ExecutionLogSkeleton() {
  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-4">
        <Terminal className="w-5 h-5 text-primary" />
        <Skeleton className="h-6 w-32" />
        <div className="ml-auto w-2 h-2 bg-profit rounded-full animate-pulse" />
      </div>

      <div className="flex gap-2 mb-4">
        <Skeleton className="h-9 w-24" />
        <Skeleton className="h-9 w-32" />
        <Skeleton className="h-9 w-24" />
        <Skeleton className="h-9 w-24 ml-auto" />
      </div>

      <div className="h-64 w-full rounded-md border border-border p-3 bg-muted/30 font-mono text-xs">
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="flex gap-2">
              <Skeleton className="h-4 w-20 shrink-0" />
              <Skeleton className="h-4 w-64" />
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

/**
 * Error state for ExecutionLog
 */
function ExecutionLogError({ error, onRetry }: { error: Error; onRetry: () => void }) {
  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-4">
        <Terminal className="w-5 h-5 text-primary" />
        <h2 className="text-xl font-bold">Execution Log</h2>
      </div>

      <Alert variant="destructive" className="mb-4">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          Failed to load execution logs: {error.message}
        </AlertDescription>
      </Alert>

      <Button onClick={onRetry} variant="outline" size="sm">
        <RefreshCw className="w-4 h-4 mr-2" />
        Retry
      </Button>
    </Card>
  );
}

export function ExecutionLog() {
  const {
    logs,
    isLoading,
    error,
    filters,
    setFilters,
    isPaused,
    setIsPaused,
    clearLogs,
    exportLogs,
    refreshLogs,
  } = useExecutionLog();

  const [showFilters, setShowFilters] = useState(false);

  /**
   * Toggle event type filter
   */
  const toggleEventType = (eventType: ExecutionLogLevel) => {
    const current = filters.eventTypes || [];
    const updated = current.includes(eventType)
      ? current.filter((t) => t !== eventType)
      : [...current, eventType];

    setFilters({
      ...filters,
      eventTypes: updated.length > 0 ? updated : undefined,
    });
  };

  /**
   * Clear all filters
   */
  const clearFilters = () => {
    setFilters({});
  };

  /**
   * Get filtered logs
   */
  const filteredLogs = logs.filter((log) => {
    if (filters.eventTypes && filters.eventTypes.length > 0) {
      if (!filters.eventTypes.includes(log.level)) {
        return false;
      }
    }
    if (filters.symbol && log.details?.symbol) {
      if (log.details.symbol !== filters.symbol) {
        return false;
      }
    }
    if (filters.ticket && log.tradeTicket) {
      if (!log.tradeTicket.includes(filters.ticket)) {
        return false;
      }
    }
    return true;
  });

  /**
   * Format timestamp
   */
  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(date);
  };

  /**
   * Get log color
   */
  const getLogColor = (level: ExecutionLogLevel) => {
    switch (level) {
      case 'success': return 'text-profit';
      case 'error': return 'text-loss';
      case 'warning': return 'text-yellow-500';
      default: return 'text-muted-foreground';
    }
  };

  if (isLoading) {
    return <ExecutionLogSkeleton />;
  }

  if (error) {
    return <ExecutionLogError error={error} onRetry={refreshLogs} />;
  }

  const hasActiveFilters = !!(
    filters.eventTypes?.length ||
    filters.symbol ||
    filters.ticket
  );

  return (
    <Card className="p-4 sm:p-6">
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <Terminal className="w-5 h-5 text-primary" />
        <h2 className="text-xl font-bold">Execution Log</h2>
        <div className="ml-auto flex items-center gap-2">
          {isPaused ? (
            <Badge variant="outline" className="text-yellow-500 border-yellow-500">
              Paused
            </Badge>
          ) : (
            <div className="w-2 h-2 bg-profit rounded-full animate-pulse" title="Live updates enabled" />
          )}
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-wrap gap-2 mb-4">
        {/* Filter Toggle */}
        <Button
          variant={showFilters ? "default" : "outline"}
          size="sm"
          onClick={() => setShowFilters(!showFilters)}
        >
          <Filter className="w-4 h-4 mr-2" />
          Filters
          {hasActiveFilters && (
            <Badge variant="secondary" className="ml-2 h-5 px-1.5 text-xs">
              {(filters.eventTypes?.length || 0) +
                (filters.symbol ? 1 : 0) +
                (filters.ticket ? 1 : 0)}
            </Badge>
          )}
        </Button>

        {/* Clear Filters */}
        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={clearFilters}>
            <X className="w-4 h-4 mr-2" />
            Clear Filters
          </Button>
        )}

        {/* Pause/Resume */}
        <Button
          variant={isPaused ? "default" : "outline"}
          size="sm"
          onClick={() => setIsPaused(!isPaused)}
          className="ml-auto"
        >
          {isPaused ? (
            <>
              <Play className="w-4 h-4 mr-2" />
              Resume
            </>
          ) : (
            <>
              <Pause className="w-4 h-4 mr-2" />
              Pause
            </>
          )}
        </Button>

        {/* Clear Logs */}
        <Button variant="outline" size="sm" onClick={clearLogs}>
          <Trash2 className="w-4 h-4 mr-2" />
          Clear
        </Button>

        {/* Export Logs */}
        <Button variant="outline" size="sm" onClick={exportLogs}>
          <Download className="w-4 h-4 mr-2" />
          Export
        </Button>

        {/* Refresh */}
        <Button variant="outline" size="sm" onClick={refreshLogs}>
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Filter Panel */}
      {showFilters && (
        <div className="mb-4 p-3 bg-muted/50 rounded-md border border-border space-y-3">
          {/* Event Type Filters */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-2 block">
              Event Types
            </label>
            <div className="flex flex-wrap gap-2">
              {EVENT_TYPES.map((type) => (
                <Badge
                  key={type.value}
                  variant={filters.eventTypes?.includes(type.value) ? "default" : "outline"}
                  className={cn(
                    "cursor-pointer hover:opacity-80",
                    !filters.eventTypes?.includes(type.value) && type.color
                  )}
                  onClick={() => toggleEventType(type.value)}
                >
                  {type.label}
                </Badge>
              ))}
            </div>
          </div>

          {/* Symbol Filter */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-2 block">
              Symbol
            </label>
            <div className="flex flex-wrap gap-2">
              <Badge
                variant={!filters.symbol ? "default" : "outline"}
                className="cursor-pointer hover:opacity-80"
                onClick={() => setFilters({ ...filters, symbol: undefined })}
              >
                All
              </Badge>
              {VOLATILITY_INDICES.map((symbol) => (
                <Badge
                  key={symbol}
                  variant={filters.symbol === symbol ? "default" : "outline"}
                  className="cursor-pointer hover:opacity-80"
                  onClick={() => setFilters({ ...filters, symbol })}
                >
                  {symbol}
                </Badge>
              ))}
            </div>
          </div>

          {/* Ticket Search */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-2 block">
              Search by Ticket ID
            </label>
            <input
              type="text"
              value={filters.ticket || ''}
              onChange={(e) => setFilters({ ...filters, ticket: e.target.value || undefined })}
              placeholder="Enter ticket ID..."
              className="w-full px-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
        </div>
      )}

      {/* Log Display */}
      <ScrollArea className="h-64 w-full rounded-md border border-border p-3 bg-muted/30 font-mono text-xs">
        {filteredLogs.length === 0 ? (
          <div className="flex items-center justify-center h-full text-muted-foreground">
            {hasActiveFilters ? 'No logs match the current filters' : 'No logs available'}
          </div>
        ) : (
          <div className="space-y-2">
            {filteredLogs.map((log) => (
              <div key={log.id} className="flex gap-2 items-start group">
                <span className="text-muted-foreground shrink-0">
                  [{formatTime(log.timestamp)}]
                </span>
                <span className={cn("font-medium", getLogColor(log.level))}>
                  [{log.level.toUpperCase()}]
                </span>
                <span className="flex-1 break-words">
                  {log.message}
                  {log.tradeTicket && (
                    <Badge variant="outline" className="ml-2 text-xs">
                      #{log.tradeTicket}
                    </Badge>
                  )}
                </span>
                {log.details && (
                  <details className="text-xs text-muted-foreground cursor-help">
                    <summary>Details</summary>
                    <pre className="mt-1 p-2 bg-background rounded border border-border overflow-x-auto">
                      {JSON.stringify(log.details, null, 2)}
                    </pre>
                  </details>
                )}
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Footer Info */}
      <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
        <span>Showing {filteredLogs.length} of {logs.length} logs</span>
        {logs.length > 0 && (
          <span>Last updated: {formatTime(logs[0]?.timestamp || new Date().toISOString())}</span>
        )}
      </div>
    </Card>
  );
}
