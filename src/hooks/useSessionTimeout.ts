'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import {
  SessionManager,
  SESSION_TIMEOUT_MS,
  SESSION_WARNING_MS,
  validateSessionOnLoad,
  getSessionInfo,
} from '@/lib/auth/session';

/**
 * Session timeout hook
 *
 * Manages session timeout with:
 * - 15 minutes of inactivity
 * - Warning dialog 1 minute before timeout
 * - Session extension on user activity
 * - Auto-logout on timeout
 * - Redirect to login with session expired message
 */

interface UseSessionTimeoutOptions {
  /** Enable session timeout (default: true) */
  enabled?: boolean;
  /** Custom timeout in milliseconds (default: 15 minutes) */
  timeoutMs?: number;
  /** Custom warning time in milliseconds before timeout (default: 1 minute) */
  warningMs?: number;
  /** Enable activity tracking (default: true) */
  enableActivityTracking?: boolean;
}

export function useSessionTimeout(options: UseSessionTimeoutOptions = {}) {
  const {
    enabled = true,
    timeoutMs = SESSION_TIMEOUT_MS,
    warningMs = SESSION_WARNING_MS,
    enableActivityTracking = true,
  } = options;

  const router = useRouter();
  const { user, logout } = useAuth();
  const sessionManagerRef = useRef<SessionManager | null>(null);
  const isInitializedRef = useRef(false);

  const [showWarning, setShowWarning] = useState(false);
  const [remainingTime, setRemainingTime] = useState(0);
  const [isSessionValid, setIsSessionValid] = useState(true);

  /**
   * Handle session timeout - logout and redirect to login
   */
  const handleTimeout = useCallback(async () => {
    setShowWarning(false);

    // Perform logout
    await logout();

    // Redirect to login with session expired message
    router.push('/login?session=expired');
  }, [logout, router]);

  /**
   * Handle session warning - show dialog
   */
  const handleWarning = useCallback((timeRemaining: number) => {
    setRemainingTime(timeRemaining);
    setShowWarning(true);
  }, []);

  /**
   * Continue session - extend session and hide warning
   */
  const continueSession = useCallback(() => {
    setShowWarning(false);

    // Reset the timer in the session manager
    if (sessionManagerRef.current) {
      sessionManagerRef.current.resetTimer();
    }
  }, []);

  /**
   * Initialize session manager on mount (only once)
   */
  useEffect(() => {
    if (isInitializedRef.current) {
      return;
    }

    isInitializedRef.current = true;

    // Validate session on page load (check if expired while tab was closed)
    if (!validateSessionOnLoad()) {
      setIsSessionValid(false);
      handleTimeout();
      return;
    }

    // Only initialize session timeout if user is authenticated
    if (!user) {
      return;
    }

    // Create and configure session manager
    const manager = new SessionManager({
      timeoutMs,
      warningMs,
      onTimeout: handleTimeout,
      onWarning: handleWarning,
      enableActivityTracking,
    });

    sessionManagerRef.current = manager;

    // Start the session manager
    manager.start();

    // Cleanup on unmount
    return () => {
      if (sessionManagerRef.current) {
        sessionManagerRef.current.stop();
        sessionManagerRef.current = null;
      }
    };
    // Only run once on mount - empty deps array by design
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /**
   * Start/restart session manager when user logs in
   */
  useEffect(() => {
    if (!user || !enabled) {
      // Stop session manager if user logs out or timeout is disabled
      if (sessionManagerRef.current) {
        sessionManagerRef.current.stop();
      }
      return;
    }

    // Session manager is already initialized, just make sure it's running
    if (sessionManagerRef.current && !isSessionValid) {
      setIsSessionValid(true);
      sessionManagerRef.current.start();
    }
  }, [user, enabled, isSessionValid]);

  /**
   * Manual reset of session timer (call this to extend session)
   */
  const resetSession = useCallback(() => {
    if (sessionManagerRef.current) {
      sessionManagerRef.current.resetTimer();
    }
  }, []);

  /**
   * Get current session info
   */
  const getSessionDetails = useCallback(() => {
    if (sessionManagerRef.current) {
      return {
        remainingTime: sessionManagerRef.current.getRemainingTime(),
        idleTime: sessionManagerRef.current.getIdleTime(),
        isExpired: sessionManagerRef.current.isExpired(),
      };
    }

    // Return info from localStorage if session manager not initialized
    return getSessionInfo();
  }, []);

  return {
    /** Whether the timeout warning dialog is visible */
    showWarning,

    /** Remaining time in milliseconds */
    remainingTime,

    /** Whether the session is valid (not expired) */
    isSessionValid,

    /** Function to continue session (extends timeout) */
    continueSession,

    /** Function to manually reset session timer */
    resetSession,

    /** Get current session details */
    getSessionDetails,

    /** Session manager instance (advanced usage) */
    sessionManager: sessionManagerRef.current,
  };
}

/**
 * Hook to get session info without setting up timeout
 * Useful for displaying session status in UI
 */
export function useSessionInfo() {
  const [sessionInfo, setSessionInfo] = useState(() => getSessionInfo());

  useEffect(() => {
    // Update session info every second
    const interval = setInterval(() => {
      setSessionInfo(getSessionInfo());
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return sessionInfo;
}
