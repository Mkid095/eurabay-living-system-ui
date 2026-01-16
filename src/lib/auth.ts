import { betterAuth } from 'better-auth';
import { drizzleAdapter } from 'better-auth/adapters/drizzle';
import { db } from '@/lib/db';
import * as schema from '@/lib/db/schema';

/**
 * Better Auth configuration for EURABAY Living System
 *
 * Features:
 * - Email/password authentication
 * - Session management with httpOnly cookie
 * - CSRF protection enabled
 * - Access token: 15 minutes (via freshAge)
 * - Refresh token: 7 days (via expiresIn)
 */

export const auth = betterAuth({
  baseURL: process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000',
  apiURL: process.env.NEXT_PUBLIC_API_URL || '/api/auth',

  // Database adapter using existing Drizzle setup
  database: drizzleAdapter(db, {
    provider: 'sqlite',
    schema: {
      user: schema.users,
      session: null, // Will be added in US-002
      account: null, // Will be added in US-002
    },
  }),

  // Email/password authentication provider
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false, // Can be enabled later
    sendResetPassword: async () => {
      // TODO: Implement email sending for password reset (US-011)
      throw new Error('Password reset not implemented yet');
    },
    sendVerificationEmail: async () => {
      // TODO: Implement email verification
      throw new Error('Email verification not implemented yet');
    },
  },

  // Session configuration
  session: {
    expiresIn: 60 * 60 * 24 * 7, // 7 days in seconds (refresh token)
    updateAge: 24 * 60 * 60, // 1 day in seconds
    freshAge: 15 * 60, // 15 minutes - session considered fresh for this duration
  },

  // Advanced security features
  advanced: {
    // CSRF protection - by default it's enabled, use disableCSRFCheck to disable
    // We keep it enabled by not setting disableCSRFCheck

    // Cross-origin configuration
    crossSubDomainCookies: {
      enabled: false,
    },

    // Additional security headers
    useSecureCookies: process.env.NODE_ENV === 'production',
  },

  // Account linking for future OAuth providers
  account: {
    accountLinking: {
      enabled: false,
      trustedProviders: [],
    },
  },
});

/**
 * Type exports for TypeScript
 */
export type Session = typeof auth.$Infer.Session;
