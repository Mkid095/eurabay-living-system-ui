"use client";

import { ReactNode } from "react";
import { useAuth } from "@/hooks/useAuth";
import { ROLE_DISPLAY_NAMES, type UserRole } from "@/lib/auth/rbac";
import { Spinner } from "@/components/ui/spinner";
import { Lock } from "lucide-react";

interface RoleGuardProps {
  children: ReactNode;
  allowedRoles: readonly UserRole[];
  fallback?: ReactNode;
  showAccessDenied?: boolean;
}

/**
 * RoleGuard component - restricts child content to users with specified roles
 *
 * Wraps children to only render if the current user has one of the allowed roles.
 * Shows a loading spinner while checking authentication and optionally shows
 * an access denied message when access is denied.
 *
 * @example
 * // Only show admin panel to admin users
 * <RoleGuard allowedRoles={["admin"]}>
 *   <AdminPanel />
 * </RoleGuard>
 *
 * // Show to traders and admins
 * <RoleGuard allowedRoles={["admin", "trader"]}>
 *   <TradeControls />
 * </RoleGuard>
 *
 * // Show custom fallback on access denied
 * <RoleGuard allowedRoles={["admin"]} fallback={<div>Not authorized</div>}>
 *   <AdminSettings />
 * </RoleGuard>
 */
export function RoleGuard({
  children,
  allowedRoles,
  fallback,
  showAccessDenied = false,
}: RoleGuardProps) {
  const { user, loading } = useAuth();

  // Show loading state while checking auth
  if (loading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Spinner />
      </div>
    );
  }

  // Check if user has required role
  const hasAccess = user && allowedRoles.includes(user.role);

  if (!hasAccess) {
    // Show custom fallback if provided
    if (fallback !== undefined) {
      return <>{fallback}</>;
    }

    // Show access denied message if enabled
    if (showAccessDenied) {
      return (
        <div className="flex flex-col items-center justify-center p-8 text-center">
          <div className="w-16 h-16 rounded-full bg-muted flex items-center justify-center mb-4">
            <Lock className="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Access Denied</h3>
          <p className="text-sm text-muted-foreground max-w-sm">
            This content requires one of the following roles:{' '}
            {allowedRoles.map((r) => ROLE_DISPLAY_NAMES[r]).join(', ')}
          </p>
          <p className="text-xs text-muted-foreground mt-2">
            Your current role:{' '}
            {user ? ROLE_DISPLAY_NAMES[user.role] : 'Not authenticated'}
          </p>
        </div>
      );
    }

    // Show nothing by default
    return null;
  }

  return <>{children}</>;
}

/**
 * AdminGuard - convenience component for admin-only content
 *
 * @example
 * <AdminGuard>
 *   <SystemControls />
 * </AdminGuard>
 */
export function AdminGuard({ children, fallback, showAccessDenied }: Omit<RoleGuardProps, 'allowedRoles'>) {
  return (
    <RoleGuard allowedRoles={['admin']} fallback={fallback} showAccessDenied={showAccessDenied}>
      {children}
    </RoleGuard>
  );
}

/**
 * TraderGuard - convenience component for trader and admin content
 *
 * @example
 * <TraderGuard>
 *   <TradeApprovalButtons />
 * </TraderGuard>
 */
export function TraderGuard({ children, fallback, showAccessDenied }: Omit<RoleGuardProps, 'allowedRoles'>) {
  return (
    <RoleGuard
      allowedRoles={['admin', 'trader']}
      fallback={fallback}
      showAccessDenied={showAccessDenied}
    >
      {children}
    </RoleGuard>
  );
}

/**
 * ViewerGuard - convenience component for all authenticated users
 *
 * @example
 * <ViewerGuard>
 *   <DashboardContent />
 * </ViewerGuard>
 */
export function ViewerGuard({ children, fallback, showAccessDenied }: Omit<RoleGuardProps, 'allowedRoles'>) {
  return (
    <RoleGuard
      allowedRoles={['admin', 'trader', 'viewer']}
      fallback={fallback}
      showAccessDenied={showAccessDenied}
    >
      {children}
    </RoleGuard>
  );
}
