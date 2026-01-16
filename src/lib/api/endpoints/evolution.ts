/**
 * Evolution API Endpoints
 *
 * API endpoint functions for evolution system data including metrics,
 * generation history, feature success rates, and mutation statistics.
 * All functions are fully typed with JSDoc comments.
 */

import { apiClient } from '../client';
import type {
  EvolutionMetrics,
  GenerationHistory,
  FeatureSuccess,
  MutationSuccess,
  ControllerDecisionHistory,
  EvolutionLog,
  EvolutionParameters,
} from '../types';

// ============================================================================
// EVOLUTION METRICS ENDPOINTS
// ============================================================================

/**
 * Get current evolution metrics
 * GET /evolution/metrics
 *
 * Retrieves the current state of the evolution system including
 * generation number, controller decision, and system statistics.
 *
 * @returns Promise resolving to evolution metrics
 *
 * @example
 * ```ts
 * const metrics = await getMetrics();
 * console.log(metrics.currentGeneration); // 42
 * console.log(metrics.controllerDecision); // 'EVOLVE_MODERATE'
 * ```
 */
export async function getMetrics(): Promise<EvolutionMetrics> {
  const { data } = await apiClient.get<EvolutionMetrics>('/evolution/metrics');
  return data;
}

/**
 * Get generation history
 * GET /evolution/generation-history
 *
 * Retrieves historical data about past evolution generations.
 * Optionally filter by number of days.
 *
 * @param days - Number of days of history to retrieve (default: all)
 * @returns Promise resolving to array of generation history entries
 *
 * @example
 * ```ts
 * // Get all generation history
 * const allHistory = await getGenerationHistory();
 *
 * // Get last 7 days
 * const weekHistory = await getGenerationHistory(7);
 * ```
 */
export async function getGenerationHistory(days?: number): Promise<GenerationHistory[]> {
  const params = days !== undefined ? { days } : undefined;
  const { data } = await apiClient.get<GenerationHistory[]>('/evolution/generation-history', params);
  return data;
}

/**
 * Get controller decision history
 * GET /evolution/controller-history
 *
 * Retrieves the history of controller decisions with reasoning
 * and performance metrics for each decision point.
 *
 * @param days - Number of days of history to retrieve (default: all)
 * @returns Promise resolving to array of controller decision entries
 *
 * @example
 * ```ts
 * const history = await getControllerHistory(30);
 * history.forEach(entry => {
 *   console.log(`Generation ${entry.generation}: ${entry.decision}`);
 *   console.log(`Reason: ${entry.reason}`);
 * });
 * ```
 */
export async function getControllerHistory(days?: number): Promise<ControllerDecisionHistory[]> {
  const params = days !== undefined ? { days } : undefined;
  const { data } = await apiClient.get<ControllerDecisionHistory[]>(
    '/evolution/controller-history',
    params
  );
  return data;
}

// ============================================================================
// FEATURE & MUTATION ENDPOINTS
// ============================================================================

/**
 * Get feature success statistics
 * GET /evolution/feature-success
 *
 * Retrieves success rate statistics for all evolved features.
 * Optionally filter by minimum number of uses.
 *
 * @param minUses - Filter by minimum number of uses (optional)
 * @returns Promise resolving to array of feature success entries
 *
 * @example
 * ```ts
 * // Get all features
 * const features = await getFeatureSuccess();
 *
 * // Get only features used at least 10 times
 * const provenFeatures = await getFeatureSuccess(10);
 *
 * // Find best performing feature
 * const best = features.reduce((a, b) => a.successRate > b.successRate ? a : b);
 * console.log(`Best feature: ${best.featureName} with ${(best.successRate * 100).toFixed(1)}% win rate`);
 * ```
 */
export async function getFeatureSuccess(minUses?: number): Promise<FeatureSuccess[]> {
  const params = minUses !== undefined ? { minUses } : undefined;
  const { data } = await apiClient.get<FeatureSuccess[]>('/evolution/feature-success', params);
  return data;
}

/**
 * Get mutation success statistics
 * GET /evolution/mutation-success
 *
 * Retrieves statistics about mutation operations including
 * success rates and fitness improvements by mutation type.
 *
 * @param minAttempts - Filter by minimum number of attempts (optional)
 * @returns Promise resolving to array of mutation success entries
 *
 * @example
 * ```ts
 * const mutations = await getMutationSuccess(5);
 * mutations.forEach(m => {
 *   console.log(`${m.mutationType}: ${(m.successRate * 100).toFixed(1)}% success rate`);
 *   console.log(`Average fitness improvement: ${m.avgFitnessImprovement.toFixed(4)}`);
 * });
 * ```
 */
export async function getMutationSuccess(minAttempts?: number): Promise<MutationSuccess[]> {
  const params = minAttempts !== undefined ? { minAttempts } : undefined;
  const { data } = await apiClient.get<MutationSuccess[]>('/evolution/mutation-success', params);
  return data;
}

// ============================================================================
// EVOLUTION LOGS ENDPOINTS
// ============================================================================

/**
 * Get evolution system logs
 * GET /evolution/logs
 *
 * Retrieves log entries from the evolution system.
 * Optionally filter by event type.
 *
 * @param eventType - Filter by event type (optional): 'MUTATION' | 'EVOLUTION_CYCLE' | 'FEATURE_SUCCESS' | 'FEATURE_FAILURE'
 * @returns Promise resolving to array of evolution log entries
 *
 * @example
 * ```ts
 * // Get all logs
 * const allLogs = await getLogs();
 *
 * // Get only mutation events
 * const mutationLogs = await getLogs('MUTATION');
 *
 * // Display recent logs
 * allLogs.slice(0, 10).forEach(log => {
 *   console.log(`[${log.timestamp}] ${log.type}: ${log.message}`);
 * });
 * ```
 */
export async function getLogs(eventType?: 'MUTATION' | 'EVOLUTION_CYCLE' | 'FEATURE_SUCCESS' | 'FEATURE_FAILURE'): Promise<EvolutionLog[]> {
  const params = eventType !== undefined ? { type: eventType } : undefined;
  const { data } = await apiClient.get<EvolutionLog[]>('/evolution/logs', params);
  return data;
}

// ============================================================================
// EVOLUTION PARAMETER MANAGEMENT
// ============================================================================

/**
 * Update evolution parameters
 * POST /evolution/parameters
 *
 * Updates the evolution system parameters. Only the provided
 * parameters will be updated; others remain unchanged.
 *
 * @param params - Evolution parameters to update
 * @returns Promise resolving when parameters are updated
 *
 * @example
 * ```ts
 * // Update mutation rate
 * await updateParameters({ mutationRate: 0.15 });
 *
 * // Update multiple parameters
 * await updateParameters({
 *   mutationRate: 0.12,
 *   crossoverRate: 0.8,
 *   populationSize: 100,
 *   selectionStrategy: 'tournament'
 * });
 * ```
 */
export async function updateParameters(params: EvolutionParameters): Promise<void> {
  await apiClient.post<void, EvolutionParameters>('/evolution/parameters', params);
}

/**
 * Get current evolution parameters
 * GET /evolution/parameters
 *
 * Retrieves the current evolution system parameters.
 *
 * @returns Promise resolving to current evolution parameters
 *
 * @example
 * ```ts
 * const params = await getParameters();
 * console.log(`Mutation rate: ${params.mutationRate}`);
 * console.log(`Selection strategy: ${params.selectionStrategy}`);
 * ```
 */
export async function getParameters(): Promise<EvolutionParameters> {
  const { data } = await apiClient.get<EvolutionParameters>('/evolution/parameters');
  return data;
}

// ============================================================================
// EVOLUTION CONTROL ENDPOINTS
// ============================================================================

/**
 * Force an immediate evolution cycle
 * POST /evolution/force
 *
 * Triggers an immediate evolution cycle, bypassing the normal
 * timing and controller decision logic.
 *
 * @returns Promise resolving when evolution cycle completes
 *
 * @example
 * ```ts
 * await forceEvolution();
 * console.log('Forced evolution cycle completed');
 * ```
 */
export async function forceEvolution(): Promise<void> {
  await apiClient.post<void>('/evolution/force');
}

/**
 * Force aggressive evolution mode
 * POST /evolution/force-aggressive
 *
 * Triggers an aggressive evolution cycle with higher mutation
 * rates and more significant changes to the feature set.
 *
 * @returns Promise resolving when aggressive evolution completes
 *
 * @example
 * ```ts
 * await forceAggressiveEvolution();
 * console.log('Aggressive evolution cycle completed');
 * ```
 */
export async function forceAggressiveEvolution(): Promise<void> {
  await apiClient.post<void>('/evolution/force-aggressive');
}

/**
 * Reset evolution to a specific generation
 * POST /evolution/reset-generation
 *
 * Resets the evolution system to a previous generation number.
 * This will discard all features and mutations from later generations.
 *
 * @param generation - Target generation number (default: 1)
 * @returns Promise resolving when reset completes
 *
 * @example
 * ```ts
 * // Reset to generation 1 (start fresh)
 * await resetToGeneration(1);
 *
 * // Reset to a known good generation
 * await resetToGeneration(25);
 * ```
 */
export async function resetToGeneration(generation: number = 1): Promise<void> {
  await apiClient.post<void, { generation: number }>('/evolution/reset-generation', { generation });
}

// ============================================================================
// EXPORTED API OBJECT
// ============================================================================

/**
 * Evolution API object
 *
 * Provides a convenient way to import all evolution-related functions:
 * ```ts
 * import { evolutionApi } from '@/lib/api';
 *
 * const metrics = await evolutionApi.getMetrics();
 * const history = await evolutionApi.getGenerationHistory(30);
 * ```
 */
export const evolutionApi = {
  // Metrics and history
  getMetrics,
  getGenerationHistory,
  getControllerHistory,

  // Features and mutations
  getFeatureSuccess,
  getMutationSuccess,

  // Logs
  getLogs,

  // Parameters
  getParameters,
  updateParameters,

  // Control
  forceEvolution,
  forceAggressiveEvolution,
  resetToGeneration,
} as const;
