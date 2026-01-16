"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Target,
  Calendar,
  Settings,
  History,
  DollarSign,
  Activity,
  AlertCircle,
  X,
} from "lucide-react";
import { fetchFeatureDetails } from "@/lib/api/evolution";
import type { FeatureDetail, FeatureSuccess } from "@/types/evolution";

interface FeatureDetailModalProps {
  feature: FeatureSuccess | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

// Helper function to get trend color and icon
function getTrendDisplay(trend?: 'improving' | 'declining' | 'stable', trendPercent?: number) {
  if (trend === 'improving') {
    return {
      icon: TrendingUp,
      color: 'text-profit',
      bgColor: 'bg-profit/10',
      label: 'Improving'
    };
  }
  if (trend === 'declining') {
    return {
      icon: TrendingDown,
      color: 'text-loss',
      bgColor: 'bg-loss/10',
      label: 'Declining'
    };
  }
  return {
    icon: Minus,
    color: 'text-muted-foreground',
    bgColor: 'bg-muted',
    label: 'Stable'
  };
}

// Helper function to get success rate color
function getSuccessRateColor(successRate: number): string {
  if (successRate > 70) return 'text-profit';
  if (successRate >= 40) return 'text-warning';
  return 'text-loss';
}

function getSuccessRateBgColor(successRate: number): string {
  if (successRate > 70) return 'bg-profit/10';
  if (successRate >= 40) return 'bg-warning/10';
  return 'bg-loss/10';
}

export function FeatureDetailModal({
  feature,
  open,
  onOpenChange,
}: FeatureDetailModalProps) {
  const [featureDetails, setFeatureDetails] = useState<FeatureDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Fetch feature details when modal opens
  useEffect(() => {
    if (open && feature?.featureId) {
      setLoading(true);
      setError(null);
      fetchFeatureDetails(feature.featureId)
        .then((data) => {
          setFeatureDetails(data);
        })
        .catch((err) => {
          console.error('Failed to fetch feature details:', err);
          setError('Failed to load feature details');
        })
        .finally(() => {
          setLoading(false);
        });
    }
  }, [open, feature?.featureId]);

  if (!feature) return null;

  const trendDisplay = getTrendDisplay(featureDetails?.trend, featureDetails?.trendPercent);
  const TrendIcon = trendDisplay.icon;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <DialogTitle className="text-xl">
                {feature.featureName}
              </DialogTitle>
              <DialogDescription className="mt-1">
                Feature ID: <span className="font-mono text-xs">{feature.featureId}</span>
              </DialogDescription>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => onOpenChange(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        <div className="space-y-6">
          {/* Loading State */}
          {loading && (
            <div className="space-y-4">
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-40 w-full" />
            </div>
          )}

          {/* Error State */}
          {error && !loading && (
            <div className="flex items-center gap-3 p-4 bg-destructive/10 rounded-lg">
              <AlertCircle className="h-5 w-5 text-destructive" />
              <div>
                <p className="font-medium text-destructive">Error Loading Details</p>
                <p className="text-sm text-muted-foreground">{error}</p>
              </div>
            </div>
          )}

          {/* Feature Details */}
          {featureDetails && !loading && (
            <>
              {/* Header Section with Type, Category, and Trend */}
              <div className="flex flex-wrap items-center gap-2">
                {featureDetails.featureType && (
                  <Badge variant="outline">{featureDetails.featureType}</Badge>
                )}
                {featureDetails.category && (
                  <Badge variant="secondary">{featureDetails.category}</Badge>
                )}
                <Badge
                  className={`${trendDisplay.bgColor} ${trendDisplay.color} border-0`}
                >
                  <TrendIcon className="h-3 w-3 mr-1" />
                  {trendDisplay.label}
                  {featureDetails.trendPercent !== undefined && (
                    <span className="ml-1">
                      ({featureDetails.trendPercent >= 0 ? '+' : ''}
                      {featureDetails.trendPercent.toFixed(1)}%)
                    </span>
                  )}
                </Badge>
              </div>

              {/* Success Rate with Trend */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Target className="w-4 h-4 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Success Rate</p>
                  </div>
                  <div className={`text-3xl font-bold ${getSuccessRateColor(featureDetails.successRate)}`}>
                    {featureDetails.successRate.toFixed(1)}%
                  </div>
                  <div
                    className={`h-2 rounded-full ${getSuccessRateBgColor(featureDetails.successRate)}`}
                  >
                    <div
                      className="h-full rounded-full bg-current"
                      style={{ width: `${featureDetails.successRate}%` }}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <Activity className="w-4 h-4 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Total Uses</p>
                  </div>
                  <p className="text-3xl font-bold">{featureDetails.totalUses}</p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4 text-muted-foreground" />
                    <p className="text-sm text-muted-foreground">Avg P&L</p>
                  </div>
                  <p
                    className={`text-3xl font-bold ${
                      featureDetails.avgPnL >= 0 ? 'text-profit' : 'text-loss'
                    }`}
                  >
                    {featureDetails.avgPnL >= 0 ? '+' : ''}
                    {featureDetails.avgPnL.toFixed(2)}
                  </p>
                </div>
              </div>

              <Separator />

              {/* Win/Loss Record */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Wins</p>
                  <p className="text-2xl font-bold text-profit">{featureDetails.wins}</p>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Losses</p>
                  <p className="text-2xl font-bold text-loss">{featureDetails.losses}</p>
                </div>
              </div>

              <Separator />

              {/* Win Rate by Symbol */}
              <div className="space-y-3">
                <h3 className="font-semibold flex items-center gap-2">
                  <Target className="w-4 h-4" />
                  Win Rate by Symbol
                </h3>
                {featureDetails.winRatesBySymbol.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                    {featureDetails.winRatesBySymbol.map((item) => (
                      <div
                        key={item.symbol}
                        className="p-3 rounded-lg border"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium">{item.symbol}</span>
                          <Badge
                            variant="outline"
                            className={
                              item.winRate > 70
                                ? 'border-profit text-profit'
                                : item.winRate >= 40
                                ? 'border-warning text-warning'
                                : 'border-loss text-loss'
                            }
                          >
                            {item.winRate.toFixed(1)}%
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {item.wins}W - {item.losses}L ({item.totalTrades} trades)
                        </div>
                        <Progress value={item.winRate} className="h-1 mt-2" />
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No symbol data available</p>
                )}
              </div>

              <Separator />

              {/* Win Rate by Timeframe */}
              <div className="space-y-3">
                <h3 className="font-semibold flex items-center gap-2">
                  <Activity className="w-4 h-4" />
                  Win Rate by Timeframe
                </h3>
                {featureDetails.winRatesByTimeframe.length > 0 ? (
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {featureDetails.winRatesByTimeframe.map((item) => (
                      <div
                        key={item.timeframe}
                        className="p-3 rounded-lg border"
                      >
                        <div className="text-center">
                          <div className="text-sm font-medium mb-1">{item.timeframe}</div>
                          <div
                            className={`text-2xl font-bold ${
                              item.winRate > 70
                                ? 'text-profit'
                                : item.winRate >= 40
                                ? 'text-warning'
                                : 'text-loss'
                            }`}
                          >
                            {item.winRate.toFixed(0)}%
                          </div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {item.wins}W - {item.losses}L
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No timeframe data available</p>
                )}
              </div>

              <Separator />

              {/* Evolution History */}
              <div className="space-y-3">
                <h3 className="font-semibold flex items-center gap-2">
                  <History className="w-4 h-4" />
                  Evolution History
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-muted-foreground">Created</p>
                    <p className="text-sm font-medium">
                      {new Date(featureDetails.createdAt).toLocaleString()}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Last Modified</p>
                    <p className="text-sm font-medium">
                      {new Date(featureDetails.lastModified).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Feature Parameters */}
              <div className="space-y-3">
                <h3 className="font-semibold flex items-center gap-2">
                  <Settings className="w-4 h-4" />
                  Feature Parameters
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(featureDetails.parameters).map(([key, value]) => (
                    <div key={key} className="flex justify-between items-center p-2 rounded bg-muted/50">
                      <span className="text-sm text-muted-foreground capitalize">
                        {key.replace(/([A-Z])/g, ' $1').trim()}
                      </span>
                      <span className="text-sm font-mono font-medium">
                        {typeof value === 'boolean' ? (value ? 'true' : 'false') : String(value)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <Separator />

              {/* Recent Trades */}
              <div className="space-y-3">
                <h3 className="font-semibold flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  Recent Trades Using This Feature
                </h3>
                {featureDetails.recentTrades.length > 0 ? (
                  <div className="rounded-lg border">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Ticket</TableHead>
                          <TableHead>Symbol</TableHead>
                          <TableHead>Side</TableHead>
                          <TableHead className="text-right">P&L</TableHead>
                          <TableHead>Entry Time</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {featureDetails.recentTrades.map((trade) => (
                          <TableRow key={trade.ticket}>
                            <TableCell className="font-mono text-xs">
                              #{trade.ticket}
                            </TableCell>
                            <TableCell className="font-medium">
                              {trade.symbol}
                            </TableCell>
                            <TableCell>
                              <Badge
                                variant="outline"
                                className={
                                  trade.side === 'BUY'
                                    ? 'border-profit text-profit'
                                    : 'border-loss text-loss'
                                }
                              >
                                {trade.side}
                              </Badge>
                            </TableCell>
                            <TableCell
                              className={`text-right font-medium ${
                                trade.pnl >= 0 ? 'text-profit' : 'text-loss'
                              }`}
                            >
                              {trade.pnl >= 0 ? '+' : ''}
                              {trade.pnl.toFixed(2)}
                            </TableCell>
                            <TableCell className="text-sm text-muted-foreground">
                              {new Date(trade.entryTime).toLocaleDateString()}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <p className="text-sm text-muted-foreground">No recent trades available</p>
                )}
              </div>
            </>
          )}

          {/* Show basic info when not loading but no details */}
          {!loading && !featureDetails && !error && (
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Success Rate</p>
                  <div className={`text-2xl font-bold ${getSuccessRateColor(feature.successRate)}`}>
                    {feature.successRate.toFixed(1)}%
                  </div>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Total Uses</p>
                  <p className="text-2xl font-bold">{feature.totalUses}</p>
                </div>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">Avg P&L</p>
                  <p className={`text-2xl font-bold ${feature.avgPnL >= 0 ? 'text-profit' : 'text-loss'}`}>
                    {feature.avgPnL >= 0 ? '+' : ''}{feature.avgPnL.toFixed(2)}
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
