"use client";

import { ReactNode } from "react";
import { AuthGuard } from "@/components/auth/AuthGuard";

interface DashboardLayoutProps {
  children: ReactNode;
}

/**
 * Dashboard layout - protected route that requires authentication
 *
 * All pages under /dashboard/* require the user to be authenticated.
 * Unauthenticated users will be redirected to /login.
 */
export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <AuthGuard>
      {children}
    </AuthGuard>
  );
}
