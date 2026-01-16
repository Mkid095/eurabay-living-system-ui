/**
 * Configuration API Endpoints
 *
 * API endpoint functions for system configuration management.
 * All functions are fully typed with JSDoc comments.
 */

import { apiClient } from '../client';
import type {
  SystemConfiguration,
  EvolutionParameters,
} from '../types';

// ============================================================================
// CONFIGURATION ENDPOINTS
// ============================================================================

/**
 * Get system configuration
 * GET /config
 *
 * Retrieves the current system configuration including
 * evolution parameters, trading settings, and feature flags.
 *
 * @returns Promise resolving to system configuration
 *
 * @example
 * ```ts
 * const config = await getConfig();
 * console.log(`Override Mode: ${config.overrideMode}`);
 * console.log(`Evolution Enabled: ${config.evolutionEnabled}`);
 * console.log(`Auto-trading: ${config.autoTradingEnabled}`);
 * console.log(`Risk Percent: ${config.riskPercent}%`);
 * console.log(`Mutation Rate: ${config.evolution.mutationRate}`);
 * ```
 */
export async function getConfig(): Promise<SystemConfiguration> {
  const { data } = await apiClient.get<SystemConfiguration>('/config');
  return data;
}

/**
 * Update system configuration
 * PUT /config
 *
 * Updates the system configuration. Only the provided
 * fields will be updated; other fields remain unchanged.
 *
 * @param config - Partial configuration object with fields to update
 * @returns Promise resolving to updated system configuration
 *
 * @example
 * ```ts
 * // Update trading settings
 * const updated = await updateConfig({
 *   autoTradingEnabled: true,
 *   riskPercent: 2.5,
 *   maxConcurrentTrades: 5
 * });
 *
 * // Update evolution parameters
 * const evolved = await updateConfig({
 *   evolution: {
 *     mutationRate: 0.15,
 *     crossoverRate: 0.8,
 *     populationSize: 100
 *   }
 * });
 *
 * // Toggle override mode
 * const override = await updateConfig({
 *   overrideMode: true
 * });
 * ```
 */
export async function updateConfig(config: Partial<SystemConfiguration>): Promise<SystemConfiguration> {
  const { data } = await apiClient.put<SystemConfiguration, Partial<SystemConfiguration>>(
    '/config',
    config
  );
  return data;
}

/**
 * Reset configuration to defaults
 * POST /config/reset
 *
 * Resets all configuration values to their defaults.
 * Use with caution as this will discard all custom settings.
 *
 * @returns Promise resolving to default system configuration
 *
 * @example
 * ```ts
 * const defaults = await resetConfig();
 * console.log('Configuration reset to defaults');
 * ```
 */
export async function resetConfig(): Promise<SystemConfiguration> {
  const { data } = await apiClient.post<SystemConfiguration>('/config/reset');
  return data;
}

/**
 * Get evolution parameters only
 * GET /config/evolution
 *
 * Retrieves only the evolution-related configuration parameters.
 *
 * @returns Promise resolving to evolution parameters
 *
 * @example
 * ```ts
 * const params = await getEvolutionParameters();
 * console.log(`Mutation Rate: ${params.mutationRate}`);
 * console.log(`Crossover Rate: ${params.crossoverRate}`);
 * console.log(`Population Size: ${params.populationSize}`);
 * ```
 */
export async function getEvolutionParameters(): Promise<EvolutionParameters> {
  const { data } = await apiClient.get<EvolutionParameters>('/config/evolution');
  return data;
}

/**
 * Update evolution parameters only
 * PUT /config/evolution
 *
 * Updates only the evolution-related configuration parameters.
 *
 * @param params - Evolution parameters to update
 * @returns Promise resolving to updated evolution parameters
 *
 * @example
 * ```ts
 * const updated = await updateEvolutionParameters({
 *   mutationRate: 0.12,
 *   selectionStrategy: 'tournament'
 * });
 * ```
 */
export async function updateEvolutionParameters(params: Partial<EvolutionParameters>): Promise<EvolutionParameters> {
  const { data } = await apiClient.put<EvolutionParameters, Partial<EvolutionParameters>>(
    '/config/evolution',
    params
  );
  return data;
}

/**
 * Export configuration
 * GET /config/export
 *
 * Exports the current configuration as JSON for backup purposes.
 *
 * @returns Promise resolving to configuration export
 *
 * @example
 * ```ts
 * const exportData = await exportConfig();
 * console.log(JSON.stringify(exportData, null, 2));
 * ```
 */
export async function exportConfig(): Promise<{
  version: string;
  exportedAt: string;
  config: SystemConfiguration;
}> {
  const { data } = await apiClient.get('/config/export');
  return data;
}

/**
 * Import configuration
 * POST /config/import
 *
 * Imports configuration from a previous export.
 * Validates the configuration before applying.
 *
 * @param config - Configuration object to import
 * @returns Promise resolving to imported configuration
 *
 * @example
 * ```ts
 * const imported = await importConfig({
 *   overrideMode: false,
 *   evolutionEnabled: true,
 *   riskPercent: 2.0,
 *   // ... other config fields
 * });
 * ```
 */
export async function importConfig(config: Partial<SystemConfiguration>): Promise<SystemConfiguration> {
  const { data } = await apiClient.post<SystemConfiguration, Partial<SystemConfiguration>>(
    '/config/import',
    config
  );
  return data;
}

// ============================================================================
// EXPORTED API OBJECT
// ============================================================================

/**
 * Configuration API object
 *
 * Provides a convenient way to import all configuration-related functions:
 * ```ts
 * import { configApi } from '@/lib/api';
 *
 * const config = await configApi.getConfig();
 * await configApi.updateConfig({ riskPercent: 2.5 });
 * ```
 */
export const configApi = {
  getConfig,
  updateConfig,
  resetConfig,

  // Evolution-specific
  getEvolutionParameters,
  updateEvolutionParameters,

  // Import/Export
  exportConfig,
  importConfig,
} as const;
