"use client";

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { useMT5Connection } from '@/hooks/useMT5Connection';
import { cn } from '@/lib/utils';

/**
 * MT5 Connection Status Indicator Component
 *
 * Displays real-time MT5 connection status with:
 * - Color-coded status indicator (green/yellow/red)
 * - Account number when connected
 * - Tooltip with connection details (latency, server)
 * - Connect MT5 button when disconnected
 */

interface MT5ConnectionStatusProps {
  className?: string;
  showLabel?: boolean;
}

export function MT5ConnectionStatus({
  className,
  showLabel = true,
}: MT5ConnectionStatusProps) {
  const { connectionState, connectionInfo, accountInfo, latency, connect, isLoading } = useMT5Connection();
  const [isConnecting, setIsConnecting] = useState(false);

  const handleConnect = async () => {
    setIsConnecting(true);
    try {
      await connect();
    } catch (error) {
      console.error('[MT5ConnectionStatus] Connection failed:', error);
    } finally {
      setIsConnecting(false);
    }
  };

  const getStatusText = (): string => {
    switch (connectionState) {
      case 'connected':
        return 'MT5 Connected';
      case 'disconnected':
        return 'MT5 Disconnected';
      case 'error':
        return 'MT5 Error';
      default:
        return 'Unknown';
    }
  };

  const getStatusColor = (): string => {
    switch (connectionState) {
      case 'connected':
        return 'bg-green-500';
      case 'disconnected':
        return 'bg-red-500';
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-gray-500';
    }
  };

  const shouldShowConnectButton = connectionState === 'disconnected' || connectionState === 'error';

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
                connectionState === 'connected' && 'animate-pulse'
              )}
            >
              {/* Outer glow effect for connected state */}
              {connectionState === 'connected' && (
                <div className="absolute inset-0 rounded-full bg-green-500 opacity-30 animate-ping" />
              )}
            </div>

            {/* Account Number when connected */}
            {connectionState === 'connected' && accountInfo && (
              <span className="text-sm font-medium text-foreground tabular-nums">
                {accountInfo.login}
              </span>
            )}

            {/* Status Label when not connected */}
            {showLabel && connectionState !== 'connected' && (
              <span className="text-sm font-medium text-foreground">
                MT5
              </span>
            )}
          </div>
        </TooltipTrigger>

        {/* Tooltip Content */}
        <TooltipContent side="bottom" align="center">
          <div className="space-y-1">
            <div className="font-medium">MT5 Connection</div>
            <div className="text-xs text-muted-foreground space-y-0.5">
              <div>Status: {getStatusText()}</div>
              {connectionState === 'connected' && connectionInfo && (
                <>
                  {latency !== null && (
                    <div>Latency: {latency}ms</div>
                  )}
                  {connectionInfo.server && (
                    <div>Server: {connectionInfo.server}</div>
                  )}
                  {connectionInfo.company && (
                    <div>Broker: {connectionInfo.company}</div>
                  )}
                </>
              )}
            </div>
          </div>
        </TooltipContent>
      </Tooltip>

      {/* Connect MT5 Button */}
      {shouldShowConnectButton && (
        <Button
          variant="outline"
          size="sm"
          onClick={handleConnect}
          disabled={isConnecting || isLoading}
          className="h-7 px-2 text-xs"
        >
          {isConnecting ? 'Connecting...' : 'Connect MT5'}
        </Button>
      )}
    </div>
  );
}
