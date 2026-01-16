"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { TrendingUp, TrendingDown, RefreshCw, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { fetchMarketDetail } from "@/lib/api/markets";
import type { MarketDetailData, PriceUpdate } from "@/types/market";
import { Skeleton } from "@/components/ui/skeleton";

// Refresh interval for modal data (2 seconds as per requirements)
const POLL_INTERVAL = 2000;

/**
 * Format price for display
 */
function formatPrice(price: number): string {
  return price.toFixed(2);
}

/**
 * Format percentage change
 */
function formatPercentage(change: number): string {
  const sign = change >= 0 ? "+" : "";
  return `${sign}${change.toFixed(2)}%`;
}

/**
 * Format timestamp for display
 */
function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  return date.toLocaleTimeString();
}

/**
 * Get trend badge styles
 */
function getTrendBadgeStyles(trend: string): string {
  switch (trend) {
    case "BULLISH":
      return "bg-green-500/20 text-green-600 border-green-500/30";
    case "BEARISH":
      return "bg-red-500/20 text-red-600 border-red-500/30";
    case "NEUTRAL":
      return "bg-gray-500/20 text-gray-600 border-gray-500/30";
    default:
      return "bg-gray-500/20 text-gray-600 border-gray-500/30";
  }
}

/**
 * Loading skeleton for market detail modal
 */
function MarketDetailSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header skeleton */}
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-5 w-48" />
        </div>
        <Skeleton className="h-12 w-12 rounded-full" />
      </div>

      {/* Price skeleton */}
      <div className="text-center py-6">
        <Skeleton className="h-16 w-48 mx-auto mb-2" />
        <Skeleton className="h-6 w-32 mx-auto" />
      </div>

      {/* Stats grid skeleton */}
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <Card key={i} className="p-4">
            <Skeleton className="h-4 w-20 mb-2" />
            <Skeleton className="h-6 w-16" />
          </Card>
        ))}
      </div>

      {/* Chart skeleton */}
      <Card className="p-4">
        <Skeleton className="h-4 w-24 mb-4" />
        <Skeleton className="h-48 w-full" />
      </Card>

      {/* Recent updates skeleton */}
      <Card className="p-4">
        <Skeleton className="h-4 w-32 mb-4" />
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <Skeleton key={i} className="h-10 w-full" />
          ))}
        </div>
      </Card>
    </div>
  );
}

/**
 * Simple sparkline chart component
 */
function SparklineChart({ data, isUp }: { data: number[]; isUp: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Set canvas size
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * 2;
    canvas.height = rect.height * 2;
    ctx.scale(2, 2);

    const width = rect.width;
    const height = rect.height;
    const padding = 10;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Calculate min and max values
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    // Calculate points
    const points = data.map((value, index) => {
      const x = padding + (index / (data.length - 1)) * (width - 2 * padding);
      const y = height - padding - ((value - min) / range) * (height - 2 * padding);
      return { x, y };
    });

    // Set line style
    ctx.strokeStyle = isUp ? "#10b981" : "#ef4444";
    ctx.lineWidth = 2;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    // Draw line
    ctx.beginPath();
    points.forEach((point, index) => {
      if (index === 0) {
        ctx.moveTo(point.x, point.y);
      } else {
        ctx.lineTo(point.x, point.y);
      }
    });
    ctx.stroke();

    // Fill area under line
    ctx.fillStyle = isUp ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)";
    ctx.beginPath();
    ctx.moveTo(points[0].x, height - padding);
    points.forEach((point) => {
      ctx.lineTo(point.x, point.y);
    });
    ctx.lineTo(points[points.length - 1].x, height - padding);
    ctx.closePath();
    ctx.fill();
  }, [data, isUp]);

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-48 rounded-lg"
      style={{ background: "rgba(0, 0, 0, 0.02)" }}
    />
  );
}

interface MarketDetailModalProps {
  /** Market symbol (e.g., "V10", "V25") */
  symbol: string;
  /** Whether the modal is open */
  open: boolean;
  /** Callback when modal is closed */
  onOpenChange: (open: boolean) => void;
}

export function MarketDetailModal({
  symbol,
  open,
  onOpenChange,
}: MarketDetailModalProps) {
  const [marketData, setMarketData] = useState<MarketDetailData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Fetch market detail data
  const fetchMarketData = useCallback(async () => {
    try {
      setError(null);
      setRefreshing(true);
      const data = await fetchMarketDetail(symbol);
      setMarketData(data.market);
      setLoading(false);
      setRefreshing(false);
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to fetch market data";
      setError(errorMessage);
      setLoading(false);
      setRefreshing(false);
    }
  }, [symbol]);

  // Initial fetch and polling setup
  useEffect(() => {
    if (!open) return;

    fetchMarketData();

    // Set up polling interval (2 seconds)
    const intervalId = setInterval(fetchMarketData, POLL_INTERVAL);

    return () => clearInterval(intervalId);
  }, [open, fetchMarketData]);

  // Reset state when modal closes
  useEffect(() => {
    if (!open) {
      setMarketData(null);
      setLoading(true);
      setError(null);
    }
  }, [open]);

  const isUp = marketData?.priceChangePercentage >= 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        {/* Header with close button */}
        <div className="flex items-start justify-between">
          <DialogHeader>
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-primary/20 rounded-full flex items-center justify-center">
                <span className="font-bold text-primary text-sm">
                  {symbol}
                </span>
              </div>
              <div>
                <DialogTitle className="text-xl">
                  {marketData?.displayName || symbol}
                </DialogTitle>
                {marketData && (
                  <Badge className={cn("mt-1", getTrendBadgeStyles(marketData.trend))}>
                    {marketData.trend}
                  </Badge>
                )}
              </div>
            </div>
          </DialogHeader>

          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={fetchMarketData}
              disabled={loading || refreshing}
              aria-label="Refresh"
            >
              <RefreshCw
                className={cn(
                  "h-4 w-4",
                  refreshing && "animate-spin"
                )}
              />
            </Button>
          </div>
        </div>

        {/* Content */}
        <div className="mt-6">
          {loading ? (
            <MarketDetailSkeleton />
          ) : error ? (
            <Card className="p-8">
              <div className="text-center">
                <p className="text-destructive mb-4">{error}</p>
                <Button onClick={fetchMarketData} variant="outline">
                  Retry
                </Button>
              </div>
            </Card>
          ) : marketData ? (
            <div className="space-y-6">
              {/* Current Price */}
              <div className="text-center py-6 bg-muted/50 rounded-lg">
                <p className="text-5xl font-bold mb-2">
                  {formatPrice(marketData.price)}
                </p>
                <div
                  className={cn(
                    "flex items-center justify-center gap-2 text-lg font-medium",
                    isUp ? "text-green-600" : "text-red-600"
                  )}
                >
                  {isUp ? (
                    <TrendingUp className="h-5 w-5" />
                  ) : (
                    <TrendingDown className="h-5 w-5" />
                  )}
                  <span>{formatPercentage(marketData.priceChangePercentage)}</span>
                </div>
              </div>

              {/* 24h Statistics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                <Card className="p-4">
                  <p className="text-xs text-muted-foreground mb-1">24h Open</p>
                  <p className="text-lg font-semibold">
                    {formatPrice(marketData.open24h)}
                  </p>
                </Card>
                <Card className="p-4">
                  <p className="text-xs text-muted-foreground mb-1">24h High</p>
                  <p className="text-lg font-semibold text-green-600">
                    {formatPrice(marketData.high24h)}
                  </p>
                </Card>
                <Card className="p-4">
                  <p className="text-xs text-muted-foreground mb-1">24h Low</p>
                  <p className="text-lg font-semibold text-red-600">
                    {formatPrice(marketData.low24h)}
                  </p>
                </Card>
                <Card className="p-4">
                  <p className="text-xs text-muted-foreground mb-1">24h Close</p>
                  <p className="text-lg font-semibold">
                    {formatPrice(marketData.close24h)}
                  </p>
                </Card>
              </div>

              {/* Additional Info */}
              <div className="grid grid-cols-2 gap-4">
                <Card className="p-4">
                  <p className="text-xs text-muted-foreground mb-1">
                    Market Spread
                  </p>
                  <p className="text-lg font-semibold">
                    {marketData.spread.toFixed(2)}
                  </p>
                </Card>
                <Card className="p-4">
                  <p className="text-xs text-muted-foreground mb-1">
                    Volatility Index
                  </p>
                  <p className="text-lg font-semibold">
                    {marketData.volatilityIndex}
                  </p>
                </Card>
              </div>

              {/* Price Chart */}
              <Card className="p-4">
                <p className="text-sm font-medium mb-4">Price Movement</p>
                <SparklineChart
                  data={[
                    marketData.close24h,
                    ...marketData.recentUpdates.slice(-9).map((u) => u.price),
                    marketData.price,
                  ]}
                  isUp={isUp}
                />
              </Card>

              {/* Recent Price Updates */}
              <Card className="p-4">
                <p className="text-sm font-medium mb-4">
                  Recent Price Updates (Last 10)
                </p>
                <div className="space-y-2">
                  {marketData.recentUpdates.map((update, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between py-2 px-3 rounded-lg bg-muted/50 text-sm"
                    >
                      <span className="font-mono font-medium">
                        {formatPrice(update.price)}
                      </span>
                      <div className="flex items-center gap-3">
                        <span
                          className={cn(
                            "font-medium",
                            update.change >= 0 ? "text-green-600" : "text-red-600"
                          )}
                        >
                          {update.change >= 0 ? "+" : ""}
                          {update.change.toFixed(2)}
                        </span>
                        <span className="text-muted-foreground text-xs">
                          {formatTime(update.timestamp)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </Card>

              {/* Market Status */}
              <div className="flex items-center justify-center py-2">
                <div
                  className={cn(
                    "flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium",
                    marketData.status === "open"
                      ? "bg-green-500/20 text-green-600"
                      : "bg-gray-500/20 text-gray-600"
                  )}
                >
                  <div
                    className={cn(
                      "w-2 h-2 rounded-full",
                      marketData.status === "open" ? "bg-green-500" : "bg-gray-500"
                    )}
                  />
                  <span>
                    Market {marketData.status === "open" ? "Open" : "Closed"}
                  </span>
                </div>
              </div>
            </div>
          ) : null}
        </div>

        {/* Close button */}
        <div className="flex justify-end mt-6">
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
