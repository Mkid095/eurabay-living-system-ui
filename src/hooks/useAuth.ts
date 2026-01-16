import { useState, useEffect, useCallback } from 'react';

/**
 * Type definition for user data returned by useAuth hook
 */
export type AuthUser = {
  id: string;
  email: string;
  name: string;
  role: 'admin' | 'trader' | 'viewer';
  emailVerified: boolean;
  image: string | null;
  createdAt: Date;
  updatedAt: Date;
};

/**
 * Type definition for authentication error
 */
export type AuthError = {
  message: string;
  code?: string;
};

/**
 * Type definition for login credentials
 */
export type LoginCredentials = {
  email: string;
  password: string;
  rememberMe?: boolean;
};

/**
 * Type definition for registration data
 */
export type RegisterData = {
  name: string;
  email: string;
  password: string;
};

/**
 * Result type for authentication operations
 */
export type AuthResult = {
  success: boolean;
  error?: string;
};

/**
 * Custom hook for authentication state and operations
 * Provides access to current user, loading state, and auth methods
 *
 * @example
 * ```tsx
 * const { user, loading, login, logout, register, error } = useAuth();
 *
 * if (loading) return <Spinner />;
 * if (!user) return <LoginPage onLogin={login} />;
 * return <Dashboard />;
 * ```
 */
export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<AuthError | null>(null);

  /**
   * Fetch the current session from the server
   */
  const fetchSession = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/auth/get-session', {
        method: 'GET',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 401) {
          // Not authenticated, but not an error
          setUser(null);
          return;
        }
        throw new Error('Failed to fetch session');
      }

      const data = await response.json();

      if (data.user) {
        setUser({
          ...data.user,
          createdAt: new Date(data.user.createdAt),
          updatedAt: new Date(data.user.updatedAt),
        });
      } else {
        setUser(null);
      }
    } catch (err) {
      const authError: AuthError = {
        message: err instanceof Error ? err.message : 'Failed to fetch session',
      };
      setError(authError);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Log in with email and password
   *
   * @param credentials - Login credentials
   * @returns Promise with success status and optional error message
   */
  const login = useCallback(async (credentials: LoginCredentials): Promise<AuthResult> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/auth/sign-in/email', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: credentials.email,
          password: credentials.password,
          rememberMe: credentials.rememberMe ?? false,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: data.message || data.error || 'Login failed',
        };
      }

      // Fetch the user session after successful login
      await fetchSession();

      return { success: true };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Login failed';
      setError({ message: errorMessage });
      return {
        success: false,
        error: errorMessage,
      };
    } finally {
      setLoading(false);
    }
  }, [fetchSession]);

  /**
   * Register a new user account
   *
   * @param data - Registration data
   * @returns Promise with success status and optional error message
   */
  const register = useCallback(async (data: RegisterData): Promise<AuthResult> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/auth/sign-up/email', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: data.email,
          password: data.password,
          name: data.name,
        }),
      });

      const responseData = await response.json();

      if (!response.ok) {
        return {
          success: false,
          error: responseData.message || responseData.error || 'Registration failed',
        };
      }

      // Fetch the user session after successful registration
      await fetchSession();

      return { success: true };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Registration failed';
      setError({ message: errorMessage });
      return {
        success: false,
        error: errorMessage,
      };
    } finally {
      setLoading(false);
    }
  }, [fetchSession]);

  /**
   * Log out the current user
   *
   * @returns Promise with success status and optional error message
   */
  const logout = useCallback(async (): Promise<AuthResult> => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/auth/sign-out', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const data = await response.json();
        return {
          success: false,
          error: data.message || data.error || 'Logout failed',
        };
      }

      setUser(null);
      return { success: true };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Logout failed';
      setError({ message: errorMessage });
      return {
        success: false,
        error: errorMessage,
      };
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Check if the current user has a specific role
   *
   * @param role - Role to check
   * @returns true if user has the role, false otherwise
   */
  const hasRole = useCallback((role: 'admin' | 'trader' | 'viewer'): boolean => {
    return user?.role === role;
  }, [user]);

  /**
   * Check if the current user has any of the specified roles
   *
   * @param roles - Array of roles to check
   * @returns true if user has any of the roles, false otherwise
   */
  const hasAnyRole = useCallback((roles: readonly ('admin' | 'trader' | 'viewer')[]): boolean => {
    return user ? roles.includes(user.role) : false;
  }, [user]);

  /**
   * Check if the current user can access a specific resource
   *
   * @param resource - Resource identifier
   * @returns true if user can access, false otherwise
   */
  const canAccessResource = useCallback((resource: string): boolean => {
    if (!user) return false;

    // Admin wildcard access
    if (user.role === 'admin') return true;

    // Define resource permissions by role
    const permissions: Record<'admin' | 'trader' | 'viewer', string[]> = {
      admin: ['*'],
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

    const rolePermissions = permissions[user.role];
    return rolePermissions.includes(resource);
  }, [user]);

  // Fetch session on mount
  useEffect(() => {
    fetchSession();
  }, [fetchSession]);

  return {
    /**
     * Current authenticated user, or null if not authenticated
     */
    user,

    /**
     * Loading state - true while fetching session or performing auth operations
     */
    loading,

    /**
     * Current error state, or null if no error
     */
    error,

    /**
     * Login with email and password
     */
    login,

    /**
     * Register a new account
     */
    register,

    /**
     * Logout the current user
     */
    logout,

    /**
     * Check if user has a specific role
     */
    hasRole,

    /**
     * Check if user has any of the specified roles
     */
    hasAnyRole,

    /**
     * Check if user can access a specific resource
     */
    canAccessResource,

    /**
     * Refresh the session from the server
     */
    refreshSession: fetchSession,

    /**
     * Whether the user is authenticated
     */
    isAuthenticated: user !== null,
  };
}
