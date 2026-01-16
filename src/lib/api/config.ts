/**
 * API Configuration
 *
 * Central configuration for API endpoints and settings.
 * In production, these values should come from environment variables.
 */

export const API_CONFIG = {
  // Base URL for the backend API
  // Using placeholder value - should be configured via environment variables
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api',

  // WebSocket URL for real-time updates
  wsURL: process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws',

  // Request timeout in milliseconds (from NEXT_PUBLIC_API_TIMEOUT env var, default 30s)
  timeout: Number(process.env.NEXT_PUBLIC_API_TIMEOUT) || 30000,

  // Default headers
  headers: {
    'Content-Type': 'application/json',
  },
} as const;

/**
 * Validate required environment variables
 * Throws an error if required variables are missing in production
 */
export function validateEnvVars(): void {
  const requiredVars: Array<{ name: string; value: string | undefined }> = [
    { name: 'NEXT_PUBLIC_API_URL', value: process.env.NEXT_PUBLIC_API_URL },
    { name: 'NEXT_PUBLIC_WS_URL', value: process.env.NEXT_PUBLIC_WS_URL },
    { name: 'NEXT_PUBLIC_API_TIMEOUT', value: process.env.NEXT_PUBLIC_API_TIMEOUT },
  ];

  const missingVars = requiredVars.filter((v) => !v.value);

  if (missingVars.length > 0 && process.env.NODE_ENV === 'production') {
    throw new Error(
      `Missing required environment variables: ${missingVars.map((v) => v.name).join(', ')}`
    );
  }

  // Log warnings in development if vars are missing
  if (missingVars.length > 0 && process.env.NODE_ENV === 'development') {
    console.warn(
      `[API Config] Using default values for: ${missingVars.map((v) => v.name).join(', ')}`
    );
  }

  // Validate API timeout is a valid number
  const timeout = Number(process.env.NEXT_PUBLIC_API_TIMEOUT);
  if (process.env.NEXT_PUBLIC_API_TIMEOUT && (isNaN(timeout) || timeout <= 0)) {
    console.warn('[API Config] NEXT_PUBLIC_API_TIMEOUT must be a positive number, using default 30000ms');
  }
}

/**
 * API endpoint paths
 * Organized by feature/module for easy maintenance
 */
export const API_ENDPOINTS = {
  // Evolution endpoints
  evolution: {
    metrics: '/evolution/metrics',
    generationHistory: '/evolution/generation-history',
    featureSuccess: '/evolution/feature-success',
    mutationSuccess: '/evolution/mutation-success',
    controllerHistory: '/evolution/controller-history',
    logs: '/evolution/logs',
    parameters: '/evolution/parameters',
    featureDetails: '/evolution/feature-details',
  },

  // Trading endpoints
  trading: {
    activeTrades: '/trades/active',
    tradesHistory: '/trades/recent',
    pendingSignals: '/trades/pending-signals',
    executionLog: '/trades/execution-log',
  },

  // System endpoints
  system: {
    forceEvolution: '/system/force-evolution',
    status: '/system/status',
    start: '/system/start',
    stop: '/system/stop',
  },

  // Evolution control endpoints (for manual triggers)
  evolutionControl: {
    forceEvolution: '/evolution/force',
    forceAggressive: '/evolution/force-aggressive',
    resetToGeneration: '/evolution/reset-generation',
  },

  // WebSocket endpoint
  websocket: '/ws',
} as const;
