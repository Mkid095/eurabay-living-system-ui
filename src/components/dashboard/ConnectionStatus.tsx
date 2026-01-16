"use client"

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useConnectionState } from '@/hooks/useConnectionState';
import { useReconnectionState } from '@/hooks/useReconnectionState';
import { ConnectionState } from '@/lib/websocket/client';
import { cn } from '@/lib/utils';

/**
 * Connection Status Indicator Component
 *
 * Displays real-time WebSocket connection status with:
 * - Color-coded status indicator (green/yellow/red)
 * - Connection state text
 * - Latency display when connected
 * - Tooltip with detailed connection information
 * - Manual reconnect button when disconnected
 * - Reconnecting message during reconnection attempts
 * - Error message after 3 consecutive failed attempts
 */

interface ConnectionStatusProps {
  className?: string;
  showLabel?: boolean;
  showLatency?: boolean;
}

export function ConnectionStatus({
  className,
  showLabel = true,
  showLatency = true,
}: ConnectionStatusProps) {
  const { state, latency, reconnectAttemptCount, reconnect } = useConnectionState();
  const { isReconnecting, attempt, consecutiveFailures, hasMaxFailures, reset: resetRecovery } = useReconnectionState();
  const [isManualReconnecting, setIsManualReconnecting] = useState(false);

  const handleReconnect = async () => {
    setIsManualReconnecting(true);
    // Reset recovery state when manually reconnecting
    resetRecovery();
    reconnect();
    // Reset manual reconnecting state after a short delay
    setTimeout(() => setIsManualReconnecting(false), 2000);
  };

  const getStatusText = (): string => {
    // Show "Reconnecting..." when auto-reconnecting
    if (isReconnecting) {
      return `Reconnecting... (${attempt})`;
    }

    switch (state) {
      case 'connected':
        return 'Connected';
      case 'connecting':
        return 'Connecting...';
      case 'disconnected':
        return 'Disconnected';
      case 'error':
        return 'Connection Error';
      default:
        return 'Unknown';
    }
  };

  const getStatusColor = (): string => {
    switch (state) {
      case 'connected':
        return 'bg-green-500';
      case 'connecting':
        return 'bg-yellow-500';
      case 'disconnected':
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const shouldShowReconnectButton = state === 'disconnected' || state === 'error';

  return (
    <div className={cn('flex items-center gap-2', className)}>
      {/* Connection Status Indicator */}
      <Tooltip>
        <TooltipTrigger asChild>
          <div className="flex items-center gap-2 cursor-default">
            {/* Status Dot */}
            <div
              className={cn(
                'w-2.5 h-2.5 rounded-full relative',
                getStatusColor(),
                (state === 'connecting' || isReconnecting) && 'animate-pulse'
              )}
            >
              {/* Outer glow effect for connected state */}
              {state === 'connected' && (
                <div className="absolute inset-0 rounded-full bg-green-500 opacity-30 animate-ping" />
              )}
            </div>

            {/* Status Label */}
            {showLabel && (
              <span className="text-sm font-medium text-foreground">
                {getStatusText()}
              </span>
            )}

            {/* Latency Display */}
            {showLatency && state === 'connected' && latency !== null && (
              <span className="text-xs text-muted-foreground tabular-nums">
                {latency}ms
              </span>
            )}
          </div>
        </TooltipTrigger>

        {/* Tooltip Content */}
        <TooltipContent side="bottom" align="center">
          <div className="space-y-1">
            <div className="font-medium">Connection Status</div>
            <div className="text-xs text-muted-foreground space-y-0.5">
              <div>State: {state === 'connecting' ? 'Connecting' : state}</div>
              {state === 'connected' && latency !== null && (
                <div>Latency: {latency}ms</div>
              )}
              {isReconnecting && (
                <div>Reconnection attempt: {attempt}</div>
              )}
              {reconnectAttemptCount > 0 && !isReconnecting && (
                <div>Total reconnect attempts: {reconnectAttemptCount}</div>
              )}
              {consecutiveFailures > 0 && (
                <div className={cn(
                  consecutiveFailures >= 3 ? 'text-red-500 font-medium' : 'text-yellow-600'
                )}>
                  Consecutive failures: {consecutiveFailures}
                </div>
              )}
            </div>
          </div>
        </TooltipContent>
      </Tooltip>

      {/* Manual Reconnect Button */}
      {shouldShowReconnectButton && (
        <Button
          variant="outline"
          size="sm"
          onClick={handleReconnect}
          disabled={isReconnecting || isManualReconnecting}
          className="h-7 px-2 text-xs"
        >
          {isManualReconnecting ? 'Reconnecting...' : 'Reconnect'}
        </Button>
      )}

      {/* Error message after 3 consecutive failed attempts */}
      {hasMaxFailures && (
        <div className="text-xs text-red-500 font-medium">
          Connection failed after {consecutiveFailures} attempts
        </div>
      )}
    </div>
  );
}
