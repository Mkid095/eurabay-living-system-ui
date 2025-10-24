"use client";

import { useState, useEffect } from "react";
import type {
  EvolutionMetrics,
  ControllerDecisionHistory,
  FeatureSuccess,
  MutationSuccess,
  GenerationHistory,
  EvolutionLog,
  EvolvedTrade
} from "@/types/evolution";

export const useEvolutionData = () => {
  const [evolutionMetrics, setEvolutionMetrics] = useState<EvolutionMetrics>({
    currentGeneration: 42,
    controllerDecision: 'EVOLVE_MODERATE',
    cyclesCompleted: 1547,
    systemVersion: 'v5.0',
    birthTime: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    uptime: '7d 14h 23m',
  });

  const [controllerHistory, setControllerHistory] = useState<ControllerDecisionHistory[]>([
    {
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      decision: 'EVOLVE_MODERATE',
      performance: 68.5,
      reason: 'Performance dip detected, moderate evolution triggered'
    },
    {
      timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
      decision: 'STABLE',
      performance: 72.3,
      reason: 'System performing well, maintaining current features'
    },
    {
      timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000).toISOString(),
      decision: 'EVOLVE_CONSERVATIVE',
      performance: 69.8,
      reason: 'Minor performance decline, conservative evolution applied'
    },
    {
      timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
      decision: 'EVOLVE_AGGRESSIVE',
      performance: 58.2,
      reason: 'Significant drawdown, aggressive evolution required'
    },
  ]);

  const [featureSuccess, setFeatureSuccess] = useState<FeatureSuccess[]>([
    {
      featureId: 'evolved_momentum',
      featureName: 'Evolved Momentum',
      successRate: 72.5,
      totalUses: 234,
      wins: 170,
      losses: 64,
      avgPnL: 12.45
    },
    {
      featureId: 'high_vol_chaos',
      featureName: 'High Vol Chaos',
      successRate: 68.3,
      totalUses: 189,
      wins: 129,
      losses: 60,
      avgPnL: 9.87
    },
    {
      featureId: 'trend_reversal',
      featureName: 'Trend Reversal',
      successRate: 65.1,
      totalUses: 156,
      wins: 102,
      losses: 54,
      avgPnL: 8.23
    },
    {
      featureId: 'breakout_detector',
      featureName: 'Breakout Detector',
      successRate: 58.9,
      totalUses: 142,
      wins: 84,
      losses: 58,
      avgPnL: 6.54
    },
    {
      featureId: 'regime_adaptive',
      featureName: 'Regime Adaptive',
      successRate: 52.3,
      totalUses: 128,
      wins: 67,
      losses: 61,
      avgPnL: 3.21
    },
  ]);

  const [mutationSuccess, setMutationSuccess] = useState<MutationSuccess[]>([
    {
      mutationType: 'Feature Combination',
      successRate: 65.4,
      totalAttempts: 78,
      successful: 51,
      avgFitnessImprovement: 8.7
    },
    {
      mutationType: 'Parameter Tweak',
      successRate: 58.2,
      totalAttempts: 92,
      successful: 54,
      avgFitnessImprovement: 5.3
    },
    {
      mutationType: 'New Feature',
      successRate: 45.6,
      totalAttempts: 65,
      successful: 30,
      avgFitnessImprovement: 12.1
    },
    {
      mutationType: 'Feature Removal',
      successRate: 72.3,
      totalAttempts: 47,
      successful: 34,
      avgFitnessImprovement: 6.8
    },
  ]);

  const [generationHistory, setGenerationHistory] = useState<GenerationHistory[]>([
    { generation: 35, timestamp: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(), fitness: 62.3, avgPerformance: 58.5 },
    { generation: 36, timestamp: new Date(Date.now() - 6 * 24 * 60 * 60 * 1000).toISOString(), fitness: 65.1, avgPerformance: 61.2 },
    { generation: 37, timestamp: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(), fitness: 63.8, avgPerformance: 59.8 },
    { generation: 38, timestamp: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000).toISOString(), fitness: 68.4, avgPerformance: 65.3 },
    { generation: 39, timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(), fitness: 71.2, avgPerformance: 68.7 },
    { generation: 40, timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(), fitness: 69.5, avgPerformance: 66.9 },
    { generation: 41, timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(), fitness: 72.8, avgPerformance: 70.5 },
    { generation: 42, timestamp: new Date().toISOString(), fitness: 74.3, avgPerformance: 72.1 },
  ]);

  const [evolutionLogs, setEvolutionLogs] = useState<EvolutionLog[]>([
    {
      timestamp: new Date(Date.now() - 30 * 60 * 1000).toISOString(),
      type: 'EVOLUTION_CYCLE',
      generation: 42,
      message: 'Evolution cycle completed. Fitness improved by 2.1%',
      details: { fitnessGain: 2.1, mutationsApplied: 3 }
    },
    {
      timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
      type: 'FEATURE_SUCCESS',
      generation: 42,
      message: 'Feature "evolved_momentum" achieved 73% win rate',
      details: { featureId: 'evolved_momentum', winRate: 73 }
    },
    {
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      type: 'MUTATION',
      generation: 42,
      message: 'Applied parameter tweak mutation to breakout detector',
      details: { mutationType: 'parameter_tweak', targetFeature: 'breakout_detector' }
    },
    {
      timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(),
      type: 'FEATURE_FAILURE',
      generation: 41,
      message: 'Feature "old_indicator" removed due to poor performance',
      details: { featureId: 'old_indicator', winRate: 38 }
    },
  ]);

  const [evolvedTrades, setEvolvedTrades] = useState<EvolvedTrade[]>([
    {
      ticket: 'T001234',
      symbol: 'V10',
      side: 'BUY',
      entryPrice: 1234.56,
      currentPrice: 1245.32,
      pnl: 107.60,
      stopLoss: 1220.45,
      takeProfit: 1260.00,
      entryTime: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      htfContext: 'BULLISH H1 R_10',
      ltfContext: 'STRONG_BUY M1',
      featuresUsed: ['evolved_momentum', 'high_vol_chaos'],
      confidence: 0.87
    },
    {
      ticket: 'T001235',
      symbol: 'V25',
      side: 'SELL',
      entryPrice: 2345.67,
      currentPrice: 2332.45,
      pnl: 132.20,
      stopLoss: 2360.00,
      takeProfit: 2320.00,
      entryTime: new Date(Date.now() - 1.5 * 60 * 60 * 1000).toISOString(),
      htfContext: 'BEARISH H1 R_25',
      ltfContext: 'STRONG_SELL M1',
      featuresUsed: ['trend_reversal', 'breakout_detector'],
      confidence: 0.92
    },
  ]);

  // TODO: Replace with real API calls
  useEffect(() => {
    const fetchEvolutionData = async () => {
      // Fetch from backend API
      // const response = await fetch('/api/evolution/metrics');
      // const data = await response.json();
      // setEvolutionMetrics(data);
    };

    fetchEvolutionData();
    const interval = setInterval(fetchEvolutionData, 5000); // Update every 5 seconds

    return () => clearInterval(interval);
  }, []);

  return {
    evolutionMetrics,
    controllerHistory,
    featureSuccess,
    mutationSuccess,
    generationHistory,
    evolutionLogs,
    evolvedTrades,
  };
};
