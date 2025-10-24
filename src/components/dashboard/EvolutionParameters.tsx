"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Settings, RotateCcw, Save } from "lucide-react";

interface EvolutionParams {
  mutationRate: number;
  adaptiveMinAccuracy: number;
  minPerformanceThreshold: number;
  evolutionAggression: number;
}

export const EvolutionParameters = () => {
  const [params, setParams] = useState<EvolutionParams>({
    mutationRate: 0.3,
    adaptiveMinAccuracy: 0.55,
    minPerformanceThreshold: 0.45,
    evolutionAggression: 0.5,
  });

  const [isSaving, setIsSaving] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    // TODO: Send to backend API
    await new Promise(resolve => setTimeout(resolve, 1000));
    setIsSaving(false);
  };

  const handleReset = () => {
    setParams({
      mutationRate: 0.3,
      adaptiveMinAccuracy: 0.55,
      minPerformanceThreshold: 0.45,
      evolutionAggression: 0.5,
    });
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">Evolution Parameters</h3>
          <p className="text-sm text-muted-foreground">Fine-tune evolution behavior</p>
        </div>
        <Settings className="w-5 h-5 text-primary" />
      </div>

      <div className="space-y-6">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="mutation-rate">Mutation Rate</Label>
            <span className="text-sm font-mono">{params.mutationRate.toFixed(2)}</span>
          </div>
          <Slider
            id="mutation-rate"
            min={0.1}
            max={0.8}
            step={0.05}
            value={[params.mutationRate]}
            onValueChange={([value]) => setParams({ ...params, mutationRate: value })}
            className="w-full"
          />
          <p className="text-xs text-muted-foreground">
            Controls how aggressively features are mutated
          </p>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="min-accuracy">Adaptive Min Accuracy</Label>
            <span className="text-sm font-mono">{(params.adaptiveMinAccuracy * 100).toFixed(0)}%</span>
          </div>
          <Slider
            id="min-accuracy"
            min={0.4}
            max={0.7}
            step={0.05}
            value={[params.adaptiveMinAccuracy]}
            onValueChange={([value]) => setParams({ ...params, adaptiveMinAccuracy: value })}
            className="w-full"
          />
          <p className="text-xs text-muted-foreground">
            Minimum accuracy threshold for feature survival
          </p>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="performance-threshold">Performance Threshold</Label>
            <span className="text-sm font-mono">{(params.minPerformanceThreshold * 100).toFixed(0)}%</span>
          </div>
          <Slider
            id="performance-threshold"
            min={0.3}
            max={0.6}
            step={0.05}
            value={[params.minPerformanceThreshold]}
            onValueChange={([value]) => setParams({ ...params, minPerformanceThreshold: value })}
            className="w-full"
          />
          <p className="text-xs text-muted-foreground">
            Minimum performance to trigger evolution
          </p>
        </div>

        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label htmlFor="aggression">Evolution Aggression</Label>
            <span className="text-sm font-mono">{(params.evolutionAggression * 100).toFixed(0)}%</span>
          </div>
          <Slider
            id="aggression"
            min={0}
            max={1}
            step={0.1}
            value={[params.evolutionAggression]}
            onValueChange={([value]) => setParams({ ...params, evolutionAggression: value })}
            className="w-full"
          />
          <p className="text-xs text-muted-foreground">
            Overall evolution intensity (conservative to aggressive)
          </p>
        </div>

        <div className="flex gap-2 pt-4">
          <Button 
            onClick={handleSave} 
            disabled={isSaving}
            className="flex-1"
          >
            <Save className="w-4 h-4 mr-2" />
            {isSaving ? 'Saving...' : 'Save Parameters'}
          </Button>
          <Button 
            onClick={handleReset}
            variant="outline"
          >
            <RotateCcw className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
};
