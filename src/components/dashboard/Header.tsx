"use client";

import { Bell, Search, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SystemHealth } from "@/hooks/useDashboardData";
import { cn } from "@/lib/utils";
import { UserMenu } from "@/components/layout/UserMenu";
import { MT5ConnectionStatus } from "@/components/dashboard/MT5ConnectionStatus";
import { useRealTimeSystemStatus } from "@/hooks/useRealTimeSystemStatus";
import { ConnectionStatus } from "@/components/dashboard/ConnectionStatus";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface HeaderProps {
  initialSystemHealth?: SystemHealth;
}

export function Header({ initialSystemHealth }: HeaderProps) {
  const {
    systemHealth,
    showBanner,
    dismissBanner,
    bannerMessage,
    bannerSeverity,
  } = useRealTimeSystemStatus(initialSystemHealth, {
    enableUnhealthyAlerts: true,
    enableAlertBanner: true,
  });

  const getStatusColor = (health: SystemHealth | null) => {
    if (!health) return 'bg-gray-500';
    switch (health.health) {
      case 'healthy':
        return 'bg-profit animate-pulse';
      case 'degraded':
        return 'bg-yellow-500';
      case 'unhealthy':
      case 'critical':
        return 'bg-loss';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <>
      {/* System Status Alert Banner */}
      {showBanner && (
        <Alert className={cn(
          "rounded-none border-l-4",
          bannerSeverity === 'error' ? "border-destructive" : "border-yellow-500"
        )}>
          <XCircle className={cn(
            "h-4 w-4",
            bannerSeverity === 'error' ? "text-destructive" : "text-yellow-500"
          )} />
          <AlertDescription className="flex items-center justify-between">
            <span>{bannerMessage}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={dismissBanner}
              className="h-auto p-1 ml-2"
            >
              <XCircle className="h-4 w-4" />
            </Button>
          </AlertDescription>
        </Alert>
      )}

      <header className="sticky top-0 z-30 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b border-border">
        <div className="flex items-center justify-between px-4 sm:px-6 py-4">
          {/* Search */}
          <div className="flex-1 max-w-md hidden sm:block">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search coins, news etc"
                className="pl-10 bg-card border-border"
              />
            </div>
          </div>

          {/* System Status & Actions */}
          <div className="flex items-center gap-4">
            {/* WebSocket Connection Status */}
            <div className="hidden lg:flex items-center gap-2 px-3 py-2 bg-card rounded-lg border border-border">
              <ConnectionStatus showLabel={true} showLatency={true} />
            </div>

            {/* MT5 Connection Status */}
            <div className="hidden md:flex items-center gap-2 px-3 py-2 bg-card rounded-lg border border-border">
              <MT5ConnectionStatus showLabel={false} />
            </div>

            {/* System Health Indicator */}
            {systemHealth && (
              <div className="hidden md:flex items-center gap-2 px-3 py-2 bg-card rounded-lg border border-border">
                <div className={cn(
                  "w-2 h-2 rounded-full",
                  getStatusColor(systemHealth)
                )} />
                <span className="text-xs text-muted-foreground hidden lg:inline">
                  {systemHealth.uptime}
                </span>
              </div>
            )}

            {/* Notifications */}
            <Button variant="ghost" size="icon" className="relative">
              <Bell className="w-5 h-5" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-primary rounded-full" />
            </Button>

            {/* User Profile Menu */}
            <UserMenu />
          </div>
        </div>
      </header>
    </>
  );
}
