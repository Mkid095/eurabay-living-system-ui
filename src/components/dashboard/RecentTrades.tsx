"use client";

import { useState, useCallback, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  TrendingUp,
  TrendingDown,
  History,
  Download,
  RefreshCw,
  AlertCircle,
  Search,
  Shield,
  Target,
  Clock,
} from "lucide-react";
import { useRecentTrades, type DateRange, type OutcomeFilter } from "@/hooks/useRecentTrades";
import { TradeDetailModal } from "./TradeDetailModal";
import type { ClosedTrade } from "@/types/evolution";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export function RecentTrades() {
  const [symbolFilter, setSymbolFilter] = useState<string>("all");
  const [outcomeFilter, setOutcomeFilter] = useState<OutcomeFilter>("all");
  const [dateRange, setDateRange] = useState<DateRange>("all");
  const [searchTicket, setSearchTicket] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [selectedTrade, setSelectedTrade] = useState<ClosedTrade | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const {
    trades,
    isLoading,
    error,
    totalCount,
    currentPage,
    pageSize,
    totalPages,
    refreshTrades,
    setFilters,
    setPage,
  } = useRecentTrades({
    symbol: symbolFilter,
    outcome: outcomeFilter,
    dateRange,
    searchTicket: debouncedSearch,
    page: 1,
    pageSize: 20,
  });

  // Debounce search input
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setDebouncedSearch(searchTicket);
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchTicket]);

  const handleRowClick = useCallback((trade: ClosedTrade) => {
    setSelectedTrade(trade);
    setIsModalOpen(true);
  }, []);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      // Export current filtered data to CSV
      const headers = ['Ticket', 'Symbol', 'Side', 'Entry Price', 'Exit Price', 'P&L', 'P&L %', 'Entry Time', 'Exit Time', 'Duration', 'HTF Context', 'LTF Context'];
      const csvRows = [headers.join(',')];

      trades.forEach(trade => {
        const row = [
          trade.ticket,
          trade.symbol,
          trade.side,
          trade.entryPrice.toFixed(5),
          trade.exitPrice.toFixed(5),
          trade.pnl.toFixed(2),
          trade.pnlPercent.toFixed(2),
          trade.entryTime,
          trade.exitTime,
          trade.duration,
          trade.htfContext,
          trade.ltfContext,
        ];
        csvRows.push(row.join(','));
      });

      const csv = csvRows.join('\n');
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `recent_trades_${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      toast.success('Trades exported to CSV successfully');
    } catch (error) {
      toast.error(
        `Failed to export trades: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    } finally {
      setIsExporting(false);
    }
  };

  // Update filters when they change
  const handleSymbolChange = (value: string) => {
    setSymbolFilter(value);
    setFilters({ symbol: value });
  };

  const handleOutcomeChange = (value: string) => {
    const outcome = value as OutcomeFilter;
    setOutcomeFilter(outcome);
    setFilters({ outcome });
  };

  const handleDateRangeChange = (value: string) => {
    const range = value as DateRange;
    setDateRange(range);
    setFilters({ dateRange: range });
  };

  const handleSearchChange = (value: string) => {
    setSearchTicket(value);
  };

  // Get unique symbols from trades for filter
  const availableSymbols = Array.from(new Set(trades.map(t => t.symbol))).sort();

  if (isLoading) {
    return (
      <Card className="p-4 sm:p-6">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-5" />
            <Skeleton className="h-6 w-40" />
          </div>
          <div className="flex items-center gap-2">
            <Skeleton className="h-9 w-24" />
            <Skeleton className="h-9 w-20" />
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 mb-4">
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
          <Skeleton className="h-9 w-full" />
        </div>

        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-16 w-full" />
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
          <h3 className="text-lg font-semibold mb-2">Failed to Load Recent Trades</h3>
          <p className="text-sm text-muted-foreground mb-4">{error.message}</p>
          <Button onClick={refreshTrades} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card className="p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-4">
          <div className="flex items-center gap-2">
            <History className="w-5 h-5 text-primary" />
            <h2 className="text-xl font-bold">Recent Trades</h2>
            <span className="text-sm text-muted-foreground">
              ({totalCount} total)
            </span>
          </div>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <Button
              size="sm"
              variant="outline"
              onClick={refreshTrades}
              className="flex-shrink-0"
            >
              <RefreshCw className="w-4 h-4" />
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleExport}
              disabled={isExporting || trades.length === 0}
              className="flex-shrink-0"
            >
              <Download className="w-4 h-4" />
              Export
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          {/* Symbol Filter */}
          <Select value={symbolFilter} onValueChange={handleSymbolChange}>
            <SelectTrigger size="sm">
              <SelectValue placeholder="Symbol" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Symbols</SelectItem>
              {availableSymbols.map((symbol) => (
                <SelectItem key={symbol} value={symbol}>
                  {symbol}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Outcome Filter */}
          <Select value={outcomeFilter} onValueChange={handleOutcomeChange}>
            <SelectTrigger size="sm">
              <SelectValue placeholder="Outcome" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Outcomes</SelectItem>
              <SelectItem value="profit">Profit Only</SelectItem>
              <SelectItem value="loss">Loss Only</SelectItem>
            </SelectContent>
          </Select>

          {/* Date Range Filter */}
          <Select value={dateRange} onValueChange={handleDateRangeChange}>
            <SelectTrigger size="sm">
              <SelectValue placeholder="Date Range" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Time</SelectItem>
              <SelectItem value="today">Today</SelectItem>
              <SelectItem value="week">Last 7 Days</SelectItem>
              <SelectItem value="month">Last 30 Days</SelectItem>
            </SelectContent>
          </Select>

          {/* Search by Ticket ID */}
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search ticket..."
              value={searchTicket}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-8"
            />
          </div>
        </div>

        {/* Trades Table */}
        {trades.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            No trades found matching the current filters
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                    Ticket
                  </th>
                  <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                    Symbol
                  </th>
                  <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                    Side
                  </th>
                  <th className="text-right py-3 px-2 text-sm font-medium text-muted-foreground">
                    Entry
                  </th>
                  <th className="text-right py-3 px-2 text-sm font-medium text-muted-foreground">
                    Exit
                  </th>
                  <th className="text-right py-3 px-2 text-sm font-medium text-muted-foreground">
                    P&L
                  </th>
                  <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                    SL/TP
                  </th>
                  <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                    Entry
                  </th>
                  <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                    Exit
                  </th>
                  <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                    Duration
                  </th>
                  <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                    Context
                  </th>
                  <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                    Features
                  </th>
                  <th className="text-left py-3 px-2 text-sm font-medium text-muted-foreground">
                    Confidence
                  </th>
                </tr>
              </thead>
              <tbody>
                {trades.map((trade) => (
                  <tr
                    key={trade.ticket}
                    className="border-b border-border hover:bg-accent/5 cursor-pointer transition-colors"
                    onClick={() => handleRowClick(trade)}
                  >
                    <td className="py-3 px-2">
                      <span className="font-mono text-sm">{trade.ticket}</span>
                    </td>
                    <td className="py-3 px-2">
                      <span className="font-medium">{trade.symbol}</span>
                    </td>
                    <td className="py-3 px-2">
                      <Badge
                        className={
                          trade.side === "BUY"
                            ? "bg-profit/20 text-profit"
                            : "bg-loss/20 text-loss"
                        }
                      >
                        {trade.side === "BUY" ? (
                          <TrendingUp className="w-3 h-3 mr-1" />
                        ) : (
                          <TrendingDown className="w-3 h-3 mr-1" />
                        )}
                        {trade.side}
                      </Badge>
                    </td>
                    <td className="py-3 px-2 text-right font-mono text-sm">
                      {trade.entryPrice.toFixed(5)}
                    </td>
                    <td className="py-3 px-2 text-right font-mono text-sm">
                      {trade.exitPrice.toFixed(5)}
                    </td>
                    <td className="py-3 px-2 text-right">
                      <div className="space-y-1">
                        <span
                          className={
                            trade.pnl >= 0
                              ? "text-profit font-semibold"
                              : "text-loss font-semibold"
                          }
                        >
                          {trade.pnl >= 0 ? "+" : ""}
                          {formatCurrency(trade.pnl)}
                        </span>
                        <div className="text-xs text-muted-foreground">
                          ({trade.pnlPercent >= 0 ? "+" : ""}
                          {trade.pnlPercent.toFixed(2)}%)
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-2">
                      <div className="flex gap-1">
                        {trade.stopLoss && (
                          <div
                            className={cn(
                              "flex items-center gap-1 text-xs",
                              trade.stopLossHit ? "text-loss" : "text-muted-foreground"
                            )}
                            title="Stop Loss"
                          >
                            <Shield className="w-3 h-3" />
                            {trade.stopLoss.toFixed(5)}
                            {trade.stopLossHit && "!"}
                          </div>
                        )}
                        {trade.takeProfit && (
                          <div
                            className={cn(
                              "flex items-center gap-1 text-xs",
                              trade.takeProfitHit ? "text-profit" : "text-muted-foreground"
                            )}
                            title="Take Profit"
                          >
                            <Target className="w-3 h-3" />
                            {trade.takeProfit.toFixed(5)}
                            {trade.takeProfitHit && "!"}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-2 text-xs text-muted-foreground">
                      {formatDate(trade.entryTime)}
                    </td>
                    <td className="py-3 px-2 text-xs text-muted-foreground">
                      {formatDate(trade.exitTime)}
                    </td>
                    <td className="py-3 px-2">
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <Clock className="w-3 h-3" />
                        {trade.duration}
                      </div>
                    </td>
                    <td className="py-3 px-2">
                      <div className="space-y-1">
                        <div className="text-xs">
                          <span className="text-muted-foreground">HTF:</span>{" "}
                          <span className="font-medium">{trade.htfContext}</span>
                        </div>
                        <div className="text-xs">
                          <span className="text-muted-foreground">LTF:</span>{" "}
                          <span className="font-medium">{trade.ltfContext}</span>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 px-2">
                      <div className="flex flex-wrap gap-1 max-w-[150px]">
                        {trade.featuresUsed.slice(0, 2).map((feature, idx) => (
                          <Badge key={idx} variant="outline" className="text-xs">
                            {feature}
                          </Badge>
                        ))}
                        {trade.featuresUsed.length > 2 && (
                          <Badge variant="outline" className="text-xs">
                            +{trade.featuresUsed.length - 2}
                          </Badge>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-2">
                      <div className="w-16">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs text-muted-foreground">
                            {(trade.confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary"
                            style={{ width: `${trade.confidence * 100}%` }}
                          />
                        </div>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="mt-4 flex justify-center">
            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    onClick={() => setPage(Math.max(1, currentPage - 1))}
                    className={currentPage === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"}
                  />
                </PaginationItem>
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                  <PaginationItem key={page}>
                    <PaginationLink
                      onClick={() => setPage(page)}
                      isActive={page === currentPage}
                      className="cursor-pointer"
                    >
                      {page}
                    </PaginationLink>
                  </PaginationItem>
                ))}
                <PaginationItem>
                  <PaginationNext
                    onClick={() => setPage(Math.min(totalPages, currentPage + 1))}
                    className={currentPage === totalPages ? "pointer-events-none opacity-50" : "cursor-pointer"}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          </div>
        )}
      </Card>

      <TradeDetailModal
        trade={selectedTrade}
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
      />
    </>
  );
}
