/**
 * API Configuration
 *
 * Central configuration for API endpoints and settings.
 * In production, these values should come from environment variables.
 */

export const API_CONFIG = {
  // Base URL for the backend API
  // Using placeholder value - should be configured via environment variables
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001',

  // Request timeout in milliseconds
  timeout: 10000,

  // Default headers
  headers: {
    'Content-Type': 'application/json',
  },
} as const;

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
  },

  // Trading endpoints
  trading: {
    activeTrades: '/trading/active',
    tradesHistory: '/trading/history',
    pendingSignals: '/trading/signals/pending',
  },

  // System endpoints
  system: {
    forceEvolution: '/system/force-evolution',
    status: '/system/status',
  },

  // WebSocket endpoint
  websocket: '/ws',
} as const;
