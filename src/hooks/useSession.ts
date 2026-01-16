"use client";

import { useState, useEffect } from "react";
import type { Session } from "@/lib/auth";

interface UseSessionResult {
  data: Session | null;
  isLoading: boolean;
  error: Error | null;
}

/**
 * Hook to get the current session
 *
 * This is a client-side hook that fetches the session from the server.
 * In a production environment, this would use the better-auth client hooks.
 */
export function useSession(): UseSessionResult {
  const [session, setSession] = useState<Session | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchSession = async () => {
      try {
        const response = await fetch("/api/auth/get-session");
        if (response.ok) {
          const data = await response.json();
          setSession(data);
        }
      } catch {
        setError(new Error("Failed to fetch session"));
      } finally {
        setIsLoading(false);
      }
    };

    fetchSession();
  }, []);

  return { data: session, isLoading, error };
}
