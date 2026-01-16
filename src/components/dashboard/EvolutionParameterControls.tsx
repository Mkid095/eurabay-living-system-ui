"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Settings, RotateCcw, Save, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { evolutionApi } from "@/lib/api";
import { AdminGuard } from "@/components/auth/RoleGuard";

type SelectionStrategy = 'roulette' | 'tournament' | 'rank';

interface EvolutionParams {
  mutationRate: number;
  crossoverRate: number;
  populationSize: number;
  eliteCount: number;
  selectionStrategy: SelectionStrategy;
  fitnessTarget: number;
}

interface EvolutionParamsWithDefaults extends EvolutionParams {
  defaults: {
    mutationRate: number;
    crossoverRate: number;
    populationSize: number;
    eliteCount: number;
    selectionStrategy: SelectionStrategy;
    fitnessTarget: number;
  };
}

const DEFAULT_PARAMS: EvolutionParams = {
  mutationRate: 0.1,
  crossoverRate: 0.5,
  populationSize: 50,
  eliteCount: 5,
  selectionStrategy: 'tournament',
  fitnessTarget: 0.75,
};

const SELECTION_STRATEGY_LABELS: Record<SelectionStrategy, string> = {
  roulette: 'Roulette Wheel',
  tournament: 'Tournament',
  rank: 'Rank-Based',
};

/**
 * EvolutionParameterControls component
 *
 * Admin-only controls for adjusting evolution parameters.
 * Provides sliders for numeric parameters and dropdown for selection strategy.
 */
export const EvolutionParameterControls = () => {
  const [params, setParams] = useState<EvolutionParams>(DEFAULT_PARAMS);
  const [currentValues, setCurrentValues] = useState<EvolutionParams>(DEFAULT_PARAMS);
  const [applyOnNextGeneration, setApplyOnNextGeneration] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  /**
   * Fetch current evolution parameters on mount
   */
  useEffect(() => {
    const fetchParams = async () => {
      try {
        setIsLoading(true);
        // Note: The API should return current parameters
        // For now, initialize with defaults
        setCurrentValues(DEFAULT_PARAMS);
        setParams(DEFAULT_PARAMS);
      } catch (error) {
        toast.error("Failed to load evolution parameters");
      } finally {
        setIsLoading(false);
      }
    };

    fetchParams();
  }, []);

  /**
   * Check if parameters differ from current values
   */
  const hasChanges = Object.keys(params).some(
    (key) => params[key as keyof EvolutionParams] !== currentValues[key as keyof EvolutionParams]
  );

  /**
   * Check if any parameter is at extreme value
   */
  const hasExtremeValues =
    params.mutationRate > 0.4 ||
    params.mutationRate < 0.02 ||
    params.crossoverRate > 0.8 ||
    params.crossoverRate < 0.2 ||
    params.populationSize > 90 ||
    params.populationSize < 15 ||
    params.eliteCount > 8 ||
    params.fitnessTarget > 0.95 ||
    params.fitnessTarget < 0.6;

  /**
   * Handle save parameters
   */
  const handleSave = async () => {
    setIsSaving(true);

    try {
      await evolutionApi.updateEvolutionParameters({
        mutationRate: params.mutationRate,
        crossoverRate: params.crossoverRate,
        populationSize: params.populationSize,
        eliteCount: params.eliteCount,
        selectionStrategy: params.selectionStrategy,
        fitnessTarget: params.fitnessTarget,
      });

      setCurrentValues(params);
      toast.success("Evolution parameters saved successfully", {
        description: applyOnNextGeneration
          ? "Changes will apply on next generation"
          : "Changes applied immediately",
      });
    } catch (error) {
      toast.error("Failed to save evolution parameters", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsSaving(false);
    }
  };

  /**
   * Handle reset to defaults
   */
  const handleReset = () => {
    setParams(DEFAULT_PARAMS);
    toast.info("Parameters reset to defaults");
  };

  /**
   * Handle reset to current saved values
   */
  const handleResetToCurrent = () => {
    setParams(currentValues);
    toast.info("Parameters reset to current values");
  };

  if (isLoading) {
    return (
      <Card className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-muted rounded w-1/3" />
          <div className="space-y-3">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 bg-muted rounded w-1/4" />
                <div className="h-2 bg-muted rounded" />
              </div>
            ))}
          </div>
        </div>
      </Card>
    );
  }

  return (
    <AdminGuard>
      <Card className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold">Evolution Parameters</h3>
            <p className="text-sm text-muted-foreground">Adjust evolution behavior and genetics</p>
          </div>
          <Settings className="w-5 h-5 text-primary" />
        </div>

        {/* Extreme values warning */}
        {hasExtremeValues && (
          <div className="mb-4 p-3 rounded-lg bg-warning/10 border border-warning/30 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-warning shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-warning">Extreme values detected</p>
              <p className="text-xs text-muted-foreground mt-1">
                Some parameters are set to extreme values. This may affect system stability or performance.
              </p>
            </div>
          </div>
        )}

        <div className="space-y-6">
          {/* Mutation Rate */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="mutation-rate">Mutation Rate</Label>
              <div className="flex items-center gap-2">
                <span className={`text-sm font-mono ${params.mutationRate !== currentValues.mutationRate ? 'text-warning' : ''}`}>
                  {params.mutationRate.toFixed(2)}
                </span>
                {params.mutationRate !== DEFAULT_PARAMS.mutationRate && (
                  <span className="text-xs text-muted-foreground">
                    (default: {DEFAULT_PARAMS.mutationRate})
                  </span>
                )}
              </div>
            </div>
            <Slider
              id="mutation-rate"
              min={0.01}
              max={0.5}
              step={0.01}
              value={[params.mutationRate]}
              onValueChange={([value]) => setParams({ ...params, mutationRate: value })}
              className="w-full"
            />
            <p className="text-xs text-muted-foreground">
              Probability of gene mutation (0.01-0.5)
            </p>
          </div>

          {/* Crossover Rate */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="crossover-rate">Crossover Rate</Label>
              <div className="flex items-center gap-2">
                <span className={`text-sm font-mono ${params.crossoverRate !== currentValues.crossoverRate ? 'text-warning' : ''}`}>
                  {params.crossoverRate.toFixed(2)}
                </span>
                {params.crossoverRate !== DEFAULT_PARAMS.crossoverRate && (
                  <span className="text-xs text-muted-foreground">
                    (default: {DEFAULT_PARAMS.crossoverRate})
                  </span>
                )}
              </div>
            </div>
            <Slider
              id="crossover-rate"
              min={0.1}
              max={0.9}
              step={0.05}
              value={[params.crossoverRate]}
              onValueChange={([value]) => setParams({ ...params, crossoverRate: value })}
              className="w-full"
            />
            <p className="text-xs text-muted-foreground">
              Probability of gene crossover (0.1-0.9)
            </p>
          </div>

          {/* Population Size */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="population-size">Population Size</Label>
              <div className="flex items-center gap-2">
                <span className={`text-sm font-mono ${params.populationSize !== currentValues.populationSize ? 'text-warning' : ''}`}>
                  {params.populationSize}
                </span>
                {params.populationSize !== DEFAULT_PARAMS.populationSize && (
                  <span className="text-xs text-muted-foreground">
                    (default: {DEFAULT_PARAMS.populationSize})
                  </span>
                )}
              </div>
            </div>
            <Slider
              id="population-size"
              min={10}
              max={100}
              step={5}
              value={[params.populationSize]}
              onValueChange={([value]) => setParams({ ...params, populationSize: value })}
              className="w-full"
            />
            <p className="text-xs text-muted-foreground">
              Number of individuals per generation (10-100)
            </p>
          </div>

          {/* Elite Count */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="elite-count">Elite Count</Label>
              <div className="flex items-center gap-2">
                <span className={`text-sm font-mono ${params.eliteCount !== currentValues.eliteCount ? 'text-warning' : ''}`}>
                  {params.eliteCount}
                </span>
                {params.eliteCount !== DEFAULT_PARAMS.eliteCount && (
                  <span className="text-xs text-muted-foreground">
                    (default: {DEFAULT_PARAMS.eliteCount})
                  </span>
                )}
              </div>
            </div>
            <Slider
              id="elite-count"
              min={1}
              max={10}
              step={1}
              value={[params.eliteCount]}
              onValueChange={([value]) => setParams({ ...params, eliteCount: value })}
              className="w-full"
            />
            <p className="text-xs text-muted-foreground">
              Number of top individuals to preserve (1-10)
            </p>
          </div>

          {/* Selection Strategy */}
          <div className="space-y-2">
            <Label htmlFor="selection-strategy">Selection Strategy</Label>
            <Select
              value={params.selectionStrategy}
              onValueChange={(value) => setParams({ ...params, selectionStrategy: value as SelectionStrategy })}
            >
              <SelectTrigger id="selection-strategy" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(SELECTION_STRATEGY_LABELS).map(([value, label]) => (
                  <SelectItem key={value} value={value}>
                    <div className="flex items-center justify-between w-full gap-2">
                      <span>{label}</span>
                      {value === DEFAULT_PARAMS.selectionStrategy && (
                        <span className="text-xs text-muted-foreground">(default)</span>
                      )}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Method for selecting parents for reproduction
            </p>
          </div>

          {/* Fitness Target */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="fitness-target">Fitness Target</Label>
              <div className="flex items-center gap-2">
                <span className={`text-sm font-mono ${params.fitnessTarget !== currentValues.fitnessTarget ? 'text-warning' : ''}`}>
                  {(params.fitnessTarget * 100).toFixed(0)}%
                </span>
                {params.fitnessTarget !== DEFAULT_PARAMS.fitnessTarget && (
                  <span className="text-xs text-muted-foreground">
                    (default: {(DEFAULT_PARAMS.fitnessTarget * 100).toFixed(0)}%)
                  </span>
                )}
              </div>
            </div>
            <Slider
              id="fitness-target"
              min={0.5}
              max={0.99}
              step={0.01}
              value={[params.fitnessTarget]}
              onValueChange={([value]) => setParams({ ...params, fitnessTarget: value })}
              className="w-full"
            />
            <p className="text-xs text-muted-foreground">
              Target fitness threshold for convergence (50-99%)
            </p>
          </div>

          {/* Apply on Next Generation */}
          <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/30">
            <Checkbox
              id="apply-next-gen"
              checked={applyOnNextGeneration}
              onCheckedChange={(checked) => setApplyOnNextGeneration(checked as boolean)}
            />
            <div className="flex-1">
              <label htmlFor="apply-next-gen" className="text-sm font-medium cursor-pointer">
                Apply on Next Generation
              </label>
              <p className="text-xs text-muted-foreground">
                Delay parameter changes until next evolution cycle
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 pt-4">
            <Button
              onClick={handleSave}
              disabled={!hasChanges || isSaving}
              className="flex-1"
            >
              <Save className="w-4 h-4 mr-2" />
              {isSaving ? 'Saving...' : 'Save Parameters'}
            </Button>
            <Button
              onClick={handleReset}
              variant="outline"
              title="Reset to defaults"
            >
              <RotateCcw className="w-4 h-4 mr-2" />
              Defaults
            </Button>
            {hasChanges && (
              <Button
                onClick={handleResetToCurrent}
                variant="ghost"
                title="Reset to current values"
              >
                Revert
              </Button>
            )}
          </div>
        </div>
      </Card>
    </AdminGuard>
  );
};
