# PRD: Authentication & User Management

## Overview

The EURABAY Living System currently has Better Auth configured but not implemented. This PRD defines complete authentication and user management functionality to secure the application and enable multi-user access.

## Goals

- Implement secure user authentication with Better Auth
- Create login/register UI pages
- Implement session management with token refresh
- Add protected routes with auth guards
- Implement role-based access control (RBAC)
- Add user profile management
- Implement password reset flow
- Add session timeout and logout

## Current State

**Problem:**
- Better Auth is installed but not configured
- No login/register pages exist
- No authentication logic implemented
- All routes are publicly accessible
- No session management
- No user profile storage
- No role-based permissions

**Impact:**
- Anyone can access the dashboard without authentication
- No way to track user activity
- No way to restrict sensitive operations
- Cannot implement user-specific settings
- Security vulnerability

## User Stories

### US-001: Configure Better Auth

**Description:** As a developer, I need to configure Better Auth for authentication.

**Acceptance Criteria:**
- [ ] Create `src/lib/auth.ts` with Better Auth configuration
- [ ] Configure authentication provider (email/password)
- [ ] Configure session storage (localStorage with httpOnly cookie backup)
- [ ] Configure token expiration (access token: 15min, refresh token: 7 days)
- [ ] Configure CSRF protection
- [ ] Add rate limiting for auth endpoints
- [ ] Configure allowed origins for CORS
- [ ] Add auth middleware for Next.js
- [ ] Typecheck passes

**Priority:** 1

**Technical Implementation:**

```typescript
// src/lib/auth.ts
import { betterAuth } from "better-auth";

export const auth = betterAuth({
  baseURL: process.env.NEXT_PUBLIC_APP_URL,
  baseURL: process.env.NEXT_PUBLIC_API_URL,

  // Database configuration for Drizzle
  database: drizzleAdapter(db, {
    provider: "postgresql", // or sqlite, mysql
  }),

  // Session configuration
  session: {
    expiresIn: 60 * 15, // 15 minutes
    updateAge: 60 * 5, // Update every 5 minutes
    cookieCache: {
      enabled: true,
      maxAge: 5 * 60, // 5 minutes
    },
  },

  // Advanced options
  advanced: {
    cookiePrefix: "eurabay",
    crossSubDomainCookies: {
      enabled: false,
    },
  },
});
```

### US-002: Create Database Schema for Users

**Description:** As a system, I need database tables to store user accounts and sessions.

**Acceptance Criteria:**
- [ ] Create `user` table with fields: id, email, password_hash, name, role, created_at, updated_at
- [ ] Create `session` table with fields: id, user_id, expires_at, token, created_at
- [ ] Create `account` table for OAuth providers (future-proofing)
- [ ] Add unique index on email field
- [ ] Add indexes on user_id for session table
- [ ] Create migration file with schema changes
- [ ] Run migration successfully
- [ ] Typecheck passes

**Priority:** 1

**Technical Implementation:**

```sql
-- Migration file
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  role TEXT DEFAULT 'user',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sessions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  expires_at TIMESTAMP NOT NULL,
  token TEXT UNIQUE NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX sessions_user_id_idx ON sessions(user_id);
CREATE INDEX sessions_token_idx ON sessions(token);
```

### US-003: Create Login Page

**Description:** As a user, I need a login page to authenticate.

**Acceptance Criteria:**
- [ ] Create `src/app/login/page.tsx` login page
- [ ] Create login form with email and password fields
- [ ] Add form validation (email format, password min length)
- [ ] Add "Remember me" checkbox
- [ ] Add "Forgot password" link
- [ ] Add "Don't have an account? Sign up" link
- [ ] Show loading state during authentication
- [ ] Show error messages for failed login
- [ ] Redirect to dashboard on successful login
- [ ] Redirect to login if already authenticated
- [ ] Typecheck passes
- [ ] Verify in browser that login works

**Priority:** 2

**Technical Implementation:**

```typescript
// src/app/login/page.tsx
"use client";

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const formData = new FormData(e.currentTarget);
    const email = formData.get('email') as string;
    const password = formData.get('password') as string;

    try {
      await auth.api.signInEmail({ email, password });
      router.push('/dashboard');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Login form UI */}
    </form>
  );
}
```

### US-004: Create Register Page

**Description:** As a new user, I need a registration page to create an account.

**Acceptance Criteria:**
- [ ] Create `src/app/register/page.tsx` registration page
- [ ] Create registration form with name, email, password, confirm password fields
- [ ] Add form validation (email format, password matching, password strength)
- [ ] Add password strength indicator
- [ ] Add terms of service checkbox
- [ ] Show loading state during registration
- [ ] Show error messages for failed registration
- [ ] Show success message and redirect to login
- [ ] Redirect to dashboard if already authenticated
- [ ] Typecheck passes
- [ ] Verify in browser that registration works

**Priority:** 2

**Technical Implementation:**

```typescript
// src/app/register/page.tsx
"use client";

export default function RegisterPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    const formData = new FormData(e.currentTarget);
    const name = formData.get('name') as string;
    const email = formData.get('email') as string;
    const password = formData.get('password') as string;

    try {
      await auth.api.signUpEmail({ email, password, name });
      router.push('/login?registered=true');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Registration form UI */}
    </form>
  );
}
```

### US-005: Implement Auth Guard Middleware

**Description:** As a system, I need to protect authenticated routes.

**Acceptance Criteria:**
- [ ] Create `src/middleware.ts` for route protection
- [ ] Protect `/dashboard` route and all sub-routes
- [ ] Protect `/config` route
- [ ] Redirect unauthenticated users to `/login`
- [ ] Allow public access to `/login`, `/register`, `/api/auth/*`
- [ ] Add auth state check for protected routes
- [ ] Add session validation on each request
- [ ] Typecheck passes

**Priority:** 3

**Technical Implementation:**

```typescript
// src/middleware.ts
import { authMiddleware } from "better-auth/api";
import { NextResponse } from "next/server";

export default authMiddleware({
  // Define which routes require authentication
  authenticatedRoutes: ["/dashboard", "/config"],

  // Define routes that should always redirect to dashboard if authenticated
  redirectIfAuthenticated: ["/login", "/register"],

  // Login route to redirect to if not authenticated
  loginRoute: "/login",

  // API routes that should be handled differently
  apiRoutes: ["/api/auth"],
});

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
```

### US-006: Create Auth Context Provider

**Description:** As a developer, I need a React context to manage auth state.

**Acceptance Criteria:**
- [ ] Create `src/contexts/AuthContext.tsx` with auth provider
- [ ] Provide user object to all components
- [ ] Provide loading state for auth checks
- [ ] Provide login/logout functions
- [ ] Provide session refresh function
- [ ] Update auth state on session changes
- [ ] Handle session expiration gracefully
- [ ] Add TypeScript types for auth context
- [ ] Typecheck passes

**Priority:** 3

**Technical Implementation:**

```typescript
// src/contexts/AuthContext.tsx
"use client";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshSession: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const session = await auth.api.getSession();
      setUser(session.user);
    } catch (error) {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshSession }}>
      {children}
    </AuthContext.Provider>
  );
}
```

### US-007: Add User Menu to Header

**Description:** As a user, I need a menu to access my account and logout.

**Acceptance Criteria:**
- [ ] Add user avatar/name to header when authenticated
- [ ] Create dropdown menu with user options
- [ ] Add "Profile" menu item
- [ ] Add "Settings" menu item
- [ ] Add "Logout" menu item
- [ ] Show loading state while checking auth
- [ ] Redirect to login if not authenticated
- [ ] Typecheck passes
- [ ] Verify in browser that user menu works

**Priority:** 4

**Technical Implementation:**

```typescript
// src/components/dashboard/UserMenu.tsx
export function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);

  if (!user) return null;

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger>
        <Avatar>
          <AvatarImage src={user.avatar} />
          <AvatarFallback>{user.name[0]}</AvatarFallback>
        </Avatar>
      </DropdownMenuTrigger>
      <DropdownMenuContent>
        <DropdownMenuItem>Profile</DropdownMenuItem>
        <DropdownMenuItem>Settings</DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={logout}>Logout</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
```

### US-008: Implement Role-Based Access Control

**Description:** As an admin, I need to restrict certain features based on user roles.

**Acceptance Criteria:**
- [ ] Define user roles: admin, trader, viewer
- [ ] Add role field to user schema
- [ ] Create `usePermissions` hook to check user permissions
- [ ] Restrict system controls to admin role only
- [ ] Restrict trading operations to trader role and above
- [ ] Allow all roles to view dashboard
- [ ] Show permission denied message for restricted actions
- [ ] Add permission check API endpoint
- [ ] Typecheck passes

**Priority:** 5

**Technical Implementation:**

```typescript
// src/lib/permissions.ts
export enum Role {
  ADMIN = 'admin',
  TRADER = 'trader',
  VIEWER = 'viewer',
}

export const permissions = {
  [Role.ADMIN]: ['*'], // All permissions
  [Role.TRADER]: [
    'view:dashboard',
    'view:trades',
    'view:analytics',
    'control:trading',
  ],
  [Role.VIEWER]: [
    'view:dashboard',
    'view:trades',
    'view:analytics',
  ],
};

export function hasPermission(userRole: Role, permission: string): boolean {
  const userPermissions = permissions[userRole] || [];
  return userPermissions.includes('*') || userPermissions.includes(permission);
}

// src/hooks/usePermissions.ts
export function usePermissions() {
  const { user } = useAuth();

  return {
    can: (permission: string) => {
      if (!user) return false;
      return hasPermission(user.role as Role, permission);
    },
    isAdmin: user?.role === Role.ADMIN,
    isTrader: user?.role === Role.TRADER || user?.role === Role.ADMIN,
    isViewer: user?.role === Role.VIEWER,
  };
}
```

### US-009: Implement Password Reset Flow

**Description:** As a user, I need to reset my password if I forget it.

**Acceptance Criteria:**
- [ ] Create `/forgot-password` page with email input
- [ ] Send password reset email with token
- [ ] Create `/reset-password` page with token and new password fields
- [ ] Validate reset token (expires after 1 hour)
- [ ] Update password in database
- [ ] Invalidate all existing sessions after password reset
- [ ] Show success/error messages
- [ ] Redirect to login after successful reset
- [ ] Typecheck passes
- [ ] Verify in browser that password reset works

**Priority:** 6

**Technical Implementation:**

```typescript
// src/app/forgot-password/page.tsx
export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const email = new FormData(e.currentTarget).get('email') as string;
    await auth.api.forgetPassword({ email });
    setSent(true);
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Forgot password form */}
    </form>
  );
}

// src/app/reset-password/page.tsx
export default function ResetPasswordPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const password = new FormData(e.currentTarget).get('password') as string;
    await auth.api.resetPassword({ token, password });
    router.push('/login?reset=true');
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Reset password form */}
    </form>
  );
}
```

### US-010: Add User Profile Management

**Description:** As a user, I need to update my profile information.

**Acceptance Criteria:**
- [ ] Create `/profile` page
- [ ] Show current user information (name, email)
- [ ] Allow updating name and email
- [ ] Allow changing password
- [ ] Add profile picture upload (optional)
- [ ] Show save/cancel buttons
- [ ] Validate all inputs
- [ ] Show loading state during update
- [ ] Show success/error messages
- [ ] Typecheck passes
- [ ] Verify in browser that profile updates work

**Priority:** 7

**Technical Implementation:**

```typescript
// src/app/profile/page.tsx
"use client";

export default function ProfilePage() {
  const { user, refreshSession } = useAuth();
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setSuccess(false);

    const formData = new FormData(e.currentTarget);
    try {
      await auth.api.updateUser({
        name: formData.get('name') as string,
        email: formData.get('email') as string,
      });
      await refreshSession();
      setSuccess(true);
    } catch (error) {
      // Handle error
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Profile update form */}
    </form>
  );
}
```

## Functional Requirements

- FR-1: Users must authenticate with email and password
- FR-2: Passwords must be hashed using bcrypt (minimum 10 rounds)
- FR-3: Access tokens must expire after 15 minutes
- FR-4: Refresh tokens must expire after 7 days
- FR-5: Sessions must be refreshable without re-authentication
- FR-6: Users must be able to logout and invalidate their session
- FR-7: All protected routes must redirect to login if not authenticated
- FR-8: Password reset tokens must expire after 1 hour
- FR-9: Users must have one of three roles: admin, trader, viewer
- FR-10: Admin users have full system access
- FR-11: Trader users can view and control trading
- FR-12: Viewer users can only view data

## Non-Goals

- No OAuth/social login in this phase (Google, GitHub, etc.)
- No two-factor authentication (2FA)
- No passwordless authentication (magic links)
- No multi-factor authentication (MFA)
- No SAML/SSO integration
- No user invitation system
- No audit log for auth events

## Technical Considerations

### Dependencies
- `better-auth` v1.3.10 - already installed
- `bcrypt` v6.0.0 - for password hashing
- Database: Drizzle ORM with libSQL (already configured)

### Security Considerations
- All passwords must be hashed with bcrypt
- All auth cookies must be httpOnly and secure
- All auth requests must use HTTPS in production
- CSRF tokens must be validated on state-changing operations
- Rate limiting must prevent brute force attacks
- Session tokens must be stored securely

### Session Management
- Access token lifetime: 15 minutes
- Refresh token lifetime: 7 days
- Session refresh window: 5 minutes
- Max concurrent sessions per user: 5
- Session invalidation on password change
- Session invalidation on logout

### Database Schema
```sql
users table:
- id: TEXT PRIMARY KEY
- email: TEXT UNIQUE NOT NULL
- password_hash: TEXT NOT NULL
- name: TEXT NOT NULL
- role: TEXT DEFAULT 'viewer'
- created_at: TIMESTAMP
- updated_at: TIMESTAMP

sessions table:
- id: TEXT PRIMARY KEY
- user_id: TEXT REFERENCES users(id)
- token: TEXT UNIQUE NOT NULL
- expires_at: TIMESTAMP NOT NULL
- created_at: TIMESTAMP
```

### Password Requirements
- Minimum length: 8 characters
- Maximum length: 128 characters
- Must contain at least one letter
- Must contain at least one number
- Optional: Special character requirement

## Success Metrics

- Authentication success rate > 95%
- Average login time < 2 seconds
- Zero unauthorized access to protected routes
- Zero password leaks (no plaintext storage)
- Session refresh success rate > 99%
- Password reset completion rate > 80%
- Profile update success rate > 95%

## Implementation Order

1. US-001: Configure Better Auth
2. US-002: Create Database Schema for Users
3. US-005: Implement Auth Guard Middleware
4. US-006: Create Auth Context Provider
5. US-003: Create Login Page
6. US-004: Create Register Page
7. US-007: Add User Menu to Header
8. US-008: Implement Role-Based Access Control
9. US-009: Implement Password Reset Flow
10. US-010: Add User Profile Management

## Testing Strategy

### Unit Tests
- Test password hashing/validation
- Test token generation/validation
- Test session refresh logic
- Test permission checking logic

### Integration Tests
- Test complete login flow
- Test registration flow
- Test password reset flow
- Test protected route redirects
- Test role-based access control

### Manual Testing
- Test login with valid credentials
- Test login with invalid credentials
- Test registration flow
- Test logout and session invalidation
- Test password reset flow
- Test profile updates
- Test role-based permissions

### Security Testing
- Test SQL injection prevention
- Test XSS prevention
- Test CSRF token validation
- Test session hijacking prevention
- Test brute force prevention

## Known Issues & Risks

- Better Auth is in beta (v1.3.10) - may have breaking changes
- libSQL database support for auth may be limited
- Email delivery for password reset requires backend service
- Session management complexity with multiple tabs/devices
- CSRF protection requires careful implementation

## Related PRDs

- PRD: Backend API Integration (protected endpoints)
- PRD: WebSocket Integration (authenticated connections)
- PRD: System Control Features (admin-only operations)
- PRD: Trading System Features (trader permissions)
