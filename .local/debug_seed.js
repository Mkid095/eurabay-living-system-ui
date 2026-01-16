const fs = require('fs');
const path = require('path');

const logFile = path.join(__dirname, 'seed_debug.log');

function log(message) {
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] ${message}\n`;
  fs.appendFileSync(logFile, logMessage);
  console.log(message); // Also try to console.log
}

log('=== Seed Debug Started ===');

try {
  log('Importing db...');
  const { db } = require('../src/lib/db/index.ts');
  log('Database imported successfully');

  log('Importing schema...');
  const { signals, systemLogs } = require('../src/lib/db/schema.ts');
  log('Schema imported successfully');

  log('All imports successful!');
  log('=== Seed Debug Completed ===');
} catch (error) {
  log(`ERROR: ${error.message}`);
  log(`STACK: ${error.stack}`);
  log('=== Seed Debug Failed ===');
  process.exit(1);
}
