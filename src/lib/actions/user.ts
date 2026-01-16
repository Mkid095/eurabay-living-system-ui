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
