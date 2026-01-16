"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { AlertCircle, RefreshCw, Download, Search, Pause, Play, Trash2 } from "lucide-react";
import { Activity, Dna, TrendingUp, TrendingDown, Info } from "lucide-react";
import { toast } from "sonner";
import { evolutionApi } from "@/lib/api";
import { useWebSocket } from "@/hooks/useWebSocket";
import type { EvolutionLog } from "@/types/evolution";

type EventType = 'INFO' | 'MUTATION' | 'GENERATION' | 'WARNING' | 'ERROR' | 'ALL';

interface EvolutionLogViewerProps {
  logs?: EvolutionLog[];
}

/**
 * Extended log type to include INFO, WARNING, ERROR types
 */
interface ExtendedEvolutionLog extends EvolutionLog {
  eventType?: EventType;
}

const EVENT_TYPE_COLORS: Record<EventType, string> = {
  INFO: 'bg-info/20 text-info border-info/30',
  MUTATION: 'bg-purple-500/20 text-purple-500 border-purple-500/30',
  GENERATION: 'bg-profit/20 text-profit border-profit/30',
  WARNING: 'bg-warning/20 text-warning border-warning/30',
  ERROR: 'bg-loss/20 text-loss border-loss/30',
  ALL: 'bg-muted text-muted-foreground',
};

export const EvolutionLogViewer = ({ logs: initialLogs }: EvolutionLogViewerProps) => {
  // State for logs data
  const [logs, setLogs] = useState<ExtendedEvolutionLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // UI state
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedEventTypes, setSelectedEventTypes] = useState<EventType[]>(['ALL']);
  const [isPaused, setIsPaused] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);

  // Ref for scroll management
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const scrollViewportRef = useRef<HTMLDivElement>(null);

  /**
   * Fetch evolution logs from API
   */
  const fetchLogs = useCallback(async (eventType?: string) => {
    setLoading(true);
    setError(null);

    try {
      const fetchedLogs = await evolutionApi.fetchEvolutionLogs(eventType);
      setLogs(fetchedLogs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch evolution logs");
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Handle WebSocket message for new evolution events
   */
  const handleWebSocketMessage = useCallback((message: { type: string; data: unknown }) => {
    if (isPaused) return;

    const newLog = message.data as ExtendedEvolutionLog;

    // Show toast for important events
    if (newLog.type === 'EVOLUTION_CYCLE' || newLog.eventType === 'GENERATION') {
      toast.success(`New Generation: #${newLog.generation}`, {
        description: newLog.message,
      });
    } else if (newLog.eventType === 'WARNING') {
      toast.warning("Evolution Warning", {
        description: newLog.message,
      });
    } else if (newLog.eventType === 'ERROR') {
      toast.error("Evolution Error", {
        description: newLog.message,
      });
    }

    setLogs((prev) => {
      // Avoid duplicates
      const exists = prev.some(
        (log) =>
          log.timestamp === newLog.timestamp &&
          log.type === newLog.type &&
          log.message === newLog.message
      );

      if (exists) return prev;

      const updated = [newLog, ...prev];

      // Keep only last 500 logs to prevent memory issues
      if (updated.length > 500) {
        return updated.slice(0, 500);
      }

      return updated;
    });
  }, [isPaused]);

  /**
   * WebSocket connection for real-time updates
   */
  const { isConnected: wsConnected, reconnect } = useWebSocket("evolution_event", {
    onMessage: handleWebSocketMessage,
  });

  /**
   * Auto-scroll to top when new logs arrive
   */
  useEffect(() => {
    if (autoScroll && !isPaused && scrollViewportRef.current) {
      scrollViewportRef.current.scrollTop = 0;
    }
  }, [logs, autoScroll, isPaused]);

  /**
   * Initial fetch
   */
  useEffect(() => {
    fetchLogs();
  }, [fetchLogs]);

  /**
   * Get log type color
   */
  const getLogTypeColor = (type: string) => {
    switch (type) {
      case 'EVOLUTION_CYCLE':
        return EVENT_TYPE_COLORS.GENERATION;
      case 'MUTATION':
        return EVENT_TYPE_COLORS.MUTATION;
      case 'FEATURE_SUCCESS':
        return EVENT_TYPE_COLORS.GENERATION;
      case 'FEATURE_FAILURE':
        return EVENT_TYPE_COLORS.ERROR;
      default:
        return EVENT_TYPE_COLORS.INFO;
    }
  };

  /**
   * Get log icon
   */
  const getLogIcon = (type: string) => {
    switch (type) {
      case 'EVOLUTION_CYCLE':
        return <Dna className="w-4 h-4" />;
      case 'MUTATION':
        return <Activity className="w-4 h-4" />;
      case 'FEATURE_SUCCESS':
        return <TrendingUp className="w-4 h-4" />;
      case 'FEATURE_FAILURE':
        return <TrendingDown className="w-4 h-4" />;
      default:
        return <Info className="w-4 h-4" />;
    }
  };

  /**
   * Filter logs by search query and event types
   */
  const filteredLogs = logs.filter((log) => {
    // Filter by event type
    if (!selectedEventTypes.includes('ALL')) {
      const logEventType = (log.eventType || determineEventType(log.type)) as EventType;
      if (!selectedEventTypes.includes(logEventType)) {
        return false;
      }
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        log.message.toLowerCase().includes(query) ||
        log.type.toLowerCase().includes(query) ||
        log.generation.toString().includes(query)
      );
    }

    return true;
  });

  /**
   * Determine event type from log type
   */
  function determineEventType(type: string): EventType {
    if (type.includes('ERROR') || type === 'FEATURE_FAILURE') return 'ERROR';
    if (type.includes('WARN') || type.includes('WARNING')) return 'WARNING';
    if (type.includes('MUTATION')) return 'MUTATION';
    if (type.includes('GENERATION') || type === 'EVOLUTION_CYCLE') return 'GENERATION';
    return 'INFO';
  }

  /**
   * Toggle event type filter
   */
  const toggleEventType = (eventType: EventType) => {
    if (eventType === 'ALL') {
      setSelectedEventTypes(['ALL']);
    } else {
      setSelectedEventTypes((prev) => {
        const withoutAll = prev.filter((t) => t !== 'ALL');
        if (withoutAll.includes(eventType)) {
          return withoutAll.length > 0 ? withoutAll : ['ALL'];
        } else {
          return [...withoutAll, eventType];
        }
      });
    }
  };

  /**
   * Export logs to CSV
   */
  const exportLogs = useCallback(() => {
    const headers = ['Timestamp', 'Type', 'Generation', 'Message', 'Details'];
    const rows = filteredLogs.map((log) => [
      log.timestamp,
      log.type,
      log.generation.toString(),
      `"${log.message.replace(/"/g, '""')}"`,
      log.details ? `"${JSON.stringify(log.details).replace(/"/g, '""')}"` : '',
    ]);

    const csv = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `evolution-logs-${new Date().toISOString()}.csv`;
    link.click();
    URL.revokeObjectURL(url);

    toast.success('Logs exported successfully');
  }, [filteredLogs]);

  /**
   * Clear logs
   */
  const clearLogs = useCallback(() => {
    setLogs([]);
    toast.success('Logs cleared');
  }, []);

  return (
    <Card className="p-6 flex flex-col h-[500px]">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold">Evolution Log</h3>
          <p className="text-sm text-muted-foreground">
            Real-time evolution events {wsConnected && <span className="text-profit">(Live)</span>}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => fetchLogs()}
            disabled={loading}
            title="Refresh logs"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={exportLogs}
            disabled={filteredLogs.length === 0}
            title="Export to CSV"
          >
            <Download className="w-4 h-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={clearLogs}
            disabled={logs.length === 0}
            title="Clear logs"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
          <Dna className="w-5 h-5 text-primary" />
        </div>
      </div>

      {/* Filters */}
      <div className="space-y-3 mb-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Event type filters and controls */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex flex-wrap gap-2">
            {(['ALL', 'INFO', 'MUTATION', 'GENERATION', 'WARNING', 'ERROR'] as EventType[]).map(
              (eventType) => (
                <Badge
                  key={eventType}
                  variant={selectedEventTypes.includes(eventType) ? 'default' : 'outline'}
                  className={`cursor-pointer ${EVENT_TYPE_COLORS[eventType]} ${
                    selectedEventTypes.includes(eventType) ? '' : 'opacity-50'
                  }`}
                  onClick={() => toggleEventType(eventType)}
                >
                  {eventType}
                </Badge>
              )
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsPaused(!isPaused)}
              title={isPaused ? 'Resume updates' : 'Pause updates'}
            >
              {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
            </Button>
            <div className="flex items-center gap-2">
              <Checkbox
                id="auto-scroll"
                checked={autoScroll}
                onCheckedChange={(checked) => setAutoScroll(checked as boolean)}
              />
              <label htmlFor="auto-scroll" className="text-sm text-muted-foreground cursor-pointer">
                Auto-scroll
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* Logs display */}
      <div className="flex-1 min-h-0">
        {loading ? (
          // Loading skeleton
          <div className="space-y-3 pr-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="p-3 rounded-lg border border-border">
                <div className="flex items-start gap-3">
                  <Skeleton className="w-4 h-4 mt-0.5" />
                  <div className="flex-1 space-y-2">
                    <div className="flex items-center justify-between gap-2">
                      <Skeleton className="h-5 w-24" />
                      <Skeleton className="h-4 w-16" />
                    </div>
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-3 w-32" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          // Error state
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <AlertCircle className="w-12 h-12 text-loss" />
            <div className="text-center">
              <h4 className="font-semibold text-destructive">Failed to load logs</h4>
              <p className="text-sm text-muted-foreground mt-1">{error}</p>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => fetchLogs()} variant="outline">
                <RefreshCw className="w-4 h-4 mr-2" />
                Retry
              </Button>
              <Button onClick={reconnect} variant="outline">
                Reconnect
              </Button>
            </div>
          </div>
        ) : filteredLogs.length === 0 ? (
          // Empty state
          <div className="flex flex-col items-center justify-center h-full">
            <Activity className="w-12 h-12 text-muted-foreground" />
            <p className="text-muted-foreground mt-2">No logs to display</p>
          </div>
        ) : (
          // Logs list
          <ScrollArea ref={scrollAreaRef} className="h-full">
            <div
              ref={scrollViewportRef}
              className="space-y-3 pr-4"
            >
              {filteredLogs.map((log, index) => (
                <div
                  key={`${log.timestamp}-${index}`}
                  className="p-3 rounded-lg bg-card border border-border hover:bg-accent/5 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <div className={`mt-0.5 ${getLogTypeColor(log.type).split(' ')[1]}`}>
                      {getLogIcon(log.type)}
                    </div>

                    <div className="flex-1 space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <Badge className={getLogTypeColor(log.type)}>
                          {log.type.replace(/_/g, ' ')}
                        </Badge>
                        <span className="text-xs text-muted-foreground">
                          Gen #{log.generation}
                        </span>
                      </div>

                      <p className="text-sm">{log.message}</p>

                      {log.details && Object.keys(log.details).length > 0 && (
                        <div className="text-xs text-muted-foreground font-mono bg-muted/30 p-2 rounded">
                          {JSON.stringify(log.details, null, 2)}
                        </div>
                      )}

                      <span className="text-xs text-muted-foreground">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        )}
      </div>

      {/* Footer with log count */}
      <div className="mt-4 pt-4 border-t border-border">
        <p className="text-xs text-muted-foreground">
          Showing {filteredLogs.length} of {logs.length} logs
        </p>
      </div>
    </Card>
  );
};
