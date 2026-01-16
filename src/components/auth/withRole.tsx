import { ReactNode } from 'react';
import { useAuth } from '@/hooks/useAuth';
import type { UserRole } from '@/lib/auth/rbac';
import { Spinner } from '@/components/ui/spinner';

/**
 * Higher-Order Component for role-based access control
 *
 * Wraps a component to only render if the current user has the required role.
 * Shows a loading spinner while checking authentication and renders
 * a fallback (if provided) when access is denied.
 *
 * @param Component - The component to wrap
 * @param requiredRole - The role required to access the component
 * @param fallback - Optional fallback to render when access is denied
 * @returns A new component with role-based access control
 *
 * @example
 * // Wrap a component to require admin role
 * const AdminPanel = withRole(() => <div>Admin Settings</div>, 'admin');
 *
 * // Render with fallback
 * const AdminPanel = withRole(
 *   () => <div>Admin Settings</div>,
 *   'admin',
 *   <div>Access Denied</div>
 * );
 */
export function withRole<P extends object>(
  Component: React.ComponentType<P>,
  requiredRole: UserRole,
  fallback?: ReactNode
): React.ComponentType<P> {
  return function WithRoleComponent(props: P) {
    const { user, loading } = useAuth();

    // Show loading state while checking auth
    if (loading) {
      return (
        <div className="flex items-center justify-center p-4">
          <Spinner />
        </div>
      );
    }

    // Show fallback if not authenticated or wrong role
    if (!user || user.role !== requiredRole) {
      return <>{fallback}</>;
    }

    // Render the protected component
    return <Component {...props} />;
  };
}

/**
 * Higher-Order Component for multiple role-based access control
 *
 * Wraps a component to only render if the current user has any of the required roles.
 *
 * @param Component - The component to wrap
 * @param allowedRoles - Array of roles that can access the component
 * @param fallback - Optional fallback to render when access is denied
 * @returns A new component with role-based access control
 *
 * @example
 * const TradeControls = withAnyRole(
 *   () => <div>Approve/Reject Buttons</div>,
 *   ['admin', 'trader']
 * );
 */
export function withAnyRole<P extends object>(
  Component: React.ComponentType<P>,
  allowedRoles: readonly UserRole[],
  fallback?: ReactNode
): React.ComponentType<P> {
  return function WithAnyRoleComponent(props: P) {
    const { user, loading } = useAuth();

    // Show loading state while checking auth
    if (loading) {
      return (
        <div className="flex items-center justify-center p-4">
          <Spinner />
        </div>
      );
    }

    // Show fallback if not authenticated or no matching role
    if (!user || !allowedRoles.includes(user.role)) {
      return <>{fallback}</>;
    }

    // Render the protected component
    return <Component {...props} />;
  };
}

/**
 * Higher-Order Component for minimum role requirement
 *
 * Wraps a component to only render if the current user meets or exceeds
 * the minimum required role in the hierarchy (admin > trader > viewer).
 *
 * @param Component - The component to wrap
 * @param minimumRole - The minimum role required
 * @param fallback - Optional fallback to render when access is denied
 * @returns A new component with role-based access control
 *
 * @example
 * const AdminOrTraderPanel = withMinimumRole(
 *   () => <div>Advanced Features</div>,
 *   'trader' // admin and trader can access
 * );
 */
export function withMinimumRole<P extends object>(
  Component: React.ComponentType<P>,
  minimumRole: UserRole,
  fallback?: ReactNode
): React.ComponentType<P> {
  return function WithMinimumRoleComponent(props: P) {
    const { user, loading, hasRole } = useAuth();

    // Show loading state while checking auth
    if (loading) {
      return (
        <div className="flex items-center justify-center p-4">
          <Spinner />
        </div>
      );
    }

    // Show fallback if not authenticated or below minimum role
    if (!user) {
      return <>{fallback}</>;
    }

    // Check role hierarchy
    const roleHierarchy: Record<UserRole, number> = {
      admin: 3,
      trader: 2,
      viewer: 1,
    };

    const currentLevel = roleHierarchy[user.role];
    const requiredLevel = roleHierarchy[minimumRole];

    if (currentLevel < requiredLevel) {
      return <>{fallback}</>;
    }

    // Render the protected component
    return <Component {...props} />;
  };
}
