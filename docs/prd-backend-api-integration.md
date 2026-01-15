# PRD: Backend API Integration

## Overview

The EURABAY Living System v5.0 frontend currently uses mock data in all hooks. This PRD defines the complete implementation of actual HTTP API integration to connect the frontend with the Python backend, replacing all mock data with real API calls.

## Goals

- Replace all mock data with real API calls to Python backend
- Implement type-safe API client with proper error handling
- Add loading states, error states, and retry logic
- Ensure all components receive real-time data from backend
- Implement proper authentication flow
- Add request/response caching where appropriate
- Handle connection failures gracefully with fallback to cached data

## Current State

**Problem:**
- `useDashboardData.ts` returns hardcoded mock data
- `useEvolutionData.ts` returns hardcoded mock data
- No API client implementation exists
- No environment variables configured
- No error handling for API failures
- No loading states in components
- No authentication implementation

**Impact:**
- Dashboard shows fake data that doesn't reflect actual trading activity
- Cannot monitor real system performance
- Evolution metrics are not connected to actual evolution engine
- System appears functional but is completely disconnected

## User Stories

### US-001: Create API Client Foundation

**Description:** As a developer, I need a type-safe API client to make HTTP requests to the backend.

**Acceptance Criteria:**
- [ ] Create `src/lib/api.ts` with base API client configuration
- [ ] Implement `apiClient` class with methods: `get()`, `post()`, `put()`, `delete()`
- [ ] Add base URL configuration from `NEXT_PUBLIC_API_URL` env var
- [ ] Implement request interceptors for adding auth headers
- [ ] Implement response interceptors for error handling
- [ ] Add request timeout (default 30s)
- [ ] Add retry logic for failed requests (3 retries with exponential backoff)
- [ ] Create TypeScript interfaces for all API request/response types
- [ ] Add Zod schemas for runtime validation of API responses
- [ ] Typecheck passes

**Priority:** 1

**Technical Implementation:**

```typescript
// src/lib/api.ts
class APIClient {
  private baseURL: string;
  private defaultTimeout: number = 30000;

  async get<T>(endpoint: string, params?: Record<string, any>): Promise<T>
  async post<T>(endpoint: string, body?: any): Promise<T>
  async put<T>(endpoint: string, body?: any): Promise<T>
  async delete<T>(endpoint: string): Promise<T>
}
```

### US-002: Add Environment Variables Configuration

**Description:** As a developer, I need environment variables to configure API connections.

**Acceptance Criteria:**
- [ ] Create `.env.local.example` with all required env vars
- [ ] Add `NEXT_PUBLIC_API_URL` variable
- [ ] Add `NEXT_PUBLIC_WS_URL` variable
- [ ] Add `NEXT_PUBLIC_API_TIMEOUT` variable
- [ ] Update `README.md` with environment setup instructions
- [ ] Add validation at app startup to verify required env vars
- [ ] Typecheck passes

**Priority:** 1

**Technical Implementation:**

```bash
# .env.local.example
NEXT_PUBLIC_API_URL=http://localhost:8000/api
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_API_TIMEOUT=30000
```

### US-003: Create API Endpoint Modules

**Description:** As a developer, I need organized API endpoint modules for each feature area.

**Acceptance Criteria:**
- [ ] Create `src/lib/api/endpoints/system.ts` for system status endpoints
- [ ] Create `src/lib/api/endpoints/evolution.ts` for evolution endpoints
- [ ] Create `src/lib/api/endpoints/trades.ts` for trading endpoints
- [ ] Create `src/lib/api/endpoints/portfolio.ts` for portfolio endpoints
- [ ] Create `src/lib/api/endpoints/markets.ts` for market data endpoints
- [ ] Create `src/lib/api/endpoints/config.ts` for configuration endpoints
- [ ] Export all endpoints from `src/lib/api/endpoints/index.ts`
- [ ] Each endpoint function has full TypeScript types
- [ ] Each endpoint function includes JSDoc comments
- [ ] Typecheck passes

**Priority:** 2

**Technical Implementation:**

```typescript
// src/lib/api/endpoints/system.ts
export const systemEndpoints = {
  getStatus: () => apiClient.get<SystemStatus>('/system/status'),
  getHealth: () => apiClient.get<SystemHealth>('/system/health'),
  start: () => apiClient.post<{success: boolean}>('/system/start'),
  stop: () => apiClient.post<{success: boolean}>('/system/stop'),
};

// Similar structure for other endpoint modules
```

### US-004: Replace useDashboardData Mock Data

**Description:** As a user, I need to see real trading data instead of mock data.

**Acceptance Criteria:**
- [ ] Update `useDashboardData.ts` to call real API endpoints
- [ ] Add `loading` state to hook
- [ ] Add `error` state to hook with error message
- [ ] Implement `refetch()` function for manual refresh
- [ ] Add automatic polling every 3 seconds when data is stale
- [ ] Handle API errors gracefully with fallback to last known good data
- [ ] Add retry logic with exponential backoff
- [ ] Update all components using this hook to handle loading/error states
- [ ] Add unit tests for hook with mocked API calls
- [ ] Typecheck passes
- [ ] Verify in browser that real data displays

**Priority:** 3

**Technical Implementation:**

```typescript
// src/hooks/useDashboardData.ts
export function useDashboardData() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [portfolio, trades, metrics] = await Promise.all([
          systemEndpoints.getPortfolioMetrics(),
          tradesEndpoints.getActiveTrades(),
          performanceEndpoints.getMetrics(),
        ]);
        setData({ portfolio, trades, metrics });
        setError(null);
      } catch (err) {
        setError(err as Error);
        // Keep last known good data
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 3000);
    return () => clearInterval(interval);
  }, []);

  return { data, loading, error, refetch: fetchData };
}
```

### US-005: Replace useEvolutionData Mock Data

**Description:** As a user, I need to see real evolution metrics instead of mock data.

**Acceptance Criteria:**
- [ ] Update `useEvolutionData.ts` to call real API endpoints
- [ ] Add `loading` state to hook
- [ ] Add `error` state to hook with error message
- [ ] Implement `refetch()` function for manual refresh
- [ ] Add automatic polling every 5 seconds for evolution data
- [ ] Handle API errors gracefully with fallback to cached data
- [ ] Add retry logic with exponential backoff
- [ ] Update all components using this hook to handle loading/error states
- [ ] Add unit tests for hook with mocked API calls
- [ ] Typecheck passes
- [ ] Verify in browser that real evolution data displays

**Priority:** 3

**Technical Implementation:**

```typescript
// src/hooks/useEvolutionData.ts
export const useEvolutionData = () => {
  const [evolutionMetrics, setEvolutionMetrics] = useState<EvolutionMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [metrics, history, features, mutations] = await Promise.all([
          evolutionEndpoints.getMetrics(),
          evolutionEndpoints.getGenerationHistory(),
          evolutionEndpoints.getFeatureSuccess(),
          evolutionEndpoints.getMutationSuccess(),
        ]);
        setEvolutionMetrics(metrics);
        // ... set other state
        setError(null);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, []);

  return { evolutionMetrics, loading, error, refetch: fetchData };
};
```

### US-006: Add Loading States to All Components

**Description:** As a user, I need visual feedback when data is loading.

**Acceptance Criteria:**
- [ ] Create `src/components/ui/loading-skeleton.tsx` component
- [ ] Add skeleton screens for all dashboard cards
- [ ] Add skeleton screens for all tables
- [ ] Add skeleton screens for all charts
- [ ] Add loading spinner component for inline loading
- [ ] Update `EnhancedActiveTradesTable` to show skeleton when loading
- [ ] Update `EvolutionMetrics` to show skeleton when loading
- [ ] Update `PerformanceMetrics` to show skeleton when loading
- [ ] Update all chart components to show skeleton when loading
- [ ] Typecheck passes
- [ ] Verify in browser that loading states display smoothly

**Priority:** 4

**Technical Implementation:**

```typescript
// src/components/ui/loading-skeleton.tsx
export function DataTableSkeleton({ rowCount = 5 }: { rowCount?: number }) {
  return (
    <div className="space-y-3">
      {Array.from({ length: rowCount }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}

// Usage in components
{loading ? (
  <DataTableSkeleton rowCount={10} />
) : (
  <EnhancedActiveTradesTable trades={trades} />
)}
```

### US-007: Add Error States to All Components

**Description:** As a user, I need to see helpful error messages when API calls fail.

**Acceptance Criteria:**
- [ ] Create `src/components/ui/error-state.tsx` component
- [ ] Error state displays error message
- [ ] Error state includes retry button
- [ ] Error state includes helpful troubleshooting steps
- [ ] Update all data-fetching components to show error state
- [ ] Add toast notifications for transient errors
- [ ] Add fallback UI for non-critical data failures
- [ ] Log all errors to console with full context
- [ ] Typecheck passes
- [ ] Verify in browser that error states display correctly

**Priority:** 4

**Technical Implementation:**

```typescript
// src/components/ui/error-state.tsx
interface ErrorStateProps {
  error: Error;
  retry?: () => void;
  fallback?: React.ReactNode;
}

export function ErrorState({ error, retry, fallback }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8">
      <AlertCircle className="h-12 w-12 text-destructive mb-4" />
      <h3 className="text-lg font-semibold mb-2">Failed to load data</h3>
      <p className="text-sm text-muted-foreground mb-4">{error.message}</p>
      {retry && (
        <Button onClick={retry} variant="outline">
          <RefreshCw className="mr-2 h-4 w-4" />
          Retry
        </Button>
      )}
    </div>
  );
}
```

### US-008: Implement Request Caching

**Description:** As a user, I need the dashboard to load quickly by caching frequently accessed data.

**Acceptance Criteria:**
- [ ] Create `src/lib/cache.ts` with in-memory cache implementation
- [ ] Implement TTL-based cache expiration (default 5s for real-time data)
- [ ] Cache system status endpoint for 10 seconds
- [ ] Cache configuration endpoint for 60 seconds
- [ ] Cache market overview for 5 seconds
- [ ] Add cache invalidation for mutation endpoints
- [ ] Add cache stats monitoring (hit rate, memory usage)
- [ ] Implement cache warming on app startup
- [ ] Typecheck passes

**Priority:** 5

**Technical Implementation:**

```typescript
// src/lib/cache.ts
class APICache {
  private cache = new Map<string, { data: any; expires: number }>();

  get<T>(key: string): T | null {
    const item = this.cache.get(key);
    if (!item) return null;
    if (Date.now() > item.expires) {
      this.cache.delete(key);
      return null;
    }
    return item.data as T;
  }

  set<T>(key: string, data: T, ttl: number): void {
    this.cache.set(key, {
      data,
      expires: Date.now() + ttl * 1000,
    });
  }

  invalidate(pattern: string): void {
    // Delete all keys matching pattern
  }
}

export const apiCache = new APICache();
```

### US-009: Add API Response Validation

**Description:** As a developer, I need runtime validation to ensure API responses match expected types.

**Acceptance Criteria:**
- [ ] Create Zod schemas for all API response types in `src/lib/api/schemas.ts`
- [ ] Add schema validation in API client response interceptor
- [ ] Log validation errors with full response details
- [ ] Return safe defaults when validation fails
- [ ] Add schema validation tests
- [ ] Document all schema validation rules
- [ ] Typecheck passes

**Priority:** 5

**Technical Implementation:**

```typescript
// src/lib/api/schemas.ts
import { z } from 'zod';

export const SystemStatusSchema = z.object({
  system_version: z.string(),
  birth_time: z.string(),
  uptime: z.string(),
  cycles_completed: z.number(),
  is_running: z.boolean(),
  mt5_connected: z.boolean(),
  health_status: z.enum(['healthy', 'degraded', 'unhealthy']),
  cpu_usage: z.number(),
  memory_usage: z.number(),
  connection_errors: z.number(),
});

// Similar schemas for all API responses
```

### US-010: Add Request/Response Logging

**Description:** As a developer, I need detailed logging to debug API issues.

**Acceptance Criteria:**
- [ ] Log all API requests with method, URL, and params
- [ ] Log all API responses with status code and data
- [ ] Log all API errors with full error details
- [ ] Add request timing for performance monitoring
- [ ] Add correlation IDs to track request chains
- [ ] Implement log level filtering (error, warn, info, debug)
- [ ] Add option to enable verbose logging in development
- [ ] Sanitize sensitive data (tokens, passwords) from logs
- [ ] Typecheck passes

**Priority:** 6

**Technical Implementation:**

```typescript
// src/lib/api/logger.ts
export class APILogger {
  logRequest(config: RequestConfig): void {
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API] ${config.method} ${config.url}`, {
        params: config.params,
        body: config.body,
        timestamp: Date.now(),
      });
    }
  }

  logResponse(response: any, duration: number): void {
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API] Response in ${duration}ms`, response);
    }
  }

  logError(error: Error, config: RequestConfig): void {
    console.error(`[API] Error`, {
      error: error.message,
      url: config.url,
      method: config.method,
      timestamp: Date.now(),
    });
  }
}
```

## Functional Requirements

- FR-1: All API calls must use the centralized API client
- FR-2: All API requests must include authentication headers when available
- FR-3: All API requests must timeout after 30 seconds by default
- FR-4: Failed requests must be retried up to 3 times with exponential backoff
- FR-5: Real-time data must be refreshed every 3-5 seconds
- FR-6: Configuration data must be cached for 60 seconds
- FR-7: All API responses must be validated against Zod schemas
- FR-8: Loading states must display within 100ms of request initiation
- FR-9: Error states must display user-friendly messages
- FR-10: API calls must be logged in development mode

## Non-Goals

- No offline mode support (system requires active connection)
- No request batching beyond browser's native connection pooling
- No GraphQL support (REST only)
- No file upload/download endpoints in this phase
- No WebSocket implementation in this PRD (see separate PRD)

## Technical Considerations

### Dependencies
- `zod` - Runtime type validation
- Existing fetch API or axios (prefer fetch for Next.js)

### Integration Points
- All existing hooks must be updated
- All components using data hooks must handle loading/error states
- Environment variables must be configured in deployment

### Performance Requirements
- Initial page load must complete in under 2 seconds
- Subsequent data refreshes must complete in under 500ms
- Cache hit rate must be above 80% for configuration data
- Memory usage for cache must not exceed 50MB

### Error Handling Strategy
- Transient errors (network blips): Retry with backoff
- 4xx errors: Show user-friendly error, don't retry
- 5xx errors: Retry up to 3 times, then show error
- Timeout errors: Retry once, then show error
- Parse errors: Log full response, show error to user

### Monitoring
- Track API response times
- Track error rates by endpoint
- Track cache hit rates
- Track retry rates

## Success Metrics

- All mock data removed from hooks
- API integration test coverage > 80%
- Average API response time < 500ms
- Error rate < 1% for successful requests
- Cache hit rate > 80% for config data
- Zero data loss during error states (fallback to cached data)
- Loading states display for all data fetching operations
- Error states display helpful messages for all failure scenarios

## Implementation Order

1. US-001: Create API Client Foundation
2. US-002: Add Environment Variables Configuration
3. US-003: Create API Endpoint Modules
4. US-006: Add Loading States to All Components
5. US-007: Add Error States to All Components
6. US-004: Replace useDashboardData Mock Data
7. US-005: Replace useEvolutionData Mock Data
8. US-008: Implement Request Caching
9. US-009: Add API Response Validation
10. US-010: Add Request/Response Logging

## Testing Strategy

### Unit Tests
- Test API client methods with mocked fetch
- Test retry logic with various error scenarios
- Test cache behavior (get, set, expire)
- Test schema validation with valid/invalid data

### Integration Tests
- Test hooks with mocked API endpoints
- Test error handling throughout the stack
- Test loading state transitions

### Manual Testing
- Verify all components show real data
- Test error states by stopping backend
- Test loading states with slow network
- Verify cache behavior with browser dev tools

## Known Issues & Risks

- Backend API not yet implemented - need to coordinate with backend team
- CORS configuration needed on backend
- Rate limiting may impact polling frequency
- WebSocket integration needed for true real-time updates (separate PRD)
- Authentication implementation needed (separate PRD)

## Related PRDs

- PRD: WebSocket Integration (real-time updates)
- PRD: Authentication & User Management (auth tokens)
- PRD: Trading System Features (trading endpoints)
- PRD: Evolution System Features (evolution endpoints)
