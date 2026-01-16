"use client";

import { ReactNode } from "react";
import { AuthGuard } from "@/components/auth/AuthGuard";

interface SettingsLayoutProps {
  children: ReactNode;
}

/**
 * Settings layout - protected route that requires authentication
 *
 * All pages under /settings/* require the user to be authenticated.
 * Unauthenticated users will be redirected to /login.
 */
export default function SettingsLayout({ children }: SettingsLayoutProps) {
  return (
    <AuthGuard>
      {children}
    </AuthGuard>
  );
}
