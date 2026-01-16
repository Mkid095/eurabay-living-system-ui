/**
 * Trades and Signals API Endpoints
 *
 * API endpoint functions for trading operations including active trades,
 * trade history, signals, and execution logs.
 * All functions are fully typed with JSDoc comments.
 */

import { apiClient } from '../client';
import type {
  EvolvedTrade,
  ClosedTrade,
  PendingSignal,
  SignalActionResult,
  ExecutionLogEntry,
  TradeModificationRequest,
  TradeCloseRequest,
  TradeCloseResult,
} from '../types';

// ============================================================================
// ACTIVE TRADES ENDPOINTS
// ============================================================================

/**
 * Get all active trades
 * GET /trades/active
 *
 * Retrieves all currently active (open) trades in the system.
 * Includes real-time P&L and current market prices.
 *
 * @returns Promise resolving to array of active trades
 *
 * @example
 * ```ts
 * const activeTrades = await getActiveTrades();
 * activeTrades.forEach(trade => {
 *   console.log(`${trade.symbol}: ${trade.pnl.toFixed(2)} (${trade.pnlPercent.toFixed(2)}%)`);
 * });
 * ```
 */
export async function getActiveTrades(): Promise<EvolvedTrade[]> {
  const { data } = await apiClient.get<EvolvedTrade[]>('/trades/active');
  return data;
}

/**
 * Get active trades filtered by symbol
 * GET /trades/active?symbol={symbol}
 *
 * Retrieves active trades for a specific trading symbol.
 *
 * @param symbol - Trading symbol to filter by (e.g., 'V10', 'V25')
 * @returns Promise resolving to array of filtered active trades
 *
 * @example
 * ```ts
 * const v10Trades = await getActiveTradesBySymbol('V10');
 * console.log(`Found ${v10Trades.length} active V10 trades`);
 * ```
 */
export async function getActiveTradesBySymbol(symbol: string): Promise<EvolvedTrade[]> {
  const { data } = await apiClient.get<EvolvedTrade[]>('/trades/active', { symbol });
  return data;
}

// ============================================================================
// TRADE HISTORY ENDPOINTS
// ============================================================================

/**
 * Get recent closed trades
 * GET /trades/recent
 *
 * Retrieves recently closed trades. Optionally filter by
 * date range, symbol, or limit the number of results.
 *
 * @param options - Optional filters for the query
 * @returns Promise resolving to array of closed trades
 *
 * @example
 * ```ts
 * // Get last 50 trades
 * const recent = await getRecentTrades({ limit: 50 });
 *
 * // Get trades for specific symbol
 * const v25Trades = await getRecentTrades({ symbol: 'V25' });
 *
 * // Get trades from last 7 days
 * const weekTrades = await getRecentTrades({ days: 7 });
 * ```
 */
export async function getRecentTrades(options?: {
  /** Maximum number of trades to return */
  limit?: number;
  /** Filter by trading symbol */
  symbol?: string;
  /** Filter by number of recent days */
  days?: number;
}): Promise<ClosedTrade[]> {
  const params = options ? {
    limit: options.limit,
    symbol: options.symbol,
    days: options.days,
  } : undefined;
  const { data } = await apiClient.get<ClosedTrade[]>('/trades/recent', params);
  return data;
}

/**
 * Get trade execution log
 * GET /trades/execution-log
 *
 * Retrieves the execution log showing all trade-related events
 * including signal generation, approval, execution, and closure.
 *
 * @param options - Optional filters for the log
 * @returns Promise resolving to array of execution log entries
 *
 * @example
 * ```ts
 * // Get all execution logs
 * const logs = await getExecutionLog();
 *
 * // Get only errors
 * const errors = await getExecutionLog({ level: 'error' });
 *
 * // Get logs for specific trade
 * const tradeLogs = await getExecutionLog({ tradeTicket: 'TRD-001' });
 * ```
 */
export async function getExecutionLog(options?: {
  /** Filter by log level */
  level?: 'info' | 'warning' | 'error' | 'success';
  /** Filter by trade ticket */
  tradeTicket?: string;
  /** Maximum number of entries to return */
  limit?: number;
}): Promise<ExecutionLogEntry[]> {
  const params = options ? {
    level: options.level,
    tradeTicket: options.tradeTicket,
    limit: options.limit,
  } : undefined;
  const { data } = await apiClient.get<ExecutionLogEntry[]>('/trades/execution-log', params);
  return data;
}

// ============================================================================
// PENDING SIGNALS ENDPOINTS
// ============================================================================

/**
 * Get pending signals awaiting approval
 * GET /trades/pending-signals
 *
 * Retrieves all trading signals that are pending approval
 * from a trader before execution.
 *
 * @returns Promise resolving to array of pending signals
 *
 * @example
 * ```ts
 * const signals = await getPendingSignals();
 * console.log(`Found ${signals.length} signals awaiting approval`);
 *
 * signals.forEach(signal => {
 *   console.log(`${signal.symbol}: ${signal.signalType} (${(signal.confidence * 100).toFixed(0)}% confidence)`);
 * });
 * ```
 */
export async function getPendingSignals(): Promise<PendingSignal[]> {
  const { data } = await apiClient.get<PendingSignal[]>('/trades/pending-signals');
  return data;
}

/**
 * Approve a pending signal for execution
 * POST /trades/signals/{id}/approve
 *
 * Approves a pending trading signal, which will trigger
 * the execution of the trade through MT5 or the connected broker.
 *
 * @param signalId - The ID of the signal to approve
 * @param notes - Optional notes for the approval decision
 * @returns Promise resolving to approval action result
 *
 * @example
 * ```ts
 * const result = await approveSignal('SIG-001', 'Strong technical indicators');
 * if (result.success) {
 *   console.log('Signal approved and trade executed');
 * }
 * ```
 */
export async function approveSignal(signalId: string, notes?: string): Promise<SignalActionResult> {
  const { data } = await apiClient.post<SignalActionResult, { notes?: string }>(
    `/trades/signals/${signalId}/approve`,
    { notes }
  );
  return data;
}

/**
 * Reject a pending signal
 * POST /trades/signals/{id}/reject
 *
 * Rejects a pending trading signal, preventing it from being executed.
 * The signal will be logged with the rejection reason.
 *
 * @param signalId - The ID of the signal to reject
 * @param notes - Optional notes explaining the rejection
 * @returns Promise resolving to rejection action result
 *
 * @example
 * ```ts
 * const result = await rejectSignal('SIG-002', 'Market conditions unfavorable');
 * if (result.success) {
 *   console.log('Signal rejected');
 * }
 * ```
 */
export async function rejectSignal(signalId: string, notes?: string): Promise<SignalActionResult> {
  const { data } = await apiClient.post<SignalActionResult, { notes?: string }>(
    `/trades/signals/${signalId}/reject`,
    { notes }
  );
  return data;
}

// ============================================================================
// TRADE MANAGEMENT ENDPOINTS
// ============================================================================

/**
 * Close an active trade
 * POST /trades/{ticket}/close
 *
 * Closes an active trade, optionally specifying a partial close.
 * Supports partial position closure by specifying lots.
 *
 * @param ticket - The trade ticket to close
 * @param lots - Number of lots to close (optional, defaults to full position)
 * @returns Promise resolving to close result with closed trade details
 *
 * @example
 * ```ts
 * // Close full position
 * const result = await closeTrade('TRD-001');
 * console.log(`Closed trade with final P&L: ${result.trade?.pnl}`);
 *
 * // Close partial position (half the lots)
 * const partialResult = await closeTrade('TRD-002', 0.5);
 * ```
 */
export async function closeTrade(ticket: string, lots?: number): Promise<TradeCloseResult> {
  const { data } = await apiClient.post<TradeCloseResult, TradeCloseRequest>(
    `/trades/${ticket}/close`,
    { ticket, lots }
  );
  return data;
}

/**
 * Modify an active trade
 * PUT /trades/{ticket}
 *
 * Modifies parameters of an active trade such as stop loss,
 * take profit, or position size.
 *
 * @param ticket - The trade ticket to modify
 * @param modifications - The modifications to apply
 * @returns Promise resolving to modified trade
 *
 * @example
 * ```ts
 * // Update stop loss and take profit
 * const modified = await modifyTrade('TRD-001', {
 *   stopLoss: 1.0850,
 *   takeProfit: 1.0950
 * });
 *
 * // Adjust position size
 * const resized = await modifyTrade('TRD-002', {
 *   lots: 1.5
 * });
 * ```
 */
export async function modifyTrade(
  ticket: string,
  modifications: Omit<TradeModificationRequest, 'ticket'>
): Promise<EvolvedTrade> {
  const { data } = await apiClient.put<EvolvedTrade, TradeModificationRequest>(
    `/trades/${ticket}`,
    { ticket, ...modifications }
  );
  return data;
}

/**
 * Get trade statistics
 * GET /trades/statistics
 *
 * Retrieves aggregated statistics for trades including
 * win rate, average win/loss, profit factor, and more.
 *
 * @param options - Optional filters for statistics
 * @returns Promise resolving to trade statistics
 *
 * @example
 * ```ts
 * // Get all-time statistics
 * const allTimeStats = await getTradeStatistics();
 *
 * // Get statistics for last 30 days
 * const monthlyStats = await getTradeStatistics({ days: 30 });
 *
 * // Get statistics for specific symbol
 * const symbolStats = await getTradeStatistics({ symbol: 'V10' });
 * ```
 */
export async function getTradeStatistics(options?: {
  /** Filter by number of recent days */
  days?: number;
  /** Filter by trading symbol */
  symbol?: string;
}): Promise<{
  totalTrades: number;
  winRate: number;
  totalProfitLoss: number;
  averageWin: number;
  averageLoss: number;
  profitFactor: number;
  largestWinningTrade: number;
  largestLosingTrade: number;
  bestPerformingSymbol: string;
  worstPerformingSymbol: string;
}> {
  const params = options ? {
    days: options.days,
    symbol: options.symbol,
  } : undefined;
  const { data } = await apiClient.get('/trades/statistics', params);
  return data;
}

// ============================================================================
// EXPORTED API OBJECT
// ============================================================================

/**
 * Trades and signals API object
 *
 * Provides a convenient way to import all trade-related functions:
 * ```ts
 * import { tradesApi } from '@/lib/api';
 *
 * const active = await tradesApi.getActiveTrades();
 * const pending = await tradesApi.getPendingSignals();
 * ```
 */
export const tradesApi = {
  // Active trades
  getActiveTrades,
  getActiveTradesBySymbol,

  // Trade history
  getRecentTrades,

  // Execution log
  getExecutionLog,

  // Pending signals
  getPendingSignals,
  approveSignal,
  rejectSignal,

  // Trade management
  closeTrade,
  modifyTrade,

  // Statistics
  getTradeStatistics,
} as const;
