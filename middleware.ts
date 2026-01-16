import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';

/**
 * Rate limiter for auth endpoints
 * Simple in-memory rate limiting (10 requests per minute per IP)
 */
class RateLimiter {
  private requests: Map<string, number[]> = new Map();
  private readonly maxRequests: number;
  private readonly windowMs: number;

  constructor(maxRequests: number = 10, windowMs: number = 60000) {
    this.maxRequests = maxRequests;
    this.windowMs = windowMs;

    // Clean up old entries every minute
    setInterval(() => this.cleanup(), 60000);
  }

  private cleanup(): void {
    const now = Date.now();
    for (const [ip, timestamps] of this.requests.entries()) {
      const validTimestamps = timestamps.filter(t => now - t < this.windowMs);
      if (validTimestamps.length === 0) {
        this.requests.delete(ip);
      } else {
        this.requests.set(ip, validTimestamps);
      }
    }
  }

  check(ip: string): boolean {
    const now = Date.now();
    const timestamps = this.requests.get(ip) || [];

    // Remove timestamps outside the window
    const validTimestamps = timestamps.filter(t => now - t < this.windowMs);

    if (validTimestamps.length >= this.maxRequests) {
      return false;
    }

    validTimestamps.push(now);
    this.requests.set(ip, validTimestamps);
    return true;
  }
}

// Create rate limiter instance: 10 requests per minute
const rateLimiter = new RateLimiter(10, 60000);

/**
 * Get client IP address from request headers
 */
function getClientIp(request: Request): string {
  // Check various headers for the real IP
  const forwardedFor = request.headers.get('x-forwarded-for');
  if (forwardedFor) {
    return forwardedFor.split(',')[0].trim();
  }

  const realIp = request.headers.get('x-real-ip');
  if (realIp) {
    return realIp;
  }

  const cfConnectingIp = request.headers.get('cf-connecting-ip');
  if (cfConnectingIp) {
    return cfConnectingIp;
  }

  // Fallback to a default IP (not ideal but necessary)
  return 'unknown';
}

/**
 * Check if the origin is allowed based on environment variable
 */
function isOriginAllowed(origin: string | null): boolean {
  const allowedOriginsEnv = process.env.CORS_ALLOWED_ORIGINS;

  // If no env var is set, allow all origins (development friendly)
  if (!allowedOriginsEnv || allowedOriginsEnv === '*') {
    return true;
  }

  if (!origin) {
    return true;
  }

  const allowedOrigins = allowedOriginsEnv.split(',').map(o => o.trim());
  return allowedOrigins.some(allowed => {
    // Support wildcards
    if (allowed === '*') return true;
    if (allowed.endsWith('*')) {
      const prefix = allowed.slice(0, -1);
      return origin.startsWith(prefix);
    }
    return origin === allowed;
  });
}

/**
 * Helper function to check if a path is public
 */
function isPublicPath(pathname: string): boolean {
  const publicPaths = [
    '/login',
    '/register',
    '/forgot-password',
    '/reset-password',
    '/api/auth',
    '/_next',
    '/favicon.ico',
    '/icon.png',
  ];

  return publicPaths.some(path => pathname.startsWith(path));
}

/**
 * Better Auth middleware for Next.js
 *
 * Features:
 * - Protects routes and handles authentication
 * - Rate limiting for auth endpoints (10 requests per minute)
 * - CORS configuration from environment variables
 * - Redirects unauthenticated users to /login
 * - Redirects authenticated users away from /login to /dashboard
 */
export async function middleware(request: NextRequest) {
  const url = request.nextUrl.clone();
  const origin = request.headers.get('origin');
  const ip = getClientIp(request);

  // Handle OPTIONS request for CORS preflight
  if (request.method === 'OPTIONS') {
    return new NextResponse(null, {
      status: 200,
      headers: {
        'Access-Control-Allow-Origin': origin || '*',
        'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        'Access-Control-Max-Age': '86400',
      },
    });
  }

  // CORS check for API routes
  if (url.pathname.startsWith('/api/')) {
    if (!isOriginAllowed(origin)) {
      return new NextResponse('Forbidden', {
        status: 403,
        headers: {
          'Access-Control-Allow-Origin': origin || '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        },
      });
    }

    // Rate limiting for auth endpoints
    if (url.pathname.startsWith('/api/auth/')) {
      if (!rateLimiter.check(ip)) {
        return new NextResponse(
          JSON.stringify({
            error: 'Too many requests',
            message: 'Rate limit exceeded. Please try again later.',
          }),
          {
            status: 429,
            headers: {
              'Content-Type': 'application/json',
              'Retry-After': '60',
              'Access-Control-Allow-Origin': origin || '*',
              'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
              'Access-Control-Allow-Headers': 'Content-Type, Authorization',
            },
          }
        );
      }
    }
  }

  // For auth API endpoints, forward to Better Auth handler
  if (url.pathname.startsWith('/api/auth/')) {
    // Create a new Request with the original URL
    const authUrl = new URL(request.url);
    const authRequest = new Request(authUrl.toString(), {
      method: request.method,
      headers: request.headers,
      body: request.body,
      // @ts-expect-error - duplex is required for Node 18+
      duplex: 'half',
    });

    try {
      // Better Auth handler will process the request
      const response = await auth.handler(authRequest);

      // Add CORS headers to response
      const newResponse = new NextResponse(response.body, {
        status: response.status,
        headers: {
          ...Object.fromEntries(response.headers.entries()),
          'Access-Control-Allow-Origin': origin || '*',
          'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
          'Access-Control-Allow-Headers': 'Content-Type, Authorization',
        },
      });

      return newResponse;
    } catch (error) {
      console.error('Auth handler error:', error);
      return new NextResponse(
        JSON.stringify({ error: 'Authentication error' }),
        {
          status: 500,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }
  }

  // Check if user is authenticated by trying to get session
  let session = null;
  let isAuthenticated = false;

  // Only check session for non-public paths
  if (!isPublicPath(url.pathname)) {
    try {
      // Create a request to Better Auth to get session
      const sessionUrl = new URL('/api/auth/get-session', request.url);
      const sessionRequest = new Request(sessionUrl.toString(), {
        headers: request.headers,
      });

      const sessionResponse = await auth.handler(sessionRequest);

      if (sessionResponse.ok) {
        const sessionData = await sessionResponse.json();
        session = sessionData;
        isAuthenticated = !!session?.user;
      }
    } catch (error) {
      // If session check fails, assume not authenticated
      isAuthenticated = false;
    }
  }

  // Redirect authenticated users away from login/register to dashboard
  if (isAuthenticated && (url.pathname === '/login' || url.pathname === '/register')) {
    url.pathname = '/dashboard';
    return NextResponse.redirect(url);
  }

  // Redirect unauthenticated users trying to access protected routes
  if (!isAuthenticated && !isPublicPath(url.pathname)) {
    url.pathname = '/login';
    url.searchParams.set('redirect', request.nextUrl.pathname);
    return NextResponse.redirect(url);
  }

  // Continue with the request
  const response = NextResponse.next();

  // Add CORS headers to API responses
  if (url.pathname.startsWith('/api/')) {
    response.headers.set('Access-Control-Allow-Origin', origin || '*');
    response.headers.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    response.headers.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');
  }

  return response;
}

/**
 * Configure which paths the middleware should run on
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public files (images, etc.)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)',
  ],
};
