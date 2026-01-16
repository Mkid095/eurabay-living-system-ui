/**
 * System Status API Endpoints
 *
 * API endpoint functions for system status, health, and control operations.
 * All functions are fully typed with JSDoc comments.
 */

import { apiClient } from '../client';
import type {
  SystemStatus,
  SystemHealth,
  SystemConfiguration,
} from '../types';

// ============================================================================
// SYSTEM STATUS ENDPOINTS
// ============================================================================

/**
 * Get current system status
 * GET /system/status
 *
 * @returns Promise resolving to system status information
 *
 * @example
 * ```ts
 * const status = await getStatus();
 * console.log(status.generation); // 42
 * ```
 */
export async function getStatus(): Promise<SystemStatus> {
  const { data } = await apiClient.get<SystemStatus>('/system/status');
  return data;
}

/**
 * Get detailed system health information
 * GET /system/health
 *
 * @returns Promise resolving to system health details
 *
 * @example
 * ```ts
 * const health = await getHealth();
 * console.log(health.cpuUsage); // 45.2
 * ```
 */
export async function getHealth(): Promise<SystemHealth> {
  const { data } = await apiClient.get<SystemHealth>('/system/health');
  return data;
}

// ============================================================================
// SYSTEM CONTROL ENDPOINTS
// ============================================================================

/**
 * Start the trading system
 * POST /system/start
 *
 * Initiates the trading system, enabling automated trading and evolution.
 *
 * @returns Promise resolving when system has started
 *
 * @example
 * ```ts
 * await startSystem();
 * console.log('System started successfully');
 * ```
 */
export async function startSystem(): Promise<void> {
  await apiClient.post<void>('/system/start');
}

/**
 * Stop the trading system
 * POST /system/stop
 *
 * Gracefully stops the trading system. Active positions will be managed
 * according to the system's stop-loss and take-profit rules.
 *
 * @returns Promise resolving when system has stopped
 *
 * @example
 * ```ts
 * await stopSystem();
 * console.log('System stopped successfully');
 * ```
 */
export async function stopSystem(): Promise<void> {
  await apiClient.post<void>('/system/stop');
}

/**
 * Force an evolution cycle
 * POST /system/force-evolution
 *
 * Triggers an immediate evolution cycle regardless of the current
 * controller decision. This can be used to manually accelerate
 * the evolution process.
 *
 * @returns Promise resolving when evolution cycle completes
 *
 * @example
 * ```ts
 * await forceEvolution();
 * console.log('Evolution cycle triggered');
 * ```
 */
export async function forceEvolution(): Promise<void> {
  await apiClient.post<void>('/system/force-evolution');
}

/**
 * Toggle system override mode
 * POST /system/override
 *
 * Enables or disables override mode, which allows manual control
 * of trading decisions and bypasses the automated evolution system.
 *
 * @param enabled - Whether to enable (true) or disable (false) override mode
 * @returns Promise resolving to updated system configuration
 *
 * @example
 * ```ts
 * const config = await toggleOverride(true);
 * console.log(config.overrideMode); // true
 * ```
 */
export async function toggleOverride(enabled: boolean): Promise<SystemConfiguration> {
  const { data } = await apiClient.post<SystemConfiguration, { enabled: boolean }>(
    '/system/override',
    { enabled }
  );
  return data;
}

/**
 * Get current system configuration
 * GET /system/config
 *
 * Retrieves the current system configuration including evolution parameters,
 * trading settings, and feature flags.
 *
 * @returns Promise resolving to system configuration
 *
 * @example
 * ```ts
 * const config = await getConfig();
 * console.log(config.evolution.mutationRate); // 0.1
 * ```
 */
export async function getConfig(): Promise<SystemConfiguration> {
  const { data } = await apiClient.get<SystemConfiguration>('/system/config');
  return data;
}

/**
 * Update system configuration
 * PUT /system/config
 *
 * Updates the system configuration with new values. Only the provided
 * fields will be updated; other fields remain unchanged.
 *
 * @param config - Partial configuration object with fields to update
 * @returns Promise resolving to updated system configuration
 *
 * @example
 * ```ts
 * const updated = await updateConfig({
 *   evolution: { mutationRate: 0.15 },
 *   riskPercent: 2.5
 * });
 * ```
 */
export async function updateConfig(
  config: Partial<SystemConfiguration>
): Promise<SystemConfiguration> {
  const { data } = await apiClient.put<SystemConfiguration, Partial<SystemConfiguration>>(
    '/system/config',
    config
  );
  return data;
}

// ============================================================================
// EXPORTED API OBJECT
// ============================================================================

/**
 * System status and control API object
 *
 * Provides a convenient way to import all system-related functions:
 * ```ts
 * import { systemApi } from '@/lib/api';
 *
 * const status = await systemApi.getStatus();
 * const health = await systemApi.getHealth();
 * ```
 */
export const systemApi = {
  // Status endpoints
  getStatus,
  getHealth,

  // Control endpoints
  startSystem,
  stopSystem,
  forceEvolution,
  toggleOverride,

  // Configuration endpoints
  getConfig,
  updateConfig,
} as const;
