"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileText, Search, Filter, Download } from "lucide-react";
import { cn } from "@/lib/utils";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Log {
  id: string;
  timestamp: Date;
  level: 'info' | 'warning' | 'error' | 'success';
  category: string;
  message: string;
}

export function LogsViewer() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterLevel, setFilterLevel] = useState("all");

  const logs: Log[] = [
    {
      id: '1',
      timestamp: new Date(),
      level: 'success',
      category: 'TRADE',
      message: 'EUR/USD BUY order executed successfully at 1.0892',
    },
    {
      id: '2',
      timestamp: new Date(Date.now() - 120000),
      level: 'info',
      category: 'SYSTEM',
      message: 'Market data synchronization completed',
    },
    {
      id: '3',
      timestamp: new Date(Date.now() - 240000),
      level: 'warning',
      category: 'RISK',
      message: 'Position size approaching maximum limit',
    },
    {
      id: '4',
      timestamp: new Date(Date.now() - 360000),
      level: 'success',
      category: 'TRADE',
      message: 'GBP/USD SELL order filled at 1.2698',
    },
    {
      id: '5',
      timestamp: new Date(Date.now() - 480000),
      level: 'info',
      category: 'ANALYTICS',
      message: 'Performance metrics calculated for last 24h',
    },
    {
      id: '6',
      timestamp: new Date(Date.now() - 600000),
      level: 'error',
      category: 'CONNECTION',
      message: 'Temporary connection loss to broker API (recovered)',
    },
    {
      id: '7',
      timestamp: new Date(Date.now() - 720000),
      level: 'info',
      category: 'SYSTEM',
      message: 'Risk parameters updated by administrator',
    },
  ];

  const filteredLogs = logs.filter(log => {
    const matchesSearch = log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         log.category.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesFilter = filterLevel === "all" || log.level === filterLevel;
    return matchesSearch && matchesFilter;
  });

  const getLevelColor = (level: Log['level']) => {
    switch (level) {
      case 'success': return 'text-profit';
      case 'error': return 'text-loss';
      case 'warning': return 'text-yellow-500';
      default: return 'text-muted-foreground';
    }
  };

  const getLevelBg = (level: Log['level']) => {
    switch (level) {
      case 'success': return 'bg-profit/10';
      case 'error': return 'bg-loss/10';
      case 'warning': return 'bg-yellow-500/10';
      default: return 'bg-muted/30';
    }
  };

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }).format(date);
  };

  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-4">
        <FileText className="w-5 h-5 text-primary" />
        <h2 className="text-xl font-bold">System Logs</h2>
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-3 mb-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-card"
          />
        </div>
        <Select value={filterLevel} onValueChange={setFilterLevel}>
          <SelectTrigger className="w-full sm:w-[180px] bg-card">
            <Filter className="w-4 h-4 mr-2" />
            <SelectValue placeholder="Filter by level" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Levels</SelectItem>
            <SelectItem value="info">Info</SelectItem>
            <SelectItem value="success">Success</SelectItem>
            <SelectItem value="warning">Warning</SelectItem>
            <SelectItem value="error">Error</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon">
          <Download className="w-4 h-4" />
        </Button>
      </div>

      {/* Logs */}
      <ScrollArea className="h-96 w-full rounded-md border border-border">
        <div className="p-3 space-y-2">
          {filteredLogs.map((log) => (
            <div
              key={log.id}
              className={cn(
                "p-3 rounded-lg border border-border",
                getLevelBg(log.level)
              )}
            >
              <div className="flex items-start justify-between gap-2 mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-muted-foreground">
                    {formatTime(log.timestamp)}
                  </span>
                  <span className={cn(
                    "text-xs font-bold uppercase px-2 py-0.5 rounded",
                    getLevelColor(log.level)
                  )}>
                    {log.level}
                  </span>
                  <span className="text-xs font-medium text-primary">
                    [{log.category}]
                  </span>
                </div>
              </div>
              <p className="text-sm">{log.message}</p>
            </div>
          ))}
        </div>
      </ScrollArea>
    </Card>
  );
}
