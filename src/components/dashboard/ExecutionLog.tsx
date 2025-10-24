"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Terminal } from "lucide-react";
import { cn } from "@/lib/utils";

interface LogEntry {
  id: string;
  timestamp: Date;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
}

export function ExecutionLog() {
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      id: '1',
      timestamp: new Date(),
      type: 'success',
      message: 'EUR/USD BUY order executed at 1.0892',
    },
    {
      id: '2',
      timestamp: new Date(Date.now() - 60000),
      type: 'info',
      message: 'Market analysis completed for 8 pairs',
    },
    {
      id: '3',
      timestamp: new Date(Date.now() - 120000),
      type: 'success',
      message: 'GBP/USD SELL order filled at 1.2698',
    },
    {
      id: '4',
      timestamp: new Date(Date.now() - 180000),
      type: 'warning',
      message: 'High volatility detected on USD/JPY',
    },
    {
      id: '5',
      timestamp: new Date(Date.now() - 240000),
      type: 'info',
      message: 'Risk parameters updated successfully',
    },
  ]);

  useEffect(() => {
    const interval = setInterval(() => {
      const messages = [
        'Position monitoring: All trades within limits',
        'Market data feed: Connected and streaming',
        'Signal generated for AUD/USD',
        'Portfolio rebalancing check completed',
      ];
      
      const newLog: LogEntry = {
        id: Date.now().toString(),
        timestamp: new Date(),
        type: 'info',
        message: messages[Math.floor(Math.random() * messages.length)],
      };
      
      setLogs(prev => [newLog, ...prev].slice(0, 10));
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(date);
  };

  const getLogColor = (type: LogEntry['type']) => {
    switch (type) {
      case 'success': return 'text-profit';
      case 'error': return 'text-loss';
      case 'warning': return 'text-yellow-500';
      default: return 'text-muted-foreground';
    }
  };

  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-4">
        <Terminal className="w-5 h-5 text-primary" />
        <h2 className="text-xl font-bold">Execution Log</h2>
        <div className="ml-auto w-2 h-2 bg-profit rounded-full animate-pulse" />
      </div>

      <ScrollArea className="h-64 w-full rounded-md border border-border p-3 bg-muted/30 font-mono text-xs">
        <div className="space-y-2">
          {logs.map((log) => (
            <div key={log.id} className="flex gap-2">
              <span className="text-muted-foreground shrink-0">
                [{formatTime(log.timestamp)}]
              </span>
              <span className={cn("font-medium", getLogColor(log.type))}>
                {log.message}
              </span>
            </div>
          ))}
        </div>
      </ScrollArea>
    </Card>
  );
}
