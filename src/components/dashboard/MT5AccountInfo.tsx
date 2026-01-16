"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardSkeleton } from "@/components/ui/loading-skeleton";
import { CompactErrorState } from "@/components/ui/error-state";
import { useMT5Connection } from "@/hooks/useMT5Connection";
import {
  Wallet,
  Building2,
  Coins,
  TrendingUp,
  Shield,
  ArrowUpRight,
  RefreshCw,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * MT5AccountInfo Component
 *
 * Displays comprehensive MT5 account information including:
 * - Account number, company, and currency
 * - Balance, equity, used margin, and free margin
 * - Margin level percentage with visual indicator
 * - Leverage ratio
 * - Auto-refresh every 5 seconds
 * - Loading skeleton during data fetch
 * - Error state with retry functionality
 */
export function MT5AccountInfo() {
  const {
    connectionState,
    connectionInfo,
    accountInfo,
    latency,
    isLoading,
    error,
    refreshStatus,
  } = useMT5Connection();

  const handleRefresh = async () => {
    await refreshStatus();
  };

  // Show loading skeleton
  if (isLoading || connectionState === "connecting") {
    return (
      <Card className="p-6">
        <div className="mb-4">
          <h3 className="text-lg font-semibold">MT5 Account</h3>
          <p className="text-sm text-muted-foreground">Loading account information...</p>
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
  if (error || connectionState === "error") {
    return (
      <Card className="p-6">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">MT5 Account</h3>
            <p className="text-sm text-muted-foreground">Unable to load account information</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </Button>
        </div>
        <CompactErrorState
          error={error || new Error("Connection to MT5 terminal failed")}
          onRetry={handleRefresh}
        />
      </Card>
    );
  }

  // Show disconnected state
  if (connectionState === "disconnected" || !accountInfo) {
    return (
      <Card className="p-6">
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-semibold mb-2">MT5 Not Connected</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Connect to MT5 terminal to view account information
          </p>
          <Button variant="outline" size="sm" onClick={handleRefresh} className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Check Connection
          </Button>
        </div>
      </Card>
    );
  }

  // Calculate margin level percentage for visual indicator
  const marginLevelPercent = Math.min((accountInfo.marginLevel / 100) * 100, 100);

  // Determine margin level status color
  const getMarginLevelColor = (level: number): string => {
    if (level < 100) return "text-destructive";
    if (level < 200) return "text-yellow-600 dark:text-yellow-500";
    return "text-green-600 dark:text-green-500";
  };

  // Format currency values
  const formatCurrency = (value: number, currency: string): string => {
    return `${value.toFixed(2)} ${currency}`;
  };

  return (
    <Card className="p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">MT5 Account</h3>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="outline" className="text-xs">
              {accountInfo.company}
            </Badge>
            {latency !== null && (
              <span className="text-xs text-muted-foreground">
                {latency}ms
              </span>
            )}
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleRefresh}
          className="gap-2"
        >
          <RefreshCw className="h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Account Info Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Account Number */}
        <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
          <div className="p-2 rounded-lg bg-primary/10">
            <Wallet className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-1">Account</p>
            <p className="text-lg font-semibold tabular-nums">
              {accountInfo.login}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {accountInfo.company}
            </p>
          </div>
        </div>

        {/* Balance */}
        <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
          <div className="p-2 rounded-lg bg-green-500/10">
            <Coins className="h-5 w-5 text-green-600 dark:text-green-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-1">Balance</p>
            <p className="text-lg font-semibold tabular-nums">
              {formatCurrency(accountInfo.balance, accountInfo.currency)}
            </p>
          </div>
        </div>

        {/* Equity */}
        <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
          <div className="p-2 rounded-lg bg-blue-500/10">
            <TrendingUp className="h-5 w-5 text-blue-600 dark:text-blue-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-1">Equity</p>
            <p className="text-lg font-semibold tabular-nums">
              {formatCurrency(accountInfo.equity, accountInfo.currency)}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              {accountInfo.profit >= 0 ? "+" : ""}
              {formatCurrency(accountInfo.profit, accountInfo.currency)} P&L
            </p>
          </div>
        </div>

        {/* Used Margin */}
        <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
          <div className="p-2 rounded-lg bg-orange-500/10">
            <Shield className="h-5 w-5 text-orange-600 dark:text-orange-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-1">Used Margin</p>
            <p className="text-lg font-semibold tabular-nums">
              {formatCurrency(accountInfo.margin, accountInfo.currency)}
            </p>
          </div>
        </div>

        {/* Free Margin */}
        <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
          <div className="p-2 rounded-lg bg-purple-500/10">
            <ArrowUpRight className="h-5 w-5 text-purple-600 dark:text-purple-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-1">Free Margin</p>
            <p className="text-lg font-semibold tabular-nums">
              {formatCurrency(accountInfo.freeMargin, accountInfo.currency)}
            </p>
          </div>
        </div>

        {/* Margin Level */}
        <div className="flex items-start gap-3 p-4 rounded-lg border bg-card">
          <div className="p-2 rounded-lg bg-cyan-500/10">
            <Building2 className="h-5 w-5 text-cyan-600 dark:text-cyan-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-1">Margin Level</p>
            <div className="flex items-baseline gap-2">
              <p
                className={cn(
                  "text-lg font-semibold tabular-nums",
                  getMarginLevelColor(accountInfo.marginLevel)
                )}
              >
                {accountInfo.marginLevel.toFixed(2)}%
              </p>
            </div>
            {/* Visual indicator bar */}
            <div className="mt-2 w-full h-2 bg-muted rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full transition-all duration-300",
                  accountInfo.marginLevel < 100
                    ? "bg-destructive"
                    : accountInfo.marginLevel < 200
                    ? "bg-yellow-600 dark:bg-yellow-500"
                    : "bg-green-600 dark:bg-green-500"
                )}
                style={{ width: `${marginLevelPercent}%` }}
              />
            </div>
          </div>
        </div>

        {/* Leverage */}
        <div className="flex items-start gap-3 p-4 rounded-lg border bg-card sm:col-span-2 lg:col-span-3">
          <div className="p-2 rounded-lg bg-indigo-500/10">
            <TrendingUp className="h-5 w-5 text-indigo-600 dark:text-indigo-500" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-muted-foreground mb-1">Leverage</p>
            <p className="text-lg font-semibold tabular-nums">
              1:{accountInfo.leverage}
            </p>
          </div>
        </div>
      </div>

      {/* Footer with connection status */}
      <div className="mt-4 pt-4 border-t flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <div
            className={cn(
              "w-2 h-2 rounded-full",
              connectionState === "connected" ? "bg-green-500" : "bg-red-500"
            )}
          />
          <span className="text-muted-foreground">
            {connectionState === "connected" ? "Connected" : "Disconnected"}
          </span>
        </div>
        {connectionInfo?.server && (
          <span className="text-muted-foreground">
            Server: {connectionInfo.server}
          </span>
        )}
      </div>
    </Card>
  );
}
