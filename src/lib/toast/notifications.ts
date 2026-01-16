/**
 * Toast Notification Utilities
 *
 * Centralized toast notification system with actionable buttons support,
 * throttling to prevent spam, and consistent styling across the application.
 */

import { toast } from 'sonner';
import type { PendingSignal, EvolvedTrade, ClosedTrade } from '@/types/evolution';

/**
 * Default throttle duration for toast notifications (in milliseconds)
 * Prevents spamming similar toasts
 */
export const DEFAULT_TOAST_THROTTLE_MS = 5000;

/**
 * Toast action button configuration
 */
export interface ToastAction {
  label: string;
  onClick: () => void;
}

/**
 * Toast notification options with support for actionable buttons
 */
export interface ToastOptions {
  description?: string;
  duration?: number;
  action?: ToastAction;
  actions?: ToastAction[];
  id?: string;
}

/**
 * Toast throttle manager to prevent spam
 */
class ToastThrottleManager {
  private lastShownTimes = new Map<string, number>();
  private throttleMs: number;

  constructor(throttleMs: number = DEFAULT_TOAST_THROTTLE_MS) {
    this.throttleMs = throttleMs;
  }

  /**
   * Check if a toast should be throttled
   * @param key Unique key for the toast type
   * @returns true if toast should be throttled (skipped), false otherwise
   */
  shouldThrottle(key: string): boolean {
    const now = Date.now();
    const lastShown = this.lastShownTimes.get(key);

    if (lastShown && now - lastShown < this.throttleMs) {
      return true;
    }

    this.lastShownTimes.set(key, now);

    // Clean up old entries
    setTimeout(() => {
      this.lastShownTimes.delete(key);
    }, this.throttleMs * 2);

    return false;
  }

  /**
   * Clear all throttle timestamps
   */
  clear(): void {
    this.lastShownTimes.clear();
  }

  /**
   * Update throttle duration
   */
  setThrottleMs(ms: number): void {
    this.throttleMs = ms;
  }
}

/**
 * Global throttle manager instance
 */
const globalThrottleManager = new ToastThrottleManager();

/**
 * Show success toast with optional actions
 */
export function showSuccessToast(title: string, options: ToastOptions = {}): string | undefined {
  const { description, duration, action, actions, id } = options;

  return toast.success(title, {
    description,
    duration,
    id,
    ...(action && { action }),
    ...(actions && actions.length > 0 && { action: actions[0] }),
  });
}

/**
 * Show error toast with optional actions
 */
export function showErrorToast(title: string, options: ToastOptions = {}): string | undefined {
  const { description, duration, action, actions, id } = options;

  return toast.error(title, {
    description,
    duration,
    id,
    ...(action && { action }),
    ...(actions && actions.length > 0 && { action: actions[0] }),
  });
}

/**
 * Show warning toast with optional actions
 */
export function showWarningToast(title: string, options: ToastOptions = {}): string | undefined {
  const { description, duration, action, actions, id } = options;

  return toast.warning(title, {
    description,
    duration,
    id,
    ...(action && { action }),
    ...(actions && actions.length > 0 && { action: actions[0] }),
  });
}

/**
 * Show info toast with optional actions
 */
export function showInfoToast(title: string, options: ToastOptions = {}): string | undefined {
  const { description, duration, action, actions, id } = options;

  return toast.info(title, {
    description,
    duration,
    id,
    ...(action && { action }),
    ...(actions && actions.length > 0 && { action: actions[0] }),
  });
}

/**
 * Show toast with throttling to prevent spam
 * @param type Toast type (success, error, warning, info)
 * @param title Toast title
 * @param options Toast options
 * @param throttleKey Unique key for throttling (optional)
 * @returns Toast ID if shown, undefined if throttled
 */
export function showThrottledToast(
  type: 'success' | 'error' | 'warning' | 'info',
  title: string,
  options: ToastOptions = {},
  throttleKey?: string
): string | undefined {
  if (throttleKey && globalThrottleManager.shouldThrottle(throttleKey)) {
    return undefined;
  }

  switch (type) {
    case 'success':
      return showSuccessToast(title, options);
    case 'error':
      return showErrorToast(title, options);
    case 'warning':
      return showWarningToast(title, options);
    case 'info':
      return showInfoToast(title, options);
  }
}

/**
 * Toast notification functions for specific trading events
 */

/**
 * Show toast for new pending signal with Approve/Reject buttons
 * @param signal The pending signal
 * @param onApprove Callback when approve button is clicked
 * @param onReject Callback when reject button is clicked
 * @param onView Callback when view button is clicked (optional)
 * @param throttleKey Unique key for throttling (optional)
 */
export function showNewSignalToast(
  signal: PendingSignal,
  onApprove: () => void,
  onReject: () => void,
  onView?: () => void,
  throttleKey?: string
): string | undefined {
  const confidence = (signal.confidence * 100).toFixed(0);
  const title = `New ${signal.signalType} Signal`;
  const description = `${signal.symbol} - Confidence: ${confidence}%`;

  return showThrottledToast(
    'success',
    title,
    {
      description,
      duration: 10000,
      actions: [
        ...(onView ? [{ label: 'View', onClick: onView }] : []),
        { label: 'Approve', onClick: onApprove },
        { label: 'Reject', onClick: onReject },
      ],
    },
    throttleKey || `signal-${signal.id}`
  );
}

/**
 * Show toast for trade closed with significant P&L
 * @param trade The closed trade
 * @param onView Callback when view button is clicked (optional)
 * @param throttleKey Unique key for throttling (optional)
 */
export function showTradeClosedToast(
  trade: ClosedTrade | EvolvedTrade,
  onView?: () => void,
  throttleKey?: string
): string | undefined {
  const isProfit = trade.pnl >= 0;
  const pnlText = `${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)}`;
  const title = isProfit ? 'Trade Closed - Profit' : 'Trade Closed - Loss';
  const description = `${trade.symbol}: ${pnlText} (${trade.pnlPercent?.toFixed(1) || '0'}%)`;

  return showThrottledToast(
    isProfit ? 'success' : 'error',
    title,
    {
      description,
      duration: 8000,
      ...(onView && { action: { label: 'View', onClick: onView } }),
    },
    throttleKey || `trade-closed-${trade.ticket}`
  );
}

/**
 * Show toast for significant P&L change on active trade
 * @param trade The trade with P&L change
 * @ pnlChangePercent The P&L change percentage
 * @param onView Callback when view button is clicked (optional)
 * @param throttleKey Unique key for throttling (optional)
 */
export function showPnLChangeToast(
  trade: EvolvedTrade,
  pnlChangePercent: number,
  onView?: () => void,
  throttleKey?: string
): string | undefined {
  const isProfit = trade.pnl >= 0;
  const title = isProfit ? 'Profit Increase' : 'Loss Increase';
  const pnlText = `${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)}`;
  const description = `${trade.symbol}: ${pnlText} (${pnlChangePercent.toFixed(1)}% change)`;

  return showThrottledToast(
    isProfit ? 'success' : 'error',
    title,
    {
      description,
      duration: 6000,
      ...(onView && { action: { label: 'View', onClick: onView } }),
    },
    throttleKey || `pnl-change-${trade.ticket}-${Date.now()}`
  );
}

/**
 * Show toast for evolution generation change
 * @param generation The new generation number
 * @param fitness The best fitness value
 * @param onView Callback when view button is clicked (optional)
 * @param throttleKey Unique key for throttling (optional)
 */
export function showGenerationChangedToast(
  generation: number,
  fitness: number,
  onView?: () => void,
  throttleKey?: string
): string | undefined {
  return showThrottledToast(
    'info',
    'New Generation',
    {
      description: `Generation ${generation} started. Best fitness: ${fitness.toFixed(2)}`,
      duration: 5000,
      ...(onView && { action: { label: 'View', onClick: onView } }),
    },
    throttleKey || `generation-${generation}`
  );
}

/**
 * Show toast for MT5 connection status change
 * @param connected Whether MT5 is connected
 * @param server MT5 server name
 * @param accountId MT5 account ID
 * @param reason Disconnection reason (if disconnected)
 * @param throttleKey Unique key for throttling (optional)
 */
export function showMT5ConnectionToast(
  connected: boolean,
  server?: string,
  accountId?: string,
  reason?: string,
  throttleKey?: string
): string | undefined {
  if (connected) {
    return showThrottledToast(
      'success',
      'MT5 Connected',
      {
        description: `Connected to ${server}${accountId ? ` (Account: ${accountId})` : ''}`,
        duration: 5000,
      },
      throttleKey || 'mt5-connected'
    );
  }

  return showThrottledToast(
    'warning',
    'MT5 Disconnected',
    {
      description: reason || 'Connection to MT5 terminal lost',
      duration: 7000,
    },
    throttleKey || 'mt5-disconnected'
  );
}

/**
 * Show toast for system status change to unhealthy
 * @param healthStatus The health status (unhealthy or critical)
 * @param cpuUsage CPU usage percentage
 * @param memoryUsage Memory usage percentage
 * @param message Additional message (optional)
 * @param throttleKey Unique key for throttling (optional)
 */
export function showSystemUnhealthyToast(
  healthStatus: 'unhealthy' | 'critical',
  cpuUsage: number,
  memoryUsage: number,
  message?: string,
  throttleKey?: string
): string | undefined {
  const isCritical = healthStatus === 'critical';
  const title = isCritical ? 'System Critical' : 'System Unhealthy';
  const description = message || `System health is ${healthStatus}. CPU: ${cpuUsage.toFixed(1)}%, Memory: ${memoryUsage.toFixed(1)}%`;

  return showThrottledToast(
    isCritical ? 'error' : 'warning',
    title,
    {
      description,
      duration: isCritical ? 10000 : 5000,
    },
    throttleKey || `system-${healthStatus}`
  );
}

/**
 * Export the global throttle manager for advanced usage
 */
export { globalThrottleManager };

/**
 * Utility function to clear all throttle timestamps
 */
export function clearToastThrottle(): void {
  globalThrottleManager.clear();
}
