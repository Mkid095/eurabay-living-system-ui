/**
 * useRealTimeEvolution Hook
 *
 * Manages real-time evolution event notifications via WebSocket.
 * Subscribes to evolution_event, generation_changed, controller_decision,
 * and feature_mutated events. Appends events to evolution log, updates
 * metrics on generation changes, shows toast notifications for important
 * events, auto-scrolls log to newest events, and tracks event count badge.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';
import { wsClient } from '@/lib/websocket/client';
import {
  type EvolutionEvent,
  type GenerationChangedEvent,
  type ControllerDecisionEvent,
  type FeatureMutatedEvent,
  EvolutionEventType,
  ControllerDecisionType,
  FeatureMutationType,
} from '@/lib/websocket/events';
import type { EvolutionMetrics, EvolutionLog } from '@/types/evolution';

export interface UseRealTimeEvolutionOptions {
  /**
   * Enable toast notifications for important events
   * @default true
   */
  enableToasts?: boolean;

  /**
   * Maximum number of events to keep in log
   * @default 100
   */
  maxLogSize?: number;

  /**
   * Enable auto-scroll to newest events
   * @default true
   */
  enableAutoScroll?: boolean;
}

export interface UseRealTimeEvolutionReturn {
  /**
   * Evolution metrics with real-time updates
   */
  metrics: EvolutionMetrics | null;

  /**
   * Evolution event log with newest events first
   */
  evolutionLog: EvolutionLog[];

  /**
   * Number of new events since last view
   */
  newEventCount: number;

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
   * Refresh evolution metrics from API
   */
  refresh: () => Promise<void>;

  /**
   * Clear new event count (mark events as viewed)
   */
  clearEventCount: () => void;

  /**
   * Scroll log to bottom (show newest events)
   */
  scrollToNewest: () => void;

  /**
   * Scroll log to top (show oldest events)
   */
  scrollToOldest: () => void;
}

const DEFAULT_MAX_LOG_SIZE = 100;
const TOAST_THROTTLE_MS = 5000;

/**
 * Convert EvolutionEvent to EvolutionLog entry
 */
function evolutionEventToLog(event: EvolutionEvent): EvolutionLog {
  return {
    timestamp: event.timestamp,
    type: event.eventType === EvolutionEventType.GENERATION_STARTED ||
          event.eventType === EvolutionEventType.GENERATION_COMPLETED
      ? 'EVOLUTION_CYCLE'
      : event.eventType === EvolutionEventType.FEATURE_VALIDATED
      ? 'FEATURE_SUCCESS'
      : 'FEATURE_FAILURE',
    generation: event.generation,
    message: event.details,
    details: {
      eventId: event.eventId,
      featureId: event.featureId,
      featureName: event.featureName,
      fitness: event.fitness,
    },
  };
}

/**
 * Hook to manage real-time evolution events
 */
export function useRealTimeEvolution(
  initialMetrics: EvolutionMetrics | null = null,
  initialEvolutionLog: EvolutionLog[] = [],
  options: UseRealTimeEvolutionOptions = {}
): UseRealTimeEvolutionReturn {
  const {
    enableToasts = true,
    maxLogSize = DEFAULT_MAX_LOG_SIZE,
    enableAutoScroll = true,
  } = options;

  const [metrics, setMetrics] = useState<EvolutionMetrics | null>(initialMetrics);
  const [evolutionLog, setEvolutionLog] = useState<EvolutionLog[]>(initialEvolutionLog);
  const [newEventCount, setNewEventCount] = useState(0);
  const [isConnected, setIsConnected] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const isMounted = useRef(true);
  const autoScrollEnabledRef = useRef(enableAutoScroll);
  const toastShownRef = useRef<Map<string, number>>(new Map());
  const scrollTargetRef = useRef<'newest' | 'oldest' | null>(null);
  const wsHandlersRef = useRef<Array<() => void>>([]);

  /**
   * Clear new event count
   */
  const clearEventCount = useCallback(() => {
    if (isMounted.current) {
      setNewEventCount(0);
    }
  }, []);

  /**
   * Scroll log to newest events
   */
  const scrollToNewest = useCallback(() => {
    scrollTargetRef.current = 'newest';
  }, []);

  /**
   * Scroll log to oldest events
   */
  const scrollToOldest = useCallback(() => {
    scrollTargetRef.current = 'oldest';
  }, []);

  /**
   * Check if toast should be throttled
   */
  const shouldThrottleToast = useCallback((key: string): boolean => {
    const lastShown = toastShownRef.current.get(key);
    const now = Date.now();

    if (lastShown && now - lastShown < TOAST_THROTTLE_MS) {
      return true;
    }

    toastShownRef.current.set(key, now);

    // Clean up old entries
    setTimeout(() => {
      toastShownRef.current.delete(key);
    }, TOAST_THROTTLE_MS * 2);

    return false;
  }, []);

  /**
   * Append event to evolution log
   */
  const appendToLog = useCallback((logEntry: EvolutionLog) => {
    if (!isMounted.current) return;

    setEvolutionLog((prevLog) => {
      const newLog = [logEntry, ...prevLog];

      // Trim to max log size
      if (newLog.length > maxLogSize) {
        return newLog.slice(0, maxLogSize);
      }

      return newLog;
    });

    // Increment new event count
    setNewEventCount((prev) => prev + 1);

    // Auto-scroll to newest if enabled
    if (autoScrollEnabledRef.current) {
      scrollToNewest();
    }
  }, [maxLogSize, scrollToNewest]);

  /**
   * Show toast for important events
   */
  const showEventToast = useCallback((
    title: string,
    message: string,
    type: 'success' | 'info' | 'warning',
    throttleKey?: string
  ) => {
    if (!enableToasts) return;

    if (throttleKey && shouldThrottleToast(throttleKey)) {
      return;
    }

    if (type === 'success') {
      toast.success(title, { description: message });
    } else if (type === 'warning') {
      toast.warning(title, { description: message });
    } else {
      toast.info(title, { description: message });
    }
  }, [enableToasts, shouldThrottleToast]);

  /**
   * Handle evolution_event from WebSocket
   */
  const handleEvolutionEvent = useCallback((event: EvolutionEvent) => {
    if (!isMounted.current) return;

    if (process.env.NODE_ENV === 'development') {
      console.log('[useRealTimeEvolution] Evolution event received:', event);
    }

    // Convert to log entry and append
    const logEntry = evolutionEventToLog(event);
    appendToLog(logEntry);

    // Show toast for important events
    if (event.eventType === EvolutionEventType.GENERATION_COMPLETED) {
      showEventToast(
        'Generation Completed',
        `Generation ${event.generation} completed${event.fitness ? ` with fitness ${event.fitness.toFixed(2)}` : ''}`,
        'success',
        `generation-completed-${event.generation}`
      );
    } else if (event.eventType === EvolutionEventType.AGGRESSIVE_EVOLUTION) {
      showEventToast(
        'Aggressive Evolution',
        event.details || 'Aggressive evolution triggered',
        'warning',
        'aggressive-evolution'
      );
    } else if (event.eventType === EvolutionEventType.NEW_FEATURE_DISCOVERED) {
      showEventToast(
        'New Feature Discovered',
        event.featureName
          ? `Feature "${event.featureName}" discovered in generation ${event.generation}`
          : `New feature discovered in generation ${event.generation}`,
        'success'
      );
    }
  }, [appendToLog, showEventToast]);

  /**
   * Handle generation_changed event from WebSocket
   */
  const handleGenerationChanged = useCallback((event: GenerationChangedEvent) => {
    if (!isMounted.current) return;

    if (process.env.NODE_ENV === 'development') {
      console.log('[useRealTimeEvolution] Generation changed:', event);
    }

    // Update metrics
    setMetrics((prevMetrics) => {
      if (!prevMetrics) return null;

      return {
        ...prevMetrics,
        currentGeneration: event.newGeneration,
      };
    });

    // Add log entry
    appendToLog({
      timestamp: event.timestamp,
      type: 'EVOLUTION_CYCLE',
      generation: event.newGeneration,
      message: `Generation changed from ${event.previousGeneration} to ${event.newGeneration}`,
      details: {
        bestFitness: event.bestFitness,
        averageFitness: event.averageFitness,
        populationSize: event.populationSize,
      },
    });

    // Show toast
    showEventToast(
      'New Generation',
      `Generation ${event.newGeneration} started. Best fitness: ${event.bestFitness.toFixed(2)}`,
      'info',
      `generation-changed-${event.newGeneration}`
    );
  }, [appendToLog, showEventToast]);

  /**
   * Handle controller_decision event from WebSocket
   */
  const handleControllerDecision = useCallback((event: ControllerDecisionEvent) => {
    if (!isMounted.current) return;

    if (process.env.NODE_ENV === 'development') {
      console.log('[useRealTimeEvolution] Controller decision:', event);
    }

    // Add log entry
    appendToLog({
      timestamp: event.timestamp,
      type: 'EVOLUTION_CYCLE',
      generation: 0, // Controller decisions don't always have a generation
      message: `Decision: ${event.decisionType.replace(/_/g, ' ').toLowerCase()} for ${event.symbol}`,
      details: {
        decisionId: event.decisionId,
        decisionType: event.decisionType,
        symbol: event.symbol,
        confidence: event.confidence,
        reasoning: event.reasoning,
        parameters: event.parameters,
      },
    });

    // Show toast for significant decisions
    if (event.decisionType === ControllerDecisionType.OPEN_POSITION ||
        event.decisionType === ControllerDecisionType.CLOSE_POSITION) {
      showEventToast(
        `Controller Decision: ${event.decisionType.replace(/_/g, ' ')}`,
        `${event.symbol} - ${event.reasoning.substring(0, 100)}${event.reasoning.length > 100 ? '...' : ''}`,
        'info'
      );
    }
  }, [appendToLog, showEventToast]);

  /**
   * Handle feature_mutated event from WebSocket
   */
  const handleFeatureMutated = useCallback((event: FeatureMutatedEvent) => {
    if (!isMounted.current) return;

    if (process.env.NODE_ENV === 'development') {
      console.log('[useRealTimeEvolution] Feature mutated:', event);
    }

    // Add log entry
    const isSuccess = event.mutationType === FeatureMutationType.ADDED ||
                     event.mutationType === FeatureMutationType.MODIFIED;

    appendToLog({
      timestamp: event.timestamp,
      type: isSuccess ? 'FEATURE_SUCCESS' : 'FEATURE_FAILURE',
      generation: 0,
      message: `Feature "${event.featureName}" ${event.mutationType.replace(/_/g, ' ').toLowerCase()}`,
      details: {
        featureId: event.featureId,
        featureName: event.featureName,
        mutationType: event.mutationType,
        previousValue: event.previousValue,
        newValue: event.newValue,
        weight: event.weight,
        importance: event.importance,
      },
    });

    // Show toast for important mutations
    if (event.mutationType === FeatureMutationType.ADDED) {
      showEventToast(
        'Feature Added',
        `Feature "${event.featureName}" added with value ${event.newValue.toFixed(2)}`,
        'success'
      );
    } else if (event.mutationType === FeatureMutationType.REMOVED) {
      showEventToast(
        'Feature Removed',
        `Feature "${event.featureName}" removed from the system`,
        'warning'
      );
    }
  }, [appendToLog, showEventToast]);

  /**
   * Refresh evolution metrics from API
   */
  const refresh = useCallback(async () => {
    if (!isMounted.current) return;

    setIsLoading(true);
    setError(null);

    try {
      // This would typically fetch from API
      // For now, we rely on the initial data passed in
      // The caller should refetch and pass new data
      await new Promise(resolve => setTimeout(resolve, 100));

      if (isMounted.current) {
        setIsLoading(false);
      }
    } catch (err) {
      if (isMounted.current) {
        const errorObj = err instanceof Error ? err : new Error('Failed to refresh evolution metrics');
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
   * Subscribe to evolution events
   */
  useEffect(() => {
    const unsubscribeEvolutionEvent = wsClient.on<EvolutionEvent>(
      'evolution_event',
      handleEvolutionEvent
    );

    const unsubscribeGenerationChanged = wsClient.on<GenerationChangedEvent>(
      'generation_changed',
      handleGenerationChanged
    );

    const unsubscribeControllerDecision = wsClient.on<ControllerDecisionEvent>(
      'controller_decision',
      handleControllerDecision
    );

    const unsubscribeFeatureMutated = wsClient.on<FeatureMutatedEvent>(
      'feature_mutated',
      handleFeatureMutated
    );

    wsHandlersRef.current = [
      unsubscribeEvolutionEvent,
      unsubscribeGenerationChanged,
      unsubscribeControllerDecision,
      unsubscribeFeatureMutated,
    ];

    if (process.env.NODE_ENV === 'development') {
      console.log('[useRealTimeEvolution] Subscribed to evolution events');
    }

    return () => {
      wsHandlersRef.current.forEach(unsubscribe => unsubscribe?.());

      if (process.env.NODE_ENV === 'development') {
        console.log('[useRealTimeEvolution] Unsubscribed from evolution events');
      }
    };
  }, [handleEvolutionEvent, handleGenerationChanged, handleControllerDecision, handleFeatureMutated]);

  /**
   * Update metrics when initial data changes
   */
  useEffect(() => {
    setMetrics(initialMetrics);
  }, [initialMetrics]);

  /**
   * Update evolution log when initial data changes
   */
  useEffect(() => {
    setEvolutionLog(initialEvolutionLog);
  }, [initialEvolutionLog]);

  /**
   * Cleanup on unmount
   */
  useEffect(() => {
    isMounted.current = true;

    return () => {
      isMounted.current = false;
      toastShownRef.current.clear();
    };
  }, []);

  return {
    metrics,
    evolutionLog,
    newEventCount,
    isConnected,
    isLoading,
    error,
    refresh,
    clearEventCount,
    scrollToNewest,
    scrollToOldest,
  };
}
