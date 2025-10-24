"use client";

import { Card } from "@/components/ui/card";
import { Target } from "lucide-react";
import type { FeatureSuccess } from "@/types/evolution";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell
} from "recharts";

interface FeatureSuccessChartProps {
  data: FeatureSuccess[];
}

export const FeatureSuccessChart = ({ data }: FeatureSuccessChartProps) => {
  const getBarColor = (successRate: number) => {
    if (successRate >= 70) return 'var(--profit)';
    if (successRate >= 50) return 'var(--warning)';
    return 'var(--loss)';
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">Feature Success Rate</h3>
          <p className="text-sm text-muted-foreground">Performance of evolved features</p>
        </div>
        <Target className="w-5 h-5 text-primary" />
      </div>

      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="horizontal">
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis 
              type="number" 
              stroke="var(--muted-foreground)"
              fontSize={12}
              domain={[0, 100]}
            />
            <YAxis 
              type="category"
              dataKey="featureName" 
              stroke="var(--muted-foreground)"
              fontSize={12}
              width={120}
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: 'var(--card)',
                border: '1px solid var(--border)',
                borderRadius: '0.5rem'
              }}
              formatter={(value: number) => [`${value.toFixed(1)}%`, 'Success Rate']}
            />
            <Bar dataKey="successRate" radius={[0, 4, 4, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={getBarColor(entry.successRate)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 space-y-2">
        {data.slice(0, 3).map((feature) => (
          <div key={feature.featureId} className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{feature.featureName}</span>
            <div className="flex items-center gap-3">
              <span className="font-mono">{feature.wins}W / {feature.losses}L</span>
              <span className="font-semibold" style={{ color: getBarColor(feature.successRate) }}>
                {feature.successRate.toFixed(1)}%
              </span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};
