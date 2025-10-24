"use client";

import { Card } from "@/components/ui/card";
import { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: string | number;
  change?: number;
  icon: LucideIcon;
  iconColor?: string;
  suffix?: string;
  trend?: 'up' | 'down' | 'neutral';
}

export function MetricCard({ 
  title, 
  value, 
  change, 
  icon: Icon, 
  iconColor = "text-primary",
  suffix = "",
  trend = 'neutral'
}: MetricCardProps) {
  const isPositive = change !== undefined && change >= 0;
  
  return (
    <Card className="p-4 sm:p-6 hover:border-primary/50 transition-colors">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <p className="text-sm text-muted-foreground mb-1">{title}</p>
          <h3 className="text-2xl sm:text-3xl font-bold mb-2">
            {value}{suffix}
          </h3>
          {change !== undefined && (
            <div className={cn(
              "text-sm font-medium flex items-center gap-1",
              isPositive ? "text-profit" : "text-loss"
            )}>
              <span>{isPositive ? "↑" : "↓"}</span>
              <span>{Math.abs(change).toFixed(2)}%</span>
            </div>
          )}
        </div>
        <div className={cn(
          "p-3 rounded-lg bg-card border",
          iconColor
        )}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </Card>
  );
}
