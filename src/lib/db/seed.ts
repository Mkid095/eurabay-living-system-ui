import { db } from './index';
import { users, trades } from './schema';
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

// Main function to run all seeds
export async function seed() {
  try {
    await seedUsers();
    await seedTrades();
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
