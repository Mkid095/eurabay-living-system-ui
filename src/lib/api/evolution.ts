/**
 * Evolution API Service
 *
 * Service methods for interacting with evolution-related endpoints.
 * Provides type-safe API calls for evolution metrics, history, and logs.
 */

import { apiClient, ApiRequestError } from './client';
import { API_ENDPOINTS } from './config';
import type {
  EvolutionMetrics,
  GenerationHistory,
  FeatureSuccess,
  MutationSuccess,
  ControllerDecisionHistory,
  EvolutionLog,
  FeatureDetail,
} from '@/types/evolution';

/**
 * Fetch current evolution metrics
 * GET /evolution/metrics
 */
export async function fetchEvolutionMetrics(): Promise<EvolutionMetrics> {
  const { data } = await apiClient.get<EvolutionMetrics>(API_ENDPOINTS.evolution.metrics);
  return data;
}

/**
 * Fetch generation history
 * GET /evolution/generation-history
 *
 * @param days - Number of days of history to retrieve (default: all)
 */
export async function fetchGenerationHistory(days?: number): Promise<GenerationHistory[]> {
  const url = days
    ? `${API_ENDPOINTS.evolution.generationHistory}?days=${days}`
    : API_ENDPOINTS.evolution.generationHistory;

  const { data } = await apiClient.get<GenerationHistory[]>(url);
  return data;
}

/**
 * Fetch feature success data
 * GET /evolution/feature-success
 *
 * @param minUses - Filter by minimum number of uses (optional)
 */
export async function fetchFeatureSuccess(minUses?: number): Promise<FeatureSuccess[]> {
  const url = minUses
    ? `${API_ENDPOINTS.evolution.featureSuccess}?minUses=${minUses}`
    : API_ENDPOINTS.evolution.featureSuccess;

  const { data } = await apiClient.get<FeatureSuccess[]>(url);
  return data;
}

/**
 * Fetch mutation success data
 * GET /evolution/mutation-success
 *
 * @param minAttempts - Filter by minimum number of attempts (optional)
 */
export async function fetchMutationSuccess(minAttempts?: number): Promise<MutationSuccess[]> {
  const url = minAttempts
    ? `${API_ENDPOINTS.evolution.mutationSuccess}?minAttempts=${minAttempts}`
    : API_ENDPOINTS.evolution.mutationSuccess;

  const { data } = await apiClient.get<MutationSuccess[]>(url);
  return data;
}

/**
 * Fetch controller decision history
 * GET /evolution/controller-history
 *
 * @param days - Number of days of history to retrieve (default: all)
 */
export async function fetchControllerHistory(days?: number): Promise<ControllerDecisionHistory[]> {
  const url = days
    ? `${API_ENDPOINTS.evolution.controllerHistory}?days=${days}`
    : API_ENDPOINTS.evolution.controllerHistory;

  const { data } = await apiClient.get<ControllerDecisionHistory[]>(url);
  return data;
}

/**
 * Fetch evolution logs
 * GET /evolution/logs
 *
 * @param eventType - Filter by event type (optional)
 */
export async function fetchEvolutionLogs(eventType?: string): Promise<EvolutionLog[]> {
  const url = eventType
    ? `${API_ENDPOINTS.evolution.logs}?type=${eventType}`
    : API_ENDPOINTS.evolution.logs;

  const { data } = await apiClient.get<EvolutionLog[]>(url);
  return data;
}

/**
 * Update evolution parameters
 * POST /evolution/parameters
 *
 * @param params - Evolution parameters to update
 */
export async function updateEvolutionParameters(params: {
  mutationRate?: number;
  crossoverRate?: number;
  populationSize?: number;
  eliteCount?: number;
  selectionStrategy?: 'roulette' | 'tournament' | 'rank';
  fitnessTarget?: number;
}): Promise<void> {
  await apiClient.post(API_ENDPOINTS.evolution.parameters, params);
}

/**
 * Force evolution cycle
 * POST /evolution/force
 */
export async function forceEvolution(): Promise<void> {
  await apiClient.post(API_ENDPOINTS.evolutionControl.forceEvolution);
}

/**
 * Force aggressive evolution
 * POST /evolution/force-aggressive
 */
export async function forceAggressiveEvolution(): Promise<void> {
  await apiClient.post(API_ENDPOINTS.evolutionControl.forceAggressive);
}

/**
 * Reset to generation 1
 * POST /evolution/reset-generation
 *
 * @param generation - Target generation number (default: 1)
 */
export async function resetToGeneration(generation: number = 1): Promise<void> {
  await apiClient.post(API_ENDPOINTS.evolutionControl.resetToGeneration, { generation });
}

/**
 * Fetch feature details
 * GET /evolution/feature-details/:featureId
 *
 * @param featureId - The feature ID to fetch details for
 */
export async function fetchFeatureDetails(featureId: string): Promise<FeatureDetail> {
  const { data } = await apiClient.get<FeatureDetail>(
    `${API_ENDPOINTS.evolution.featureDetails}/${featureId}`
  );
  return data;
}

/**
 * Export evolution service object
 */
export const evolutionApi = {
  fetchEvolutionMetrics,
  fetchGenerationHistory,
  fetchFeatureSuccess,
  fetchMutationSuccess,
  fetchControllerHistory,
  fetchEvolutionLogs,
  updateEvolutionParameters,
  forceEvolution,
  forceAggressiveEvolution,
  resetToGeneration,
  fetchFeatureDetails,
} as const;

/**
 * Type guard to check if error is an API request error
 */
export function isApiRequestError(error: unknown): error is ApiRequestError {
  return error instanceof ApiRequestError;
}
