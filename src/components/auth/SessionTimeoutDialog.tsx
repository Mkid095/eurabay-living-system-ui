'use client';

import { useState, useEffect, useCallback, memo } from 'react';
import { useRouter } from 'next/navigation';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { formatTimeRemaining } from '@/lib/auth/session';

/**
 * Session timeout warning dialog component
 *
 * Shows a warning dialog when the session is about to expire due to inactivity.
 * The dialog cannot be closed by the user (no close button, no escape key).
 * Provides "Continue Session" button to extend the session.
 */

interface SessionTimeoutDialogProps {
  /** Remaining time in milliseconds */
  remainingTime: number;
  /** Callback to extend the session */
  onContinue: () => void;
  /** Callback when session expires (logout) */
  onTimeout: () => void;
  /** Whether the dialog is open */
  open: boolean;
}

function SessionTimeoutDialog({
  remainingTime,
  onContinue,
  onTimeout,
  open,
}: SessionTimeoutDialogProps) {
  const router = useRouter();
  const [timeLeft, setTimeLeft] = useState(remainingTime);

  // Update the displayed time
  useEffect(() => {
    if (!open) {
      return;
    }

    setTimeLeft(remainingTime);

    const interval = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1000) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1000;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [remainingTime, open]);

  // Auto-logout when time runs out
  useEffect(() => {
    if (!open || timeLeft > 0) {
      return;
    }

    // Trigger timeout callback
    onTimeout();
  }, [open, timeLeft, onTimeout]);

  // Calculate progress percentage (inverse - shows time remaining)
  const maxTime = 60000; // 1 minute in milliseconds
  const progressPercentage = Math.max(0, Math.min(100, (timeLeft / maxTime) * 100));

  // Handle continue session button click
  const handleContinue = useCallback(() => {
    onContinue();
  }, [onContinue]);

  // Get warning message based on time left
  const getWarningMessage = () => {
    const seconds = Math.ceil(timeLeft / 1000);
    if (seconds <= 10) {
      return 'Your session will expire in less than 10 seconds due to inactivity.';
    } else if (seconds <= 30) {
      return 'Your session will expire in less than 30 seconds due to inactivity.';
    }
    return 'Your session will expire in 1 minute due to inactivity.';
  };

  // Determine dialog color based on urgency
  const getUrgencyColor = () => {
    const seconds = Math.ceil(timeLeft / 1000);
    if (seconds <= 10) return 'destructive';
    if (seconds <= 30) return 'destructive';
    return 'default';
  };

  return (
    <Dialog open={open} modal={true}>
      <DialogContent
        showCloseButton={false}
        onEscapeKeyDown={(e) => e.preventDefault()}
        onPointerDownOutside={(e) => e.preventDefault()}
        onInteractOutside={(e) => e.preventDefault()}
        className="sm:max-w-md"
      >
        <DialogHeader>
          <DialogTitle className="text-xl">
            Session Expiring
          </DialogTitle>
          <DialogDescription className="text-base pt-2">
            {getWarningMessage()}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Time remaining display */}
          <div className="text-center">
            <div className="text-4xl font-mono font-bold">
              {formatTimeRemaining(timeLeft)}
            </div>
            <div className="text-sm text-muted-foreground mt-1">
              Time remaining
            </div>
          </div>

          {/* Progress bar */}
          <div className="space-y-2">
            <Progress
              value={progressPercentage}
              className="h-2"
            />
          </div>

          {/* Info message */}
          <div className="text-sm text-muted-foreground text-center">
            Click &quot;Continue Session&quot; to stay logged in, or you will be
            automatically logged out.
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            onClick={handleContinue}
            variant={getUrgencyColor()}
            className="w-full sm:w-auto"
            autoFocus
          >
            Continue Session
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Memoized export to prevent unnecessary re-renders
 */
export default memo(SessionTimeoutDialog);
