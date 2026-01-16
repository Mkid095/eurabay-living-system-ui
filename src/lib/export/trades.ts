/**
 * Trade Export Utilities
 *
 * Functions for exporting trade data to CSV and JSON formats.
 * Supports date range filtering and symbol filtering.
 */

import { apiClient } from '@/lib/api/client';
import type { Trade } from '@/hooks/useDashboardData';

/**
 * Export format options
 */
export type ExportFormat = 'csv' | 'json';

/**
 * Date range filter options
 */
export type DateRange = 'today' | 'week' | 'month' | 'all';

/**
 * Export filters
 */
export interface TradeExportFilters {
  startDate?: Date;
  endDate?: Date;
  symbol?: string;
}

/**
 * API response type for trades endpoint
 */
interface TradesApiResponse {
  trades: Trade[];
}

/**
 * Fetch trades from API with filters
 * GET /trades/recent
 */
async function fetchTrades(filters: TradeExportFilters = {}): Promise<Trade[]> {
  const params: Record<string, string | number> = {};

  if (filters.startDate) {
    params.startDate = filters.startDate.toISOString();
  }
  if (filters.endDate) {
    params.endDate = filters.endDate.toISOString();
  }
  if (filters.symbol) {
    params.symbol = filters.symbol;
  }

  const { data } = await apiClient.get<TradesApiResponse>('/trades/recent', params);
  return data.trades || [];
}

/**
 * Format trade data for CSV export
 * Headers: ticket, symbol, side, entryPrice, exitPrice, pnl, entryTime, exitTime
 */
function formatTradeForCSV(trade: Trade): Record<string, string> {
  const formatPrice = (price: number): string => price.toFixed(5);
  const formatCurrency = (amount: number): string => amount.toFixed(2);
  const formatDate = (date: Date): string => date.toISOString();

  return {
    ticket: trade.id,
    symbol: trade.pair,
    side: trade.type,
    entryPrice: formatPrice(trade.entryPrice),
    exitPrice: formatPrice(trade.currentPrice),
    pnl: formatCurrency(trade.pnl),
    entryTime: formatDate(trade.timestamp),
    exitTime: trade.status === 'closed' ? formatDate(trade.timestamp) : '',
  };
}

/**
 * Convert trades data to CSV string
 */
function tradesToCSV(trades: Trade[]): string {
  if (trades.length === 0) {
    return 'ticket,symbol,side,entryPrice,exitPrice,pnl,entryTime,exitTime\n';
  }

  const headers = ['ticket', 'symbol', 'side', 'entryPrice', 'exitPrice', 'pnl', 'entryTime', 'exitTime'];
  const rows = trades.map(formatTradeForCSV);

  const headerRow = headers.join(',');
  const dataRows = rows.map(row =>
    headers.map(header => {
      const value = row[header as keyof typeof row];
      return value;
    }).join(',')
  );

  return [headerRow, ...dataRows].join('\n');
}

/**
 * Generate filename for export
 * Format: trades_YYYY-MM-DD.{extension}
 */
function generateExportFilename(extension: string): string {
  const date = new Date();
  const dateStr = date.toISOString().split('T')[0];
  return `trades_${dateStr}.${extension}`;
}

/**
 * Trigger browser download for exported data
 */
function triggerDownload(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export trades to CSV format
 *
 * @param filters - Optional filters for date range and symbol
 * @returns Promise that resolves when export is complete
 */
export async function exportTradesToCSV(filters: TradeExportFilters = {}): Promise<void> {
  try {
    const trades = await fetchTrades(filters);
    const csv = tradesToCSV(trades);
    const filename = generateExportFilename('csv');
    triggerDownload(csv, filename, 'text/csv');
  } catch (error) {
    throw new Error(
      `Failed to export trades to CSV: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Export trades to JSON format
 *
 * @param filters - Optional filters for date range and symbol
 * @returns Promise that resolves when export is complete
 */
export async function exportTradesToJSON(filters: TradeExportFilters = {}): Promise<void> {
  try {
    const trades = await fetchTrades(filters);
    const json = JSON.stringify(trades, null, 2);
    const filename = generateExportFilename('json');
    triggerDownload(json, filename, 'application/json');
  } catch (error) {
    throw new Error(
      `Failed to export trades to JSON: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Export trades to specified format
 *
 * @param format - Export format ('csv' or 'json')
 * @param filters - Optional filters for date range and symbol
 * @returns Promise that resolves when export is complete
 */
export async function exportTrades(
  format: ExportFormat,
  filters: TradeExportFilters = {}
): Promise<void> {
  if (format === 'csv') {
    return exportTradesToCSV(filters);
  }
  return exportTradesToJSON(filters);
}
