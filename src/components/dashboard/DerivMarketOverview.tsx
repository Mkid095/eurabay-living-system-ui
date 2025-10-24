"use client";

import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { TrendingUp, Activity } from "lucide-react";

interface MarketData {
  symbol: string;
  displayName: string;
  price: number;
  change24h: number;
  volume: number;
  spread: number;
  volatility: number;
  trend: 'BULLISH' | 'BEARISH' | 'SIDEWAYS';
}

interface DerivMarketOverviewProps {
  markets?: MarketData[];
}

export const DerivMarketOverview = ({ markets }: DerivMarketOverviewProps) => {
  // Default Deriv volatility indices
  const defaultMarkets: MarketData[] = [
    {
      symbol: 'V10',
      displayName: 'Volatility 10 Index',
      price: 1234.56,
      change24h: 2.3,
      volume: 15234,
      spread: 0.5,
      volatility: 10,
      trend: 'BULLISH'
    },
    {
      symbol: 'V25',
      displayName: 'Volatility 25 Index',
      price: 2345.67,
      change24h: -1.2,
      volume: 12456,
      spread: 1.2,
      volatility: 25,
      trend: 'BEARISH'
    },
    {
      symbol: 'V50',
      displayName: 'Volatility 50 Index',
      price: 3456.78,
      change24h: 0.5,
      volume: 9876,
      spread: 2.5,
      volatility: 50,
      trend: 'SIDEWAYS'
    },
    {
      symbol: 'V75',
      displayName: 'Volatility 75 Index',
      price: 4567.89,
      change24h: 3.1,
      volume: 7654,
      spread: 3.7,
      volatility: 75,
      trend: 'BULLISH'
    },
    {
      symbol: 'V100',
      displayName: 'Volatility 100 Index',
      price: 5678.90,
      change24h: -0.8,
      volume: 5432,
      spread: 5.0,
      volatility: 100,
      trend: 'SIDEWAYS'
    },
  ];

  const displayMarkets = markets || defaultMarkets;

  const getTrendBadge = (trend: string) => {
    switch (trend) {
      case 'BULLISH':
        return 'bg-profit/20 text-profit border-profit/30';
      case 'BEARISH':
        return 'bg-loss/20 text-loss border-loss/30';
      case 'SIDEWAYS':
        return 'bg-muted text-muted-foreground border-border';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">Deriv Markets</h3>
          <p className="text-sm text-muted-foreground">Volatility Indices</p>
        </div>
        <Activity className="w-5 h-5 text-primary" />
      </div>

      <div className="space-y-4">
        {displayMarkets.map((market) => (
          <div key={market.symbol} className="p-4 rounded-lg bg-card border border-border hover:bg-accent/5 transition-colors">
            <div className="flex items-start justify-between mb-2">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-semibold">{market.symbol}</h4>
                  <Badge className={getTrendBadge(market.trend)}>
                    {market.trend}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">{market.displayName}</p>
              </div>
              <div className="text-right">
                <p className="font-mono font-semibold">{market.price.toFixed(2)}</p>
                <p className={`text-xs font-medium ${market.change24h >= 0 ? 'text-profit' : 'text-loss'}`}>
                  {market.change24h >= 0 ? '+' : ''}{market.change24h.toFixed(2)}%
                </p>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-border">
              <div>
                <p className="text-xs text-muted-foreground">Spread</p>
                <p className="text-sm font-medium">{market.spread.toFixed(1)}</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Volume</p>
                <p className="text-sm font-medium">{(market.volume / 1000).toFixed(1)}K</p>
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Vol Index</p>
                <p className="text-sm font-medium">{market.volatility}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};
