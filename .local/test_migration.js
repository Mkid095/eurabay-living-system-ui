const { createClient } = require('@libsql/client');
const fs = require('fs');
const path = require('path');

const client = createClient({ url: 'file:.local/test_db.sqlite' });
const migrationSQL = fs.readFileSync(path.join(__dirname, '../drizzle/0001_initial_schema.sql'), 'utf8');

(async () => {
  try {
    // Execute migration split by statements
    const statements = migrationSQL.split(';').filter(s => s.trim());
    for (const stmt of statements) {
      if (stmt.trim()) {
        await client.execute(stmt);
      }
    }
    console.log('Migration executed successfully!');
    
    // Verify tables exist
    const result = await client.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name");
    console.log('\nTables created:');
    result.rows.forEach(row => console.log('  -', row.name));
    
    // Test inserting a user
    await client.execute({
      sql: 'INSERT INTO users (id, email, passwordHash, name, role, createdAt, updatedAt) VALUES (?, ?, ?, ?, ?, ?, ?)',
      args: ['test-1', 'test@example.com', 'hash', 'Test User', 'viewer', Date.now(), Date.now()]
    });
    console.log('\nTest insert: OK');
    
    // Verify the user was inserted
    const user = await client.execute({
      sql: 'SELECT * FROM users WHERE id = ?',
      args: ['test-1']
    });
    console.log('Retrieved user:', user.rows[0]);
    
    console.log('\nAll tests passed!');
    
  } catch (error) {
    console.error('Migration failed:', error.message);
    process.exit(1);
  } finally {
    client.close();
  }
})();
