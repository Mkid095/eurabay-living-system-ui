// MT5 Connection Types
export type MT5ConnectionState = 'connected' | 'disconnected' | 'error';

export interface MT5ConnectionInfo {
  connected: boolean;
  accountNumber?: number;
  company?: string;
  server?: string;
  terminalPath?: string;
  lastHeartbeat?: Date;
  latency?: number;
}

// MT5 Account Types
export interface MT5AccountInfo {
  login: number;
  company: string;
  currency: string;
  balance: number;
  equity: number;
  margin: number;
  freeMargin: number;
  marginLevel: number;
  leverage: number;
  profit: number;
  marginCall: number;
  stopOut: number;
}

// MT5 Order Types
export type MT5OrderType = 'BUY' | 'SELL' | 'BUY_LIMIT' | 'SELL_LIMIT' | 'BUY_STOP' | 'SELL_STOP';

export type MT5OrderTimeType = 'GTC' | 'IOC' | 'FOK' | 'DAY';

export interface MT5OrderRequest {
  symbol: string;
  volume: number;
  orderType: MT5OrderType;
  price?: number;
  stopLoss?: number;
  takeProfit?: number;
  deviation?: number;
  magic?: number;
  comment?: string;
  expiration?: Date;
}

export interface MT5OrderResult {
  success: boolean;
  ticket?: number;
  error?: MT5Error;
  executionPrice?: number;
  executionTime?: Date;
  comment?: string;
}

// MT5 Position Types
export type MT5PositionDirection = 'BUY' | 'SELL';

export interface MT5Position {
  ticket: number;
  symbol: string;
  direction: MT5PositionDirection;
  volume: number;
  openPrice: number;
  currentPrice: number;
  stopLoss: number;
  takeProfit: number;
  profit: number;
  swap: number;
  commission: number;
  openTime: Date;
  expiration?: Date;
  magic: number;
  comment: string;
}

// MT5 Trade History Types
export type MT5TradeDirection = 'BUY' | 'SELL';

export interface MT5TradeHistory {
  ticket: number;
  symbol: string;
  direction: MT5TradeDirection;
  lots: number;
  openPrice: number;
  closePrice: number;
  openTime: Date;
  closeTime: Date;
  profit: number;
  commission: number;
  swap: number;
  comment: string;
  magic: number;
}

// MT5 Indicator Types
export type MT5Timeframe = 'M1' | 'M5' | 'M15' | 'M30' | 'H1' | 'H4' | 'D1' | 'W1' | 'MN';

export interface IndicatorRequest {
  symbol: string;
  timeframe: MT5Timeframe;
  period: number;
}

export interface RSIResult {
  value: number;
  timestamp: Date;
}

export interface MACDResult {
  macd: number;
  signal: number;
  histogram: number;
  timestamp: Date;
}

export interface MAResult {
  value: number;
  timestamp: Date;
}

export interface BollingerBandsResult {
  upper: number;
  middle: number;
  lower: number;
  timestamp: Date;
}

export interface ATRResult {
  value: number;
  timestamp: Date;
}

export interface IndicatorResult {
  rsi?: RSIResult;
  macd?: MACDResult;
  ma?: MAResult;
  bollinger?: BollingerBandsResult;
  atr?: ATRResult;
}

// MT5 Error Types
export enum MT5ErrorCode {
  TERMINAL_NOT_FOUND = 'TERMINAL_NOT_FOUND',
  LOGIN_FAILED = 'LOGIN_FAILED',
  CONNECTION_LOST = 'CONNECTION_LOST',
  ORDER_REJECTED = 'ORDER_REJECTED',
  NOT_ENOUGH_MONEY = 'NOT_ENOUGH_MONEY',
  MARKET_CLOSED = 'MARKET_CLOSED',
  INVALID_PRICE = 'INVALID_PRICE',
  INVALID_VOLUME = 'INVALID_VOLUME',
  INVALID_PARAMETERS = 'INVALID_PARAMETERS',
  SERVER_BUSY = 'SERVER_BUSY',
  TRADE_DISABLED = 'TRADE_DISABLED',
  POSITION_NOT_FOUND = 'POSITION_NOT_FOUND',
  INVALID_TICKET = 'INVALID_TICKET',
  UNKNOWN_ERROR = 'UNKNOWN_ERROR'
}

export interface MT5Error {
  code: MT5ErrorCode;
  message: string;
  details?: string;
}

// MT5 Terminal Status Types
export interface MT5TerminalStatus {
  isConnected: boolean;
  terminalPath: string;
  buildVersion: string;
  connectionState: MT5ConnectionState;
  ping: number;
  lastHeartbeat: Date;
  tradeAllowed: boolean;
  tradeContextBusy: boolean;
  dataBuffers: Record<string, number>;
  errors: MT5ErrorLog[];
}

export interface MT5ErrorLog {
  timestamp: Date;
  code: MT5ErrorCode;
  message: string;
  details?: string;
}

// MT5 Symbol Info Types
export interface MT5SymbolInfo {
  symbol: string;
  bid: number;
  ask: number;
  spread: number;
  point: number;
  digits: number;
  volumeMin: number;
  volumeMax: number;
  volumeStep: number;
  stopLevel: number;
  freezeLevel: number;
  tradeAllowed: boolean;
}

// Price Sync Types
export interface DerivPriceData {
  symbol: string;
  price: number;
  timestamp: Date;
  bid?: number;
  ask?: number;
}

export interface PriceSyncResult {
  success: boolean;
  synced: number;
  failed: number;
  errors: string[];
}

// Signal Execution Types
export interface TradingSignal {
  signalId: string;
  symbol: string;
  direction: 'BUY' | 'SELL';
  confidence: number;
  features: number[];
  riskPercent: number;
  timestamp: Date;
}

export interface ExecutedTrade {
  systemTicket: string;
  mt5Ticket?: number;
  symbol: string;
  direction: 'BUY' | 'SELL';
  volume: number;
  entryPrice?: number;
  stopLoss?: number;
  takeProfit?: number;
  executionTime: Date;
  status: 'PENDING' | 'FILLED' | 'FAILED' | 'CANCELLED';
  error?: string;
}

// Listener Types
export type MT5ConnectionListener = (state: MT5ConnectionState, info?: MT5ConnectionInfo) => void;
export type MT5PositionListener = (positions: MT5Position[]) => void;
export type MT5ErrorListener = (error: MT5Error) => void;
