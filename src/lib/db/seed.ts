import { db } from './index';
import { users, trades, evolutionGenerations, features, mutations, signals, systemLogs } from './schema';
import { eq } from 'drizzle-orm';
import bcrypt from 'bcrypt';
import { cacheWarmer, cacheManager } from './cache';
import { tradeRepository } from './repositories/trade.repository';
import { evolutionRepository } from './repositories/evolution.repository';
import { userRepository } from './repositories/user.repository';
import { signalRepository } from './repositories/signal.repository';

/**
 * Seed script for admin and demo users
 * Run with: npm run db:seed
 */

const SALT_ROUNDS = 10;

export async function seedUsers() {
  console.log('Seeding users...');

  // Hash passwords
  const adminPasswordHash = await bcrypt.hash('admin123', SALT_ROUNDS);
  const traderPasswordHash = await bcrypt.hash('trader123', SALT_ROUNDS);

  const now = new Date();

  // Insert admin user
  await db.insert(users).values({
    id: 'admin-001',
    email: 'admin@eurabay.com',
    passwordHash: adminPasswordHash,
    name: 'Admin User',
    role: 'admin',
    emailVerified: true,
    createdAt: now,
    updatedAt: now,
  }).onConflictDoNothing(); // Skip if already exists

  // Insert demo trader user
  await db.insert(users).values({
    id: 'trader-001',
    email: 'trader@eurabay.com',
    passwordHash: traderPasswordHash,
    name: 'Demo Trader',
    role: 'trader',
    emailVerified: true,
    createdAt: now,
    updatedAt: now,
  }).onConflictDoNothing(); // Skip if already exists

  // Insert demo viewer user
  const viewerPasswordHash = await bcrypt.hash('viewer123', SALT_ROUNDS);
  await db.insert(users).values({
    id: 'viewer-001',
    email: 'viewer@eurabay.com',
    passwordHash: viewerPasswordHash,
    name: 'Demo Viewer',
    role: 'viewer',
    emailVerified: true,
    createdAt: now,
    updatedAt: now,
  }).onConflictDoNothing(); // Skip if already exists

  console.log('Users seeded successfully!');
  console.log('  - admin@eurabay.com (role: admin, password: admin123)');
  console.log('  - trader@eurabay.com (role: trader, password: trader123)');
  console.log('  - viewer@eurabay.com (role: viewer, password: viewer123)');
}

/**
 * Seed script for sample trades
 * Creates 50 sample trades with varying symbols, directions, and statuses
 */
const SYMBOLS = ['V10', 'V25', 'V50', 'V75', 'V100'];
const DIRECTIONS = ['BUY', 'SELL'] as const;
const STATUSES = ['active', 'closed', 'pending'] as const;

const TRADER_USER_ID = 'trader-001';

function getRandomItem<T>(array: readonly T[]): T {
  return array[Math.floor(Math.random() * array.length)];
}

function getRandomFloat(min: number, max: number, decimals = 2): number {
  const value = Math.random() * (max - min) + min;
  return Number(value.toFixed(decimals));
}

function getRandomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function getRandomDate(daysBack: number): Date {
  const date = new Date();
  date.setDate(date.getDate() - getRandomInt(0, daysBack));
  date.setHours(getRandomInt(0, 23), getRandomInt(0, 59), getRandomInt(0, 59));
  return date;
}

function generateFeaturesUsed(): string {
  const numFeatures = getRandomInt(2, 5);
  const featureIds: string[] = [];
  for (let i = 0; i < numFeatures; i++) {
    featureIds.push(`feature-${getRandomInt(1, 20).toString().padStart(3, '0')}`);
  }
  return JSON.stringify(featureIds);
}

export async function seedTrades() {
  console.log('Seeding trades...');

  const tradeCount = 50;
  const now = new Date();

  for (let i = 0; i < tradeCount; i++) {
    const symbol = getRandomItem(SYMBOLS);
    const direction = getRandomItem(DIRECTIONS);
    const status = getRandomItem(STATUSES);
    const lots = getRandomFloat(0.01, 2.0, 2);
    const entryPrice = getRandomFloat(1.05, 1.15, 5);
    const evolutionGeneration = getRandomInt(1, 10);
    const confidence = getRandomFloat(0.5, 0.95, 2);

    // Generate base price based on direction
    let currentPrice: number | null = null;
    let stopLoss: number | null = null;
    let takeProfit: number | null = null;
    let closeTime: Date | null = null;
    let pnl: number | null = null;

    if (status === 'active') {
      // Active trades have current price
      currentPrice = getRandomFloat(entryPrice - 0.02, entryPrice + 0.02, 5);
      stopLoss = direction === 'BUY'
        ? Number((entryPrice - getRandomFloat(0.005, 0.015, 5)).toFixed(5))
        : Number((entryPrice + getRandomFloat(0.005, 0.015, 5)).toFixed(5));
      takeProfit = direction === 'BUY'
        ? Number((entryPrice + getRandomFloat(0.01, 0.03, 5)).toFixed(5))
        : Number((entryPrice - getRandomFloat(0.01, 0.03, 5)).toFixed(5));
    } else if (status === 'closed') {
      // Closed trades have close time and PnL
      currentPrice = getRandomFloat(entryPrice - 0.03, entryPrice + 0.03, 5);
      closeTime = getRandomDate(30);

      // Calculate PnL based on direction and price movement
      const priceDiff = direction === 'BUY'
        ? currentPrice - entryPrice
        : entryPrice - currentPrice;
      pnl = Number((priceDiff * lots * 100000).toFixed(2));
    }

    const openTime = getRandomDate(90);

    // Ensure closeTime is after openTime
    if (closeTime && closeTime < openTime) {
      closeTime = new Date(openTime.getTime() + getRandomInt(1, 7) * 24 * 60 * 60 * 1000);
    }

    const systemTicket = `SYS-${getRandomInt(100000, 999999)}`;
    const mt5Ticket = getRandomInt(10000000, 99999999);

    await db.insert(trades).values({
      systemTicket,
      mt5Ticket,
      symbol,
      direction,
      lots,
      entryPrice,
      currentPrice,
      stopLoss,
      takeProfit,
      openTime,
      closeTime,
      pnl,
      status,
      evolutionGeneration,
      featuresUsed: generateFeaturesUsed(),
      confidence,
      userId: TRADER_USER_ID,
    }).onConflictDoNothing();
  }

  console.log(`Trades seeded successfully! (${tradeCount} records)`);
}

/**
 * Seed script for evolution data
 * Creates 10 generations, 20 features, and 100 mutations
 */
const CONTROLLER_DECISIONS = ['EVOLVE', 'MAINTAIN', 'RESET'] as const;
const MUTATION_TYPES = ['ADD_FEATURE', 'MODIFY_FEATURE', 'REMOVE_FEATURE', 'OPTIMIZE_PARAMS', 'HYBRIDIZE'] as const;

// Feature name templates for realistic trading features
const FEATURE_TEMPLATES = [
  'RSI_Divergence',
  'MACD_Crossover',
  'Bollinger_Breakout',
  'Volume_Spike',
  'EMA_Trend',
  'Fibonacci_Retracement',
  'Support_Resistance',
  'Candlestick_Pattern',
  'Momentum_Oscillator',
  'ATR_Volatility',
  'Price_Channel',
  'Moving_Average_Convergence',
  'Stochastic_Overbought',
  'Pivot_Point_Reversal',
  'Gap_Trading',
  'Trendline_Break',
  'Ichimoku_Cloud',
  'Parabolic_SAR',
  'CCI_Pattern',
  'OBV_Divergence'
];

function getGenerationReason(decision: string): string {
  const reasons = {
    EVOLVE: [
      'Performance plateau detected, applying mutations',
      'Fitness improvement potential identified',
      'Successful patterns require refinement',
      'Market regime change requires adaptation'
    ],
    MAINTAIN: [
      'Current generation performing optimally',
      'Fitness metrics within target range',
      'Stable performance across all symbols',
      'No significant improvement opportunities'
    ],
    RESET: [
      'Performance degradation detected',
      'Fitness below minimum threshold',
      'Excessive failure rate in recent trades',
      'Market conditions invalidating current strategy'
    ]
  };

  const reasonList = reasons[decision as keyof typeof reasons] || reasons.MAINTAIN;
  return getRandomItem(reasonList);
}

export async function seedEvolutionGenerations(): Promise<number[]> {
  console.log('Seeding evolution generations...');

  const generationCount = 10;
  const generationIds: number[] = [];
  const now = new Date();

  // Start from 90 days ago and work forward
  const startDate = new Date(now);
  startDate.setDate(startDate.getDate() - 90);

  for (let i = 1; i <= generationCount; i++) {
    // Calculate fitness with some upward trend then plateau
    const baseFitness = 0.4 + (i * 0.04); // 0.44 to 0.76
    const fitnessVariance = getRandomFloat(-0.05, 0.05, 3);
    const fitness = Number(Math.min(0.95, Math.max(0.3, baseFitness + fitnessVariance)).toFixed(3));

    // Average performance correlates with fitness
    const avgPerformance = Number((fitness * getRandomFloat(0.8, 1.2, 2)).toFixed(3));

    // Controller decision based on performance
    let controllerDecision: typeof CONTROLLER_DECISIONS[number];
    if (fitness < 0.5) {
      controllerDecision = 'RESET';
    } else if (fitness > 0.7 && i < generationCount) {
      controllerDecision = 'EVOLVE';
    } else {
      controllerDecision = getRandomItem(CONTROLLER_DECISIONS);
    }

    // Timestamp: spread generations across the 90-day period
    const timestamp = new Date(startDate);
    timestamp.setDate(timestamp.getDate() + (i * 9) + getRandomInt(0, 3));

    await db.insert(evolutionGenerations).values({
      generationNumber: i,
      timestamp,
      fitness,
      avgPerformance,
      controllerDecision,
      reason: getGenerationReason(controllerDecision),
    }).onConflictDoNothing();

    // Get the inserted ID
    const inserted = await db.select().from(evolutionGenerations)
      .where(eq(evolutionGenerations.generationNumber, i));

    if (inserted.length > 0) {
      generationIds.push(inserted[0].id);
    }
  }

  console.log(`Evolution generations seeded successfully! (${generationCount} records)`);
  return generationIds;
}

export async function seedFeatures(): Promise<string[]> {
  console.log('Seeding features...');

  const featureCount = 20;
  const featureIds: string[] = [];
  const now = new Date();

  // Start from 90 days ago
  const startDate = new Date(now);
  startDate.setDate(startDate.getDate() - 90);

  for (let i = 1; i <= featureCount; i++) {
    const featureId = `feature-${i.toString().padStart(3, '0')}`;
    const featureName = FEATURE_TEMPLATES[i - 1];

    // Success rate between 0.3 and 0.9, weighted toward higher for later features
    const baseSuccessRate = 0.3 + ((i / featureCount) * 0.4); // 0.32 to 0.7
    const successRate = Number((baseSuccessRate + getRandomFloat(-0.1, 0.1, 2)).toFixed(3));
    const clampedSuccessRate = Math.max(0.3, Math.min(0.9, successRate));

    // Total uses correlate with success rate (better features used more)
    const totalUses = getRandomInt(10, 200);
    const wins = Math.floor(totalUses * clampedSuccessRate);
    const losses = totalUses - wins;

    // Average PnL correlates with success rate
    const avgPnl = Number((clampedSuccessRate * getRandomFloat(50, 150)).toFixed(2));

    // Created timestamp spread across first 60 days
    const createdAt = new Date(startDate);
    createdAt.setDate(createdAt.getDate() + getRandomInt(0, 60));

    // Updated timestamp more recent
    const updatedAt = new Date(createdAt);
    updatedAt.setDate(updatedAt.getDate() + getRandomInt(1, 30));

    await db.insert(features).values({
      featureId,
      featureName,
      successRate: clampedSuccessRate,
      totalUses,
      wins,
      losses,
      avgPnl,
      createdAt,
      updatedAt,
    }).onConflictDoNothing();

    featureIds.push(featureId);
  }

  console.log(`Features seeded successfully! (${featureCount} records)`);
  return featureIds;
}

export async function seedMutations(generationIds: number[], featureIds: string[]) {
  console.log('Seeding mutations...');

  const mutationCount = 100;
  const now = new Date();

  // Start from 85 days ago
  const startDate = new Date(now);
  startDate.setDate(startDate.getDate() - 85);

  for (let i = 0; i < mutationCount; i++) {
    const mutationType = getRandomItem(MUTATION_TYPES);
    const generationId = getRandomItem(generationIds);
    const targetFeatureId = getRandomItem(featureIds);

    // Success rate: higher for later generations, some randomness
    const baseSuccessRate = 0.4;
    const generationIndex = generationIds.indexOf(generationId);
    const generationBonus = (generationIndex / generationIds.length) * 0.3;
    const successProbability = baseSuccessRate + generationBonus + getRandomFloat(-0.15, 0.15, 2);
    const clampedProbability = Math.max(0.2, Math.min(0.9, successProbability));
    const success = Math.random() < clampedProbability ? 1 : 0;

    // Fitness improvement: positive for successful mutations, negative for failed
    const baseImprovement = success ? getRandomFloat(0.01, 0.05, 4) : getRandomFloat(-0.03, -0.005, 4);
    const fitnessImprovement = Number(baseImprovement.toFixed(4));

    // Timestamp spread across the period
    const daysOffset = Math.floor((i / mutationCount) * 85) + getRandomInt(0, 2);
    const timestamp = new Date(startDate);
    timestamp.setDate(timestamp.getDate() + daysOffset);

    await db.insert(mutations).values({
      mutationType,
      generationId,
      targetFeatureId,
      success,
      fitnessImprovement,
      timestamp,
    }).onConflictDoNothing();
  }

  console.log(`Mutations seeded successfully! (${mutationCount} records)`);
}

export async function seedEvolutionData() {
  const generationIds = await seedEvolutionGenerations();
  const featureIds = await seedFeatures();
  await seedMutations(generationIds, featureIds);
  console.log('Evolution data seeded successfully!');
}

/**
 * Seed script for sample signals
 * Creates 30 sample signals with varied types, statuses, and confidence levels
 */
const SIGNAL_TYPES = ['STRONG_BUY', 'BUY', 'SELL', 'STRONG_SELL'] as const;
const SIGNAL_STATUSES = ['pending', 'approved', 'rejected', 'executed'] as const;
const HTF_CONTEXTS = ['Bullish Trend', 'Bearish Trend', 'Range Bound', 'Breakout', 'Reversal'] as const;

function generateSignalFeaturesUsed(): string {
  const numFeatures = getRandomInt(2, 4);
  const featureIds: string[] = [];
  for (let i = 0; i < numFeatures; i++) {
    featureIds.push(`feature-${getRandomInt(1, 20).toString().padStart(3, '0')}`);
  }
  return JSON.stringify(featureIds);
}

function getSignalReason(signalType: typeof SIGNAL_TYPES[number], status: string): string {
  const reasons = {
    pending: [
      'Awaiting trader approval',
      'Confirmation needed',
      'Risk assessment in progress'
    ],
    approved: [
      'Strong technical indicators',
      'High confidence alignment',
      'Favorable risk-reward ratio'
    ],
    rejected: [
      'Risk parameters exceeded',
      'Market conditions unfavorable',
      'Confidence below threshold'
    ],
    executed: [
      'Trade successfully opened',
      'Order filled at target price',
      'Position established'
    ]
  };

  const reasonList = reasons[status as keyof typeof reasons] || reasons.pending;
  return getRandomItem(reasonList);
}

export async function seedSignals() {
  console.log('Seeding signals...');

  const signalCount = 30;
  const now = new Date();

  // Start from 60 days ago
  const startDate = new Date(now);
  startDate.setDate(startDate.getDate() - 60);

  for (let i = 0; i < signalCount; i++) {
    const signalId = `SIG-${getRandomInt(100000, 999999)}`;
    const symbol = getRandomItem(SYMBOLS);
    const signalType = getRandomItem(SIGNAL_TYPES);
    const status = getRandomItem(SIGNAL_STATUSES);
    const evolutionGeneration = getRandomInt(1, 10);

    // Confidence between 0.5 and 0.95
    const baseConfidence = signalType.includes('STRONG') ? 0.75 : 0.6;
    const confidence = Number((baseConfidence + getRandomFloat(-0.1, 0.2, 2)).toFixed(2));
    const clampedConfidence = Math.max(0.5, Math.min(0.95, confidence));

    // HTF context based on signal type
    let htfContext: string | null = null;
    if (signalType === 'STRONG_BUY' || signalType === 'BUY') {
      htfContext = getRandomItem(['Bullish Trend', 'Breakout', 'Reversal']);
    } else {
      htfContext = getRandomItem(['Bearish Trend', 'Breakout', 'Reversal']);
    }

    // Timestamp spread across the 60-day period
    const timestamp = new Date(startDate);
    timestamp.setDate(timestamp.getDate() + getRandomInt(0, 60));
    timestamp.setHours(getRandomInt(0, 23), getRandomInt(0, 59), getRandomInt(0, 59));

    await db.insert(signals).values({
      signalId,
      symbol,
      signalType,
      confidence: clampedConfidence,
      htfContext,
      featuresUsed: generateSignalFeaturesUsed(),
      status,
      timestamp,
      evolutionGeneration,
    }).onConflictDoNothing();
  }

  console.log(`Signals seeded successfully! (${signalCount} records)`);
}

/**
 * Seed script for sample system logs
 * Creates 50 system logs with varied levels, components, and messages
 */
const LOG_LEVELS = ['INFO', 'WARN', 'ERROR', 'DEBUG'] as const;
const LOG_COMPONENTS = ['trading', 'evolution', 'mt5', 'api', 'system', 'database'] as const;

function getLogMessage(component: string, level: string): string {
  const messages: Record<string, string[]> = {
    trading: [
      'Trade execution initiated',
      'Signal generated for V10',
      'Position closed with profit',
      'Risk parameters validated',
      'Order submission successful',
      'Trade execution failed',
      'Position size calculated',
      'Stop loss updated'
    ],
    evolution: [
      'New generation started',
      'Fitness calculation completed',
      'Mutation applied to feature',
      'Controller decision made',
      'Feature performance updated',
      'Evolution cycle completed',
      'Generation threshold reached',
      'Mutation optimization started'
    ],
    mt5: [
      'Connection established',
      'Price data received',
      'Order confirmed by broker',
      'Account balance updated',
      'Connection lost, retrying',
      'Ping response time: 45ms',
      'Historical data fetched',
      'Order modification failed'
    ],
    api: [
      'Request received',
      'Response sent successfully',
      'Authentication verified',
      'Rate limit approached',
      'Invalid request payload',
      'API endpoint called',
      'Cache miss for request',
      'Request timeout occurred'
    ],
    system: [
      'System startup initiated',
      'Health check passed',
      'Memory usage: 45%',
      'CPU load: 32%',
      'Disk space adequate',
      'Backup completed',
      'Configuration loaded',
      'Service restart required'
    ],
    database: [
      'Query executed successfully',
      'Connection pool active',
      'Transaction committed',
      'Index rebuild completed',
      'Database backup started',
      'Slow query detected',
      'Connection timeout',
      'Data migration completed'
    ]
  };

  const componentMessages = messages[component] || messages.system;
  return getRandomItem(componentMessages);
}

function getLogDetails(component: string, level: string, message: string): string | null {
  // Only add details for WARN and ERROR levels
  if (level !== 'WARN' && level !== 'ERROR') {
    return null;
  }

  const details: Record<string, object> = {
    trading: { tradeId: `SYS-${getRandomInt(100000, 999999)}`, symbol: getRandomItem(SYMBOLS) },
    evolution: { generation: getRandomInt(1, 10), fitness: getRandomFloat(0.3, 0.9, 3) },
    mt5: { errorCode: getRandomInt(1000, 9999), retryCount: getRandomInt(1, 5) },
    api: { endpoint: '/api/trades/execute', statusCode: getRandomInt(400, 599) },
    system: { memoryUsage: `${getRandomInt(70, 95)}%`, cpuLoad: `${getRandomInt(60, 95)}%` },
    database: { queryTime: `${getRandomFloat(1.5, 5.0, 2)}s`, table: 'trades' }
  };

  return JSON.stringify(details[component] || { timestamp: new Date().toISOString() });
}

export async function seedSystemLogs() {
  console.log('Seeding system logs...');

  const logCount = 50;
  const now = new Date();

  // Start from 30 days ago
  const startDate = new Date(now);
  startDate.setDate(startDate.getDate() - 30);

  // Weight log levels toward INFO (most common), then WARN, some DEBUG, fewer ERROR
  const levelWeights = ['INFO', 'INFO', 'INFO', 'INFO', 'INFO', 'WARN', 'WARN', 'DEBUG', 'DEBUG', 'ERROR'];

  for (let i = 0; i < logCount; i++) {
    const component = getRandomItem(LOG_COMPONENTS);
    const level = getRandomItem(levelWeights);
    const message = getLogMessage(component, level);
    const details = getLogDetails(component, level, message);

    // Timestamp spread across the 30-day period
    const timestamp = new Date(startDate);
    timestamp.setDate(timestamp.getDate() + getRandomInt(0, 30));
    timestamp.setHours(getRandomInt(0, 23), getRandomInt(0, 59), getRandomInt(0, 59));

    await db.insert(systemLogs).values({
      timestamp,
      level,
      component,
      message,
      details,
    }).onConflictDoNothing();
  }

  console.log(`System logs seeded successfully! (${logCount} records)`);
}

// Main function to run all seeds
export async function seed() {
  try {
    await seedUsers();
    await seedTrades();
    await seedEvolutionData();
    await seedSignals();
    await seedSystemLogs();
    console.log('\nDatabase seeded successfully!');

    // Warm up cache with common data
    console.log('\nWarming up cache...');
    await cacheWarmer.warmUp({
      loadActiveTrades: () => tradeRepository.getActiveTrades(),
      loadEvolutionMetrics: async () => {
        const latest = await evolutionRepository.getLatestGeneration();
        const features = await evolutionRepository.getAllFeatures();
        return { latestGeneration: latest, features };
      },
      loadConfig: async () => {
        const adminUser = await userRepository.getUserById('admin-001');
        return adminUser;
      },
      loadPendingSignals: () => signalRepository.getPendingSignals(),
    });

    // Log cache statistics
    const stats = cacheManager.getStatistics();
    console.log('Cache statistics:', {
      size: stats.size,
      hits: stats.hits,
      misses: stats.misses,
      hitRate: `${(stats.hitRate * 100).toFixed(2)}%`,
    });

    process.exit(0);
  } catch (error) {
    console.error('Error seeding database:', error);
    process.exit(1);
  }
}

// Run seed if this file is executed directly
if (require.main === module) {
  seed();
}
