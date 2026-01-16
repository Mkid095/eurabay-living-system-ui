"use client";

import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import type { MarketTrend, TrendStrength } from "@/types/market";
import { TrendSparkline } from "./TrendSparkline";
import { Info } from "lucide-react";

interface TrendBadgeProps {
  /** Market trend direction */
  trend: MarketTrend;
  /** Trend strength indicator */
  strength: TrendStrength;
  /** Price history for sparkline */
  priceHistory: number[];
  /** Confidence score */
  confidence?: number;
  /** Optional className */
  className?: string;
}

/**
 * Get trend color for display
 */
function getTrendColor(trend: MarketTrend): string {
  switch (trend) {
    case "BULLISH":
      return "#22c55e"; // green-500
    case "BEARISH":
      return "#ef4444"; // red-500
    case "NEUTRAL":
      return "#6b7280"; // gray-500
    default:
      return "#6b7280";
  }
}

/**
 * Get trend background color
 */
function getTrendBgColor(trend: MarketTrend): string {
  switch (trend) {
    case "BULLISH":
      return "bg-green-500";
    case "BEARISH":
      return "bg-red-500";
    case "NEUTRAL":
      return "bg-gray-500";
    default:
      return "bg-gray-500";
  }
}

/**
 * Get trend text background color
 */
function getTrendTextBgColor(trend: MarketTrend): string {
  switch (trend) {
    case "BULLISH":
      return "bg-green-500/10 text-green-500 border-green-500/20";
    case "BEARISH":
      return "bg-red-500/10 text-red-500 border-red-500/20";
    case "NEUTRAL":
      return "bg-gray-500/10 text-gray-500 border-gray-500/20";
    default:
      return "bg-gray-500/10 text-gray-500 border-gray-500/20";
  }
}

/**
 * Format strength for display
 */
function formatStrength(strength: TrendStrength): string {
  switch (strength) {
    case "strong":
      return "Strong";
    case "moderate":
      return "Moderate";
    case "weak":
      return "Weak";
    default:
      return "Moderate";
  }
}

/**
 * TrendBadge component
 * Displays market trend with color coding and sparkline chart
 */
export function TrendBadge({
  trend,
  strength,
  priceHistory,
  confidence,
  className
}: TrendBadgeProps) {
  const color = getTrendColor(trend);
  const bgColor = getTrendTextBgColor(trend);

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Badge
          variant="outline"
          className={cn(
            "flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium border",
            bgColor,
            className
          )}
        >
          <div className="flex items-center gap-1">
            <div className={cn("w-1.5 h-1.5 rounded-full", getTrendBgColor(trend))} />
            <span>{trend}</span>
          </div>
          <TrendSparkline data={priceHistory} color={color} className="w-[60px] h-[24px]" />
        </Badge>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-xs">
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 font-medium">
            <Info className="w-3.5 h-3.5" />
            <span>Trend Information</span>
          </div>
          <div className="space-y-1 text-xs">
            <p>
              <span className="font-medium">Direction:</span> {trend.toLowerCase()}
            </p>
            <p>
              <span className="font-medium">Strength:</span> {formatStrength(strength)}
            </p>
            {confidence !== undefined && (
              <p>
                <span className="font-medium">Confidence:</span> {confidence}%
              </p>
            )}
            <p className="pt-1 border-t border-border/50 text-muted-foreground">
              Trend calculated from price movement over last 20 data points using linear regression analysis.
            </p>
          </div>
        </div>
      </TooltipContent>
    </Tooltip>
  );
}
