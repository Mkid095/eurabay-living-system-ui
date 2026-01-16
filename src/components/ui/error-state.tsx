import { Button } from "@/components/ui/button"
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert"
import { cn } from "@/lib/utils"
import { AlertCircle, RefreshCw, WifiOff, ServerCrash, Bug } from "lucide-react"
import * as React from "react"

/**
 * Error type categories for appropriate icon and message display
 */
export type ErrorCategory = "network" | "server" | "client" | "timeout" | "unknown"

/**
 * Props for the ErrorState component
 */
export interface ErrorStateProps {
  /** The error that occurred */
  error: Error | { message: string } | string | null
  /** Optional callback when retry is clicked */
  onRetry?: () => void | Promise<void>
  /** Optional custom fallback UI to display instead of default error UI */
  fallback?: React.ReactNode
  /** Optional custom className for the container */
  className?: string
  /** Optional title to override default */
  title?: string
  /** Optional custom retry button text */
  retryButtonText?: string
  /** Whether to hide the troubleshooting tips */
  hideTroubleshooting?: boolean
  /** Whether the retry action is loading */
  isRetrying?: boolean
  /** Optional error category for appropriate icon display */
  category?: ErrorCategory
}

/**
 * Determines the error category from the error object
 */
function getErrorCategory(error: Error | { message: string } | string | null): ErrorCategory {
  if (!error) return "unknown"

  const message = typeof error === "string" ? error : error.message?.toLowerCase() || ""

  if (message.includes("network") || message.includes("fetch") || message.includes("connection")) {
    return "network"
  }
  if (message.includes("timeout") || message.includes("timed out")) {
    return "timeout"
  }
  if (message.includes("500") || message.includes("502") || message.includes("503")) {
    return "server"
  }
  if (message.includes("400") || message.includes("401") || message.includes("403") || message.includes("404")) {
    return "client"
  }
  return "unknown"
}

/**
 * Gets the appropriate icon for the error category
 */
function getErrorIcon(category: ErrorCategory) {
  switch (category) {
    case "network":
      return WifiOff
    case "server":
      return ServerCrash
    case "timeout":
      return RefreshCw
    case "client":
      return AlertCircle
    default:
      return Bug
  }
}

/**
 * Gets the default title for the error category
 */
function getDefaultTitle(category: ErrorCategory): string {
  switch (category) {
    case "network":
      return "Network Error"
    case "server":
      return "Server Error"
    case "timeout":
      return "Request Timeout"
    case "client":
      return "Request Error"
    default:
      return "Something Went Wrong"
  }
}

/**
 * Gets troubleshooting tips based on error category
 */
function getTroubleshootingTips(category: ErrorCategory): string[] {
  switch (category) {
    case "network":
      return [
        "Check your internet connection",
        "Verify the API server is accessible",
        "Try refreshing the page",
      ]
    case "server":
      return [
        "The server is experiencing issues",
        "Please try again in a few moments",
        "Contact support if the problem persists",
      ]
    case "timeout":
      return [
        "The request took too long to complete",
        "Check your network connection speed",
        "Try again with a more specific query",
      ]
    case "client":
      return [
        "There was an issue with the request",
        "You may need to refresh your session",
        "Contact support if this continues",
      ]
    default:
      return [
        "An unexpected error occurred",
        "Try refreshing the page",
        "Contact support if the problem persists",
      ]
  }
}

/**
 * ErrorState component - Displays error information with optional retry action
 *
 * This component provides a consistent error display across the application
 * with contextual icons, messages, and troubleshooting tips.
 *
 * @example
 * ```tsx
 * <ErrorState
 *   error={new Error("Failed to fetch data")}
 *   onRetry={() => refetch()}
 * />
 * ```
 *
 * @example
 * ```tsx
 * <ErrorState
 *   error={error}
 *   onRetry={handleRetry}
 *   title="Custom Error Title"
 *   retryButtonText="Try Again"
 *   isRetrying={isPending}
 * />
 * ```
 */
export function ErrorState({
  error,
  onRetry,
  fallback,
  className,
  title,
  retryButtonText = "Try Again",
  hideTroubleshooting = false,
  isRetrying = false,
  category,
}: ErrorStateProps) {
  // If custom fallback is provided, render it
  if (fallback) {
    return <>{fallback}</>
  }

  // Extract error message
  const errorMessage = React.useMemo(() => {
    if (!error) return "An unknown error occurred"
    if (typeof error === "string") return error
    return error.message || "An unknown error occurred"
  }, [error])

  // Determine error category
  const errorCategory = category ?? getErrorCategory(error)

  // Get appropriate icon, title, and tips
  const ErrorIcon = getErrorIcon(errorCategory)
  const defaultTitle = getDefaultTitle(errorCategory)
  const displayTitle = title ?? defaultTitle
  const troubleshootingTips = getTroubleshootingTips(errorCategory)

  return (
    <div className={cn("flex flex-col items-center justify-center p-8", className)}>
      <Alert variant="destructive" className="max-w-lg">
        <ErrorIcon className="h-4 w-4" />
        <AlertTitle className="flex items-center gap-2">
          {displayTitle}
        </AlertTitle>
        <AlertDescription className="mt-2">
          {errorMessage}
        </AlertDescription>
      </Alert>

      {/* Retry button */}
      {onRetry && (
        <Button
          onClick={onRetry}
          variant="outline"
          className="mt-4 gap-2"
          disabled={isRetrying}
        >
          <RefreshCw className={cn("h-4 w-4", isRetrying && "animate-spin")} />
          {isRetrying ? "Retrying..." : retryButtonText}
        </Button>
      )}

      {/* Troubleshooting tips */}
      {!hideTroubleshooting && (
        <div className="mt-6 max-w-lg">
          <p className="text-sm font-medium text-muted-foreground mb-2">
            Troubleshooting tips:
          </p>
          <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
            {troubleshootingTips.map((tip, index) => (
              <li key={index}>{tip}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

/**
 * CompactErrorState - A smaller inline error state for cards and tables
 *
 * @example
 * ```tsx
 * <CompactErrorState error={error} onRetry={refetch} />
 * ```
 */
export interface CompactErrorStateProps {
  error: Error | { message: string } | string | null
  onRetry?: () => void | Promise<void>
  className?: string
  isRetrying?: boolean
}

export function CompactErrorState({
  error,
  onRetry,
  className,
  isRetrying = false,
}: CompactErrorStateProps) {
  const errorMessage = React.useMemo(() => {
    if (!error) return "An error occurred"
    if (typeof error === "string") return error
    return error.message || "An error occurred"
  }, [error])

  return (
    <div className={cn("flex flex-col items-center justify-center p-4 text-center", className)}>
      <AlertCircle className="h-8 w-8 text-destructive mb-2" />
      <p className="text-sm text-muted-foreground mb-2">{errorMessage}</p>
      {onRetry && (
        <Button
          onClick={onRetry}
          variant="ghost"
          size="sm"
          className="gap-1"
          disabled={isRetrying}
        >
          <RefreshCw className={cn("h-3 w-3", isRetrying && "animate-spin")} />
          Retry
        </Button>
      )}
    </div>
  )
}

/**
 * InlineErrorState - Minimal inline error for cards and small containers
 *
 * @example
 * ```tsx
 * <InlineErrorState error="Failed to load" />
 * ```
 */
export interface InlineErrorStateProps {
  error: Error | { message: string } | string | null
  className?: string
}

export function InlineErrorState({
  error,
  className,
}: InlineErrorStateProps) {
  const errorMessage = React.useMemo(() => {
    if (!error) return "Error"
    if (typeof error === "string") return error
    return error.message || "Error"
  }, [error])

  return (
    <div className={cn(
      "flex items-center gap-2 text-destructive text-sm p-2",
      className
    )}>
      <AlertCircle className="h-4 w-4 flex-shrink-0" />
      <span className="truncate">{errorMessage}</span>
    </div>
  )
}
