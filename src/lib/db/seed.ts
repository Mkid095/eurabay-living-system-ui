import { db } from './index';
import { users, trades, evolutionGenerations, features, mutations } from './schema';
import { eq } from 'drizzle-orm';
import bcrypt from 'bcrypt';

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

// Main function to run all seeds
export async function seed() {
  try {
    await seedUsers();
    await seedTrades();
    await seedEvolutionData();
    console.log('\nDatabase seeded successfully!');
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
