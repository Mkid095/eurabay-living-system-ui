"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import {
  GitBranch,
  Download,
  RefreshCw,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  AlertCircle,
} from "lucide-react";
import type { MutationSuccess } from "@/types/evolution";

interface MutationSuccessTrackingProps {
  data: MutationSuccess[];
  loading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  onMinAttemptsChange?: (minAttempts: number) => void;
  autoRefreshInterval?: number;
}

type SortField = "mutationType" | "successRate" | "totalAttempts" | "successful" | "avgFitnessImprovement";
type SortOrder = "asc" | "desc";

// Mutation type grouping
const MUTATION_TYPES = {
  ADD_FEATURE: "Add Feature",
  REMOVE_FEATURE: "Remove Feature",
  MODIFY_WEIGHT: "Modify Weight",
  COMBINE_FEATURES: "Combine Features",
} as const;

export const MutationSuccessTracking = ({
  data,
  loading = false,
  error = null,
  onRefresh,
  onMinAttemptsChange,
  autoRefreshInterval = 30000,
}: MutationSuccessTrackingProps) => {
  // Filter state
  const [minAttempts, setMinAttempts] = useState<number>(0);

  // Sort state
  const [sortField, setSortField] = useState<SortField>("successRate");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // Auto-refresh effect
  useEffect(() => {
    if (autoRefreshInterval > 0 && onRefresh) {
      const interval = setInterval(() => {
        onRefresh();
      }, autoRefreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefreshInterval, onRefresh]);

  // Handle min attempts change
  const handleMinAttemptsChange = useCallback((value: number) => {
    setMinAttempts(value);
    if (onMinAttemptsChange) {
      onMinAttemptsChange(value);
    }
  }, [onMinAttemptsChange]);

  // Filter and sort data
  const filteredAndSortedData = useMemo(() => {
    let result = [...data];

    // Apply minimum attempts filter
    if (minAttempts > 0) {
      result = result.filter((mutation) => mutation.totalAttempts >= minAttempts);
    }

    // Apply sorting
    result.sort((a, b) => {
      const aValue = a[sortField];
      const bValue = b[sortField];

      if (typeof aValue === "string" && typeof bValue === "string") {
        if (sortOrder === "asc") {
          return aValue.localeCompare(bValue);
        } else {
          return bValue.localeCompare(aValue);
        }
      }

      if (sortOrder === "asc") {
        return (aValue as number) > (bValue as number) ? 1 : -1;
      } else {
        return (aValue as number) < (bValue as number) ? 1 : -1;
      }
    });

    return result;
  }, [data, minAttempts, sortField, sortOrder]);

  // Sort handler
  const handleSort = useCallback((field: SortField) => {
    setSortField(field);
    setSortOrder((prev) => (prev === "asc" ? "desc" : "asc"));
  }, []);

  // Get sort icon
  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return <ArrowUpDown className="w-4 h-4 opacity-50" />;
    return sortOrder === "asc" ? (
      <ArrowUp className="w-4 h-4" />
    ) : (
      <ArrowDown className="w-4 h-4" />
    );
  };

  // Get success rate color (green >60%, yellow 30-60%, red <30%)
  const getSuccessRateColor = (successRate: number): string => {
    if (successRate > 60) return "text-profit";
    if (successRate >= 30) return "text-warning";
    return "text-loss";
  };

  const getSuccessRateBgColor = (successRate: number): string => {
    if (successRate > 60) return "bg-profit/10";
    if (successRate >= 30) return "bg-warning/10";
    return "bg-loss/10";
  };

  const getBarColor = (successRate: number): string => {
    if (successRate > 60) return "var(--profit)";
    if (successRate >= 30) return "var(--warning)";
    return "var(--loss)";
  };

  // Prepare chart data
  const chartData = useMemo(() => {
    return filteredAndSortedData.map((mutation) => ({
      name: mutation.mutationType,
      successRate: mutation.successRate,
      fitnessImprovement: mutation.avgFitnessImprovement,
    }));
  }, [filteredAndSortedData]);

  // Export to CSV
  const exportToCSV = useCallback(() => {
    const headers = [
      "Mutation Type",
      "Success Rate",
      "Total Attempts",
      "Successful",
      "Avg Fitness Improvement",
    ];

    const rows = filteredAndSortedData.map((mutation) => [
      mutation.mutationType,
      mutation.successRate.toFixed(2),
      mutation.totalAttempts.toString(),
      mutation.successful.toString(),
      mutation.avgFitnessImprovement.toFixed(4),
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((row) => row.join(",")),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `mutation-success-${new Date().toISOString().split("T")[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [filteredAndSortedData]);

  // Loading skeleton
  if (loading) {
    return (
      <Card className="w-full">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-2">
              <Skeleton className="h-6 w-48" />
              <Skeleton className="h-4 w-64" />
            </div>
            <Skeleton className="h-9 w-24" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <Skeleton className="h-9 w-32" />
            <Skeleton className="h-64 w-full" />
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card className="w-full">
        <CardContent className="flex flex-col items-center justify-center py-12">
          <AlertCircle className="w-12 h-12 text-destructive mb-4" />
          <h3 className="text-lg font-semibold mb-2">Failed to load mutation data</h3>
          <p className="text-muted-foreground text-sm mb-4">{error}</p>
          {onRefresh && (
            <Button onClick={onRefresh} variant="outline">
              <RefreshCw className="w-4 h-4 mr-2" />
              Retry
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-primary" />
              Mutation Success Tracking
            </CardTitle>
            <CardDescription>
              Analyze mutation strategy effectiveness and fitness improvements
            </CardDescription>
          </div>
          <div className="flex gap-2">
            {onRefresh && (
              <Button
                onClick={onRefresh}
                variant="outline"
                size="sm"
                disabled={loading}
              >
                <RefreshCw className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} />
              </Button>
            )}
            <Button onClick={exportToCSV} variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Filters */}
          <div className="flex gap-4">
            <Input
              type="number"
              placeholder="Min attempts"
              value={minAttempts || ""}
              onChange={(e) => handleMinAttemptsChange(e.target.value ? parseInt(e.target.value) : 0)}
              className="w-40"
              min="0"
            />
          </div>

          {/* Results count */}
          <div className="text-sm text-muted-foreground">
            Showing {filteredAndSortedData.length} mutation types
          </div>

          {/* Bar Chart */}
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="name"
                  className="text-xs"
                  tick={{ fill: "var(--muted-foreground)" }}
                />
                <YAxis
                  className="text-xs"
                  tick={{ fill: "var(--muted-foreground)" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "var(--card)",
                    border: "1px solid var(--border)",
                    borderRadius: "0.5rem",
                  }}
                  formatter={(value: number | undefined, name?: string) => [
                    name === "successRate" ? `${(value ?? 0).toFixed(1)}%` : (value ?? 0).toFixed(4),
                    name === "successRate" ? "Success Rate" : "Fitness Improvement",
                  ]}
                />
                <Bar dataKey="successRate" radius={[4, 4, 0, 0]}>
                  {filteredAndSortedData.map((mutation, index) => (
                    <Cell key={`cell-${index}`} fill={getBarColor(mutation.successRate)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Table */}
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort("mutationType")}
                  >
                    <div className="flex items-center gap-2">
                      Mutation Type
                      {getSortIcon("mutationType")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort("successRate")}
                  >
                    <div className="flex items-center gap-2">
                      Success Rate
                      {getSortIcon("successRate")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort("totalAttempts")}
                  >
                    <div className="flex items-center gap-2">
                      Total Attempts
                      {getSortIcon("totalAttempts")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort("successful")}
                  >
                    <div className="flex items-center gap-2">
                      Successful
                      {getSortIcon("successful")}
                    </div>
                  </TableHead>
                  <TableHead
                    className="cursor-pointer hover:bg-muted/50"
                    onClick={() => handleSort("avgFitnessImprovement")}
                  >
                    <div className="flex items-center gap-2">
                      Avg Fitness Improvement
                      {getSortIcon("avgFitnessImprovement")}
                    </div>
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredAndSortedData.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={5} className="text-center py-8">
                      <div className="text-muted-foreground">
                        {minAttempts > 0
                          ? "No mutations match your filter"
                          : "No mutation data available"}
                      </div>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredAndSortedData.map((mutation) => (
                    <TableRow key={mutation.mutationType}>
                      <TableCell className="font-medium">
                        {mutation.mutationType}
                      </TableCell>
                      <TableCell>
                        <div
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSuccessRateBgColor(
                            mutation.successRate
                          )} ${getSuccessRateColor(mutation.successRate)}`}
                        >
                          {mutation.successRate.toFixed(1)}%
                        </div>
                      </TableCell>
                      <TableCell>{mutation.totalAttempts}</TableCell>
                      <TableCell className="text-profit">{mutation.successful}</TableCell>
                      <TableCell
                        className={
                          mutation.avgFitnessImprovement >= 0 ? "text-profit" : "text-loss"
                        }
                      >
                        {mutation.avgFitnessImprovement >= 0 ? "+" : ""}
                        {mutation.avgFitnessImprovement.toFixed(4)}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};
