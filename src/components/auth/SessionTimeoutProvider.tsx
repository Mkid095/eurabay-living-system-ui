'use client';

import { memo } from 'react';
import { useSessionTimeout } from '@/hooks/useSessionTimeout';
import SessionTimeoutDialog from './SessionTimeoutDialog';

/**
 * Session Timeout Provider
 *
 * Wraps the application to provide session timeout functionality:
 * - Monitors user activity
 * - Shows warning dialog before timeout
 * - Auto-logs out on inactivity
 *
 * This component should be placed in the root layout or dashboard layout
 * to enable session timeout for authenticated users.
 */

function SessionTimeoutProvider() {
  const {
    showWarning,
    remainingTime,
    continueSession,
  } = useSessionTimeout({
    enabled: true,
    // 15 minutes timeout
    timeoutMs: 15 * 60 * 1000,
    // Show warning 1 minute before timeout
    warningMs: 1 * 60 * 1000,
    // Track user activity to extend session
    enableActivityTracking: true,
  });

  return (
    <SessionTimeoutDialog
      open={showWarning}
      remainingTime={remainingTime}
      onContinue={continueSession}
      onTimeout={() => {
        // Timeout is handled by the hook
      }}
    />
  );
}

/**
 * Memoized export to prevent unnecessary re-renders
 */
export default memo(SessionTimeoutProvider);
