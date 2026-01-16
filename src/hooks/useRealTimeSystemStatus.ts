/**
 * useRealTimeSystemStatus Hook
 *
 * Manages real-time system status updates via WebSocket.
 * Subscribes to system_status events, updates status indicators,
 * shows alert banner for unhealthy status, updates CPU/memory usage,
 * and tracks uptime counter.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';
import { wsClient } from '@/lib/websocket/client';
import type { SystemStatusEvent } from '@/lib/websocket/events';
import type { SystemHealth } from '@/lib/api/types';

export interface UseRealTimeSystemStatusOptions {
  /**
   * Enable toast notifications for unhealthy status
   * @default true
   */
  enableUnhealthyAlerts?: boolean;

  /**
   * Enable alert banner for unhealthy status
   * @default true
   */
  enableAlertBanner?: boolean;

  /**
   * Health statuses that trigger alerts
   * @default ['unhealthy', 'critical']
   */
  alertHealthStatuses?: Array<'unhealthy' | 'critical' | 'degraded'>;
}

export interface UseRealTimeSystemStatusReturn {
  /**
   * Current system health status
   */
  systemHealth: SystemHealth | null;

  /**
   * Whether system status is unhealthy (unhealthy or critical)
   */
  isUnhealthy: boolean;

  /**
   * Whether the WebSocket is connected
   */
  isConnected: boolean;

  /**
   * Whether currently fetching initial data
   */
  isLoading: boolean;

  /**
   * Error from fetching or WebSocket
   */
  error: Error | null;

  /**
   * Refresh system status from API
   */
  refresh: () => Promise<void>;

  /**
   * Show alert banner (controlled by consumer)
   */
  showBanner: boolean;

  /**
   * Dismiss alert banner
   */
  dismissBanner: () => void;

  /**
   * Banner message to display
   */
  bannerMessage: string;

  /**
   * Banner severity level
   */
  bannerSeverity: 'warning' | 'error';
}

const DEFAULT_ALERT_HEALTH_STATUSES = ['unhealthy', 'critical'] as const;
const TOAST_THROTTLE_MS = 10000; // 10 seconds between toasts

/**
 * Hook to manage real-time system status updates
 */
export function useRealTimeSystemStatus(
  initialSystemHealth: SystemHealth | null = null,
  options: UseRealTimeSystemStatusOptions = {}
): UseRealTimeSystemStatusReturn {
  const {
    enableUnhealthyAlerts = true,
    enableAlertBanner = true,
    alertHealthStatuses = DEFAULT_ALERT_HEALTH_STATUSES as any,
  } = options;

  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(initialSystemHealth);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [showBanner, setShowBanner] = useState(false);
  const [bannerMessage, setBannerMessage] = useState('');
  const [bannerSeverity, setBannerSeverity] = useState<'warning' | 'error'>('warning');

  const isMounted = useRef(true);
  const lastToastTimeRef = useRef<number>(0);
  const wsHandlerRef = useRef<(() => void) | null>(null);

  /**
   * Determine if status is unhealthy based on health status
   */
  const isUnhealthy = useCallback((health: SystemHealth | null): boolean => {
    if (!health) return false;
    return health.health === 'unhealthy' || health.health === 'critical';
  }, []);

  /**
   * Determine if status should trigger an alert
   */
  const shouldTriggerAlert = useCallback((health: SystemHealth | null): boolean => {
    if (!health) return false;
    return alertHealthStatuses.includes(health.health as any);
  }, [alertHealthStatuses]);

  /**
   * Show unhealthy status toast with throttling
   */
  const showUnhealthyToast = useCallback((health: SystemHealth) => {
    if (!enableUnhealthyAlerts) return;

    const now = Date.now();
    const timeSinceLastToast = now - lastToastTimeRef.current;

    // Throttle toasts to avoid spam
    if (timeSinceLastToast < TOAST_THROTTLE_MS) {
      return;
    }

    lastToastTimeRef.current = now;

    const isCritical = health.health === 'critical';
    const title = isCritical ? 'System Critical' : 'System Unhealthy';
    const toastType = isCritical ? 'error' : 'warning';

    toast[toastType](title, {
      description: health.message || `System health is ${health.health}. CPU: ${health.cpuUsage.toFixed(1)}%, Memory: ${health.memoryUsage.toFixed(1)}%`,
      duration: isCritical ? 10000 : 5000,
    });
  }, [enableUnhealthyAlerts]);

  /**
   * Handle system status event from WebSocket
   */
  const handleSystemStatus = useCallback((data: SystemStatusEvent) => {
    if (!isMounted.current) return;

    const { status, cpuUsage, memoryUsage, uptime, activeConnections, message, timestamp } = data;

    // Map WebSocket event to SystemHealth type
    const newHealth: SystemHealth = {
      health: status,
      cpuUsage,
      memoryUsage,
      availableMemory: 0, // Not provided in WebSocket event
      totalMemory: 0, // Not provided in WebSocket event
      latency: 0, // Not provided in WebSocket event
      activeConnections,
      uptime,
      lastCheck: timestamp,
      details: message ? { message } : undefined,
    };

    setSystemHealth(newHealth);
    setError(null);

    // Check if we should trigger alerts
    if (shouldTriggerAlert(newHealth)) {
      // Show toast notification
      showUnhealthyToast(newHealth);

      // Show alert banner
      if (enableAlertBanner) {
        setBannerMessage(newHealth.message || `System health is ${newHealth.health}. CPU: ${newHealth.cpuUsage.toFixed(1)}%, Memory: ${newHealth.memoryUsage.toFixed(1)}%`);
        setBannerSeverity(newHealth.health === 'critical' ? 'error' : 'warning');
        setShowBanner(true);
      }
    } else if (newHealth.health === 'healthy' && showBanner) {
      // Auto-dismiss banner when system becomes healthy
      setShowBanner(false);
    }
  }, [shouldTriggerAlert, showUnhealthyToast, enableAlertBanner, showBanner]);

  /**
   * Dismiss alert banner
   */
  const dismissBanner = useCallback(() => {
    if (isMounted.current) {
      setShowBanner(false);
    }
  }, []);

  /**
   * Refresh system status from API
   */
  const refresh = useCallback(async () => {
    if (!isMounted.current) return;

    setIsLoading(true);
    setError(null);

    try {
      // In a real implementation, this would fetch from the API
      // For now, we simulate a successful refresh
      await new Promise(resolve => setTimeout(resolve, 100));

      if (isMounted.current) {
        setIsLoading(false);
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to refresh system status');
        setError(errorObj);
        setIsLoading(false);
      }
    }
  }, []);

  /**
   * Subscribe to WebSocket connection state
   */
  useEffect(() => {
    const unsubscribeState = wsClient.onStateChange((state) => {
      if (isMounted.current) {
        setIsConnected(state === 'connected');
      }
    });

    // Set initial state
    setIsConnected(wsClient.getState() === 'connected');

    return unsubscribeState;
  }, []);

  /**
   * Subscribe to system_status events
   */
  useEffect(() => {
    wsHandlerRef.current = () => {
      const unsubscribe = wsClient.on<SystemStatusEvent>('system_status', handleSystemStatus);

      if (process.env.NODE_ENV === 'development') {
        console.log('[useRealTimeSystemStatus] Subscribed to system_status events');
      }

      return unsubscribe;
    };

    const unsubscribe = wsHandlerRef.current();

    return () => {
      unsubscribe?.();

      if (process.env.NODE_ENV === 'development') {
        console.log('[useRealTimeSystemStatus] Unsubscribed from system_status events');
      }
    };
  }, [handleSystemStatus]);

  /**
   * Update system health when initial data changes
   */
  useEffect(() => {
    if (initialSystemHealth) {
      setSystemHealth(initialSystemHealth);
    }
  }, [initialSystemHealth]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    isMounted.current = true;

    return () => {
      isMounted.current = false;
      lastToastTimeRef.current = 0;
    };
  }, []);

  return {
    systemHealth,
    isUnhealthy: isUnhealthy(systemHealth),
    isConnected,
    isLoading,
    error,
    refresh,
    showBanner,
    dismissBanner,
    bannerMessage,
    bannerSeverity,
  };
}
