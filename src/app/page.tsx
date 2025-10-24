"use client";

import { useState } from "react";
import { 
  TrendingUp, 
  Activity, 
  Shield, 
  DollarSign 
} from "lucide-react";
import { Sidebar } from "@/components/dashboard/Sidebar";
import { Header } from "@/components/dashboard/Header";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { ActiveTradesTable } from "@/components/dashboard/ActiveTradesTable";
import { PendingSignals } from "@/components/dashboard/PendingSignals";
import { RecentTrades } from "@/components/dashboard/RecentTrades";
import { ExecutionLog } from "@/components/dashboard/ExecutionLog";
import { EquityChart } from "@/components/dashboard/EquityChart";
import { PnLChart } from "@/components/dashboard/PnLChart";
import { PerformanceMetrics } from "@/components/dashboard/PerformanceMetrics";
import { SystemControls } from "@/components/dashboard/SystemControls";
import { RiskParameters } from "@/components/dashboard/RiskParameters";
import { LogsViewer } from "@/components/dashboard/LogsViewer";
import { DerivMarketOverview } from "@/components/dashboard/DerivMarketOverview";
import { EvolutionMetrics } from "@/components/dashboard/EvolutionMetrics";
import { GenerationHistoryChart } from "@/components/dashboard/GenerationHistoryChart";
import { FeatureSuccessChart } from "@/components/dashboard/FeatureSuccessChart";
import { MutationSuccessChart } from "@/components/dashboard/MutationSuccessChart";
import { ControllerDecisionTimeline } from "@/components/dashboard/ControllerDecisionTimeline";
import { EvolutionLogViewer } from "@/components/dashboard/EvolutionLogViewer";
import { EnhancedActiveTradesTable } from "@/components/dashboard/EnhancedActiveTradesTable";
import { EvolutionParameters } from "@/components/dashboard/EvolutionParameters";
import { useDashboardData } from "@/hooks/useDashboardData";
import { useEvolutionData } from "@/hooks/useEvolutionData";

export default function Home() {
  const [activeSection, setActiveSection] = useState("dashboard");
  const {
    portfolioMetrics,
    systemHealth,
    activeTrades,
    pendingSignals,
    recentTrades,
    equityChart,
    pnlChart,
    performanceMetrics,
  } = useDashboardData();

  const {
    evolutionMetrics,
    controllerHistory,
    featureSuccess,
    mutationSuccess,
    generationHistory,
    evolutionLogs,
    evolvedTrades,
  } = useEvolutionData();

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  return (
    <div className="min-h-screen bg-background">
      <Sidebar activeSection={activeSection} onSectionChange={setActiveSection} />
      
      <div className="lg:ml-64">
        <Header systemHealth={systemHealth} />
        
        <main className="p-4 sm:p-6 lg:p-8">
          {/* Dashboard Section */}
          {activeSection === "dashboard" && (
            <div className="space-y-6">
              {/* Metrics Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                  title="Portfolio Value"
                  value={formatCurrency(portfolioMetrics.totalValue)}
                  change={portfolioMetrics.totalPnLPercent}
                  icon={DollarSign}
                  iconColor="text-primary"
                />
                <MetricCard
                  title="Total P&L"
                  value={formatCurrency(portfolioMetrics.totalPnL)}
                  change={portfolioMetrics.totalPnLPercent}
                  icon={TrendingUp}
                  iconColor="text-profit"
                />
                <MetricCard
                  title="Active Trades"
                  value={portfolioMetrics.activeTrades}
                  icon={Activity}
                  iconColor="text-primary"
                />
                <MetricCard
                  title="Win Rate"
                  value={portfolioMetrics.winRate}
                  suffix="%"
                  icon={Shield}
                  iconColor="text-profit"
                />
              </div>

              {/* Evolution Status */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <EvolutionMetrics metrics={evolutionMetrics} />
                <div className="lg:col-span-2">
                  <GenerationHistoryChart data={generationHistory} />
                </div>
              </div>

              {/* Charts Row */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <EquityChart data={equityChart} />
                <PnLChart data={pnlChart} />
              </div>

              {/* Active Trades & Market Overview */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <ActiveTradesTable trades={activeTrades.slice(0, 4)} />
                </div>
                <DerivMarketOverview />
              </div>
            </div>
          )}

          {/* Trading Section */}
          {activeSection === "trading" && (
            <div className="space-y-6">
              <div>
                <h1 className="text-3xl font-bold mb-2">Trading Activity</h1>
                <p className="text-muted-foreground">Monitor and manage all trading operations</p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                  <EnhancedActiveTradesTable trades={evolvedTrades} />
                </div>
                <div className="space-y-6">
                  <PendingSignals signals={pendingSignals} />
                  <RecentTrades trades={recentTrades} />
                </div>
              </div>

              <ExecutionLog />
            </div>
          )}

          {/* Analytics Section */}
          {activeSection === "analytics" && (
            <div className="space-y-6">
              <div>
                <h1 className="text-3xl font-bold mb-2">Analytics & Performance</h1>
                <p className="text-muted-foreground">Comprehensive performance analysis and insights</p>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                  title="Total Trades"
                  value={performanceMetrics.totalTrades}
                  icon={Activity}
                  iconColor="text-primary"
                />
                <MetricCard
                  title="Winning Trades"
                  value={performanceMetrics.winningTrades}
                  icon={TrendingUp}
                  iconColor="text-profit"
                />
                <MetricCard
                  title="Sharpe Ratio"
                  value={performanceMetrics.sharpeRatio}
                  icon={Shield}
                  iconColor="text-primary"
                />
                <MetricCard
                  title="Max Drawdown"
                  value={performanceMetrics.maxDrawdown}
                  suffix="%"
                  icon={TrendingUp}
                  iconColor="text-loss"
                />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <EquityChart data={equityChart} />
                <PnLChart data={pnlChart} />
              </div>

              {/* Evolution Analytics */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <FeatureSuccessChart data={featureSuccess} />
                <MutationSuccessChart data={mutationSuccess} />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <PerformanceMetrics metrics={performanceMetrics} />
                <ControllerDecisionTimeline data={controllerHistory} />
              </div>

              <GenerationHistoryChart data={generationHistory} />
            </div>
          )}

          {/* Evolution Section */}
          {activeSection === "evolution" && (
            <div className="space-y-6">
              <div>
                <h1 className="text-3xl font-bold mb-2">Living System Evolution</h1>
                <p className="text-muted-foreground">Track the system's evolutionary process and adaptation</p>
              </div>

              {/* Evolution Metrics */}
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <EvolutionMetrics metrics={evolutionMetrics} />
                <div className="lg:col-span-2">
                  <GenerationHistoryChart data={generationHistory} />
                </div>
              </div>

              {/* Feature & Mutation Success */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <FeatureSuccessChart data={featureSuccess} />
                <MutationSuccessChart data={mutationSuccess} />
              </div>

              {/* Controller Timeline & Evolution Logs */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <ControllerDecisionTimeline data={controllerHistory} />
                <EvolutionLogViewer logs={evolutionLogs} />
              </div>

              {/* Enhanced Active Trades */}
              <EnhancedActiveTradesTable trades={evolvedTrades} />
            </div>
          )}

          {/* Config Section */}
          {activeSection === "config" && (
            <div className="space-y-6">
              <div>
                <h1 className="text-3xl font-bold mb-2">System Configuration</h1>
                <p className="text-muted-foreground">Manage system settings and risk parameters</p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <SystemControls />
                <RiskParameters />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <EvolutionParameters />
                <div className="space-y-6">
                  <DerivMarketOverview />
                </div>
              </div>

              <LogsViewer />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}