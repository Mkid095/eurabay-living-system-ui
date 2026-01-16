/**
 * Performance Export Utilities
 *
 * Functions for generating PDF performance reports.
 * Includes performance metrics, equity curve chart, P&L chart,
 * trade statistics table, and top/bottom performing trades.
 */

import { apiClient } from '@/lib/api/client';
import type { PerformanceMetrics, DateRange } from '@/types/performance';
import type { EquityHistory } from '@/types/portfolio';
import type { PnLHistory } from '@/types/portfolio';
import { jsPDF } from 'jspdf';

/**
 * Trade data for top/bottom performers
 */
interface TradePerformance {
  id: string;
  symbol: string;
  type: string;
  pnl: number;
  entryPrice: number;
  exitPrice: number;
  timestamp: string;
}

/**
 * API response type for trades endpoint
 */
interface TradesApiResponse {
  trades: TradePerformance[];
}

/**
 * Fetch performance metrics from API
 * GET /performance/metrics
 */
async function fetchPerformanceMetrics(dateRange: DateRange = 'all'): Promise<PerformanceMetrics> {
  const { data } = await apiClient.get<PerformanceMetrics>('/performance/metrics', {
    range: dateRange,
  });
  return data;
}

/**
 * Fetch equity history from API
 * GET /portfolio/equity-history
 */
async function fetchEquityHistory(dateRange: DateRange = 'all'): Promise<EquityHistory> {
  const { data } = await apiClient.get<EquityHistory>('/portfolio/equity-history', {
    range: dateRange,
  });
  return data;
}

/**
 * Fetch P&L history from API
 * GET /portfolio/pnl-history
 */
async function fetchPnLHistory(dateRange: DateRange = 'all'): Promise<PnLHistory> {
  const { data } = await apiClient.get<PnLHistory>('/portfolio/pnl-history', {
    range: dateRange,
  });
  return data;
}

/**
 * Fetch trades for top/bottom performers
 * GET /trades/recent
 */
async function fetchTrades(dateRange: DateRange = 'all'): Promise<TradePerformance[]> {
  const params: Record<string, string | number> = { range: dateRange };
  const { data } = await apiClient.get<TradesApiResponse>('/trades/recent', params);
  return data.trades || [];
}

/**
 * Capture chart as image from DOM element
 */
async function captureChartAsImage(elementId: string): Promise<string | null> {
  const element = document.getElementById(elementId);
  if (!element) return null;

  // Create a canvas to draw the chart
  const canvas = document.createElement('canvas');
  const ctx = canvas.getContext('2d');
  if (!ctx) return null;

  // Get the element dimensions
  const rect = element.getBoundingClientRect();
  canvas.width = rect.width * 2;
  canvas.height = rect.height * 2;

  // Use html2canvas if available, otherwise return placeholder
  // For this implementation, we'll use a simplified approach
  // that works without additional dependencies

  return null; // Placeholder - actual implementation would use html2canvas
}

/**
 * Generate a simple chart image for PDF
 * This creates a basic chart representation without external dependencies
 */
function generateChartPlaceholder(
  title: string,
  dataPoints: Array<{ label: string; value: number }>,
  width: number,
  height: number
): string {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d');
  if (!ctx) return 'data:,'; // Return empty data URI

  // Clear canvas
  ctx.fillStyle = '#233d3d';
  ctx.fillRect(0, 0, width, height);

  // Draw title
  ctx.fillStyle = '#e8f5e9';
  ctx.font = 'bold 16px sans-serif';
  ctx.fillText(title, 20, 25);

  // Find max value for scaling
  const maxValue = Math.max(...dataPoints.map((p) => Math.abs(p.value)), 1);

  // Draw simple bar chart
  const barWidth = (width - 60) / dataPoints.length;
  const midY = height / 2 + 20;

  dataPoints.forEach((point, index) => {
    const x = 40 + index * barWidth;
    const barHeight = (Math.abs(point.value) / maxValue) * (height / 3);
    const y = point.value >= 0 ? midY - barHeight : midY;

    // Draw bar
    ctx.fillStyle = point.value >= 0 ? '#66bb6a' : '#ef5350';
    ctx.fillRect(x + 5, y, barWidth - 10, barHeight);

    // Draw label
    ctx.fillStyle = '#8ba69a';
    ctx.font = '10px sans-serif';
    ctx.fillText(point.label, x + 5, height - 10);
  });

  // Draw zero line
  ctx.strokeStyle = '#8ba69a';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(30, midY);
  ctx.lineTo(width - 10, midY);
  ctx.stroke();

  return canvas.toDataURL('image/png');
}

/**
 * Generate filename for performance report
 * Format: performance_report_YYYY-MM-DD.pdf
 */
function generateReportFilename(): string {
  const date = new Date();
  const dateStr = date.toISOString().split('T')[0];
  return `performance_report_${dateStr}.pdf`;
}

/**
 * Format currency for display
 */
function formatCurrency(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

/**
 * Format date for display
 */
function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  }).format(date);
}

/**
 * Add metrics section to PDF
 */
function addMetricsSection(pdf: jsPDF, metrics: PerformanceMetrics, startY: number): number {
  let y = startY;

  // Title
  pdf.setFontSize(14);
  pdf.setTextColor(220, 245, 233);
  pdf.text('Performance Metrics', 20, y);
  y += 10;

  // Metrics grid
  pdf.setFontSize(10);
  pdf.setTextColor(139, 166, 154);

  const colWidth = 85;
  const rowHeight = 8;

  // Total Return
  pdf.text('Total Return:', 20, y);
  pdf.setTextColor(metrics.totalReturnPercent >= 0 ? 102 : 239,
                  metrics.totalReturnPercent >= 0 ? 187 : 83,
                  metrics.totalReturnPercent >= 0 ? 106 : 80);
  pdf.text(`${metrics.totalReturnPercent >= 0 ? '+' : ''}${metrics.totalReturnPercent.toFixed(2)}% (${formatCurrency(metrics.totalReturn)})`, 60, y);
  y += rowHeight;

  // Sharpe Ratio
  pdf.setTextColor(139, 166, 154);
  pdf.text('Sharpe Ratio:', 20, y);
  pdf.setTextColor(220, 245, 233);
  pdf.text(metrics.sharpeRatio.toFixed(2), 60, y);
  y += rowHeight;

  // Max Drawdown
  pdf.setTextColor(139, 166, 154);
  pdf.text('Max Drawdown:', 20, y);
  pdf.setTextColor(239, 83, 80);
  pdf.text(`${metrics.maxDrawdownPercent.toFixed(1)}%`, 60, y);
  y += rowHeight;

  // Win Rate
  pdf.setTextColor(139, 166, 154);
  pdf.text('Win Rate:', 20, y);
  pdf.setTextColor(102, 187, 106);
  pdf.text(`${metrics.winRatePercent.toFixed(1)}% (${metrics.winRate}/${metrics.totalTrades})`, 60, y);
  y += rowHeight;

  // Second column
  y = startY + 10;
  pdf.setTextColor(139, 166, 154);
  pdf.text('Profit Factor:', 110, y);
  pdf.setTextColor(220, 245, 233);
  pdf.text(metrics.profitFactor.toFixed(2), 160, y);
  y += rowHeight;

  // Total Trades
  pdf.setTextColor(139, 166, 154);
  pdf.text('Total Trades:', 110, y);
  pdf.setTextColor(220, 245, 233);
  pdf.text(metrics.totalTrades.toString(), 160, y);
  y += rowHeight;

  // Benchmark (if available)
  if (metrics.benchmarkReturnPercent !== undefined) {
    pdf.setTextColor(139, 166, 154);
    pdf.text('Benchmark:', 110, y);
    pdf.setTextColor(220, 245, 233);
    pdf.text(`${metrics.benchmarkReturnPercent >= 0 ? '+' : ''}${metrics.benchmarkReturnPercent.toFixed(2)}%`, 160, y);
    y += rowHeight;
  }

  return y + 15;
}

/**
 * Add trade statistics table to PDF
 */
function addTradeStatistics(pdf: jsPDF, equityHistory: EquityHistory, pnlHistory: PnLHistory, startY: number): number {
  let y = startY;

  pdf.setFontSize(14);
  pdf.setTextColor(220, 245, 233);
  pdf.text('Trade Statistics', 20, y);
  y += 10;

  pdf.setFontSize(10);
  pdf.setTextColor(139, 166, 154);

  const rowHeight = 8;

  // Equity stats
  pdf.text('Starting Equity:', 20, y);
  pdf.setTextColor(220, 245, 233);
  pdf.text(formatCurrency(equityHistory.startingEquity), 70, y);
  y += rowHeight;

  pdf.setTextColor(139, 166, 154);
  pdf.text('Current Equity:', 20, y);
  pdf.setTextColor(equityHistory.totalReturnPercent >= 0 ? 102 : 239,
                  equityHistory.totalReturnPercent >= 0 ? 187 : 83,
                  equityHistory.totalReturnPercent >= 0 ? 106 : 80);
  pdf.text(formatCurrency(equityHistory.currentEquity), 70, y);
  y += rowHeight;

  pdf.setTextColor(139, 166, 154);
  pdf.text('Peak Equity:', 20, y);
  pdf.setTextColor(220, 245, 233);
  pdf.text(formatCurrency(equityHistory.peakEquity), 70, y);
  y += rowHeight;

  // P&L stats
  pdf.text('Total P&L:', 110, y);
  pdf.setTextColor(pnlHistory.totalPnl >= 0 ? 102 : 239,
                  pnlHistory.totalPnl >= 0 ? 187 : 83,
                  pnlHistory.totalPnl >= 0 ? 106 : 80);
  pdf.text(`${pnlHistory.totalPnl >= 0 ? '+' : ''}${formatCurrency(pnlHistory.totalPnl)}`, 150, y);
  y += rowHeight;

  pdf.setTextColor(139, 166, 154);
  pdf.text('Winning Periods:', 110, y);
  pdf.setTextColor(102, 187, 106);
  pdf.text(pnlHistory.winningPeriods.toString(), 150, y);
  y += rowHeight;

  pdf.setTextColor(139, 166, 154);
  pdf.text('Losing Periods:', 110, y);
  pdf.setTextColor(239, 83, 80);
  pdf.text(pnlHistory.losingPeriods.toString(), 150, y);

  return y + 15;
}

/**
 * Add top/bottom performing trades to PDF
 */
function addTopBottomTrades(pdf: jsPDF, trades: TradePerformance[], startY: number): number {
  let y = startY;

  pdf.setFontSize(14);
  pdf.setTextColor(220, 245, 233);
  pdf.text('Top Performing Trades', 20, y);
  y += 10;

  // Sort trades by P&L
  const sortedTrades = [...trades].sort((a, b) => b.pnl - a.pnl);
  const topTrades = sortedTrades.slice(0, 5);
  const bottomTrades = sortedTrades.slice(-5).reverse();

  pdf.setFontSize(9);
  const rowHeight = 7;
  const colWidths = [15, 25, 20, 30, 35];

  // Header
  pdf.setTextColor(139, 166, 154);
  pdf.text('#', 20, y);
  pdf.text('Symbol', 35, y);
  pdf.text('Type', 75, y);
  pdf.text('P&L', 100, y);
  pdf.text('Date', 140, y);
  y += rowHeight;

  // Top trades
  topTrades.forEach((trade, index) => {
    pdf.setTextColor(220, 245, 233);
    pdf.text((index + 1).toString(), 20, y);
    pdf.text(trade.symbol, 35, y);
    pdf.text(trade.type, 75, y);
    pdf.setTextColor(102, 187, 106);
    pdf.text(`+${formatCurrency(trade.pnl)}`, 100, y);
    pdf.setTextColor(220, 245, 233);
    pdf.text(formatDate(trade.timestamp), 140, y);
    y += rowHeight;
  });

  y += 10;

  // Bottom trades
  pdf.setFontSize(14);
  pdf.setTextColor(220, 245, 233);
  pdf.text('Bottom Performing Trades', 20, y);
  y += 10;

  pdf.setFontSize(9);
  pdf.setTextColor(139, 166, 154);
  pdf.text('#', 20, y);
  pdf.text('Symbol', 35, y);
  pdf.text('Type', 75, y);
  pdf.text('P&L', 100, y);
  pdf.text('Date', 140, y);
  y += rowHeight;

  bottomTrades.forEach((trade, index) => {
    pdf.setTextColor(220, 245, 233);
    pdf.text((index + 1).toString(), 20, y);
    pdf.text(trade.symbol, 35, y);
    pdf.text(trade.type, 75, y);
    pdf.setTextColor(239, 83, 80);
    pdf.text(formatCurrency(trade.pnl), 100, y);
    pdf.setTextColor(220, 245, 233);
    pdf.text(formatDate(trade.timestamp), 140, y);
    y += rowHeight;
  });

  return y + 10;
}

/**
 * Generate performance report PDF
 *
 * @param dateRange - Date range filter (today, week, month, all)
 * @param onProgress - Optional callback for progress updates (0-100)
 * @returns Promise that resolves with PDF blob for download
 */
export async function generatePerformanceReportPDF(
  dateRange: DateRange = 'all',
  onProgress?: (progress: number) => void
): Promise<void> {
  try {
    onProgress?.(10);

    // Fetch all required data in parallel
    const [metrics, equityHistory, pnlHistory, trades] = await Promise.all([
      fetchPerformanceMetrics(dateRange),
      fetchEquityHistory(dateRange),
      fetchPnLHistory(dateRange),
      fetchTrades(dateRange),
    ]);

    onProgress?.(30);

    // Create PDF document
    const pdf = new jsPDF({
      orientation: 'portrait',
      unit: 'mm',
      format: 'a4',
    });

    onProgress?.(40);

    // Set background color (dark theme)
    pdf.setFillColor(35, 61, 61);
    pdf.rect(0, 0, 210, 297, 'F');

    let yPosition = 20;

    // Title and date
    pdf.setFontSize(18);
    pdf.setTextColor(196, 245, 77);
    pdf.text('EURABAY Living System', 20, yPosition);
    yPosition += 8;

    pdf.setFontSize(16);
    pdf.text('Performance Report', 20, yPosition);
    yPosition += 8;

    pdf.setFontSize(10);
    pdf.setTextColor(139, 166, 154);
    const dateRangeLabel = dateRange === 'all' ? 'All Time' :
                          dateRange === 'today' ? 'Today' :
                          dateRange === 'week' ? 'This Week' : 'This Month';
    pdf.text(`Date Range: ${dateRangeLabel}`, 20, yPosition);
    pdf.text(`Generated: ${formatDate(new Date().toISOString())}`, 140, yPosition);
    yPosition += 15;

    onProgress?.(50);

    // Add metrics section
    yPosition = addMetricsSection(pdf, metrics, yPosition);

    onProgress?.(60);

    // Add trade statistics
    yPosition = addTradeStatistics(pdf, equityHistory, pnlHistory, yPosition);

    onProgress?.(70);

    // Add equity chart placeholder
    if (yPosition > 200) {
      pdf.addPage();
      pdf.setFillColor(35, 61, 61);
      pdf.rect(0, 0, 210, 297, 'F');
      yPosition = 20;
    }

    pdf.setFontSize(14);
    pdf.setTextColor(220, 245, 233);
    pdf.text('Equity Curve', 20, yPosition);
    yPosition += 5;

    // Generate simple chart image
    const equityChartData = equityHistory.history.slice(-10).map((point) => ({
      label: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: point.pnl,
    }));
    const equityChartImage = generateChartPlaceholder('Equity Growth', equityChartData, 170, 80);
    pdf.addImage(equityChartImage, 'PNG', 20, yPosition, 170, 80);
    yPosition += 90;

    onProgress?.(80);

    // Add P&L chart placeholder
    if (yPosition > 200) {
      pdf.addPage();
      pdf.setFillColor(35, 61, 61);
      pdf.rect(0, 0, 210, 297, 'F');
      yPosition = 20;
    }

    pdf.setFontSize(14);
    pdf.setTextColor(220, 245, 233);
    pdf.text('P&L History', 20, yPosition);
    yPosition += 5;

    const pnlChartData = pnlHistory.history.slice(-10).map((point) => ({
      label: new Date(point.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      value: point.pnl,
    }));
    const pnlChartImage = generateChartPlaceholder('Daily P&L', pnlChartData, 170, 80);
    pdf.addImage(pnlChartImage, 'PNG', 20, yPosition, 170, 80);
    yPosition += 90;

    onProgress?.(90);

    // Add top/bottom trades on new page if needed
    if (yPosition > 180 || trades.length > 0) {
      pdf.addPage();
      pdf.setFillColor(35, 61, 61);
      pdf.rect(0, 0, 210, 297, 'F');
      yPosition = 20;
    }

    if (trades.length > 0) {
      addTopBottomTrades(pdf, trades, yPosition);
    }

    onProgress?.(100);

    // Save PDF
    const filename = generateReportFilename();
    pdf.save(filename);

  } catch (error) {
    throw new Error(
      `Failed to generate performance report: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Export performance data as JSON
 *
 * @param dateRange - Date range filter (today, week, month, all)
 * @returns Promise that resolves when export is complete
 */
export async function exportPerformanceData(dateRange: DateRange = 'all'): Promise<void> {
  try {
    const [metrics, equityHistory, pnlHistory] = await Promise.all([
      fetchPerformanceMetrics(dateRange),
      fetchEquityHistory(dateRange),
      fetchPnLHistory(dateRange),
    ]);

    const data = {
      reportDate: new Date().toISOString(),
      dateRange,
      metrics,
      equityHistory,
      pnlHistory,
    };

    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `performance_data_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  } catch (error) {
    throw new Error(
      `Failed to export performance data: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}
