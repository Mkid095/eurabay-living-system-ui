import { eq, and, or, gte, lte, desc, sql } from 'drizzle-orm';
import { db } from '../index';
import { systemLogs, type SystemLog, type NewSystemLog } from '../schema';

/**
 * Log Repository
 * Manages system logs for diagnostics and monitoring
 */
export class LogRepository {
  /**
   * Create a new log entry
   */
  async createLog(data: NewSystemLog): Promise<SystemLog> {
    const [log] = await db.insert(systemLogs).values(data).returning();
    return log;
  }

  /**
   * Get logs by component
   */
  async getLogsByComponent(component: string, limit: number = 100): Promise<SystemLog[]> {
    return db
      .select()
      .from(systemLogs)
      .where(eq(systemLogs.component, component))
      .orderBy(desc(systemLogs.timestamp))
      .limit(limit);
  }

  /**
   * Get logs by level
   */
  async getLogsByLevel(level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG', limit: number = 100): Promise<SystemLog[]> {
    return db
      .select()
      .from(systemLogs)
      .where(eq(systemLogs.level, level))
      .orderBy(desc(systemLogs.timestamp))
      .limit(limit);
  }

  /**
   * Get logs by date range
   */
  async getLogsByDateRange(startDate: Date, endDate: Date): Promise<SystemLog[]> {
    return db
      .select()
      .from(systemLogs)
      .where(
        and(
          gte(systemLogs.timestamp, startDate),
          lte(systemLogs.timestamp, endDate)
        )
      )
      .orderBy(desc(systemLogs.timestamp));
  }

  /**
   * Get recent errors
   */
  async getRecentErrors(limit: number = 50): Promise<SystemLog[]> {
    return db
      .select()
      .from(systemLogs)
      .where(eq(systemLogs.level, 'ERROR'))
      .orderBy(desc(systemLogs.timestamp))
      .limit(limit);
  }

  /**
   * Get recent logs
   */
  async getRecentLogs(limit: number = 100): Promise<SystemLog[]> {
    return db
      .select()
      .from(systemLogs)
      .orderBy(desc(systemLogs.timestamp))
      .limit(limit);
  }

  /**
   * Get logs by component and level
   */
  async getLogsByComponentAndLevel(
    component: string,
    level: 'INFO' | 'WARN' | 'ERROR' | 'DEBUG',
    limit: number = 100
  ): Promise<SystemLog[]> {
    return db
      .select()
      .from(systemLogs)
      .where(
        and(
          eq(systemLogs.component, component),
          eq(systemLogs.level, level)
        )
      )
      .orderBy(desc(systemLogs.timestamp))
      .limit(limit);
  }

  /**
   * Search logs by message content
   */
  async searchLogsByMessage(searchTerm: string, limit: number = 100): Promise<SystemLog[]> {
    return db
      .select()
      .from(systemLogs)
      .where(sql`${systemLogs.message} LIKE ${'%' + searchTerm + '%'}`)
      .orderBy(desc(systemLogs.timestamp))
      .limit(limit);
  }

  /**
   * Get log statistics
   */
  async getLogStats(): Promise<{
    totalLogs: number;
    infoLogs: number;
    warnLogs: number;
    errorLogs: number;
    debugLogs: number;
    recentErrors: SystemLog[];
  }> {
    const [total] = await db
      .select({ count: sql<number>`count(*)` })
      .from(systemLogs);

    const [info] = await db
      .select({ count: sql<number>`count(*)` })
      .from(systemLogs)
      .where(eq(systemLogs.level, 'INFO'));

    const [warn] = await db
      .select({ count: sql<number>`count(*)` })
      .from(systemLogs)
      .where(eq(systemLogs.level, 'WARN'));

    const [error] = await db
      .select({ count: sql<number>`count(*)` })
      .from(systemLogs)
      .where(eq(systemLogs.level, 'ERROR'));

    const [debug] = await db
      .select({ count: sql<number>`count(*)` })
      .from(systemLogs)
      .where(eq(systemLogs.level, 'DEBUG'));

    const recentErrors = await this.getRecentErrors(10);

    return {
      totalLogs: total.count,
      infoLogs: info.count,
      warnLogs: warn.count,
      errorLogs: error.count,
      debugLogs: debug.count,
      recentErrors,
    };
  }

  /**
   * Get logs by multiple components
   */
  async getLogsByComponents(components: string[], limit: number = 100): Promise<SystemLog[]> {
    // Build an array of eq conditions for each component
    const conditions = components.map(component => eq(systemLogs.component, component));

    // Use or to combine conditions
    return db
      .select()
      .from(systemLogs)
      .where(or(...conditions))
      .orderBy(desc(systemLogs.timestamp))
      .limit(limit);
  }

  /**
   * Delete old logs (cleanup)
   */
  async deleteOldLogs(beforeDate: Date): Promise<number> {
    const result = await db
      .delete(systemLogs)
      .where(lte(systemLogs.timestamp, beforeDate));
    return result.rowCount || 0;
  }

  /**
   * Get log by ID
   */
  async getLogById(id: number): Promise<SystemLog | null> {
    const [log] = await db
      .select()
      .from(systemLogs)
      .where(eq(systemLogs.id, id))
      .limit(1);
    return log || null;
  }
}

/**
 * Singleton instance of LogRepository
 */
export const logRepository = new LogRepository();
