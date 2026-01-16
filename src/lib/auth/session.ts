/**
 * Session Timeout Module
 *
 * Implements client-side session timeout with inactivity detection:
 * - 15 minutes of inactivity triggers auto-logout
 * - Warning dialog shown 1 minute before timeout
 * - Session extends on user activity (mouse, keyboard)
 * - Automatic logout and cleanup on timeout
 */

// Session configuration constants
export const SESSION_TIMEOUT_MS = 15 * 60 * 1000; // 15 minutes
export const SESSION_WARNING_MS = 1 * 60 * 1000; // 1 minute before timeout
export const SESSION_STORAGE_KEY = 'sessionLastActivity';
export const WARNING_DISMISSED_KEY = 'sessionWarningDismissed';

/**
 * Session timeout callback type
 */
export type SessionTimeoutCallback = () => void;

/**
 * Session warning callback type
 */
export type SessionWarningCallback = (remainingTime: number) => void;

/**
 * Session manager configuration
 */
export interface SessionManagerConfig {
  onTimeout?: SessionTimeoutCallback;
  onWarning?: SessionWarningCallback;
  timeoutMs?: number;
  warningMs?: number;
  enableActivityTracking?: boolean;
}

/**
 * Activity event types that reset the session timer
 */
const ACTIVITY_EVENTS = [
  'mousedown',
  'keydown',
  'scroll',
  'touchstart',
  'click',
] as const;

/**
 * SessionManager class
 *
 * Manages session timeout with inactivity tracking and warning dialogs
 */
export class SessionManager {
  private timeoutMs: number;
  private warningMs: number;
  private onTimeout?: SessionTimeoutCallback;
  private onWarning?: SessionWarningCallback;
  private enableActivityTracking: boolean;

  private timeoutId: ReturnType<typeof setTimeout> | null = null;
  private warningId: ReturnType<typeof setTimeout> | null = null;
  private lastActivity: number;
  private isRunning = false;
  private isPaused = false;
  private activityListeners: Array<{ event: string; handler: () => void }> = [];

  constructor(config: SessionManagerConfig = {}) {
    this.timeoutMs = config.timeoutMs ?? SESSION_TIMEOUT_MS;
    this.warningMs = config.warningMs ?? SESSION_WARNING_MS;
    this.onTimeout = config.onTimeout;
    this.onWarning = config.onWarning;
    this.enableActivityTracking = config.enableActivityTracking ?? true;

    // Restore last activity from localStorage or use current time
    const stored = typeof window !== 'undefined'
      ? localStorage.getItem(SESSION_STORAGE_KEY)
      : null;
    this.lastActivity = stored ? parseInt(stored, 10) : Date.now();
  }

  /**
   * Start the session timeout manager
   */
  start(): void {
    if (this.isRunning) {
      return;
    }

    this.isRunning = true;
    this.isPaused = false;
    this.scheduleTimeout();
    this.scheduleWarning();

    if (this.enableActivityTracking) {
      this.attachActivityListeners();
    }
  }

  /**
   * Stop the session timeout manager
   */
  stop(): void {
    this.isRunning = false;
    this.clearTimers();
    this.detachActivityListeners();
  }

  /**
   * Pause the session timeout (useful for maintenance/debugging)
   */
  pause(): void {
    this.isPaused = true;
    this.clearTimers();
  }

  /**
   * Resume the session timeout
   */
  resume(): void {
    if (!this.isRunning) {
      return;
    }

    this.isPaused = false;
    this.resetTimer();
  }

  /**
   * Reset the session timer (extend session)
   */
  resetTimer(): void {
    if (!this.isRunning || this.isPaused) {
      return;
    }

    this.lastActivity = Date.now();
    this.saveLastActivity();

    // Clear and reschedule timers
    this.clearTimers();
    this.scheduleTimeout();
    this.scheduleWarning();
  }

  /**
   * Get the remaining time until timeout
   */
  getRemainingTime(): number {
    const elapsed = Date.now() - this.lastActivity;
    return Math.max(0, this.timeoutMs - elapsed);
  }

  /**
   * Check if the session has expired
   */
  isExpired(): boolean {
    return this.getRemainingTime() === 0;
  }

  /**
   * Clear all pending timers
   */
  private clearTimers(): void {
    if (this.timeoutId) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }

    if (this.warningId) {
      clearTimeout(this.warningId);
      this.warningId = null;
    }
  }

  /**
   * Schedule the timeout callback
   */
  private scheduleTimeout(): void {
    const remainingTime = this.getRemainingTime();

    if (remainingTime <= 0) {
      // Session already expired, trigger timeout immediately
      this.triggerTimeout();
      return;
    }

    this.timeoutId = setTimeout(() => {
      this.triggerTimeout();
    }, remainingTime);
  }

  /**
   * Schedule the warning callback
   */
  private scheduleWarning(): void {
    const remainingTime = this.getRemainingTime();
    const warningTime = this.timeoutMs - this.warningMs;

    if (remainingTime <= warningTime) {
      // Already past warning time, show warning immediately if appropriate
      if (remainingTime > 0 && remainingTime <= this.warningMs) {
        this.triggerWarning(remainingTime);
      }
      return;
    }

    const timeUntilWarning = remainingTime - this.warningMs;

    this.warningId = setTimeout(() => {
      const remaining = this.getRemainingTime();
      if (remaining > 0) {
        this.triggerWarning(remaining);
      }
    }, timeUntilWarning);
  }

  /**
   * Trigger the timeout callback
   */
  private triggerTimeout(): void {
    this.stop();
    this.clearSessionData();

    if (this.onTimeout) {
      this.onTimeout();
    }
  }

  /**
   * Trigger the warning callback
   */
  private triggerWarning(remainingTime: number): void {
    if (this.onWarning) {
      this.onWarning(remainingTime);
    }
  }

  /**
   * Attach activity event listeners
   */
  private attachActivityListeners(): void {
    if (typeof window === 'undefined') {
      return;
    }

    const handler = () => {
      this.resetTimer();
    };

    ACTIVITY_EVENTS.forEach((event) => {
      window.addEventListener(event, handler, { passive: true });
      this.activityListeners.push({ event: event, handler });
    });
  }

  /**
   * Detach activity event listeners
   */
  private detachActivityListeners(): void {
    if (typeof window === 'undefined') {
      return;
    }

    this.activityListeners.forEach(({ event, handler }) => {
      window.removeEventListener(event, handler);
    });

    this.activityListeners = [];
  }

  /**
   * Save last activity timestamp to localStorage
   */
  private saveLastActivity(): void {
    if (typeof window !== 'undefined') {
      localStorage.setItem(SESSION_STORAGE_KEY, this.lastActivity.toString());
    }
  }

  /**
   * Clear session data from localStorage
   */
  private clearSessionData(): void {
    if (typeof window !== 'undefined') {
      localStorage.removeItem(SESSION_STORAGE_KEY);
      localStorage.removeItem(WARNING_DISMISSED_KEY);
    }
  }

  /**
   * Get the time since last activity in milliseconds
   */
  getIdleTime(): number {
    return Date.now() - this.lastActivity;
  }

  /**
   * Check if the user is idle
   */
  isIdle(idleThreshold: number = 30000): boolean {
    return this.getIdleTime() > idleThreshold;
  }
}

/**
 * Create and initialize a session manager with default configuration
 *
 * @param config - Optional configuration
 * @returns SessionManager instance
 */
export function createSessionManager(config?: SessionManagerConfig): SessionManager {
  return new SessionManager(config);
}

/**
 * Format milliseconds into human-readable time (MM:SS)
 *
 * @param ms - Milliseconds to format
 * @returns Formatted time string
 */
export function formatTimeRemaining(ms: number): string {
  const totalSeconds = Math.ceil(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, '0')}`;
}

/**
 * Validate session on page load
 * Checks if session has expired while the tab was closed
 *
 * @returns true if session is valid, false if expired
 */
export function validateSessionOnLoad(): boolean {
  if (typeof window === 'undefined') {
    return true;
  }

  const stored = localStorage.getItem(SESSION_STORAGE_KEY);
  if (!stored) {
    return true; // No previous session data
  }

  const lastActivity = parseInt(stored, 10);
  const elapsed = Date.now() - lastActivity;

  if (elapsed > SESSION_TIMEOUT_MS) {
    // Session expired while tab was closed
    localStorage.removeItem(SESSION_STORAGE_KEY);
    return false;
  }

  return true;
}

/**
 * Get session info for debugging
 */
export function getSessionInfo(): {
  lastActivity: number | null;
  idleTime: number;
  remainingTime: number;
  isExpired: boolean;
} {
  const stored = typeof window !== 'undefined'
    ? localStorage.getItem(SESSION_STORAGE_KEY)
    : null;

  const lastActivity = stored ? parseInt(stored, 10) : null;
  const idleTime = lastActivity ? Date.now() - lastActivity : 0;
  const remainingTime = lastActivity
    ? Math.max(0, SESSION_TIMEOUT_MS - idleTime)
    : SESSION_TIMEOUT_MS;
  const isExpired = remainingTime === 0;

  return {
    lastActivity,
    idleTime,
    remainingTime,
    isExpired,
  };
}
