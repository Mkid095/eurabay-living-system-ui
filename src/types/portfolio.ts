/**
 * Portfolio Types
 *
 * Type definitions for portfolio-related data including equity history and P&L.
 */

import type { DateRange } from './performance';

/**
 * Single data point in equity history
 */
export interface EquityHistoryPoint {
  /** ISO date string */
  date: string;
  /** Equity value in account currency */
  equity: number;
  /** Profit/loss since starting equity */
  pnl: number;
  /** Drawdown from peak equity (0 to 1) */
  drawdown: number;
  /** Boolean indicating if this is a peak equity point */
  isPeak: boolean;
}

/**
 * Equity history response from API
 */
export interface EquityHistory {
  /** Starting equity value */
  startingEquity: number;
  /** Current equity value */
  currentEquity: number;
  /** Peak equity value */
  peakEquity: number;
  /** Maximum drawdown (0 to 1) */
  maxDrawdown: number;
  /** Total return */
  totalReturn: number;
  /** Total return percentage */
  totalReturnPercent: number;
  /** Array of equity history points */
  history: EquityHistoryPoint[];
}

/**
 * P&L history data point
 */
export interface PnLHistoryPoint {
  /** ISO date string */
  date: string;
  /** P&L amount for the period */
  pnl: number;
  /** Cumulative P&L */
  cumulativePnl: number;
  /** Number of trades in this period */
  tradesCount: number;
  /** Trading symbol (if filtered) */
  symbol?: string;
}

/**
 * P&L history response from API
 */
export interface PnLHistory {
  /** Total P&L */
  totalPnl: number;
  /** Total P&L percentage */
  totalPnlPercent: number;
  /** Number of winning periods */
  winningPeriods: number;
  /** Number of losing periods */
  losingPeriods: number;
  /** Array of P&L history points */
  history: PnLHistoryPoint[];
}
