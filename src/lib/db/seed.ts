import { db } from './index';
import { users } from './schema';
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

// Main function to run all seeds
export async function seed() {
  try {
    await seedUsers();
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
