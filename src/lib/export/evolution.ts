/**
 * Evolution Export Utilities
 *
 * Functions for exporting evolution data to CSV and JSON formats.
 * Supports generation history, feature success, and mutation success data.
 */

import { apiClient } from '@/lib/api/client';
import type {
  GenerationHistory,
  FeatureSuccess,
  MutationSuccess,
} from '@/types/evolution';

/**
 * Export format options
 */
export type EvolutionExportFormat = 'csv' | 'json';

/**
 * Evolution export data types
 */
export type EvolutionExportType = 'generation-history' | 'feature-success' | 'mutation-success' | 'all';

/**
 * API response type for generation history endpoint
 */
interface GenerationHistoryApiResponse {
  history: GenerationHistory[];
}

/**
 * Fetch generation history from API
 * GET /evolution/generation-history
 */
async function fetchGenerationHistory(days?: number): Promise<GenerationHistory[]> {
  const params: Record<string, number> = {};
  if (days) {
    params.days = days;
  }
  const { data } = await apiClient.get<GenerationHistory[]>('/evolution/generation-history', params);
  return data || [];
}

/**
 * Fetch feature success data from API
 * GET /evolution/feature-success
 */
async function fetchFeatureSuccess(minUses?: number): Promise<FeatureSuccess[]> {
  const params: Record<string, number> = {};
  if (minUses) {
    params.minUses = minUses;
  }
  const { data } = await apiClient.get<FeatureSuccess[]>('/evolution/feature-success', params);
  return data || [];
}

/**
 * Fetch mutation success data from API
 * GET /evolution/mutation-success
 */
async function fetchMutationSuccess(minAttempts?: number): Promise<MutationSuccess[]> {
  const params: Record<string, number> = {};
  if (minAttempts) {
    params.minAttempts = minAttempts;
  }
  const { data } = await apiClient.get<MutationSuccess[]>('/evolution/mutation-success', params);
  return data || [];
}

/**
 * Format generation history for CSV export
 * Headers: generation, timestamp, fitness, avgPerformance
 */
function formatGenerationHistoryForCSV(history: GenerationHistory[]): string {
  const headers = ['generation', 'timestamp', 'fitness', 'avgPerformance'];
  const rows = history.map(entry => [
    entry.generation.toString(),
    entry.timestamp,
    entry.fitness.toFixed(4),
    entry.avgPerformance.toFixed(4),
  ]);

  const headerRow = headers.join(',');
  const dataRows = rows.map(row => row.join(','));
  return [headerRow, ...dataRows].join('\n');
}

/**
 * Format feature success for CSV export
 * Headers: featureId, featureName, successRate, totalUses, wins, losses, avgPnL
 */
function formatFeatureSuccessForCSV(features: FeatureSuccess[]): string {
  const headers = ['featureId', 'featureName', 'successRate', 'totalUses', 'wins', 'losses', 'avgPnL'];
  const rows = features.map(feature => [
    feature.featureId,
    feature.featureName,
    feature.successRate.toFixed(4),
    feature.totalUses.toString(),
    feature.wins.toString(),
    feature.losses.toString(),
    feature.avgPnL.toFixed(2),
  ]);

  const headerRow = headers.join(',');
  const dataRows = rows.map(row => row.join(','));
  return [headerRow, ...dataRows].join('\n');
}

/**
 * Format mutation success for CSV export
 * Headers: mutationType, successRate, totalAttempts, successful, avgFitnessImprovement
 */
function formatMutationSuccessForCSV(mutations: MutationSuccess[]): string {
  const headers = ['mutationType', 'successRate', 'totalAttempts', 'successful', 'avgFitnessImprovement'];
  const rows = mutations.map(mutation => [
    mutation.mutationType,
    mutation.successRate.toFixed(4),
    mutation.totalAttempts.toString(),
    mutation.successful.toString(),
    mutation.avgFitnessImprovement.toFixed(4),
  ]);

  const headerRow = headers.join(',');
  const dataRows = rows.map(row => row.join(','));
  return [headerRow, ...dataRows].join('\n');
}

/**
 * Generate filename for evolution export
 * Format: evolution_YYYY-MM-DD.{extension}
 */
function generateExportFilename(extension: string): string {
  const date = new Date();
  const dateStr = date.toISOString().split('T')[0];
  return `evolution_${dateStr}.${extension}`;
}

/**
 * Trigger browser download for exported data
 */
function triggerDownload(content: string, filename: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

/**
 * Export evolution history to CSV format
 *
 * @param days - Optional number of days to filter
 * @returns Promise that resolves when export is complete
 */
export async function exportEvolutionHistoryToCSV(days?: number): Promise<void> {
  try {
    const history = await fetchGenerationHistory(days);
    const csv = formatGenerationHistoryForCSV(history);
    const filename = generateExportFilename('csv');
    triggerDownload(csv, filename, 'text/csv');
  } catch (error) {
    throw new Error(
      `Failed to export evolution history to CSV: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Export evolution history to JSON format
 *
 * @param days - Optional number of days to filter
 * @returns Promise that resolves when export is complete
 */
export async function exportEvolutionHistoryToJSON(days?: number): Promise<void> {
  try {
    const history = await fetchGenerationHistory(days);
    const json = JSON.stringify(history, null, 2);
    const filename = generateExportFilename('json');
    triggerDownload(json, filename, 'application/json');
  } catch (error) {
    throw new Error(
      `Failed to export evolution history to JSON: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Export evolution data to specified format
 *
 * @param format - Export format ('csv' or 'json')
 * @param days - Optional number of days to filter
 * @returns Promise that resolves when export is complete
 */
export async function exportEvolutionHistory(
  format: EvolutionExportFormat,
  days?: number
): Promise<void> {
  if (format === 'csv') {
    return exportEvolutionHistoryToCSV(days);
  }
  return exportEvolutionHistoryToJSON(days);
}

/**
 * Export feature success data to CSV format
 *
 * @param minUses - Optional minimum number of uses to filter
 * @returns Promise that resolves when export is complete
 */
export async function exportFeatureSuccessToCSV(minUses?: number): Promise<void> {
  try {
    const features = await fetchFeatureSuccess(minUses);
    const csv = formatFeatureSuccessForCSV(features);
    const filename = `feature_success_${generateExportFilename('csv')}`;
    triggerDownload(csv, filename, 'text/csv');
  } catch (error) {
    throw new Error(
      `Failed to export feature success to CSV: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Export feature success data to JSON format
 *
 * @param minUses - Optional minimum number of uses to filter
 * @returns Promise that resolves when export is complete
 */
export async function exportFeatureSuccessToJSON(minUses?: number): Promise<void> {
  try {
    const features = await fetchFeatureSuccess(minUses);
    const json = JSON.stringify(features, null, 2);
    const filename = `feature_success_${generateExportFilename('json')}`;
    triggerDownload(json, filename, 'application/json');
  } catch (error) {
    throw new Error(
      `Failed to export feature success to JSON: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Export mutation success data to CSV format
 *
 * @param minAttempts - Optional minimum number of attempts to filter
 * @returns Promise that resolves when export is complete
 */
export async function exportMutationSuccessToCSV(minAttempts?: number): Promise<void> {
  try {
    const mutations = await fetchMutationSuccess(minAttempts);
    const csv = formatMutationSuccessForCSV(mutations);
    const filename = `mutation_success_${generateExportFilename('csv')}`;
    triggerDownload(csv, filename, 'text/csv');
  } catch (error) {
    throw new Error(
      `Failed to export mutation success to CSV: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Export mutation success data to JSON format
 *
 * @param minAttempts - Optional minimum number of attempts to filter
 * @returns Promise that resolves when export is complete
 */
export async function exportMutationSuccessToJSON(minAttempts?: number): Promise<void> {
  try {
    const mutations = await fetchMutationSuccess(minAttempts);
    const json = JSON.stringify(mutations, null, 2);
    const filename = `mutation_success_${generateExportFilename('json')}`;
    triggerDownload(json, filename, 'application/json');
  } catch (error) {
    throw new Error(
      `Failed to export mutation success to JSON: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}

/**
 * Export all evolution data to specified format
 *
 * @param format - Export format ('csv' or 'json')
 * @returns Promise that resolves when export is complete
 */
export async function exportAllEvolutionData(format: EvolutionExportFormat): Promise<void> {
  try {
    const [history, features, mutations] = await Promise.all([
      fetchGenerationHistory(),
      fetchFeatureSuccess(),
      fetchMutationSuccess(),
    ]);

    const data = {
      generationHistory: history,
      featureSuccess: features,
      mutationSuccess: mutations,
      exportDate: new Date().toISOString(),
    };

    if (format === 'csv') {
      // For CSV, combine all three sections
      const csvSections = [
        '# GENERATION HISTORY',
        formatGenerationHistoryForCSV(history),
        '',
        '# FEATURE SUCCESS',
        formatFeatureSuccessForCSV(features),
        '',
        '# MUTATION SUCCESS',
        formatMutationSuccessForCSV(mutations),
      ];
      const csv = csvSections.join('\n');
      const filename = generateExportFilename('csv');
      triggerDownload(csv, filename, 'text/csv');
    } else {
      const json = JSON.stringify(data, null, 2);
      const filename = generateExportFilename('json');
      triggerDownload(json, filename, 'application/json');
    }
  } catch (error) {
    throw new Error(
      `Failed to export all evolution data: ${error instanceof Error ? error.message : 'Unknown error'}`
    );
  }
}
