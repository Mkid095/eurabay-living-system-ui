"use client";

import { useState, useCallback, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Brain, RefreshCw, AlertCircle, Filter } from "lucide-react";
import { useEvolutionData } from "@/hooks/useEvolutionData";
import type { ControllerDecisionHistory } from "@/types/evolution";

type DecisionType = 'ALL' | 'STABLE' | 'EVOLVE_CONSERVATIVE' | 'EVOLVE_MODERATE' | 'EVOLVE_AGGRESSIVE';
type DateRange = number | null;

export const ControllerDecisionTimeline = () => {
  const [selectedDecisionType, setSelectedDecisionType] = useState<DecisionType>('ALL');
  const [selectedDateRange, setSelectedDateRange] = useState<DateRange>(null);
  const [selectedDecision, setSelectedDecision] = useState<ControllerDecisionHistory | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const {
    controllerHistory,
    loading,
    error,
    refetchControllerHistory,
  } = useEvolutionData({
    refreshInterval: 10000, // 10 seconds
  });

  useEffect(() => {
    refetchControllerHistory(selectedDateRange ?? undefined);
  }, [selectedDateRange]);

  const getDecisionColor = (decision: string) => {
    switch (decision) {
      case 'STABLE':
        return 'bg-profit/20 text-profit border-profit/30';
      case 'EVOLVE_CONSERVATIVE':
        return 'bg-info/20 text-info border-info/30';
      case 'EVOLVE_MODERATE':
        return 'bg-warning/20 text-warning border-warning/30';
      case 'EVOLVE_AGGRESSIVE':
        return 'bg-loss/20 text-loss border-loss/30';
      default:
        return 'bg-muted text-muted-foreground';
    }
  };

  const getDecisionIcon = (decision: string) => {
    switch (decision) {
      case 'STABLE':
        return '✓';
      case 'EVOLVE_CONSERVATIVE':
        return '→';
      case 'EVOLVE_MODERATE':
        return '↗';
      case 'EVOLVE_AGGRESSIVE':
        return '⇈';
      default:
        return '•';
    }
  };

  const isTransition = (current: ControllerDecisionHistory, previous: ControllerDecisionHistory | undefined) => {
    if (!previous) return false;
    return previous.decision === 'STABLE' && current.decision.startsWith('EVOLVE_');
  };

  const filteredData = controllerHistory
    .filter(item => selectedDecisionType === 'ALL' || item.decision === selectedDecisionType)
    .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

  const handleRefresh = useCallback(() => {
    refetchControllerHistory(selectedDateRange ?? undefined);
  }, [refetchControllerHistory, selectedDateRange]);

  const handleRowClick = (decision: ControllerDecisionHistory) => {
    setSelectedDecision(decision);
    setIsModalOpen(true);
  };

  if (error.controllerHistory) {
    return (
      <Card className="p-6">
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <AlertCircle className="w-12 h-12 text-loss mb-4" />
          <h3 className="text-lg font-semibold mb-2">Failed to load controller history</h3>
          <p className="text-sm text-muted-foreground mb-4">{error.controllerHistory}</p>
          <Button onClick={handleRefresh} variant="outline">
            <RefreshCw className="w-4 h-4 mr-2" />
            Retry
          </Button>
        </div>
      </Card>
    );
  }

  return (
    <>
      <Card className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold">Controller Decision History</h3>
            <p className="text-sm text-muted-foreground">Evolution strategy timeline</p>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-muted-foreground" />
            <Select value={selectedDecisionType} onValueChange={(value) => setSelectedDecisionType(value as DecisionType)}>
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Filter by decision" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All Decisions</SelectItem>
                <SelectItem value="STABLE">STABLE</SelectItem>
                <SelectItem value="EVOLVE_CONSERVATIVE">EVOLVE CONSERVATIVE</SelectItem>
                <SelectItem value="EVOLVE_MODERATE">EVOLVE MODERATE</SelectItem>
                <SelectItem value="EVOLVE_AGGRESSIVE">EVOLVE AGGRESSIVE</SelectItem>
              </SelectContent>
            </Select>
            <Select value={selectedDateRange?.toString() ?? 'all'} onValueChange={(value) => setSelectedDateRange(value === 'all' ? null : parseInt(value))}>
              <SelectTrigger className="w-[120px]">
                <SelectValue placeholder="Date range" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Time</SelectItem>
                <SelectItem value="7">7 Days</SelectItem>
                <SelectItem value="30">30 Days</SelectItem>
                <SelectItem value="90">90 Days</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={handleRefresh} variant="outline" size="icon" disabled={loading.controllerHistory}>
              <RefreshCw className={`w-4 h-4 ${loading.controllerHistory ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>

        {loading.controllerHistory && filteredData.length === 0 ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="relative pl-8 pb-4 border-l-2 border-border">
                <div className="absolute left-[-9px] top-0 w-4 h-4 rounded-full bg-muted animate-pulse" />
                <div className="space-y-2">
                  <div className="h-6 w-32 bg-muted animate-pulse rounded" />
                  <div className="h-4 w-48 bg-muted animate-pulse rounded" />
                  <div className="h-4 w-24 bg-muted animate-pulse rounded" />
                </div>
              </div>
            ))}
          </div>
        ) : filteredData.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <Brain className="w-12 h-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No controller decisions found</h3>
            <p className="text-sm text-muted-foreground">
              {selectedDecisionType !== 'ALL' ? 'Try changing the filter' : 'Decisions will appear here as the system evolves'}
            </p>
          </div>
        ) : (
          <div className="space-y-4 max-h-[500px] overflow-y-auto pr-2">
            {filteredData.map((item, index) => {
              const previousItem = index > 0 ? filteredData[index - 1] : undefined;
              const transition = isTransition(item, previousItem);

              return (
                <div
                  key={index}
                  className={`relative pl-8 pb-4 border-l-2 last:border-l-0 cursor-pointer transition-colors rounded-lg p-4 hover:bg-muted/50 ${
                    transition ? 'border-primary bg-primary/5' : 'border-border'
                  }`}
                  onClick={() => handleRowClick(item)}
                >
                  <div className={`absolute left-[-9px] top-4 w-4 h-4 rounded-full border-2 border-background flex items-center justify-center ${
                    transition ? 'bg-primary' : 'bg-primary'
                  }`}>
                    <span className="text-[10px]">{getDecisionIcon(item.decision)}</span>
                  </div>

                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <Badge className={getDecisionColor(item.decision)}>
                        {item.decision.replace(/_/g, ' ')}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {new Date(item.timestamp).toLocaleString()}
                      </span>
                    </div>

                    <div className="flex items-center gap-4 text-sm">
                      <span className="text-muted-foreground">Generation:</span>
                      <span className="font-semibold">{item.generation}</span>
                      <span className="text-muted-foreground ml-4">Fitness:</span>
                      <span className="font-semibold">{item.fitness.toFixed(4)}</span>
                      <span className="text-muted-foreground ml-4">Performance:</span>
                      <span className="font-semibold">{item.performance.toFixed(2)}%</span>
                    </div>

                    {item.reason && (
                      <p className="text-xs text-muted-foreground italic line-clamp-1">
                        {item.reason}
                      </p>
                    )}

                    {transition && (
                      <Badge variant="outline" className="mt-2 text-xs">
                        Transition detected
                      </Badge>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </Card>

      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5" />
              Controller Decision Details
            </DialogTitle>
            <DialogDescription>
              Full details of the evolution controller decision
            </DialogDescription>
          </DialogHeader>

          {selectedDecision && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Decision Type:</span>
                <Badge className={getDecisionColor(selectedDecision.decision)}>
                  {selectedDecision.decision.replace(/_/g, ' ')}
                </Badge>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Generation:</span>
                <span className="font-semibold">{selectedDecision.generation}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Fitness Score:</span>
                <span className="font-semibold">{selectedDecision.fitness.toFixed(4)}</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Performance:</span>
                <span className="font-semibold">{selectedDecision.performance.toFixed(2)}%</span>
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Timestamp:</span>
                <span className="text-sm">{new Date(selectedDecision.timestamp).toLocaleString()}</span>
              </div>

              {selectedDecision.reason && (
                <div className="space-y-2">
                  <span className="text-sm text-muted-foreground">Reasoning:</span>
                  <p className="text-sm p-3 bg-muted rounded-lg">{selectedDecision.reason}</p>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
};
