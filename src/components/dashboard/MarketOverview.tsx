"use client";

import { Card } from "@/components/ui/card";
import { TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEffect, useState, useCallback, useRef } from "react";
import { fetchMarketsOverview, fetchMarketTrend } from "@/lib/api/markets";
import type { MarketOverviewData, FlashState, MarketTrendData } from "@/types/market";
import { wsClient } from "@/lib/websocket/client";
import type { MarketUpdateEvent } from "@/types/market";
import { MarketDetailModal } from "@/components/dashboard/MarketDetailModal";
import { TrendBadge } from "@/components/dashboard/TrendBadge";

// Refresh interval for polling (3 seconds as per requirements)
const POLL_INTERVAL = 3000;

// Trend data refresh interval (10 seconds as per requirements)
const TREND_REFRESH_INTERVAL = 10000;

// Flash animation duration (ms)
const FLASH_DURATION = 500;

/**
 * Format price for display based on value
 */
function formatPrice(price: number): string {
  // For volatility indices, show 2 decimal places
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
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSecs = Math.floor(diffMs / 1000);

  if (diffSecs < 60) {
    return `${diffSecs}s ago`;
  } else if (diffSecs < 3600) {
    return `${Math.floor(diffSecs / 60)}m ago`;
  } else {
    return date.toLocaleTimeString();
  }
}

export function MarketOverview() {
  const [markets, setMarkets] = useState<MarketOverviewData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [flashStates, setFlashStates] = useState<Record<string, FlashState>>({});
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date());

  // Trend data state
  const [trends, setTrends] = useState<Record<string, MarketTrendData>>({});
  const [trendsLoading, setTrendsLoading] = useState<Record<string, boolean>>({});
  const [trendsError, setTrendsError] = useState<Record<string, string | null>>({});

  // Modal state
  const [selectedMarket, setSelectedMarket] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Track previous prices to determine flash direction
  const previousPricesRef = useRef<Record<string, number>>({});

  // Handle market card click to open detail modal
  const handleMarketClick = useCallback((symbol: string) => {
    setSelectedMarket(symbol);
    setIsModalOpen(true);
  }, []);

  // Handle modal close
  const handleModalClose = useCallback(() => {
    setIsModalOpen(false);
    setSelectedMarket(null);
  }, []);

  // Fetch markets data
  const fetchMarkets = useCallback(async () => {
    try {
      setError(null);
      const data = await fetchMarketsOverview();

      // Determine flash states based on price changes
      const newFlashStates: Record<string, FlashState> = {};
      data.markets.forEach((market) => {
        const previousPrice = previousPricesRef.current[market.symbol];
        if (previousPrice !== undefined && previousPrice !== market.price) {
          newFlashStates[market.symbol] = market.price > previousPrice ? 'up' : 'down';
        }
        previousPricesRef.current[market.symbol] = market.price;
      });

      setMarkets(data.markets);
      setFlashStates(newFlashStates);
      setLastUpdate(new Date());

      // Clear flash states after animation
      if (Object.keys(newFlashStates).length > 0) {
        setTimeout(() => {
          setFlashStates({});
        }, FLASH_DURATION);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch market data';
      setError(errorMessage);
      console.error('Error fetching markets:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch trend data for a single market
  const fetchMarketTrendData = useCallback(async (symbol: string) => {
    try {
      setTrendsLoading((prev) => ({ ...prev, [symbol]: true }));
      setTrendsError((prev) => ({ ...prev, [symbol]: null }));

      const data = await fetchMarketTrend(symbol);
      setTrends((prev) => ({ ...prev, [symbol]: data.trend }));
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch trend data';
      setTrendsError((prev) => ({ ...prev, [symbol]: errorMessage }));
      console.error(`Error fetching trend for ${symbol}:`, err);
    } finally {
      setTrendsLoading((prev) => ({ ...prev, [symbol]: false }));
    }
  }, []);

  // Fetch trend data for all markets
  const fetchAllTrends = useCallback(async () => {
    // Only fetch if we have markets loaded
    if (markets.length === 0) return;

    // Fetch trends for each market in parallel
    await Promise.all(
      markets.map((market) => fetchMarketTrendData(market.symbol))
    );
  }, [markets, fetchMarketTrendData]);

  // Handle WebSocket market update events
  const handleMarketUpdate = useCallback((event: MarketUpdateEvent) => {
    setMarkets((prevMarkets) => {
      const updated = prevMarkets.map((market) => {
        if (market.symbol !== event.symbol) {
          return market;
        }

        // Determine flash direction based on price change
        const previousPrice = previousPricesRef.current[event.symbol];
        let flashState: FlashState = null;

        if (previousPrice !== undefined && previousPrice !== event.bid) {
          flashState = event.bid > previousPrice ? 'up' : 'down';
        }

        previousPricesRef.current[event.symbol] = event.bid;

        // Set flash state
        if (flashState) {
          setFlashStates((prev) => ({ ...prev, [event.symbol]: flashState }));
          setTimeout(() => {
            setFlashStates((prev) => {
              const next = { ...prev };
              delete next[event.symbol];
              return next;
            });
          }, FLASH_DURATION);
        }

        // Update market with WebSocket data
        return {
          ...market,
          price: event.bid,
          priceChange: event.priceChange,
          priceChangePercentage: event.priceChangePercentage,
          high24h: Math.max(market.high24h, event.bid),
          low24h: Math.min(market.low24h, event.bid),
          timestamp: event.timestamp,
        };
      });

      setLastUpdate(new Date());
      return updated;
    });
  }, []);

  // Initial fetch and polling setup
  useEffect(() => {
    fetchMarkets();

    // Set up polling interval (3 seconds)
    const intervalId = setInterval(fetchMarkets, POLL_INTERVAL);

    return () => clearInterval(intervalId);
  }, [fetchMarkets]);

  // Trend data refresh setup (10 seconds)
  useEffect(() => {
    // Initial fetch after markets are loaded
    if (markets.length > 0) {
      fetchAllTrends();
    }

    // Set up trend refresh interval (10 seconds)
    const intervalId = setInterval(fetchAllTrends, TREND_REFRESH_INTERVAL);

    return () => clearInterval(intervalId);
  }, [markets, fetchAllTrends]);

  // WebSocket subscription for real-time updates
  useEffect(() => {
    // Subscribe to market_update events
    const unsubscribe = wsClient.on<MarketUpdateEvent>(
      'market_update',
      handleMarketUpdate
    );

    return () => {
      unsubscribe();
    };
  }, [handleMarketUpdate]);

  // Render loading skeleton
  if (loading) {
    return (
      <Card className="p-4 sm:p-6">
        <div className="mb-4">
          <h2 className="text-xl font-bold mb-1">Markets Overview</h2>
          <div className="flex gap-2">
            <div className="h-7 w-20 bg-muted rounded-full animate-pulse" />
            <div className="h-7 w-24 bg-muted rounded-full animate-pulse" />
          </div>
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div
              key={i}
              className="flex items-center justify-between p-3 bg-muted/50 border border-border rounded-lg"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-muted rounded-full animate-pulse" />
                <div>
                  <div className="h-4 w-12 bg-muted rounded animate-pulse mb-1" />
                  <div className="h-3 w-20 bg-muted rounded animate-pulse" />
                </div>
              </div>
              <div className="text-right">
                <div className="h-4 w-16 bg-muted rounded animate-pulse mb-1" />
                <div className="h-3 w-12 bg-muted rounded animate-pulse" />
              </div>
            </div>
          ))}
        </div>
      </Card>
    );
  }

  // Render error state
  if (error) {
    return (
      <Card className="p-4 sm:p-6">
        <div className="mb-4">
          <h2 className="text-xl font-bold mb-1">Markets Overview</h2>
        </div>
        <div className="flex flex-col items-center justify-center py-8">
          <p className="text-destructive mb-4">{error}</p>
          <button
            onClick={fetchMarkets}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            Retry
          </button>
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-4 sm:p-6">
      <div className="mb-4">
        <div className="flex items-center justify-between mb-1">
          <h2 className="text-xl font-bold">Volatility Indices</h2>
          <span className="text-xs text-muted-foreground">
            Updated {formatTimestamp(lastUpdate.toISOString())}
          </span>
        </div>
        <div className="flex gap-2">
          <button className="px-3 py-1 bg-primary text-primary-foreground rounded-full text-sm font-medium">
            All Markets
          </button>
          <button className="px-3 py-1 bg-muted text-muted-foreground rounded-full text-sm font-medium hover:bg-muted/70">
            Volatility 10
          </button>
          <button className="px-3 py-1 bg-muted text-muted-foreground rounded-full text-sm font-medium hover:bg-muted/70">
            Volatility 100
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {markets.map((market) => {
          const flashState = flashStates[market.symbol];
          const isUp = market.priceChangePercentage >= 0;
          const trendData = trends[market.symbol];
          const trendLoading = trendsLoading[market.symbol];

          return (
            <div
              key={market.symbol}
              onClick={() => handleMarketClick(market.symbol)}
              className={cn(
                "flex items-center justify-between p-3 bg-muted/50 border border-border rounded-lg hover:border-primary/50 transition-all cursor-pointer",
                flashState === 'up' && "bg-green-500/10",
                flashState === 'down' && "bg-red-500/10"
              )}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-primary/20 rounded-full flex items-center justify-center">
                  <span className="font-bold text-primary text-xs">{market.symbol}</span>
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <p className="font-bold text-sm">{market.symbol}</p>
                    {trendData && (
                      <TrendBadge
                        trend={trendData.trend}
                        strength={trendData.strength}
                        priceHistory={trendData.priceHistory}
                        confidence={trendData.confidence}
                      />
                    )}
                    {trendLoading && (
                      <div className="w-16 h-5 bg-muted/50 rounded animate-pulse" />
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground">{market.displayName}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="font-bold text-sm">
                  {formatPrice(market.price)}
                </p>
                <div className={cn(
                  "flex items-center gap-1 text-xs font-medium justify-end",
                  isUp ? "text-green-500" : "text-red-500"
                )}>
                  {isUp ? (
                    <TrendingUp className="w-3 h-3" />
                  ) : (
                    <TrendingDown className="w-3 h-3" />
                  )}
                  <span>{formatPercentage(market.priceChangePercentage)}</span>
                </div>
              </div>
              <div className="text-right text-xs text-muted-foreground ml-4 hidden sm:block">
                <p>H: {formatPrice(market.high24h)}</p>
                <p>L: {formatPrice(market.low24h)}</p>
              </div>
              <div className="ml-2">
                <div className={cn(
                  "w-2 h-2 rounded-full",
                  market.status === 'open' ? "bg-green-500" : "bg-gray-400"
                )} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Market Detail Modal */}
      {selectedMarket && (
        <MarketDetailModal
          symbol={selectedMarket}
          open={isModalOpen}
          onOpenChange={setIsModalOpen}
        />
      )}
    </Card>
  );
}
