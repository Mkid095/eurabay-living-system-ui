'use server';

import { requireAuth } from '@/lib/auth/utils';
import { db } from '@/lib/db';
import { eq } from 'drizzle-orm';
import * as schema from '@/lib/db/schema';
import type { AuthUser } from '@/lib/auth/utils';
import { auth } from '@/lib/auth';

/**
 * Result type for user actions
 */
type ActionResult<T = void> =
  | { success: true; data?: T }
  | { success: false; error: string };

/**
 * Update user profile information
 * @param data - Profile data to update (name, image)
 * @returns Updated user object or error
 */
export async function updateUserProfile(data: {
  name?: string;
  image?: string | null;
}): Promise<ActionResult<{ user: AuthUser }>> {
  try {
    const user = await requireAuth();

    // Build update object with only provided fields
    const updateData: Record<string, unknown> = {
      updatedAt: new Date(),
    };

    if (data.name !== undefined) {
      updateData.name = data.name;
    }

    if (data.image !== undefined) {
      updateData.image = data.image;
    }

    // Update user in database
    const updatedUsers = await db
      .update(schema.users)
      .set(updateData)
      .where(eq(schema.users.id, user.id))
      .returning();

    if (!updatedUsers || updatedUsers.length === 0) {
      return { success: false, error: 'Failed to update profile' };
    }

    const updatedUser = updatedUsers[0];

    return {
      success: true,
      data: {
        user: updatedUser as AuthUser,
      },
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to update profile',
    };
  }
}

/**
 * Change user password using Better Auth's built-in changePassword endpoint
 * @param data - Password change data (currentPassword, newPassword)
 * @returns Success or error
 */
export async function changePassword(data: {
  currentPassword: string;
  newPassword: string;
  revokeOtherSessions?: boolean;
}): Promise<ActionResult> {
  try {
    const baseURL = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';

    // Use Better Auth's built-in changePassword endpoint
    const response = await fetch(`${baseURL}/api/auth/change-password`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        cookie: (await getServerCookie()) || '',
      },
      body: JSON.stringify({
        currentPassword: data.currentPassword,
        newPassword: data.newPassword,
        revokeOtherSessions: data.revokeOtherSessions ?? true,
      }),
    });

    if (!response.ok) {
      const responseData = await response.json().catch(() => ({}));
      return {
        success: false,
        error: responseData.message || responseData.error || 'Failed to change password',
      };
    }

    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to change password',
    };
  }
}

/**
 * Get user profile with additional data
 * @returns User profile data or error
 */
export async function getUserProfile(): Promise<ActionResult<{
  user: AuthUser;
  createdAt: Date;
  lastLogin?: Date;
}>> {
  try {
    const user = await requireAuth();

    // Get the most recent session for last login (ordered by createdAt descending)
    const sessions = await db
      .select()
      .from(schema.sessions)
      .where(eq(schema.sessions.userId, user.id))
      .orderBy((sessions) => [sessions.createdAt]) // Default is ascending
      .limit(1);

    const lastLogin = sessions && sessions.length > 0 ? sessions[0].createdAt : undefined;

    return {
      success: true,
      data: {
        user,
        createdAt: user.createdAt,
        lastLogin,
      },
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to fetch profile',
    };
  }
}

/**
 * Helper to get server-side cookies for fetch requests
 * This is needed when calling Better Auth endpoints from server actions
 */
async function getServerCookie(): Promise<string | undefined> {
  try {
    const { cookies } = await import('next/headers');
    const cookiesList = await cookies();
    return cookiesList
      .getAll()
      .map((c) => `${c.name}=${c.value}`)
      .join('; ');
  } catch {
    return undefined;
  }
}

/**
 * Admin: Get all users with pagination and filtering
 * @param options - Pagination and filter options
 * @returns List of users or error
 */
export async function getAllUsers(options?: {
  limit?: number;
  offset?: number;
  search?: string;
  role?: 'admin' | 'trader' | 'viewer';
}): Promise<ActionResult<{
  users: Array<{
    id: string;
    name: string;
    email: string;
    role: 'admin' | 'trader' | 'viewer';
    emailVerified: boolean;
    image: string | null;
    createdAt: Date;
    updatedAt: Date;
    lastLogin?: Date;
  }>;
  total: number;
}>> {
  try {
    // Require admin role
    const adminUser = await requireAuth();
    if (adminUser.role !== 'admin') {
      return { success: false, error: 'Permission denied. Admin role required.' };
    }

    const { limit = 50, offset = 0, search, role } = options || {};

    // Build query conditions
    const conditions: unknown[] = [];

    if (role) {
      const { eq } = await import('drizzle-orm');
      conditions.push(eq(schema.users.role, role));
    }

    // Get users with pagination
    let usersQuery = db
      .select({
        id: schema.users.id,
        name: schema.users.name,
        email: schema.users.email,
        role: schema.users.role,
        emailVerified: schema.users.emailVerified,
        image: schema.users.image,
        createdAt: schema.users.createdAt,
        updatedAt: schema.users.updatedAt,
      })
      .from(schema.users)
      .limit(limit)
      .offset(offset);

    // Apply role filter if specified
    if (role) {
      const { eq } = await import('drizzle-orm');
      usersQuery = usersQuery.where(eq(schema.users.role, role));
    }

    const users = await usersQuery;

    // Get last login for each user
    const usersWithLastLogin = await Promise.all(
      users.map(async (user) => {
        const sessions = await db
          .select()
          .from(schema.sessions)
          .where(eq(schema.sessions.userId, user.id))
          .orderBy((sessions) => [sessions.createdAt])
          .limit(1);

        return {
          ...user,
          lastLogin: sessions && sessions.length > 0 ? sessions[0].createdAt : undefined,
        };
      })
    );

    // Filter by search term if provided
    let filteredUsers = usersWithLastLogin;
    if (search) {
      const searchLower = search.toLowerCase();
      filteredUsers = usersWithLastLogin.filter(
        (user) =>
          user.name.toLowerCase().includes(searchLower) ||
          user.email.toLowerCase().includes(searchLower)
      );
    }

    // Get total count
    const allUsers = await db.select().from(schema.users);
    let totalForFilter = allUsers.length;
    if (search) {
      const searchLower = search.toLowerCase();
      totalForFilter = allUsers.filter(
        (u) =>
          u.name.toLowerCase().includes(searchLower) ||
          u.email.toLowerCase().includes(searchLower)
      ).length;
    } else if (role) {
      totalForFilter = allUsers.filter((u) => u.role === role).length;
    }

    return {
      success: true,
      data: {
        users: filteredUsers,
        total: totalForFilter,
      },
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to fetch users',
    };
  }
}

/**
 * Admin: Create a new user
 * @param data - User creation data
 * @returns Created user or error
 */
export async function createUser(data: {
  name: string;
  email: string;
  password: string;
  role: 'admin' | 'trader' | 'viewer';
}): Promise<ActionResult<{ user: { id: string; name: string; email: string; role: string } }>> {
  try {
    // Require admin role
    const adminUser = await requireAuth();
    if (adminUser.role !== 'admin') {
      return { success: false, error: 'Permission denied. Admin role required.' };
    }

    const { name, email, password, role } = data;

    // Validate input
    if (!name || name.trim().length < 2) {
      return { success: false, error: 'Name must be at least 2 characters long.' };
    }

    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      return { success: false, error: 'Invalid email address.' };
    }

    if (!password || password.length < 8) {
      return { success: false, error: 'Password must be at least 8 characters long.' };
    }

    // Check if email already exists
    const { eq } = await import('drizzle-orm');
    const existingUsers = await db
      .select()
      .from(schema.users)
      .where(eq(schema.users.email, email));

    if (existingUsers.length > 0) {
      return { success: false, error: 'A user with this email already exists.' };
    }

    // Hash password
    const bcrypt = await import('bcrypt');
    const passwordHash = await bcrypt.hash(password, 10);

    // Generate unique ID
    const crypto = await import('crypto');
    const userId = crypto.randomBytes(16).toString('hex');

    // Create user
    const newUsers = await db
      .insert(schema.users)
      .values({
        id: userId,
        name: name.trim(),
        email: email.trim().toLowerCase(),
        passwordHash,
        role,
        emailVerified: false,
        image: null,
        createdAt: new Date(),
        updatedAt: new Date(),
      })
      .returning();

    if (!newUsers || newUsers.length === 0) {
      return { success: false, error: 'Failed to create user.' };
    }

    const newUser = newUsers[0];

    return {
      success: true,
      data: {
        user: {
          id: newUser.id,
          name: newUser.name,
          email: newUser.email,
          role: newUser.role,
        },
      },
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to create user',
    };
  }
}

/**
 * Admin: Update user information
 * @param userId - ID of user to update
 * @param data - User data to update
 * @returns Updated user or error
 */
export async function updateUserAdmin(
  userId: string,
  data: {
    name?: string;
    email?: string;
    role?: 'admin' | 'trader' | 'viewer';
    emailVerified?: boolean;
  }
): Promise<ActionResult<{ user: { id: string; name: string; email: string; role: string } }>> {
  try {
    // Require admin role
    const adminUser = await requireAuth();
    if (adminUser.role !== 'admin') {
      return { success: false, error: 'Permission denied. Admin role required.' };
    }

    // Prevent admin from modifying their own role
    if (userId === adminUser.id && data.role !== undefined && data.role !== 'admin') {
      return { success: false, error: 'You cannot change your own admin role.' };
    }

    // Build update object with only provided fields
    const updateData: Record<string, unknown> = {
      updatedAt: new Date(),
    };

    if (data.name !== undefined) {
      if (data.name.trim().length < 2) {
        return { success: false, error: 'Name must be at least 2 characters long.' };
      }
      updateData.name = data.name.trim();
    }

    if (data.email !== undefined) {
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email)) {
        return { success: false, error: 'Invalid email address.' };
      }
      // Check if email is already taken by another user
      const { eq, and, ne } = await import('drizzle-orm');
      const existingUsers = await db
        .select()
        .from(schema.users)
        .where(and(eq(schema.users.email, data.email.trim().toLowerCase()), ne(schema.users.id, userId)));

      if (existingUsers.length > 0) {
        return { success: false, error: 'A user with this email already exists.' };
      }
      updateData.email = data.email.trim().toLowerCase();
    }

    if (data.role !== undefined) {
      updateData.role = data.role;
    }

    if (data.emailVerified !== undefined) {
      updateData.emailVerified = data.emailVerified;
    }

    // Update user in database
    const { eq } = await import('drizzle-orm');
    const updatedUsers = await db
      .update(schema.users)
      .set(updateData)
      .where(eq(schema.users.id, userId))
      .returning();

    if (!updatedUsers || updatedUsers.length === 0) {
      return { success: false, error: 'User not found.' };
    }

    const updatedUser = updatedUsers[0];

    return {
      success: true,
      data: {
        user: {
          id: updatedUser.id,
          name: updatedUser.name,
          email: updatedUser.email,
          role: updatedUser.role,
        },
      },
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to update user',
    };
  }
}

/**
 * Admin: Delete a user
 * @param userId - ID of user to delete
 * @returns Success or error
 */
export async function deleteUser(userId: string): Promise<ActionResult> {
  try {
    // Require admin role
    const adminUser = await requireAuth();
    if (adminUser.role !== 'admin') {
      return { success: false, error: 'Permission denied. Admin role required.' };
    }

    // Prevent admin from deleting themselves
    if (userId === adminUser.id) {
      return { success: false, error: 'You cannot delete your own account.' };
    }

    const { eq } = await import('drizzle-orm');

    // Delete user's sessions first
    await db.delete(schema.sessions).where(eq(schema.sessions.userId, userId));

    // Delete user's accounts
    await db.delete(schema.accounts).where(eq(schema.accounts.userId, userId));

    // Delete user
    const deletedUsers = await db.delete(schema.users).where(eq(schema.users.id, userId)).returning();

    if (!deletedUsers || deletedUsers.length === 0) {
      return { success: false, error: 'User not found.' };
    }

    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to delete user',
    };
  }
}

/**
 * Admin: Ban/Unban a user (by setting emailVerified to false)
 * @param userId - ID of user to ban/unban
 * @param banned - Whether to ban (true) or unban (false) the user
 * @returns Success or error
 */
export async function setUserBannedStatus(userId: string, banned: boolean): Promise<ActionResult> {
  try {
    // Require admin role
    const adminUser = await requireAuth();
    if (adminUser.role !== 'admin') {
      return { success: false, error: 'Permission denied. Admin role required.' };
    }

    // Prevent admin from banning themselves
    if (userId === adminUser.id && banned) {
      return { success: false, error: 'You cannot ban your own account.' };
    }

    const { eq } = await import('drizzle-orm');

    // Update user's banned status (using emailVerified as a proxy - false = banned)
    const updatedUsers = await db
      .update(schema.users)
      .set({
        emailVerified: !banned,
        updatedAt: new Date(),
      })
      .where(eq(schema.users.id, userId))
      .returning();

    if (!updatedUsers || updatedUsers.length === 0) {
      return { success: false, error: 'User not found.' };
    }

    return { success: true };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to update user status',
    };
  }
}
