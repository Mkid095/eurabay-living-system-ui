/**
 * Manual Override API Endpoints
 *
 * API endpoint functions for manual override of active trade management.
 * Allows traders to manually control and override automated management.
 */

import { apiClient } from '../client';
import type {
  ManualOverrideState,
  ManualOverrideResult,
  ManualOverrideRecord,
  ManualCloseRequest,
  ManualStopLossTakeProfitRequest,
  ToggleManagementRequest,
} from '../types';

// ============================================================================
// MANUAL OVERRIDE ENDPOINTS
// ============================================================================

/**
 * Get manual override state for a position
 * GET /trades/{ticket}/override-state
 *
 * Retrieves the current manual override state for a position including
 * which automated features are disabled and any manual values set.
 *
 * @param ticket - The trade ticket to query
 * @returns Promise resolving to manual override state
 *
 * @example
 * ```ts
 * const state = await getManualOverrideState('TRD-001');
 * console.log(`Management paused: ${state.managementPaused}`);
 * console.log(`Trailing stopped: ${state.trailingStopped}`);
 * ```
 */
export async function getManualOverrideState(ticket: string): Promise<ManualOverrideState> {
  const { data } = await apiClient.get<ManualOverrideState>(
    `/trades/${ticket}/override-state`
  );
  return data;
}

/**
 * Get all manual override history
 * GET /trades/override-history
 *
 * Retrieves the history of all manual override actions performed.
 * Optionally filter by specific trade ticket.
 *
 * @param options - Optional filters for the history
 * @returns Promise resolving to array of override records
 *
 * @example
 * ```ts
 * // Get all override history
 * const allHistory = await getManualOverrideHistory();
 *
 * // Get history for specific trade
 * const tradeHistory = await getManualOverrideHistory({ ticket: 'TRD-001' });
 * ```
 */
export async function getManualOverrideHistory(options?: {
  /** Filter by trade ticket */
  ticket?: string;
  /** Maximum number of records to return */
  limit?: number;
}): Promise<ManualOverrideRecord[]> {
  const params = options ? {
    ticket: options.ticket,
    limit: options.limit,
  } : undefined;
  const { data } = await apiClient.get<ManualOverrideRecord[]>(
    '/trades/override-history',
    params
  );
  return data;
}

/**
 * Manually close a position
 * POST /trades/{ticket}/manual-close
 *
 * Closes a position manually with optional partial close.
 * Requires user and reason for audit trail.
 *
 * @param ticket - The trade ticket to close
 * @param request - Close request details
 * @returns Promise resolving to override result
 *
 * @example
 * ```ts
 * // Close full position
 * const result = await manualClosePosition('TRD-001', {
 *   user: 'trader1',
 *   reason: 'Taking manual profit at resistance level',
 *   confirmed: true
 * });
 *
 * // Close partial position
 * const partialResult = await manualClosePosition('TRD-002', {
 *   lots: 0.5,
 *   user: 'trader1',
 *   reason: 'Banking partial profits',
 *   confirmed: true
 * });
 * ```
 */
export async function manualClosePosition(
  ticket: string,
  request: ManualCloseRequest
): Promise<ManualOverrideResult> {
  const { data } = await apiClient.post<ManualOverrideResult, ManualCloseRequest>(
    `/trades/${ticket}/manual-close`,
    { ticket, ...request }
  );
  return data;
}

/**
 * Set manual stop loss or take profit
 * POST /trades/{ticket}/manual-sltp
 *
 * Sets manual stop loss and/or take profit values for a position.
 * This overrides any automated SL/TP management.
 *
 * @param ticket - The trade ticket to modify
 * @param request - SL/TP modification details
 * @returns Promise resolving to override result
 *
 * @example
 * ```ts
 * // Set stop loss
 * const result = await setManualStopLossTakeProfit('TRD-001', {
 *   stopLoss: 1.0850,
 *   user: 'trader1',
 *   reason: 'Support level at 1.0850',
 *   confirmed: true
 * });
 *
 * // Set both stop loss and take profit
 * const result2 = await setManualStopLossTakeProfit('TRD-002', {
 *   stopLoss: 1.0800,
 *   takeProfit: 1.0950,
 *   user: 'trader1',
 *   reason: 'Tightening risk/reward',
 *   confirmed: true
 * });
 * ```
 */
export async function setManualStopLossTakeProfit(
  ticket: string,
  request: ManualStopLossTakeProfitRequest
): Promise<ManualOverrideResult> {
  const { data } = await apiClient.post<ManualOverrideResult, ManualStopLossTakeProfitRequest>(
    `/trades/${ticket}/manual-sltp`,
    request
  );
  return data;
}

/**
 * Disable trailing stop for a position
 * POST /trades/{ticket}/disable-trailing-stop
 *
 * Disables the trailing stop feature for a position.
 * The position will keep its current stop loss without further updates.
 *
 * @param ticket - The trade ticket
 * @param user - User performing the action
 * @param reason - Reason for disabling trailing stop
 * @param confirmed - Whether the action was confirmed
 * @returns Promise resolving to override result
 *
 * @example
 * ```ts
 * const result = await disableTrailingStop('TRD-001', 'trader1', 'Market volatility too high', true);
 * ```
 */
export async function disableTrailingStop(
  ticket: string,
  user: string,
  reason: string,
  confirmed: boolean = false
): Promise<ManualOverrideResult> {
  const { data } = await apiClient.post<ManualOverrideResult, { user: string; reason: string; confirmed?: boolean }>(
    `/trades/${ticket}/disable-trailing-stop`,
    { user, reason, confirmed }
  );
  return data;
}

/**
 * Disable breakeven for a position
 * POST /trades/{ticket}/disable-breakeven
 *
 * Disables the breakeven feature for a position.
 * The position will not automatically move SL to breakeven.
 *
 * @param ticket - The trade ticket
 * @param user - User performing the action
 * @param reason - Reason for disabling breakeven
 * @param confirmed - Whether the action was confirmed
 * @returns Promise resolving to override result
 *
 * @example
 * ```ts
 * const result = await disableBreakeven('TRD-001', 'trader1', 'Want to let position run', true);
 * ```
 */
export async function disableBreakeven(
  ticket: string,
  user: string,
  reason: string,
  confirmed: boolean = false
): Promise<ManualOverrideResult> {
  const { data } = await apiClient.post<ManualOverrideResult, { user: string; reason: string; confirmed?: boolean }>(
    `/trades/${ticket}/disable-breakeven`,
    { user, reason, confirmed }
  );
  return data;
}

/**
 * Pause or resume active management for a position
 * POST /trades/{ticket}/toggle-management
 *
 * Pauses or resumes all active management for a position.
 * When paused, no automated actions (trailing stop, breakeven, partial profit, etc.) will be taken.
 *
 * @param ticket - The trade ticket
 * @param request - Toggle management request details
 * @returns Promise resolving to override result
 *
 * @example
 * ```ts
 * // Pause management
 * const pauseResult = await toggleManagement('TRD-001', {
 *   action: 'pause',
 *   user: 'trader1',
 *   reason: 'Manual intervention needed',
 *   confirmed: true
 * });
 *
 * // Resume management
 * const resumeResult = await toggleManagement('TRD-001', {
 *   action: 'resume',
 *   user: 'trader1',
 *   reason: 'Resuming automated management',
 *   confirmed: true
 * });
 * ```
 */
export async function toggleManagement(
  ticket: string,
  request: ToggleManagementRequest
): Promise<ManualOverrideResult> {
  const { data } = await apiClient.post<ManualOverrideResult, ToggleManagementRequest>(
    `/trades/${ticket}/toggle-management`,
    request
  );
  return data;
}

/**
 * Pause active management for a position
 * POST /trades/{ticket}/pause-management
 *
 * Convenience method to pause all active management for a position.
 *
 * @param ticket - The trade ticket
 * @param user - User performing the action
 * @param reason - Reason for pausing
 * @param confirmed - Whether the action was confirmed
 * @returns Promise resolving to override result
 *
 * @example
 * ```ts
 * const result = await pauseManagement('TRD-001', 'trader1', 'News event approaching', true);
 * ```
 */
export async function pauseManagement(
  ticket: string,
  user: string,
  reason: string,
  confirmed: boolean = false
): Promise<ManualOverrideResult> {
  return toggleManagement(ticket, {
    action: 'pause',
    user,
    reason,
    confirmed,
  });
}

/**
 * Resume active management for a position
 * POST /trades/{ticket}/resume-management
 *
 * Convenience method to resume all active management for a position.
 *
 * @param ticket - The trade ticket
 * @param user - User performing the action
 * @param reason - Reason for resuming
 * @param confirmed - Whether the action was confirmed
 * @returns Promise resolving to override result
 *
 * @example
 * ```ts
 * const result = await resumeManagement('TRD-001', 'trader1', 'News event passed', true);
 * ```
 */
export async function resumeManagement(
  ticket: string,
  user: string,
  reason: string,
  confirmed: boolean = false
): Promise<ManualOverrideResult> {
  return toggleManagement(ticket, {
    action: 'resume',
    user,
    reason,
    confirmed,
  });
}

// ============================================================================
// EXPORTED API OBJECT
// ============================================================================

/**
 * Manual override API object
 *
 * Provides a convenient way to import all manual override functions:
 * ```ts
 * import { manualOverrideApi } from '@/lib/api';
 *
 * const state = await manualOverrideApi.getManualOverrideState('TRD-001');
 * const result = await manualOverrideApi.pauseManagement('TRD-001', 'trader1', 'News event');
 * ```
 */
export const manualOverrideApi = {
  // Query override state
  getManualOverrideState,
  getManualOverrideHistory,

  // Position control
  manualClosePosition,
  setManualStopLossTakeProfit,

  // Feature control
  disableTrailingStop,
  disableBreakeven,

  // Management control
  toggleManagement,
  pauseManagement,
  resumeManagement,
} as const;
