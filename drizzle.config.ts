import type { Config } from 'drizzle-kit';

export default {
  schema: './src/lib/db/schema.ts',
  out: './drizzle',
  driver: 'turso',
  dbCredentials: {
    url: process.env.TURSO_DATABASE_URL || 'file:.local/db.sqlite',
    authToken: process.env.TURSO_AUTH_TOKEN,
  },
} satisfies Config;
