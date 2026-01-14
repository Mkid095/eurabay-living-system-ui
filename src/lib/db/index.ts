import { drizzle } from 'drizzle-orm/libsql';
import { createClient } from '@libsql/client';
import * as schema from './schema';

/**
 * Database client configuration
 * Supports both local development (SQLite file) and production (Turso)
 */

const databaseUrl = process.env.TURSO_DATABASE_URL || 'file:.local/db.sqlite';

const clientConfig: { url: string; authToken?: string } = {
  url: databaseUrl,
};

// Add auth token for production (Turso)
if (process.env.TURSO_AUTH_TOKEN) {
  clientConfig.authToken = process.env.TURSO_AUTH_TOKEN;
}

const client = createClient(clientConfig);

/**
 * Database instance
 * Use this to interact with the database using Drizzle ORM
 */
export const db = drizzle(client, { schema });
