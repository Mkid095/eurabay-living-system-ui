import { headers } from 'next/headers';
import type { User } from '@/lib/db/schema';

/**
 * Type definition for the authenticated user with role
 * This matches the Better Auth extended session type
 */
export type AuthUser = User & { role: 'admin' | 'trader' | 'viewer' };

/**
 * Type definition for authentication result
 */
export type AuthResult =
  | { success: true; user: AuthUser }
  | { success: false; error: string };

/**
 * Get the base URL for the application
 */
function getBaseURL(): string {
  if (typeof window !== 'undefined') {
    // Client side: use current origin
    return window.location.origin;
  }
  // Server side: use environment variable or localhost
  return process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';
}

/**
 * Helper to get the current session from request headers
 * This should be called in server components or server actions
 *
 * @returns The session object or null if not authenticated
 */
export async function getSession(): Promise<{
  user: AuthUser;
  token: string;
} | null> {
  try {
    const headersList = await headers();
    const cookie = headersList.get('cookie');

    if (!cookie) {
      return null;
    }

    // Use Better Auth's API to get session
    const baseURL = getBaseURL();
    const response = await fetch(`${baseURL}/api/auth/get-session`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Cookie: cookie,
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      return null;
    }

    const data = await response.json();
    if (data.user && data.session) {
      return {
        user: data.user as AuthUser,
        token: data.session.token,
      };
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Helper to get the current authenticated user
 * This should be called in server components or server actions
 *
 * @returns The authenticated user object or null if not authenticated
 */
export async function getCurrentUser(): Promise<AuthUser | null> {
  try {
    const session = await getSession();
    return session?.user || null;
  } catch {
    return null;
  }
}

/**
 * Helper to check if the current user is authenticated
 * This should be called in server components or server actions
 *
 * @returns true if user is authenticated, false otherwise
 */
export async function isAuthenticated(): Promise<boolean> {
  const user = await getCurrentUser();
  return user !== null;
}

/**
 * Helper to check if the current user has a specific role
 * This should be called in server components or server actions
 *
 * @param role - The role to check for
 * @returns true if user has the specified role, false otherwise
 */
export async function hasRole(role: 'admin' | 'trader' | 'viewer'): Promise<boolean> {
  const user = await getCurrentUser();
  return user?.role === role;
}

/**
 * Helper to check if the current user has any of the specified roles
 * This should be called in server components or server actions
 *
 * @param roles - Array of roles to check for
 * @returns true if user has any of the specified roles, false otherwise
 */
export async function hasAnyRole(roles: readonly ('admin' | 'trader' | 'viewer')[]): Promise<boolean> {
  const user = await getCurrentUser();
  return user ? roles.includes(user.role) : false;
}

/**
 * Server action helper to require authentication
 * Throws an error if the user is not authenticated
 * This should be called at the beginning of server actions that require auth
 *
 * @returns The authenticated user object
 * @throws Error if user is not authenticated
 */
export async function requireAuth(): Promise<AuthUser> {
  const user = await getCurrentUser();

  if (!user) {
    throw new Error('Authentication required. Please log in to continue.');
  }

  return user;
}

/**
 * Server action helper to require a specific role
 * Throws an error if the user doesn't have the required role
 * This should be called in server actions that require specific permissions
 *
 * @param role - The required role
 * @returns The authenticated user object
 * @throws Error if user is not authenticated or doesn't have the required role
 */
export async function requireRole(role: 'admin' | 'trader' | 'viewer'): Promise<AuthUser> {
  const user = await requireAuth();

  if (user.role !== role) {
    throw new Error(`Permission denied. ${role} role required.`);
  }

  return user;
}

/**
 * Server action helper to require any of the specified roles
 * Throws an error if the user doesn't have any of the required roles
 *
 * @param roles - Array of acceptable roles
 * @returns The authenticated user object
 * @throws Error if user is not authenticated or doesn't have any of the required roles
 */
export async function requireAnyRole(roles: readonly ('admin' | 'trader' | 'viewer')[]): Promise<AuthUser> {
  const user = await requireAuth();

  if (!roles.includes(user.role)) {
    throw new Error(`Permission denied. One of the following roles required: ${roles.join(', ')}`);
  }

  return user;
}

/**
 * Check if a user can access a specific resource based on role
 * This is a simple RBAC implementation
 *
 * @param user - The user to check (or will use current user if not provided)
 * @param resource - The resource to check access for
 * @returns true if user can access the resource, false otherwise
 */
export async function canAccessResource(
  resource: string,
  user?: AuthUser | null
): Promise<boolean> {
  const currentUser = user || await getCurrentUser();

  if (!currentUser) {
    return false;
  }

  // Define resource permissions by role
  const permissions: Record<'admin' | 'trader' | 'viewer', string[]> = {
    admin: ['*'], // Admin has access to everything
    trader: [
      'trades:read',
      'trades:approve',
      'trades:reject',
      'signals:read',
      'evolution:read',
      'profile:edit',
    ],
    viewer: [
      'trades:read',
      'signals:read',
      'evolution:read',
      'profile:edit',
    ],
  };

  // Admin wildcard access
  if (currentUser.role === 'admin') {
    return true;
  }

  // Check if user's role has permission for the resource
  const rolePermissions = permissions[currentUser.role];
  return rolePermissions.includes(resource);
}

/**
 * Sign out the current user
 * This should be called from a server action
 *
 * @returns success status
 */
export async function signOut(): Promise<{ success: boolean; error?: string }> {
  try {
    const baseURL = getBaseURL();
    await fetch(`${baseURL}/api/auth/sign-out`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to sign out',
    };
  }
}
