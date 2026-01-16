/**
 * MT5 Signal Execution Functions
 *
 * Functions for executing trades based on trading signals through MetaTrader 5.
 * Calculates position sizes, stop loss/take profit levels, and executes orders.
 */

import { executeMT5Order, DEFAULT_MAGIC_NUMBER } from './orders';
import { getATR } from './indicators';
import type {
  TradingSignal,
  ExecutedTrade,
  MT5AccountInfo,
  MT5OrderResult,
  MT5Error,
  MT5ErrorCode,
  MT5Timeframe,
} from './types';

/**
 * Default ATR period for SL/TP calculation
 */
const DEFAULT_ATR_PERIOD = 14;

/**
 * Default ATR timeframe for SL/TP calculation
 */
const DEFAULT_ATR_TIMEFRAME: MT5Timeframe = 'H1';

/**
 * ATR multiplier for stop loss calculation
 */
const ATR_SL_MULTIPLIER = 2;

/**
 * ATR multiplier for take profit calculation (reward:risk ratio)
 */
const ATR_TP_MULTIPLIER = 2;

/**
 * Minimum position size in lots
 */
const MIN_POSITION_SIZE = 0.01;

/**
 * Maximum position size in lots
 */
const MAX_POSITION_SIZE = 100;

/**
 * Generate system ticket ID for a signal
 */
function generateSystemTicket(signal: TradingSignal): string {
  return `SIG-${signal.signalId}-${Date.now()}`;
}

/**
 * Create MT5 error object
 */
function createMT5Error(code: MT5ErrorCode, message: string, details?: string): MT5Error {
  return {
    code,
    message,
    details,
  };
}

/**
 * Calculate position size based on risk percentage
 *
 * @param accountInfo - MT5 account information
 * @param riskPercent - Risk percentage of account equity (e.g., 1 = 1%)
 * @param atr - Current ATR value for the symbol
 * @param stopLossDistance - Distance to stop loss in price units
 * @returns Position size in lots
 *
 * @example
 * ```typescript
 * // Account equity: $10,000, risk: 1%, ATR: 50, SL distance: 100
 * // Risk amount = $10,000 * 0.01 = $100
 * // Position size = $100 / (100 * lot_size) = 0.01 lots (simplified)
 * const lots = calculatePositionSize(accountInfo, 1, 50, 100);
 * ```
 */
function calculatePositionSize(
  accountInfo: MT5AccountInfo,
  riskPercent: number,
  atr: number,
  stopLossDistance: number
): number {
  // Calculate risk amount in account currency
  const riskAmount = accountInfo.equity * (riskPercent / 100);

  // Calculate position value per lot at stop loss distance
  const positionValuePerLot = stopLossDistance;

  // Calculate position size based on risk
  let positionSize = riskAmount / positionValuePerLot;

  // Clamp position size to min/max limits
  positionSize = Math.max(MIN_POSITION_SIZE, Math.min(positionSize, MAX_POSITION_SIZE));

  console.log(`[MT5Signals] Position size calculated:`, {
    equity: accountInfo.equity,
    riskPercent,
    riskAmount,
    atr,
    stopLossDistance,
    positionSize,
  });

  return positionSize;
}

/**
 * Calculate stop loss and take profit based on ATR
 *
 * @param currentPrice - Current market price
 * @param atr - Current ATR value
 * @param direction - Trade direction ('BUY' or 'SELL')
 * @returns Object with stopLoss and takeProfit prices
 *
 * @example
 * ```typescript
 * // Current price: 10000, ATR: 50, direction: 'BUY'
 * // SL = 10000 - (50 * 2) = 9950
 * // TP = 10000 + (50 * 2 * 2) = 10200
 * const { stopLoss, takeProfit } = calculateSLTPFromATR(10000, 50, 'BUY');
 * ```
 */
function calculateSLTPFromATR(
  currentPrice: number,
  atr: number,
  direction: 'BUY' | 'SELL'
): { stopLoss: number; takeProfit: number } {
  const slDistance = atr * ATR_SL_MULTIPLIER;
  const tpDistance = slDistance * ATR_TP_MULTIPLIER;

  let stopLoss: number;
  let takeProfit: number;

  if (direction === 'BUY') {
    stopLoss = currentPrice - slDistance;
    takeProfit = currentPrice + tpDistance;
  } else {
    stopLoss = currentPrice + slDistance;
    takeProfit = currentPrice - tpDistance;
  }

  console.log(`[MT5Signals] SL/TP calculated from ATR:`, {
    currentPrice,
    atr,
    direction,
    slDistance,
    tpDistance,
    stopLoss,
    takeProfit,
  });

  return { stopLoss, takeProfit };
}

/**
 * Create trade comment with signal information
 *
 * @param signal - Trading signal
 * @returns Trade comment string
 *
 * @example
 * ```typescript
 * // Signal ID: "SIG-123", features: [0.5, 0.8, 0.3]
 * // Comment: "SIG:SIG-123 | F:0.5,0.8,0.3 | Gen:42"
 * const comment = createSignalComment(signal);
 * ```
 */
function createSignalComment(signal: TradingSignal, evolutionGeneration: number): string {
  const featuresStr = signal.features.map(f => f.toFixed(2)).join(',');
  return `SIG:${signal.signalId} | F:${featuresStr} | Gen:${evolutionGeneration}`;
}

/**
 * Execute a trading signal through MT5
 *
 * This function orchestrates the complete signal execution flow:
 * 1. Fetches current ATR for SL/TP calculation
 * 2. Calculates position size based on risk percentage
 * 3. Calculates stop loss (2x ATR) and take profit levels
 * 4. Executes the market order through MT5
 * 5. Returns execution details with system and MT5 ticket IDs
 *
 * @param signal - Trading signal with symbol, direction, confidence, features, riskPercent
 * @param accountInfo - MT5 account information for position sizing
 * @param evolutionGeneration - Current evolution generation number
 * @param currentPrice - Optional current market price (defaults to 0, will be fetched by MT5)
 * @param atrPeriod - Optional ATR period (default: 14)
 * @param atrTimeframe - Optional ATR timeframe (default: H1)
 * @returns Promise<ExecutedTrade> - Execution result with system ticket and MT5 ticket
 *
 * @throws Error if signal execution fails
 *
 * @example
 * ```typescript
 * const signal: TradingSignal = {
 *   signalId: 'SIG-001',
 *   symbol: 'V10',
 *   direction: 'BUY',
 *   confidence: 0.85,
 *   features: [0.5, 0.8, 0.3, 0.9],
 *   riskPercent: 1.0,
 *   timestamp: new Date(),
 * };
 *
 * const accountInfo: MT5AccountInfo = {
 *   login: 123456,
 *   company: 'MetaQuotes',
 *   currency: 'USD',
 *   balance: 10000,
 *   equity: 10000,
 *   margin: 0,
 *   freeMargin: 10000,
 *   marginLevel: 0,
 *   leverage: 100,
 * };
 *
 * try {
 *   const trade = await executeSignalThroughMT5(signal, accountInfo, 42);
 *   console.log(`Trade executed: System=${trade.systemTicket}, MT5=${trade.mt5Ticket}`);
 * } catch (error) {
 *   console.error(`Signal execution failed: ${error}`);
 * }
 * ```
 */
export async function executeSignalThroughMT5(
  signal: TradingSignal,
  accountInfo: MT5AccountInfo,
  evolutionGeneration: number,
  currentPrice: number = 0,
  atrPeriod: number = DEFAULT_ATR_PERIOD,
  atrTimeframe: MT5Timeframe = DEFAULT_ATR_TIMEFRAME
): Promise<ExecutedTrade> {
  const startTime = Date.now();
  const systemTicket = generateSystemTicket(signal);

  console.log(`[MT5Signals] Executing signal through MT5:`, {
    systemTicket,
    signalId: signal.signalId,
    symbol: signal.symbol,
    direction: signal.direction,
    confidence: signal.confidence,
    riskPercent: signal.riskPercent,
    evolutionGeneration,
  });

  // Validate signal
  const validationError = validateSignal(signal, accountInfo);
  if (validationError) {
    const duration = Date.now() - startTime;
    console.error(`[MT5Signals] Signal validation failed (${duration}ms):`, validationError);

    const failedTrade: ExecutedTrade = {
      systemTicket,
      symbol: signal.symbol,
      direction: signal.direction,
      volume: 0,
      executionTime: new Date(),
      status: 'FAILED',
      error: validationError.message,
    };

    throw new Error(`Signal validation failed: ${validationError.message}`);
  }

  try {
    // Step 1: Fetch ATR for SL/TP calculation
    console.log(`[MT5Signals] Fetching ATR for SL/TP calculation...`);
    const atrResult = await getATR({
      symbol: signal.symbol,
      timeframe: atrTimeframe,
      period: atrPeriod,
    });

    const atr = atrResult.value;
    console.log(`[MT5Signals] ATR fetched: ${atr}`);

    // Step 2: Calculate SL/TP based on ATR
    // Use provided currentPrice or default to 0 (MT5 will use current market price)
    const priceForCalculation = currentPrice > 0 ? currentPrice : 10000; // Default fallback for calculation
    const { stopLoss, takeProfit } = calculateSLTPFromATR(priceForCalculation, atr, signal.direction);

    // Calculate SL distance for position sizing
    const slDistance = Math.abs(priceForCalculation - stopLoss);

    // Step 3: Calculate position size based on risk percentage
    const volume = calculatePositionSize(accountInfo, signal.riskPercent, atr, slDistance);

    // Step 4: Create trade comment with signal details
    const comment = createSignalComment(signal, evolutionGeneration);

    // Step 5: Execute the market order
    console.log(`[MT5Signals] Executing MT5 order...`);
    const orderResult: MT5OrderResult = await executeMT5Order(
      {
        symbol: signal.symbol,
        volume,
        orderType: signal.direction,
        stopLoss,
        takeProfit,
        comment,
        magic: DEFAULT_MAGIC_NUMBER,
      },
      evolutionGeneration
    );

    const duration = Date.now() - startTime;

    // Step 6: Process order result
    if (orderResult.success && orderResult.ticket) {
      const executedTrade: ExecutedTrade = {
        systemTicket,
        mt5Ticket: orderResult.ticket,
        symbol: signal.symbol,
        direction: signal.direction,
        volume,
        entryPrice: orderResult.executionPrice,
        stopLoss,
        takeProfit,
        executionTime: orderResult.executionTime || new Date(),
        status: 'FILLED',
      };

      console.log(`[MT5Signals] Signal executed SUCCESSFULLY (${duration}ms):`, {
        systemTicket: executedTrade.systemTicket,
        mt5Ticket: executedTrade.mt5Ticket,
        symbol: executedTrade.symbol,
        direction: executedTrade.direction,
        volume: executedTrade.volume,
        entryPrice: executedTrade.entryPrice,
        stopLoss: executedTrade.stopLoss,
        takeProfit: executedTrade.takeProfit,
        duration,
      });

      return executedTrade;
    }

    // Order execution failed
    const failedTrade: ExecutedTrade = {
      systemTicket,
      symbol: signal.symbol,
      direction: signal.direction,
      volume,
      executionTime: new Date(),
      status: 'FAILED',
      error: orderResult.error?.message || 'Unknown execution error',
    };

    console.error(`[MT5Signals] Signal execution FAILED (${duration}ms):`, {
      systemTicket,
      error: orderResult.error,
      duration,
    });

    throw new Error(`Signal execution failed: ${orderResult.error?.message || 'Unknown error'}`);

  } catch (error) {
    const duration = Date.now() - startTime;
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

    console.error(`[MT5Signals] Signal execution error (${duration}ms):`, {
      systemTicket,
      error: errorMessage,
      duration,
    });

    const failedTrade: ExecutedTrade = {
      systemTicket,
      symbol: signal.symbol,
      direction: signal.direction,
      volume: 0,
      executionTime: new Date(),
      status: 'FAILED',
      error: errorMessage,
    };

    throw error;
  }
}

/**
 * Validate trading signal before execution
 *
 * @param signal - Trading signal to validate
 * @param accountInfo - MT5 account information
 * @returns MT5Error if validation fails, null if valid
 */
function validateSignal(
  signal: TradingSignal,
  accountInfo: MT5AccountInfo
): MT5Error | null {
  // Check signal ID
  if (!signal.signalId || typeof signal.signalId !== 'string' || signal.signalId.trim().length === 0) {
    return createMT5Error('INVALID_PARAMETERS', 'Signal ID is required and must be a non-empty string');
  }

  // Check symbol
  if (!signal.symbol || typeof signal.symbol !== 'string' || signal.symbol.trim().length === 0) {
    return createMT5Error('INVALID_PARAMETERS', 'Symbol is required and must be a non-empty string');
  }

  // Check direction
  if (!['BUY', 'SELL'].includes(signal.direction)) {
    return createMT5Error('INVALID_PARAMETERS', `Invalid direction: ${signal.direction}. Must be BUY or SELL`);
  }

  // Check confidence
  if (typeof signal.confidence !== 'number' || signal.confidence < 0 || signal.confidence > 1) {
    return createMT5Error('INVALID_PARAMETERS', 'Confidence must be a number between 0 and 1');
  }

  // Check risk percentage
  if (typeof signal.riskPercent !== 'number' || signal.riskPercent <= 0 || signal.riskPercent > 100) {
    return createMT5Error('INVALID_PARAMETERS', 'Risk percent must be a number between 0 and 100');
  }

  // Check features array
  if (!Array.isArray(signal.features) || signal.features.length === 0) {
    return createMT5Error('INVALID_PARAMETERS', 'Features must be a non-empty array');
  }

  // Validate all feature values are numbers
  const invalidFeatures = signal.features.filter(f => typeof f !== 'number' || isNaN(f));
  if (invalidFeatures.length > 0) {
    return createMT5Error('INVALID_PARAMETERS', 'All feature values must be valid numbers');
  }

  // Check account info
  if (!accountInfo || accountInfo.equity <= 0) {
    return createMT5Error('INVALID_PARAMETERS', 'Account equity must be greater than 0');
  }

  // Check if account has enough margin for trading
  if (accountInfo.freeMargin <= 0) {
    return createMT5Error('NOT_ENOUGH_MONEY', 'Insufficient free margin for trading');
  }

  return null;
}

/**
 * Calculate position size for a signal (utility function)
 *
 * @param signal - Trading signal
 * @param accountInfo - MT5 account information
 * @param atr - Current ATR value
 * @param currentPrice - Current market price
 * @returns Position size in lots
 */
export function calculateSignalPositionSize(
  signal: TradingSignal,
  accountInfo: MT5AccountInfo,
  atr: number,
  currentPrice: number
): number {
  const slDistance = atr * ATR_SL_MULTIPLIER;
  return calculatePositionSize(accountInfo, signal.riskPercent, atr, slDistance);
}

/**
 * Calculate SL/TP for a signal (utility function)
 *
 * @param signal - Trading signal
 * @param atr - Current ATR value
 * @param currentPrice - Current market price
 * @returns Object with stopLoss and takeProfit prices
 */
export function calculateSignalSLTP(
  signal: TradingSignal,
  atr: number,
  currentPrice: number
): { stopLoss: number; takeProfit: number } {
  return calculateSLTPFromATR(currentPrice, atr, signal.direction);
}

/**
 * Create signal comment (utility function)
 *
 * @param signal - Trading signal
 * @param evolutionGeneration - Current evolution generation number
 * @returns Trade comment string
 */
export function createSignalCommentString(
  signal: TradingSignal,
  evolutionGeneration: number
): string {
  return createSignalComment(signal, evolutionGeneration);
}
