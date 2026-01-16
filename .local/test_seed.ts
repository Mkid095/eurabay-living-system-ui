import { seedSignals, seedSystemLogs } from '../src/lib/db/seed';

async function test() {
  console.log('Starting seed test...');
  try {
    console.log('Testing seedSignals...');
    await seedSignals();
    console.log('seedSignals completed');

    console.log('Testing seedSystemLogs...');
    await seedSystemLogs();
    console.log('seedSystemLogs completed');

    console.log('Test completed successfully!');
    process.exit(0);
  } catch (error) {
    console.error('Test failed:', error);
    process.exit(1);
  }
}

test();
