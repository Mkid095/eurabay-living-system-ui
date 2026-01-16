import { Skeleton } from "@/components/ui/skeleton"
import { cn } from "@/lib/utils"

/**
 * Skeleton variants for different use cases
 */
export type SkeletonVariant = "default" | "text" | "circular" | "rounded"

/**
 * Enhanced Skeleton component with variant support
 * Extends the base Skeleton component with additional predefined styles
 */
interface EnhancedSkeletonProps extends React.ComponentProps<"div"> {
  variant?: SkeletonVariant
}

export function EnhancedSkeleton({
  variant = "default",
  className,
  ...props
}: EnhancedSkeletonProps) {
  const variantStyles: Record<SkeletonVariant, string> = {
    default: "rounded-md",
    text: "rounded-sm h-4 w-full",
    circular: "rounded-full",
    rounded: "rounded-lg",
  }

  return (
    <Skeleton
      className={cn(variantStyles[variant], className)}
      {...props}
    />
  )
}

/**
 * DataTableSkeleton component for data table loading states
 * Displays a skeleton representation of a data table with header and rows
 */
interface DataTableSkeletonProps {
  /** Number of skeleton rows to display */
  rowCount?: number
  /** Number of columns in the table */
  columnCount?: number
  /** Optional custom className */
  className?: string
}

export function DataTableSkeleton({
  rowCount = 5,
  columnCount = 4,
  className,
}: DataTableSkeletonProps) {
  return (
    <div className={cn("space-y-3", className)}>
      {/* Header row */}
      <div className="flex items-center space-x-4 border-b pb-3">
        {Array.from({ length: columnCount }).map((_, i) => (
          <Skeleton
            key={`header-${i}`}
            className="h-6 flex-1"
          />
        ))}
      </div>
      {/* Data rows */}
      {Array.from({ length: rowCount }).map((_, rowIndex) => (
        <div key={`row-${rowIndex}`} className="flex items-center space-x-4 py-3">
          {Array.from({ length: columnCount }).map((_, colIndex) => (
            <Skeleton
              key={`cell-${rowIndex}-${colIndex}`}
              className="h-5 flex-1"
            />
          ))}
        </div>
      ))}
    </div>
  )
}

/**
 * CardSkeleton component for dashboard card loading states
 * Displays a skeleton representation of a metric card with icon, value, and label
 */
interface CardSkeletonProps {
  /** Optional custom className */
  className?: string
  /** Whether to show icon skeleton */
  showIcon?: boolean
}

export function CardSkeleton({
  className,
  showIcon = true,
}: CardSkeletonProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-6", className)}>
      <div className="flex items-center justify-between space-x-4">
        <div className="space-y-2 flex-1">
          {showIcon && (
            <Skeleton className="h-8 w-8 rounded-lg" />
          )}
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-4 w-24" />
        </div>
        <Skeleton className="h-12 w-12 rounded-full" />
      </div>
    </div>
  )
}

/**
 * ChartSkeleton component for chart placeholder loading states
 * Displays a skeleton representation of a chart with axes and data area
 */
interface ChartSkeletonProps {
  /** Optional custom className */
  className?: string
  /** Height of the chart skeleton */
  height?: string | number
}

export function ChartSkeleton({
  className,
  height = "h-64",
}: ChartSkeletonProps) {
  return (
    <div className={cn("rounded-lg border bg-card p-6", className)}>
      {/* Chart header */}
      <div className="space-y-2 mb-6">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-32" />
      </div>
      {/* Chart area */}
      <div className={cn("relative", height)}>
        {/* Y-axis */}
        <div className="absolute left-0 top-0 bottom-0 w-8 flex flex-col justify-between">
          <Skeleton className="h-3 w-6" />
          <Skeleton className="h-3 w-6" />
          <Skeleton className="h-3 w-6" />
          <Skeleton className="h-3 w-6" />
          <Skeleton className="h-3 w-6" />
        </div>
        {/* Chart content */}
        <div className="ml-10 h-full space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="flex items-end space-x-2 h-full">
              <Skeleton className="h-full flex-1" />
              <Skeleton className="h-3/4 flex-1" />
              <Skeleton className="h-1/2 flex-1" />
              <Skeleton className="h-2/3 flex-1" />
              <Skeleton className="h-4/5 flex-1" />
              <Skeleton className="h-1/2 flex-1" />
              <Skeleton className="h-3/4 flex-1" />
            </div>
          ))}
        </div>
      </div>
      {/* X-axis */}
      <div className="mt-4 flex justify-between">
        {Array.from({ length: 7 }).map((_, i) => (
          <Skeleton key={i} className="h-3 w-12" />
        ))}
      </div>
    </div>
  )
}

/**
 * TableSkeleton component for general table row loading states
 * Displays a simpler skeleton representation for table rows
 */
interface TableSkeletonProps {
  /** Number of skeleton rows to display */
  rowCount?: number
  /** Optional custom className */
  className?: string
}

export function TableSkeleton({
  rowCount = 5,
  className,
}: TableSkeletonProps) {
  return (
    <div className={cn("space-y-3", className)}>
      {Array.from({ length: rowCount }).map((_, i) => (
        <div key={i} className="flex items-center space-x-4 py-3 border-b">
          <Skeleton className="h-12 w-12 rounded-full" />
          <div className="space-y-2 flex-1">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-3 w-1/2" />
          </div>
          <Skeleton className="h-8 w-20" />
        </div>
      ))}
    </div>
  )
}
