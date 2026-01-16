"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Trade } from "@/hooks/useDashboardData";
import { cn } from "@/lib/utils";
import { History, Download } from "lucide-react";
import { toast } from "sonner";
import { exportTrades, type ExportFormat } from "@/lib/export/trades";

interface RecentTradesProps {
  trades: Trade[];
}

export function RecentTrades({ trades }: RecentTradesProps) {
  const [exportFormat, setExportFormat] = useState<ExportFormat>("csv");
  const [isExporting, setIsExporting] = useState(false);
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value);
  };

  const formatTime = (date: Date) => {
    return new Intl.DateTimeFormat('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      await exportTrades(exportFormat);
      toast.success(`Trades exported to ${exportFormat.toUpperCase()} successfully`);
    } catch (error) {
      toast.error(
        `Failed to export trades: ${error instanceof Error ? error.message : 'Unknown error'}`
      );
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <History className="w-5 h-5 text-primary" />
          <h2 className="text-xl font-bold">Recent Trades</h2>
        </div>
        <div className="flex items-center gap-2">
          <Select value={exportFormat} onValueChange={(value) => setExportFormat(value as ExportFormat)}>
            <SelectTrigger size="sm" className="w-[100px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="csv">CSV</SelectItem>
              <SelectItem value="json">JSON</SelectItem>
            </SelectContent>
          </Select>
          <Button
            size="sm"
            variant="outline"
            onClick={handleExport}
            disabled={isExporting || trades.length === 0}
          >
            <Download className="w-4 h-4" />
            Export
          </Button>
        </div>
      </div>

      <div className="space-y-3">
        {trades.map((trade) => (
          <div 
            key={trade.id} 
            className="flex items-center justify-between p-3 bg-muted/50 border border-border rounded-lg hover:border-primary/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className={cn(
                "w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold",
                trade.type === 'BUY' ? "bg-profit/20 text-profit" : "bg-loss/20 text-loss"
              )}>
                {trade.type}
              </div>
              <div>
                <p className="font-medium">{trade.pair}</p>
                <p className="text-xs text-muted-foreground">
                  {formatTime(trade.timestamp)} • {formatCurrency(trade.amount)}
                </p>
              </div>
            </div>
            <div className="text-right">
              <p className={cn(
                "font-bold",
                trade.pnl >= 0 ? "text-profit" : "text-loss"
              )}>
                {formatCurrency(trade.pnl)}
              </p>
              <p className={cn(
                "text-xs",
                trade.pnl >= 0 ? "text-profit" : "text-loss"
              )}>
                {trade.pnlPercent.toFixed(2)}%
              </p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
