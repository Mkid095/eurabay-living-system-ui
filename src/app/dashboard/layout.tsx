"use client";

import { ReactNode } from "react";
import { AuthGuard } from "@/components/auth/AuthGuard";
import SessionTimeoutProvider from "@/components/auth/SessionTimeoutProvider";

interface DashboardLayoutProps {
  children: ReactNode;
}

/**
 * Dashboard layout - protected route that requires authentication
 *
 * All pages under /dashboard/* require the user to be authenticated.
 * Unauthenticated users will be redirected to /login.
 *
 * Includes session timeout monitoring to auto-logout after inactivity.
 */
export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <AuthGuard>
      <SessionTimeoutProvider />
      {children}
    </AuthGuard>
  );
}
