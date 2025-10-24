"use client";

import { Card } from "@/components/ui/card";
import { TrendingUp } from "lucide-react";
import type { GenerationHistory } from "@/types/evolution";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend
} from "recharts";

interface GenerationHistoryChartProps {
  data: GenerationHistory[];
}

export const GenerationHistoryChart = ({ data }: GenerationHistoryChartProps) => {
  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">Evolution History</h3>
          <p className="text-sm text-muted-foreground">Generation progression over time</p>
        </div>
        <TrendingUp className="w-5 h-5 text-primary" />
      </div>

      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis 
              dataKey="timestamp" 
              stroke="var(--muted-foreground)"
              fontSize={12}
              tickFormatter={(value) => new Date(value).toLocaleDateString()}
            />
            <YAxis 
              stroke="var(--muted-foreground)"
              fontSize={12}
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: 'var(--card)',
                border: '1px solid var(--border)',
                borderRadius: '0.5rem'
              }}
              labelFormatter={(value) => new Date(value).toLocaleString()}
            />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="generation" 
              stroke="var(--primary)" 
              strokeWidth={2}
              name="Generation"
              dot={{ fill: 'var(--primary)', r: 4 }}
            />
            <Line 
              type="monotone" 
              dataKey="fitness" 
              stroke="var(--profit)" 
              strokeWidth={2}
              name="Fitness Score"
              dot={{ fill: 'var(--profit)', r: 4 }}
            />
            <Line 
              type="monotone" 
              dataKey="avgPerformance" 
              stroke="var(--chart-2)" 
              strokeWidth={2}
              name="Avg Performance"
              dot={{ fill: 'var(--chart-2)', r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
};
