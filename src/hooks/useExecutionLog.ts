/**
 * useExecutionLog Hook
 *
 * Fetches and manages execution log data from the API.
 * Includes real-time updates via WebSocket, loading states, and error handling.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { get } from '@/lib/api/client';
import { wsClient } from '@/lib/websocket/client';
import type { ExecutionLogEntry, ExecutionLogFilters, ExecutionLogLevel } from '@/types/evolution';

export interface UseExecutionLogReturn {
  logs: ExecutionLogEntry[];
  isLoading: boolean;
  error: Error | null;
  filters: ExecutionLogFilters;
  setFilters: (filters: ExecutionLogFilters) => void;
  isPaused: boolean;
  setIsPaused: (paused: boolean) => void;
  clearLogs: () => void;
  exportLogs: () => void;
  refreshLogs: () => Promise<void>;
}

/**
 * Convert WebSocket trade_update events to execution log entries
 */
function tradeUpdateToLogEntry(data: unknown): ExecutionLogEntry | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }

  const d = data as Record<string, unknown>;

  return {
    id: `ws-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    timestamp: new Date().toISOString(),
    level: 'info',
    message: `Trade ${d.tradeId || 'unknown'} updated: ${d.symbol || 'unknown'} - ${d.status || 'unknown'}`,
    tradeTicket: typeof d.tradeId === 'string' ? d.tradeId : undefined,
    details: d,
  };
}

/**
 * Convert WebSocket mt5 events to execution log entries
 */
function mt5EventToLogEntry(eventType: string, data: unknown): ExecutionLogEntry | null {
  if (typeof data !== 'object' || data === null) {
    return null;
  }

  const d = data as Record<string, unknown>;

  let level: ExecutionLogLevel = 'info';
  let message = '';

  switch (eventType) {
    case 'mt5_order_opened':
      level = 'success';
      message = `MT5 Order ${d.orderId || 'unknown'} opened for ${d.symbol || 'unknown'} (${d.side || 'unknown'})`;
      break;
    case 'mt5_order_closed':
      level = 'info';
      message = `MT5 Order ${d.orderId || 'unknown'} closed for ${d.symbol || 'unknown'} (${d.side || 'unknown'})`;
      break;
    case 'mt5_position_modified':
      level = 'info';
      message = `MT5 Position ${d.positionId || 'unknown'} modified for ${d.symbol || 'unknown'}`;
      break;
    case 'mt5_error':
      level = 'error';
      message = `MT5 Error (${d.errorCode || 'unknown'}): ${d.errorMessage || 'Unknown error'}`;
      break;
    case 'mt5_connected':
      level = 'success';
      message = `MT5 Connected: Account ${d.accountId || 'unknown'} on ${d.server || 'unknown'}`;
      break;
    case 'mt5_disconnected':
      level = 'warning';
      message = `MT5 Disconnected: ${d.reason || 'Connection lost'}`;
      break;
    default:
      return null;
  }

  return {
    id: `ws-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    timestamp: new Date().toISOString(),
    level,
    message,
    details: d,
  };
}

/**
 * Hook to fetch and manage execution logs with real-time updates
 */
export function useExecutionLog(): UseExecutionLogReturn {
  const [logs, setLogs] = useState<ExecutionLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [filters, setFilters] = useState<ExecutionLogFilters>({});
  const [isPaused, setIsPaused] = useState(false);

  const isMounted = useRef(true);
  const wsHandlerRefs = useRef<Array<() => void>>([]);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);

  /**
   * Fetch execution logs from API
   */
  const fetchLogs = useCallback(async (): Promise<void> => {
    if (!isMounted.current) return;

    setIsLoading(true);
    setError(null);

    try {
      const params: Record<string, string | number | boolean | undefined> = {};

      if (filters.symbol) {
        params.symbol = filters.symbol;
      }
      if (filters.ticket) {
        params.ticket = filters.ticket;
      }
      if (filters.eventTypes && filters.eventTypes.length > 0) {
        params.level = filters.eventTypes.join(',');
      }

      const response = await get<ExecutionLogEntry[]>('/trades/execution-log', params);

      if (isMounted.current && response.ok) {
        setLogs(response.data);
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to fetch execution logs');
        setError(errorObj);
        console.error('[useExecutionLog] Fetch failed:', errorObj);
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
      }
    }
  }, [filters]);

  /**
   * Refresh logs (can be called manually)
   */
  const refreshLogs = useCallback(async () => {
    await fetchLogs();
  }, [fetchLogs]);

  /**
   * Clear all logs
   */
  const clearLogs = useCallback(() => {
    setLogs([]);
  }, []);

  /**
   * Export logs to CSV
   */
  const exportLogs = useCallback(() => {
    const headers = ['Timestamp', 'Level', 'Message', 'Trade Ticket', 'Details'];
    const rows = logs.map((log) => [
      log.timestamp,
      log.level,
      `"${log.message.replace(/"/g, '""')}"`,
      log.tradeTicket || '',
      JSON.stringify(log.details || {}),
    ]);

    const csv = [headers.join(','), ...rows.map((row) => row.join(','))].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `execution_logs_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [logs]);

  /**
   * Add a new log entry from WebSocket
   */
  const addLogEntry = useCallback((entry: ExecutionLogEntry) => {
    if (!isPaused && isMounted.current) {
      setLogs((prevLogs) => {
        const updated = [entry, ...prevLogs];

        // Keep only the most recent 500 logs to prevent memory issues
        if (updated.length > 500) {
          return updated.slice(0, 500);
        }

        return updated;
      });

      // Auto-scroll to newest logs
      requestAnimationFrame(() => {
        const container = scrollContainerRef.current;
        if (container) {
          container.scrollTop = 0;
        }
      });
    }
  }, [isPaused]);

  /**
   * Handle trade_update events from WebSocket
   */
  const handleTradeUpdate = useCallback((data: unknown) => {
    const logEntry = tradeUpdateToLogEntry(data);
    if (logEntry) {
      addLogEntry(logEntry);
    }
  }, [addLogEntry]);

  /**
   * Handle MT5 events from WebSocket
   */
  const handleMT5Event = useCallback((eventType: string) => {
    return (data: unknown) => {
      const logEntry = mt5EventToLogEntry(eventType, data);
      if (logEntry) {
        addLogEntry(logEntry);
      }
    };
  }, [addLogEntry]);

  /**
   * Subscribe to WebSocket events
   */
  useEffect(() => {
    // Subscribe to trade_update events
    const unsubscribeTradeUpdate = wsClient.on('trade_update', handleTradeUpdate);
    wsHandlerRefs.current.push(unsubscribeTradeUpdate);

    // Subscribe to MT5 events
    const mt5Events = [
      'mt5_order_opened',
      'mt5_order_closed',
      'mt5_position_modified',
      'mt5_error',
      'mt5_connected',
      'mt5_disconnected',
    ];

    mt5Events.forEach((eventType) => {
      const unsubscribe = wsClient.on(eventType, handleMT5Event(eventType));
      wsHandlerRefs.current.push(unsubscribe);
    });

    return () => {
      wsHandlerRefs.current.forEach((unsubscribe) => {
        unsubscribe();
      });
      wsHandlerRefs.current = [];
    };
  }, [handleTradeUpdate, handleMT5Event]);

  /**
   * Initial fetch and auto-refresh interval
   */
  useEffect(() => {
    fetchLogs();

    const intervalId = setInterval(() => {
      if (!isPaused) {
        fetchLogs();
      }
    }, 10000); // Refresh every 10 seconds

    return () => {
      clearInterval(intervalId);
    };
  }, [fetchLogs, isPaused]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    isMounted.current = true;

    return () => {
      isMounted.current = false;
    };
  }, []);

  return {
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
  };
}
