"use client";

import { ReactNode } from "react";
import { useSession } from "@/hooks/useSession";
import type { ExtendedSession } from "@/lib/auth";

type UserRole = "admin" | "trader" | "viewer";

interface RoleGuardProps {
  children: ReactNode;
  allowedRoles: UserRole[];
  fallback?: ReactNode;
}

/**
 * RoleGuard component - restricts child content to users with specified roles
 *
 * @example
 * <RoleGuard allowedRoles={["admin"]}>
 *   <AdminPanel />
 * </RoleGuard>
 */
export function RoleGuard({ children, allowedRoles, fallback = null }: RoleGuardProps) {
  const { data: session, isLoading } = useSession();

  // Show nothing while loading session
  if (isLoading) {
    return null;
  }

  // Show fallback if no session
  if (!session) {
    return <>{fallback}</>;
  }

  // Check if user has required role
  // Use optional chaining and type assertion for safety
  const extendedSession = session as ExtendedSession | null;
  const userRole = extendedSession?.user?.role as UserRole | undefined;
  const hasAccess = userRole ? allowedRoles.includes(userRole) : false;

  if (!hasAccess) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

/**
 * Hook to check if current user has a specific role
 */
export function useRole(role: UserRole): boolean {
  const { data: session } = useSession();
  const extendedSession = session as ExtendedSession | null;
  const userRole = extendedSession?.user?.role as UserRole | undefined;
  return userRole === role;
}

/**
 * Hook to check if current user has any of the specified roles
 */
export function useHasAnyRole(roles: UserRole[]): boolean {
  const { data: session } = useSession();
  const extendedSession = session as ExtendedSession | null;
  const userRole = extendedSession?.user?.role as UserRole | undefined;
  return userRole ? roles.includes(userRole) : false;
}
