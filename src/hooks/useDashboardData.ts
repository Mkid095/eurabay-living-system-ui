"use client";

import { useState, useEffect } from 'react';

export interface Trade {
  id: string;
  pair: string;
  type: 'BUY' | 'SELL';
  entryPrice: number;
  currentPrice: number;
  amount: number;
  pnl: number;
  pnlPercent: number;
  status: 'active' | 'pending' | 'closed';
  timestamp: Date;
}

export interface SystemHealth {
  status: 'online' | 'offline' | 'warning';
  uptime: string;
  latency: number;
  apiConnections: number;
}

export interface PortfolioMetrics {
  totalValue: number;
  totalPnL: number;
  totalPnLPercent: number;
  activeTrades: number;
  winRate: number;
}

export interface ChartDataPoint {
  time: string;
  value: number;
}

export interface PerformanceMetrics {
  totalTrades: number;
  winningTrades: number;
  losingTrades: number;
  avgWin: number;
  avgLoss: number;
  sharpeRatio: number;
  maxDrawdown: number;
}

export function useDashboardData() {
  const [portfolioMetrics, setPortfolioMetrics] = useState<PortfolioMetrics>({
    totalValue: 47500.00,
    totalPnL: 2650.00,
    totalPnLPercent: 5.91,
    activeTrades: 8,
    winRate: 68.5,
  });

  const [systemHealth, setSystemHealth] = useState<SystemHealth>({
    status: 'online',
    uptime: '12d 5h 32m',
    latency: 45,
    apiConnections: 3,
  });

  const [activeTrades, setActiveTrades] = useState<Trade[]>([
    {
      id: '1',
      pair: 'EUR/USD',
      type: 'BUY',
      entryPrice: 1.0865,
      currentPrice: 1.0892,
      amount: 10000,
      pnl: 270,
      pnlPercent: 2.48,
      status: 'active',
      timestamp: new Date(Date.now() - 3600000),
    },
    {
      id: '2',
      pair: 'GBP/USD',
      type: 'SELL',
      entryPrice: 1.2745,
      currentPrice: 1.2698,
      amount: 8000,
      pnl: 376,
      pnlPercent: 4.70,
      status: 'active',
      timestamp: new Date(Date.now() - 7200000),
    },
    {
      id: '3',
      pair: 'USD/JPY',
      type: 'BUY',
      entryPrice: 149.82,
      currentPrice: 149.65,
      amount: 5000,
      pnl: -85,
      pnlPercent: -1.13,
      status: 'active',
      timestamp: new Date(Date.now() - 1800000),
    },
    {
      id: '4',
      pair: 'AUD/USD',
      type: 'BUY',
      entryPrice: 0.6523,
      currentPrice: 0.6545,
      amount: 12000,
      pnl: 264,
      pnlPercent: 3.37,
      status: 'active',
      timestamp: new Date(Date.now() - 5400000),
    },
  ]);

  const [pendingSignals, setPendingSignals] = useState<Trade[]>([
    {
      id: 'p1',
      pair: 'EUR/GBP',
      type: 'BUY',
      entryPrice: 0.8523,
      currentPrice: 0.8520,
      amount: 7500,
      pnl: 0,
      pnlPercent: 0,
      status: 'pending',
      timestamp: new Date(Date.now() - 300000),
    },
    {
      id: 'p2',
      pair: 'USD/CHF',
      type: 'SELL',
      entryPrice: 0.8856,
      currentPrice: 0.8858,
      amount: 6000,
      pnl: 0,
      pnlPercent: 0,
      status: 'pending',
      timestamp: new Date(Date.now() - 180000),
    },
  ]);

  const [recentTrades, setRecentTrades] = useState<Trade[]>([
    {
      id: 'r1',
      pair: 'EUR/USD',
      type: 'SELL',
      entryPrice: 1.0823,
      currentPrice: 1.0856,
      amount: 9000,
      pnl: 297,
      pnlPercent: 3.30,
      status: 'closed',
      timestamp: new Date(Date.now() - 14400000),
    },
    {
      id: 'r2',
      pair: 'GBP/JPY',
      type: 'BUY',
      entryPrice: 189.45,
      currentPrice: 189.12,
      amount: 4500,
      pnl: -148.50,
      pnlPercent: -3.30,
      status: 'closed',
      timestamp: new Date(Date.now() - 18000000),
    },
  ]);

  const [equityChart, setEquityChart] = useState<ChartDataPoint[]>([
    { time: '00:00', value: 44850 },
    { time: '04:00', value: 45200 },
    { time: '08:00', value: 45650 },
    { time: '12:00', value: 46100 },
    { time: '16:00', value: 46800 },
    { time: '20:00', value: 47200 },
    { time: '24:00', value: 47500 },
  ]);

  const [pnlChart, setPnlChart] = useState<ChartDataPoint[]>([
    { time: 'Mon', value: 320 },
    { time: 'Tue', value: -180 },
    { time: 'Wed', value: 450 },
    { time: 'Thu', value: 280 },
    { time: 'Fri', value: 620 },
    { time: 'Sat', value: 180 },
    { time: 'Sun', value: 420 },
  ]);

  const [performanceMetrics, setPerformanceMetrics] = useState<PerformanceMetrics>({
    totalTrades: 124,
    winningTrades: 85,
    losingTrades: 39,
    avgWin: 285.40,
    avgLoss: -142.20,
    sharpeRatio: 2.34,
    maxDrawdown: -8.2,
  });

  // Simulate real-time updates
  useEffect(() => {
    const interval = setInterval(() => {
      // Update active trades with small price changes
      setActiveTrades(prev => prev.map(trade => {
        const priceChange = (Math.random() - 0.5) * 0.001;
        const newPrice = trade.currentPrice * (1 + priceChange);
        const pnl = trade.type === 'BUY' 
          ? (newPrice - trade.entryPrice) * trade.amount
          : (trade.entryPrice - newPrice) * trade.amount;
        const pnlPercent = (pnl / (trade.entryPrice * trade.amount)) * 100;
        
        return {
          ...trade,
          currentPrice: newPrice,
          pnl,
          pnlPercent,
        };
      }));

      // Update portfolio metrics
      setPortfolioMetrics(prev => ({
        ...prev,
        totalValue: prev.totalValue + (Math.random() - 0.5) * 50,
        totalPnL: prev.totalPnL + (Math.random() - 0.5) * 10,
      }));
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  return {
    portfolioMetrics,
    systemHealth,
    activeTrades,
    pendingSignals,
    recentTrades,
    equityChart,
    pnlChart,
    performanceMetrics,
  };
}
