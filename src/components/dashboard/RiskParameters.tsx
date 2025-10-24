"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Slider } from "@/components/ui/slider";
import { Shield, Save } from "lucide-react";

export function RiskParameters() {
  const [maxDrawdown, setMaxDrawdown] = useState([10]);
  const [maxPositionSize, setMaxPositionSize] = useState([5000]);
  const [maxDailyLoss, setMaxDailyLoss] = useState([1000]);
  const [stopLoss, setStopLoss] = useState("2.5");
  const [takeProfit, setTakeProfit] = useState("5.0");

  const handleSave = () => {
    // Handle save logic
    console.log("Risk parameters saved");
  };

  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-6">
        <Shield className="w-5 h-5 text-primary" />
        <h2 className="text-xl font-bold">Risk Parameters</h2>
      </div>

      <div className="space-y-6">
        {/* Max Drawdown */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Max Drawdown</Label>
            <span className="text-sm font-medium text-primary">{maxDrawdown[0]}%</span>
          </div>
          <Slider
            value={maxDrawdown}
            onValueChange={setMaxDrawdown}
            min={5}
            max={20}
            step={1}
            className="w-full"
          />
          <p className="text-xs text-muted-foreground">
            Maximum portfolio drawdown before auto-pause
          </p>
        </div>

        {/* Max Position Size */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Max Position Size</Label>
            <span className="text-sm font-medium text-primary">
              ${maxPositionSize[0].toLocaleString()}
            </span>
          </div>
          <Slider
            value={maxPositionSize}
            onValueChange={setMaxPositionSize}
            min={1000}
            max={10000}
            step={500}
            className="w-full"
          />
          <p className="text-xs text-muted-foreground">
            Maximum size per individual position
          </p>
        </div>

        {/* Max Daily Loss */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>Max Daily Loss</Label>
            <span className="text-sm font-medium text-primary">
              ${maxDailyLoss[0].toLocaleString()}
            </span>
          </div>
          <Slider
            value={maxDailyLoss}
            onValueChange={setMaxDailyLoss}
            min={500}
            max={5000}
            step={100}
            className="w-full"
          />
          <p className="text-xs text-muted-foreground">
            Daily loss limit before trading stops
          </p>
        </div>

        {/* Stop Loss & Take Profit */}
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="stop-loss">Stop Loss %</Label>
            <Input
              id="stop-loss"
              type="number"
              value={stopLoss}
              onChange={(e) => setStopLoss(e.target.value)}
              className="bg-card"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="take-profit">Take Profit %</Label>
            <Input
              id="take-profit"
              type="number"
              value={takeProfit}
              onChange={(e) => setTakeProfit(e.target.value)}
              className="bg-card"
            />
          </div>
        </div>

        {/* Save Button */}
        <Button 
          onClick={handleSave}
          className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
        >
          <Save className="w-4 h-4 mr-2" />
          Save Parameters
        </Button>
      </div>
    </Card>
  );
}
