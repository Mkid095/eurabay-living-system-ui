import { eq, and, gte, lte, desc } from 'drizzle-orm';
import { db } from '../index';
import { trades, type Trade, type NewTrade } from '../schema';
import { cacheInvalidation, CacheTTL, cacheManager } from '../cache';
import { CacheKeys } from '../cache';

/**
 * Trade Repository
 * Provides CRUD operations and complex queries for trade data management
 */
export class TradeRepository {
  /**
   * Create a new trade
   */
  async createTrade(data: NewTrade): Promise<Trade> {
    const [trade] = await db.insert(trades).values(data).returning();
    cacheInvalidation.onTradeChange();
    return trade;
  }

  /**
   * Get trade by system ticket ID
   */
  async getTradeBySystemTicket(systemTicket: string): Promise<Trade | null> {
    const [trade] = await db
      .select()
      .from(trades)
      .where(eq(trades.systemTicket, systemTicket))
      .limit(1);
    return trade || null;
  }

  /**
   * Get trade by MT5 ticket ID
   */
  async getTradeByMT5Ticket(mt5Ticket: number): Promise<Trade | null> {
    const [trade] = await db
      .select()
      .from(trades)
      .where(eq(trades.mt5Ticket, mt5Ticket))
      .limit(1);
    return trade || null;
  }

  /**
   * Get all active trades (cached with 30s TTL)
   */
  async getActiveTrades(): Promise<Trade[]> {
    const cacheKey = CacheKeys.TRADES_ACTIVE;
    const cached = cacheManager.get<Trade[]>(cacheKey);

    if (cached !== null) {
      return cached;
    }

    const result = await db
      .select()
      .from(trades)
      .where(eq(trades.status, 'active'))
      .orderBy(desc(trades.openTime));

    cacheManager.set(cacheKey, result, CacheTTL.ACTIVE_TRADES);
    return result;
  }

  /**
   * Get recent trades (last N trades by open time)
   */
  async getRecentTrades(limit: number = 50): Promise<Trade[]> {
    return db
      .select()
      .from(trades)
      .orderBy(desc(trades.openTime))
      .limit(limit);
  }

  /**
   * Update trade
   */
  async updateTrade(systemTicket: string, data: Partial<NewTrade>): Promise<Trade | null> {
    const [trade] = await db
      .update(trades)
      .set(data)
      .where(eq(trades.systemTicket, systemTicket))
      .returning();
    cacheInvalidation.onTradeChange();
    return trade || null;
  }

  /**
   * Close a trade (set status to closed and record close time)
   */
  async closeTrade(systemTicket: string, closePrice: number, pnl: number): Promise<Trade | null> {
    const [trade] = await db
      .update(trades)
      .set({
        status: 'closed',
        currentPrice: closePrice,
        closeTime: new Date(),
        pnl,
      })
      .where(eq(trades.systemTicket, systemTicket))
      .returning();
    cacheInvalidation.onTradeChange();
    return trade || null;
  }

  /**
   * Get trades by symbol
   */
  async getTradesBySymbol(symbol: string): Promise<Trade[]> {
    return db
      .select()
      .from(trades)
      .where(eq(trades.symbol, symbol))
      .orderBy(desc(trades.openTime));
  }

  /**
   * Get trades within a date range
   */
  async getTradesByDateRange(startDate: Date, endDate: Date): Promise<Trade[]> {
    return db
      .select()
      .from(trades)
      .where(
        and(
          gte(trades.openTime, startDate),
          lte(trades.openTime, endDate)
        )
      )
      .orderBy(desc(trades.openTime));
  }

  /**
   * Get trades by user ID
   */
  async getTradesByUser(userId: string): Promise<Trade[]> {
    return db
      .select()
      .from(trades)
      .where(eq(trades.userId, userId))
      .orderBy(desc(trades.openTime));
  }

  /**
   * Get trades by status
   */
  async getTradesByStatus(status: 'active' | 'closed' | 'pending'): Promise<Trade[]> {
    return db
      .select()
      .from(trades)
      .where(eq(trades.status, status))
      .orderBy(desc(trades.openTime));
  }

  /**
   * Get trades by evolution generation
   */
  async getTradesByEvolutionGeneration(generation: number): Promise<Trade[]> {
    return db
      .select()
      .from(trades)
      .where(eq(trades.evolutionGeneration, generation))
      .orderBy(desc(trades.openTime));
  }
}

/**
 * Singleton instance of TradeRepository
 */
export const tradeRepository = new TradeRepository();
