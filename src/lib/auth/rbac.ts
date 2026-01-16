/**
 * Role-Based Access Control (RBAC) Module
 *
 * Provides centralized role and permission management for the EURABAY Living System.
 * This module defines user roles, permissions, and helper functions for access control.
 *
 * Roles:
 * - admin: Full access to all resources and controls
 * - trader: Can approve/reject trades, read market data, manage profile
 * - viewer: Read-only access to dashboard data and profile management
 */

/**
 * User role type definition
 */
export type UserRole = 'admin' | 'trader' | 'viewer';

/**
 * Resource permission type
 * Resources are formatted as "resource:action" (e.g., "trades:read", "system:control")
 */
export type ResourcePermission = string;

/**
 * User type for RBAC checks
 */
export type RBACUser = {
  role: UserRole;
};

/**
 * Permission matrix mapping roles to their allowed resources
 * Admin has wildcard access to all resources
 */
const PERMISSION_MATRIX: Record<UserRole, ResourcePermission[]> = {
  admin: ['*'], // Wildcard - admin can access everything
  trader: [
    'trades:read',
    'trades:approve',
    'trades:reject',
    'signals:read',
    'signals:approve',
    'signals:reject',
    'evolution:read',
    'profile:read',
    'profile:edit',
    'market:read',
    'analytics:read',
  ],
  viewer: [
    'trades:read',
    'signals:read',
    'evolution:read',
    'profile:read',
    'profile:edit',
    'market:read',
    'analytics:read',
  ],
};

/**
 * Resources that require specific roles
 */
export const PROTECTED_RESOURCES = {
  // System controls (start/stop) - admin only
  'system:control': ['admin'] as UserRole[],
  'system:start': ['admin'] as UserRole[],
  'system:stop': ['admin'] as UserRole[],
  'system:restart': ['admin'] as UserRole[],
  'system:config': ['admin'] as UserRole[],

  // Trade approval/rejection - trader and admin
  'trades:approve': ['trader', 'admin'] as UserRole[],
  'trades:reject': ['trader', 'admin'] as UserRole[],

  // Signal approval/rejection - trader and admin
  'signals:approve': ['trader', 'admin'] as UserRole[],
  'signals:reject': ['trader', 'admin'] as UserRole[],

  // User management - admin only
  'users:read': ['admin'] as UserRole[],
  'users:create': ['admin'] as UserRole[],
  'users:edit': ['admin'] as UserRole[],
  'users:delete': ['admin'] as UserRole[],
  'users:ban': ['admin'] as UserRole[],

  // Role management - admin only
  'roles:read': ['admin'] as UserRole[],
  'roles:assign': ['admin'] as UserRole[],

  // Risk parameters - admin only
  'risk:read': ['admin', 'trader'] as UserRole[],
  'risk:edit': ['admin'] as UserRole[],
} as const;

/**
 * Check if a user has a specific role
 *
 * @param user - The user to check (or null for unauthenticated)
 * @param role - The role to check for
 * @returns true if user has the specified role, false otherwise
 *
 * @example
 * hasRole({ role: 'admin' }, 'admin') // true
 * hasRole({ role: 'viewer' }, 'admin') // false
 * hasRole(null, 'admin') // false
 */
export function hasRole(user: RBACUser | null, role: UserRole): boolean {
  if (!user) {
    return false;
  }
  return user.role === role;
}

/**
 * Check if a user has any of the specified roles
 *
 * @param user - The user to check
 * @param roles - Array of roles to check for
 * @returns true if user has any of the specified roles, false otherwise
 *
 * @example
 * hasAnyRole({ role: 'trader' }, ['admin', 'trader']) // true
 * hasAnyRole({ role: 'viewer' }, ['admin', 'trader']) // false
 */
export function hasAnyRole(user: RBACUser | null, roles: readonly UserRole[]): boolean {
  if (!user) {
    return false;
  }
  return roles.includes(user.role);
}

/**
 * Check if a user can access a specific resource based on their role
 *
 * Uses the permission matrix to determine if the user's role grants access
 * to the requested resource. Admin users have wildcard access to all resources.
 *
 * @param user - The user to check
 * @param resource - The resource permission to check (e.g., "trades:read")
 * @returns true if user can access the resource, false otherwise
 *
 * @example
 * canAccessResource({ role: 'admin' }, 'system:control') // true (admin wildcard)
 * canAccessResource({ role: 'trader' }, 'trades:approve') // true
 * canAccessResource({ role: 'viewer' }, 'trades:approve') // false
 * canAccessResource({ role: 'viewer' }, 'trades:read') // true
 */
export function canAccessResource(user: RBACUser | null, resource: ResourcePermission): boolean {
  if (!user) {
    return false;
  }

  // Admin wildcard access
  if (user.role === 'admin') {
    return true;
  }

  // Get permissions for user's role
  const rolePermissions = PERMISSION_MATRIX[user.role];

  // Check if role has permission for the resource
  return rolePermissions.includes(resource);
}

/**
 * Check if a user has permission for a specific protected resource
 *
 * This function checks against the PROTECTED_RESOURCES mapping for more
 * granular control over individual resources.
 *
 * @param user - The user to check
 * @param resource - The resource key from PROTECTED_RESOURCES
 * @returns true if user has permission, false otherwise
 *
 * @example
 * hasResourcePermission({ role: 'admin' }, 'system:control') // true
 * hasResourcePermission({ role: 'trader' }, 'system:control') // false
 * hasResourcePermission({ role: 'trader' }, 'trades:approve') // true
 * hasResourcePermission({ role: 'viewer' }, 'trades:approve') // false
 */
export function hasResourcePermission(
  user: RBACUser | null,
  resource: keyof typeof PROTECTED_RESOURCES
): boolean {
  if (!user) {
    return false;
  }

  const allowedRoles = PROTECTED_RESOURCES[resource];
  return allowedRoles.includes(user.role);
}

/**
 * Get all permissions for a given role
 *
 * @param role - The role to get permissions for
 * @returns Array of resource permissions for the role
 *
 * @example
 * getRolePermissions('admin') // ['*']
 * getRolePermissions('viewer') // ['trades:read', 'signals:read', ...]
 */
export function getRolePermissions(role: UserRole): ResourcePermission[] {
  return PERMISSION_MATRIX[role];
}

/**
 * Check if a role is higher in hierarchy than another
 *
 * Role hierarchy: admin > trader > viewer
 *
 * @param role - The role to check
 * @param minimumRole - The minimum required role
 * @returns true if role meets or exceeds minimumRole
 *
 * @example
 * meetsMinimumRole('admin', 'trader') // true
 * meetsMinimumRole('trader', 'admin') // false
 * meetsMinimumRole('viewer', 'viewer') // true
 */
export function meetsMinimumRole(role: UserRole, minimumRole: UserRole): boolean {
  const roleHierarchy: Record<UserRole, number> = {
    admin: 3,
    trader: 2,
    viewer: 1,
  };

  return roleHierarchy[role] >= roleHierarchy[minimumRole];
}

/**
 * Validate that a user has access to a resource
 * Throws an error if access is denied
 *
 * @param user - The user to validate
 * @param resource - The resource to check access for
 * @throws Error if user is null or doesn't have access
 *
 * @example
 * try {
 *   requireResourceAccess({ role: 'admin' }, 'system:control');
 *   // Access granted
 * } catch (error) {
 *   // Access denied
 * }
 */
export function requireResourceAccess(
  user: RBACUser | null,
  resource: keyof typeof PROTECTED_RESOURCES
): void {
  if (!user) {
    throw new Error('Authentication required. Please log in to continue.');
  }

  if (!hasResourcePermission(user, resource)) {
    throw new Error(
      `Permission denied. Resource "${resource}" requires one of the following roles: ${PROTECTED_RESOURCES[resource].join(', ')}`
    );
  }
}

/**
 * Validate that a user has a specific role
 * Throws an error if the role requirement is not met
 *
 * @param user - The user to validate
 * @param role - The required role
 * @throws Error if user is null or doesn't have the required role
 *
 * @example
 * try {
 *   requireRole({ role: 'admin' }, 'admin');
 *   // Role validated
 * } catch (error) {
 *   // Permission denied
 * }
 */
export function requireRole(user: RBACUser | null, role: UserRole): void {
  if (!user) {
    throw new Error('Authentication required. Please log in to continue.');
  }

  if (!hasRole(user, role)) {
    throw new Error(`Permission denied. ${role} role required.`);
  }
}

/**
 * Validate that a user has any of the specified roles
 * Throws an error if none of the role requirements are met
 *
 * @param user - The user to validate
 * @param roles - Array of acceptable roles
 * @throws Error if user is null or doesn't have any of the required roles
 *
 * @example
 * try {
 *   requireAnyRole({ role: 'trader' }, ['admin', 'trader']);
 *   // Access granted
 * } catch (error) {
 *   // Permission denied
 * }
 */
export function requireAnyRole(user: RBACUser | null, roles: readonly UserRole[]): void {
  if (!user) {
    throw new Error('Authentication required. Please log in to continue.');
  }

  if (!hasAnyRole(user, roles)) {
    throw new Error(`Permission denied. One of the following roles required: ${roles.join(', ')}`);
  }
}

/**
 * Role display names for UI
 */
export const ROLE_DISPLAY_NAMES: Record<UserRole, string> = {
  admin: 'Administrator',
  trader: 'Trader',
  viewer: 'Viewer',
};

/**
 * Role descriptions for UI
 */
export const ROLE_DESCRIPTIONS: Record<UserRole, string> = {
  admin: 'Full access to all system controls and user management',
  trader: 'Can approve/reject trades and signals, read market data',
  viewer: 'Read-only access to dashboard, signals, and analytics',
};
