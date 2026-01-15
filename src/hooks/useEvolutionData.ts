"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type {
  EvolutionMetrics,
  ControllerDecisionHistory,
  FeatureSuccess,
  MutationSuccess,
  GenerationHistory,
  EvolutionLog,
  EvolvedTrade
} from "@/types/evolution";
import { evolutionApi, isApiRequestError } from "@/lib/api";

interface UseEvolutionDataOptions {
  /**
   * Auto-refresh interval in milliseconds
   * @default 5000 (5 seconds)
   */
  refreshInterval?: number;

  /**
   * Whether to enable auto-refresh
   * @default true
   */
  enableAutoRefresh?: boolean;
}

interface EvolutionDataState {
  evolutionMetrics: EvolutionMetrics | null;
  controllerHistory: ControllerDecisionHistory[];
  featureSuccess: FeatureSuccess[];
  mutationSuccess: MutationSuccess[];
  generationHistory: GenerationHistory[];
  evolutionLogs: EvolutionLog[];
  evolvedTrades: EvolvedTrade[];
}

interface EvolutionDataLoading {
  metrics: boolean;
  history: boolean;
  features: boolean;
  mutations: boolean;
  logs: boolean;
}

interface EvolutionDataError {
  metrics: string | null;
  history: string | null;
  features: string | null;
  mutations: string | null;
  logs: string | null;
}

/**
 * Custom hook for fetching and managing evolution data
 * Provides real-time data fetching with auto-refresh capability
 */
export const useEvolutionData = (options: UseEvolutionDataOptions = {}) => {
  const {
    refreshInterval = 5000,
    enableAutoRefresh = true,
  } = options;

  // Data state
  const [data, setData] = useState<EvolutionDataState>({
    evolutionMetrics: null,
    controllerHistory: [],
    featureSuccess: [],
    mutationSuccess: [],
    generationHistory: [],
    evolutionLogs: [],
    evolvedTrades: [],
  });

  // Loading state
  const [loading, setLoading] = useState<EvolutionDataLoading>({
    metrics: false,
    history: false,
    features: false,
    mutations: false,
    logs: false,
  });

  // Error state
  const [error, setError] = useState<EvolutionDataError>({
    metrics: null,
    history: null,
    features: null,
    mutations: null,
    logs: null,
  });

  // Refs for managing auto-refresh
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isMountedRef = useRef(true);

  /**
   * Fetch evolution metrics
   */
  const fetchMetrics = useCallback(async () => {
    if (!isMountedRef.current) return;

    setLoading((prev) => ({ ...prev, metrics: true }));
    setError((prev) => ({ ...prev, metrics: null }));

    try {
      const metrics = await evolutionApi.fetchEvolutionMetrics();
      if (isMountedRef.current) {
        setData((prev) => ({ ...prev, evolutionMetrics: metrics }));
      }
    } catch (err) {
      if (isMountedRef.current) {
        const errorMessage = isApiRequestError(err)
          ? err.message
          : 'Failed to fetch evolution metrics';
        setError((prev) => ({ ...prev, metrics: errorMessage }));
      }
    } finally {
      if (isMountedRef.current) {
        setLoading((prev) => ({ ...prev, metrics: false }));
      }
    }
  }, []);

  /**
   * Fetch controller history
   */
  const fetchHistory = useCallback(async (days?: number) => {
    if (!isMountedRef.current) return;

    setLoading((prev) => ({ ...prev, history: true }));
    setError((prev) => ({ ...prev, history: null }));

    try {
      const history = await evolutionApi.fetchControllerHistory(days);
      if (isMountedRef.current) {
        setData((prev) => ({ ...prev, controllerHistory: history }));
      }
    } catch (err) {
      if (isMountedRef.current) {
        const errorMessage = isApiRequestError(err)
          ? err.message
          : 'Failed to fetch controller history';
        setError((prev) => ({ ...prev, history: errorMessage }));
      }
    } finally {
      if (isMountedRef.current) {
        setLoading((prev) => ({ ...prev, history: false }));
      }
    }
  }, []);

  /**
   * Fetch feature success data
   */
  const fetchFeatures = useCallback(async (minUses?: number) => {
    if (!isMountedRef.current) return;

    setLoading((prev) => ({ ...prev, features: true }));
    setError((prev) => ({ ...prev, features: null }));

    try {
      const features = await evolutionApi.fetchFeatureSuccess(minUses);
      if (isMountedRef.current) {
        setData((prev) => ({ ...prev, featureSuccess: features }));
      }
    } catch (err) {
      if (isMountedRef.current) {
        const errorMessage = isApiRequestError(err)
          ? err.message
          : 'Failed to fetch feature success data';
        setError((prev) => ({ ...prev, features: errorMessage }));
      }
    } finally {
      if (isMountedRef.current) {
        setLoading((prev) => ({ ...prev, features: false }));
      }
    }
  }, []);

  /**
   * Fetch mutation success data
   */
  const fetchMutations = useCallback(async (minAttempts?: number) => {
    if (!isMountedRef.current) return;

    setLoading((prev) => ({ ...prev, mutations: true }));
    setError((prev) => ({ ...prev, mutations: null }));

    try {
      const mutations = await evolutionApi.fetchMutationSuccess(minAttempts);
      if (isMountedRef.current) {
        setData((prev) => ({ ...prev, mutationSuccess: mutations }));
      }
    } catch (err) {
      if (isMountedRef.current) {
        const errorMessage = isApiRequestError(err)
          ? err.message
          : 'Failed to fetch mutation success data';
        setError((prev) => ({ ...prev, mutations: errorMessage }));
      }
    } finally {
      if (isMountedRef.current) {
        setLoading((prev) => ({ ...prev, mutations: false }));
      }
    }
  }, []);

  /**
   * Fetch generation history
   */
  const fetchGenerationHistory = useCallback(async (days?: number) => {
    if (!isMountedRef.current) return;

    setLoading((prev) => ({ ...prev, history: true }));
    setError((prev) => ({ ...prev, history: null }));

    try {
      const history = await evolutionApi.fetchGenerationHistory(days);
      if (isMountedRef.current) {
        setData((prev) => ({ ...prev, generationHistory: history }));
      }
    } catch (err) {
      if (isMountedRef.current) {
        const errorMessage = isApiRequestError(err)
          ? err.message
          : 'Failed to fetch generation history';
        setError((prev) => ({ ...prev, history: errorMessage }));
      }
    } finally {
      if (isMountedRef.current) {
        setLoading((prev) => ({ ...prev, history: false }));
      }
    }
  }, []);

  /**
   * Fetch evolution logs
   */
  const fetchLogs = useCallback(async (eventType?: string) => {
    if (!isMountedRef.current) return;

    setLoading((prev) => ({ ...prev, logs: true }));
    setError((prev) => ({ ...prev, logs: null }));

    try {
      const logs = await evolutionApi.fetchEvolutionLogs(eventType);
      if (isMountedRef.current) {
        setData((prev) => ({ ...prev, evolutionLogs: logs }));
      }
    } catch (err) {
      if (isMountedRef.current) {
        const errorMessage = isApiRequestError(err)
          ? err.message
          : 'Failed to fetch evolution logs';
        setError((prev) => ({ ...prev, logs: errorMessage }));
      }
    } finally {
      if (isMountedRef.current) {
        setLoading((prev) => ({ ...prev, logs: false }));
      }
    }
  }, []);

  /**
   * Refetch all evolution data
   */
  const refetchAll = useCallback(() => {
    fetchMetrics();
    fetchHistory();
    fetchFeatures();
    fetchMutations();
    fetchGenerationHistory();
    fetchLogs();
  }, [fetchMetrics, fetchHistory, fetchFeatures, fetchMutations, fetchGenerationHistory, fetchLogs]);

  // Initial data fetch and setup auto-refresh
  useEffect(() => {
    // Fetch initial data
    refetchAll();

    // Setup auto-refresh if enabled
    if (enableAutoRefresh && refreshInterval > 0) {
      intervalRef.current = setInterval(() => {
        fetchMetrics();
        // Fetch other data less frequently to reduce API load
        fetchLogs();
      }, refreshInterval);
    }

    // Cleanup
    return () => {
      isMountedRef.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [enableAutoRefresh, refreshInterval, fetchMetrics, fetchLogs, refetchAll]);

  return {
    // Data
    evolutionMetrics: data.evolutionMetrics,
    controllerHistory: data.controllerHistory,
    featureSuccess: data.featureSuccess,
    mutationSuccess: data.mutationSuccess,
    generationHistory: data.generationHistory,
    evolutionLogs: data.evolutionLogs,
    evolvedTrades: data.evolvedTrades,

    // Loading states
    loading,

    // Error states
    error,

    // Refetch functions
    refetchMetrics: fetchMetrics,
    refetchHistory: fetchHistory,
    refetchFeatures: fetchFeatures,
    refetchMutations: fetchMutations,
    refetchGenerationHistory: fetchGenerationHistory,
    refetchLogs: fetchLogs,
    refetchAll,
  };
};
