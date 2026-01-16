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
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import {
  Target,
  Search,
  Download,
  RefreshCw,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  AlertCircle,
  GitCompare,
} from "lucide-react";
import type { FeatureSuccess } from "@/types/evolution";
import { FeatureDetailModal } from "./FeatureDetailModal";

interface FeatureSuccessAnalysisProps {
  data: FeatureSuccess[];
  loading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  autoRefreshInterval?: number;
}

type SortField = "successRate" | "totalUses" | "wins" | "losses" | "avgPnL";
type SortOrder = "asc" | "desc";

export const FeatureSuccessAnalysis = ({
  data,
  loading = false,
  error = null,
  onRefresh,
  autoRefreshInterval = 30000,
}: FeatureSuccessAnalysisProps) => {
  // Filter and search state
  const [searchQuery, setSearchQuery] = useState("");
  const [minUses, setMinUses] = useState<number>(0);

  // Sort state
  const [sortField, setSortField] = useState<SortField>("successRate");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 20;

  // Modal state
  const [selectedFeature, setSelectedFeature] = useState<FeatureSuccess | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  // Auto-refresh effect
  useEffect(() => {
    if (autoRefreshInterval > 0 && onRefresh) {
      const interval = setInterval(() => {
        onRefresh();
      }, autoRefreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefreshInterval, onRefresh]);

  // Filter and sort data
  const filteredAndSortedData = useMemo(() => {
    let result = [...data];

    // Apply search filter
    if (searchQuery) {
      result = result.filter((feature) =>
        feature.featureName.toLowerCase().includes(searchQuery.toLowerCase())
      );
    }

    // Apply minimum uses filter
    if (minUses > 0) {
      result = result.filter((feature) => feature.totalUses >= minUses);
    }

    // Apply sorting
    result.sort((a, b) => {
      const aValue = a[sortField];
      const bValue = b[sortField];

      if (sortOrder === "asc") {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });

    return result;
  }, [data, searchQuery, minUses, sortField, sortOrder]);

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedData.length / itemsPerPage);
  const paginatedData = filteredAndSortedData.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  );

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, minUses, sortField, sortOrder]);

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

  // Get success rate color
  const getSuccessRateColor = (successRate: number): string => {
    if (successRate > 70) return "text-profit";
    if (successRate >= 40) return "text-warning";
    return "text-loss";
  };

  const getSuccessRateBgColor = (successRate: number): string => {
    if (successRate > 70) return "bg-profit/10";
    if (successRate >= 40) return "bg-warning/10";
    return "bg-loss/10";
  };

  // Export to CSV
  const exportToCSV = useCallback(() => {
    const headers = [
      "Feature Name",
      "Success Rate",
      "Total Uses",
      "Wins",
      "Losses",
      "Avg P&L",
    ];

    const rows = filteredAndSortedData.map((feature) => [
      feature.featureName,
      feature.successRate.toFixed(2),
      feature.totalUses.toString(),
      feature.wins.toString(),
      feature.losses.toString(),
      feature.avgPnL.toFixed(2),
    ]);

    const csvContent = [
      headers.join(","),
      ...rows.map((row) => row.join(",")),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `feature-success-${new Date().toISOString().split("T")[0]}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [filteredAndSortedData]);

  // Feature detail handlers
  const handleRowClick = useCallback((feature: FeatureSuccess) => {
    setSelectedFeature(feature);
    setIsModalOpen(true);
  }, []);

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
            <div className="flex gap-4">
              <Skeleton className="h-9 flex-1" />
              <Skeleton className="h-9 w-32" />
            </div>
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
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
          <h3 className="text-lg font-semibold mb-2">Failed to load feature data</h3>
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
    <>
      <Card className="w-full">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Target className="w-5 h-5 text-primary" />
                Feature Success Analysis
              </CardTitle>
              <CardDescription>
                Performance metrics for evolved features
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
          <div className="space-y-4">
            {/* Filters */}
            <div className="flex gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                <Input
                  placeholder="Search features..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
              <Input
                type="number"
                placeholder="Min uses"
                value={minUses || ""}
                onChange={(e) => setMinUses(e.target.value ? parseInt(e.target.value) : 0)}
                className="w-32"
                min="0"
              />
            </div>

            {/* Results count */}
            <div className="text-sm text-muted-foreground">
              Showing {paginatedData.length} of {filteredAndSortedData.length} features
            </div>

            {/* Table */}
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort("successRate")}
                    >
                      <div className="flex items-center gap-2">
                        Success Rate
                        {getSortIcon("successRate")}
                      </div>
                    </TableHead>
                    <TableHead>Feature Name</TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort("totalUses")}
                    >
                      <div className="flex items-center gap-2">
                        Total Uses
                        {getSortIcon("totalUses")}
                      </div>
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort("wins")}
                    >
                      <div className="flex items-center gap-2">
                        Wins
                        {getSortIcon("wins")}
                      </div>
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort("losses")}
                    >
                      <div className="flex items-center gap-2">
                        Losses
                        {getSortIcon("losses")}
                      </div>
                    </TableHead>
                    <TableHead
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => handleSort("avgPnL")}
                    >
                      <div className="flex items-center gap-2">
                        Avg P&L
                        {getSortIcon("avgPnL")}
                      </div>
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {paginatedData.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center py-8">
                        <div className="text-muted-foreground">
                          {searchQuery || minUses > 0
                            ? "No features match your filters"
                            : "No feature data available"}
                        </div>
                      </TableCell>
                    </TableRow>
                  ) : (
                    paginatedData.map((feature) => (
                      <TableRow
                        key={feature.featureId}
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => handleRowClick(feature)}
                      >
                        <TableCell>
                          <div
                            className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getSuccessRateBgColor(
                              feature.successRate
                            )} ${getSuccessRateColor(feature.successRate)}`}
                          >
                            {feature.successRate.toFixed(1)}%
                          </div>
                        </TableCell>
                        <TableCell className="font-medium">
                          {feature.featureName}
                        </TableCell>
                        <TableCell>{feature.totalUses}</TableCell>
                        <TableCell className="text-profit">{feature.wins}</TableCell>
                        <TableCell className="text-loss">{feature.losses}</TableCell>
                        <TableCell
                          className={
                            feature.avgPnL >= 0 ? "text-profit" : "text-loss"
                          }
                        >
                          {feature.avgPnL >= 0 ? "+" : ""}
                          {feature.avgPnL.toFixed(2)}
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <Pagination>
                <PaginationContent>
                  <PaginationItem>
                    <PaginationPrevious
                      onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                      className={
                        currentPage === 1 ? "pointer-events-none opacity-50" : "cursor-pointer"
                      }
                    />
                  </PaginationItem>
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => {
                    if (
                      page === 1 ||
                      page === totalPages ||
                      (page >= currentPage - 1 && page <= currentPage + 1)
                    ) {
                      return (
                        <PaginationItem key={page}>
                          <PaginationLink
                            onClick={() => setCurrentPage(page)}
                            isActive={currentPage === page}
                            className="cursor-pointer"
                          >
                            {page}
                          </PaginationLink>
                        </PaginationItem>
                      );
                    } else if (
                      page === currentPage - 2 ||
                      page === currentPage + 2
                    ) {
                      return (
                        <PaginationItem key={page}>
                          <PaginationEllipsis />
                        </PaginationItem>
                      );
                    }
                    return null;
                  })}
                  <PaginationItem>
                    <PaginationNext
                      onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                      className={
                        currentPage === totalPages
                          ? "pointer-events-none opacity-50"
                          : "cursor-pointer"
                      }
                    />
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Feature Detail Modal */}
      <FeatureDetailModal
        feature={selectedFeature}
        open={isModalOpen}
        onOpenChange={setIsModalOpen}
      />
    </>
  );
};
