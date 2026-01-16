import { eq } from 'drizzle-orm';
import { db } from '../index';
import { users, type User, type NewUser } from '../schema';

/**
 * User Repository
 * Provides CRUD operations for user data management
 */
export class UserRepository {
  /**
   * Create a new user
   */
  async createUser(data: NewUser): Promise<User> {
    const [user] = await db.insert(users).values(data).returning();
    return user;
  }

  /**
   * Get user by ID
   */
  async getUserById(id: string): Promise<User | null> {
    const [user] = await db.select().from(users).where(eq(users.id, id)).limit(1);
    return user || null;
  }

  /**
   * Get user by email
   */
  async getUserByEmail(email: string): Promise<User | null> {
    const [user] = await db.select().from(users).where(eq(users.email, email)).limit(1);
    return user || null;
  }

  /**
   * Update user
   */
  async updateUser(id: string, data: Partial<NewUser>): Promise<User | null> {
    const [user] = await db
      .update(users)
      .set({ ...data, updatedAt: new Date() })
      .where(eq(users.id, id))
      .returning();
    return user || null;
  }

  /**
   * Delete user
   */
  async deleteUser(id: string): Promise<boolean> {
    const result = await db.delete(users).where(eq(users.id, id));
    return result.rowCount > 0;
  }

  /**
   * List all users
   */
  async listUsers(): Promise<User[]> {
    return db.select().from(users).orderBy(users.createdAt);
  }
}

/**
 * Singleton instance of UserRepository
 */
export const userRepository = new UserRepository();
