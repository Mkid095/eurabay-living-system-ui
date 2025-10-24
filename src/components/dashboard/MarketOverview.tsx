"use client";

import { Card } from "@/components/ui/card";
import { TrendingUp, TrendingDown } from "lucide-react";
import { cn } from "@/lib/utils";

interface MarketPair {
  name: string;
  symbol: string;
  price: number;
  change: number;
  volume: string;
}

export function MarketOverview() {
  const markets: MarketPair[] = [
    { name: 'BTC', symbol: 'Bitcoin', price: 57750, change: -0.24, volume: '857,750' },
    { name: 'ETH', symbol: 'Ethereum', price: 24800, change: 8.36, volume: '624,800' },
    { name: 'XRP', symbol: 'Ripple', price: 96250, change: -2.12, volume: '696,250' },
    { name: 'EUR/USD', symbol: 'Euro', price: 1.0892, change: 2.6, volume: '1.2M' },
    { name: 'GBP/USD', symbol: 'Pound', price: 1.2698, change: -1.8, volume: '890K' },
  ];

  return (
    <Card className="p-4 sm:p-6">
      <div className="mb-4">
        <h2 className="text-xl font-bold mb-1">Markets Overview</h2>
        <div className="flex gap-2">
          <button className="px-3 py-1 bg-primary text-primary-foreground rounded-full text-sm font-medium">
            Popular
          </button>
          <button className="px-3 py-1 bg-muted text-muted-foreground rounded-full text-sm font-medium hover:bg-muted/70">
            New Listing
          </button>
        </div>
      </div>

      <div className="space-y-3">
        {markets.map((market) => (
          <div
            key={market.name}
            className="flex items-center justify-between p-3 bg-muted/50 border border-border rounded-lg hover:border-primary/50 transition-colors cursor-pointer"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-primary/20 rounded-full flex items-center justify-center">
                <span className="font-bold text-primary text-sm">{market.name}</span>
              </div>
              <div>
                <p className="font-bold">{market.name}</p>
                <p className="text-xs text-muted-foreground">{market.symbol}</p>
              </div>
            </div>
            <div className="text-right">
              <p className="font-bold">
                {market.price < 100 ? market.price.toFixed(4) : market.price.toLocaleString()}
              </p>
              <div className={cn(
                "flex items-center gap-1 text-xs font-medium",
                market.change >= 0 ? "text-profit" : "text-loss"
              )}>
                {market.change >= 0 ? (
                  <TrendingUp className="w-3 h-3" />
                ) : (
                  <TrendingDown className="w-3 h-3" />
                )}
                <span>{Math.abs(market.change).toFixed(2)}%</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
