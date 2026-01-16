"use client";

import React, { useState, useMemo, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Check,
  X,
  Clock,
  TrendingUp,
  TrendingDown,
  RefreshCw,
  AlertCircle,
  Filter,
  ArrowUpDown,
  LucideIcon,
} from "lucide-react";
import { usePendingSignals } from "@/hooks/usePendingSignals";
import type { PendingSignal, SignalType } from "@/types/evolution";
import { toast } from "sonner";
import { cn } from "@/lib/utils";

type FilterSymbol = "all" | string;
type SortBy = "confidence" | "time";
type SortOrder = "asc" | "desc";

const SIGNAL_TYPE_COLORS: Record<SignalType, { className: string; icon: LucideIcon }> = {
  STRONG_BUY: { className: "bg-profit/20 text-profit border-profit/20", icon: TrendingUp },
  BUY: { className: "bg-profit/10 text-profit border-profit/10", icon: TrendingUp },
  SELL: { className: "bg-loss/10 text-loss border-loss/10", icon: TrendingDown },
  STRONG_SELL: { className: "bg-loss/20 text-loss border-loss/20", icon: TrendingDown },
};

export function PendingSignals() {
  const {
    signals,
    isLoading,
    error,
    refreshSignals,
    approveSignal,
    rejectSignal,
    approveAllSignals,
    rejectAllSignals,
  } = usePendingSignals();

  const [filterSymbol, setFilterSymbol] = useState<FilterSymbol>("all");
  const [sortBy, setSortBy] = useState<SortBy>("confidence");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  const uniqueSymbols = useMemo(() => {
    return Array.from(new Set(signals.map((s) => s.symbol))).sort();
  }, [signals]);

  const filteredAndSortedSignals = useMemo(() => {
    let filtered = signals;

    if (filterSymbol !== "all") {
      filtered = filtered.filter((s) => s.symbol === filterSymbol);
    }

    const sorted = [...filtered].sort((a, b) => {
      let comparison = 0;

      if (sortBy === "confidence") {
        comparison = a.confidence - b.confidence;
      } else if (sortBy === "time") {
        comparison = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
      }

      return sortOrder === "asc" ? comparison : -comparison;
    });

    return sorted;
  }, [signals, filterSymbol, sortBy, sortOrder]);

  const handleApprove = useCallback(
    async (signal: PendingSignal) => {
      try {
        await approveSignal(signal.id);
        toast.success(`Approved ${signal.signalType} signal for ${signal.symbol}`);
      } catch {
        toast.error(`Failed to approve signal for ${signal.symbol}`);
      }
    },
    [approveSignal]
  );

  const handleReject = useCallback(
    async (signal: PendingSignal) => {
      try {
        await rejectSignal(signal.id);
        toast.success(`Rejected ${signal.signalType} signal for ${signal.symbol}`);
      } catch {
        toast.error(`Failed to reject signal for ${signal.symbol}`);
      }
    },
    [rejectSignal]
  );

  const handleApproveAll = useCallback(async () => {
    try {
      await approveAllSignals();
      toast.success(`Approved all ${signals.length} signals`);
    } catch {
      toast.error("Failed to approve some signals");
    }
  }, [approveAllSignals, signals.length]);

  const handleRejectAll = useCallback(async () => {
    try {
      await rejectAllSignals();
      toast.success(`Rejected all ${signals.length} signals`);
    } catch {
      toast.error("Failed to reject some signals");
    }
  }, [rejectAllSignals, signals.length]);

  const toggleSortOrder = useCallback(() => {
    setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
  }, []);

  const formatTimestamp = (timestamp: string): string => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const minutes = Math.floor(diffMs / 60000);
    const hours = Math.floor(minutes / 60);

    if (hours > 0) {
      return `${hours}h ${minutes % 60}m ago`;
    }
    return `${minutes}m ago`;
  };

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="mb-6">
          <Skeleton className="h-6 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <div className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="w-12 h-12 text-destructive mb-4" />
          <h3 className="text-lg font-semibold mb-2">Failed to Load Pending Signals</h3>
          <p className="text-sm text-muted-foreground mb-4">{error.message}</p>
          <Button onClick={refreshSignals} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold">Pending Signals</h3>
          <p className="text-sm text-muted-foreground">
            Review and approve or reject trading signals
          </p>
        </div>
        <Button onClick={refreshSignals} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          Refresh
        </Button>
      </div>

      <div className="mb-4 flex flex-col sm:flex-row gap-3">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <Select value={filterSymbol} onValueChange={(value) => setFilterSymbol(value as FilterSymbol)}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Filter by symbol" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Symbols</SelectItem>
              {uniqueSymbols.map((symbol) => (
                <SelectItem key={symbol} value={symbol}>
                  {symbol}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="flex items-center gap-2">
          <ArrowUpDown className="w-4 h-4 text-muted-foreground" />
          <Select value={sortBy} onValueChange={(value) => setSortBy(value as SortBy)}>
            <SelectTrigger className="w-[140px]">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="confidence">Confidence</SelectItem>
              <SelectItem value="time">Time</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="sm"
            onClick={toggleSortOrder}
            className="px-2"
            title={`Sort ${sortOrder === "asc" ? "ascending" : "descending"}`}
          >
            {sortOrder === "asc" ? "A-Z" : "Z-A"}
          </Button>
        </div>

        {signals.length > 1 && (
          <div className="flex gap-2 ml-auto">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="sm" className="bg-profit hover:bg-profit/90 text-white">
                  Approve All
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Approve All Signals?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will approve all {signals.length} pending signals and execute trades for each.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={handleApproveAll} className="bg-profit hover:bg-profit/90">
                    Approve All
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>

            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button size="sm" variant="outline" className="border-loss text-loss hover:bg-loss/10">
                  Reject All
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Reject All Signals?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This will reject all {signals.length} pending signals.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                  <AlertDialogAction onClick={handleRejectAll} className="bg-loss hover:bg-loss/90">
                    Reject All
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {filteredAndSortedSignals.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <Clock className="w-12 h-12 mx-auto mb-4 opacity-50" />
            <p>No pending signals</p>
          </div>
        ) : (
          filteredAndSortedSignals.map((signal) => {
            const typeConfig = SIGNAL_TYPE_COLORS[signal.signalType];
            const Icon = typeConfig.icon;

            return (
              <div
                key={signal.id}
                className="p-4 bg-muted/30 border border-border rounded-lg hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="font-bold text-lg">{signal.symbol}</span>
                      <Badge className={typeConfig.className}>
                        <typeConfig.icon className="w-3 h-3 mr-1" />
                        {signal.signalType}
                      </Badge>
                      <Badge variant="outline" className="text-xs">
                        ID: {signal.id}
                      </Badge>
                    </div>
                    <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {formatTimestamp(signal.timestamp)}
                      </span>
                      <span>HTF: {signal.htfContext}</span>
                    </div>
                  </div>
                  <div className="w-24">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-muted-foreground">Confidence</span>
                      <span className="text-sm font-medium">
                        {(signal.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                    <Progress value={signal.confidence * 100} className="h-1.5" />
                  </div>
                </div>

                {signal.featuresUsed.length > 0 && (
                  <div className="mb-3 flex flex-wrap gap-1">
                    {signal.featuresUsed.map((feature, idx) => (
                      <Badge key={idx} variant="outline" className="text-xs">
                        {feature}
                      </Badge>
                    ))}
                  </div>
                )}

                <div className="flex gap-2">
                  <Button
                    size="sm"
                    className="flex-1 bg-profit hover:bg-profit/90 text-white"
                    onClick={() => handleApprove(signal)}
                  >
                    <Check className="w-4 h-4 mr-1" />
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1 border-loss text-loss hover:bg-loss/10"
                    onClick={() => handleReject(signal)}
                  >
                    <X className="w-4 h-4 mr-1" />
                    Reject
                  </Button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}
