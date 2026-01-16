"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Spinner } from "@/components/ui/spinner";

interface AuthGuardProps {
  children: React.ReactNode;
  redirectTo?: string;
}

/**
 * AuthGuard component - protects routes that require authentication
 *
 * Checks authentication status on mount and redirects unauthenticated users
 * to the login page. Shows loading state while checking auth.
 *
 * @example
 * ```tsx
 * <AuthGuard>
 *   <Dashboard />
 * </AuthGuard>
 *
 * <AuthGuard redirectTo="/auth/login">
 *   <ProtectedPage />
 * </AuthGuard>
 * ```
 */
export function AuthGuard({ children, redirectTo = "/login" }: AuthGuardProps) {
  const { user, loading, isAuthenticated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    // Redirect to login if not authenticated
    if (!loading && !isAuthenticated) {
      // Store the current path for redirect after login
      const loginUrl = `${redirectTo}?redirect=${encodeURIComponent(pathname)}`;
      router.push(loginUrl);
    }
  }, [loading, isAuthenticated, router, pathname, redirectTo]);

  // Show loading spinner while checking authentication
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Spinner className="size-8" />
          <p className="text-sm text-muted-foreground">Verifying authentication...</p>
        </div>
      </div>
    );
  }

  // Don't render children if not authenticated (will redirect)
  if (!isAuthenticated) {
    return null;
  }

  // Render children if authenticated
  return <>{children}</>;
}
