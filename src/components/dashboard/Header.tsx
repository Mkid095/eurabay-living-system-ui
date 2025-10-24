"use client";

import { Bell, Search, User } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SystemHealth } from "@/hooks/useDashboardData";
import { cn } from "@/lib/utils";

interface HeaderProps {
  systemHealth: SystemHealth;
}

export function Header({ systemHealth }: HeaderProps) {
  return (
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
          {/* System Health Indicator */}
          <div className="hidden md:flex items-center gap-2 px-3 py-2 bg-card rounded-lg border border-border">
            <div className={cn(
              "w-2 h-2 rounded-full",
              systemHealth.status === 'online' ? "bg-profit animate-pulse" :
              systemHealth.status === 'warning' ? "bg-yellow-500" : "bg-loss"
            )} />
            <span className="text-sm font-medium">
              {systemHealth.latency}ms
            </span>
            <span className="text-xs text-muted-foreground hidden lg:inline">
              {systemHealth.uptime}
            </span>
          </div>

          {/* Notifications */}
          <Button variant="ghost" size="icon" className="relative">
            <Bell className="w-5 h-5" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-primary rounded-full" />
          </Button>

          {/* User Profile */}
          <Button variant="ghost" className="gap-2">
            <div className="w-8 h-8 bg-primary rounded-full flex items-center justify-center">
              <User className="w-4 h-4 text-primary-foreground" />
            </div>
            <div className="hidden sm:block text-left">
              <p className="text-sm font-medium">Trading Admin</p>
              <p className="text-xs text-muted-foreground">Premium</p>
            </div>
          </Button>
        </div>
      </div>
    </header>
  );
}
