"use client";

import { Card } from "@/components/ui/card";
import { Sparkles } from "lucide-react";
import type { MutationSuccess } from "@/types/evolution";
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend
} from "recharts";

interface MutationSuccessChartProps {
  data: MutationSuccess[];
}

const COLORS = [
  'var(--primary)',
  'var(--profit)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--warning)',
  'var(--info)'
];

export const MutationSuccessChart = ({ data }: MutationSuccessChartProps) => {
  const chartData = data.map((item) => ({
    name: item.mutationType,
    value: item.successRate,
    successful: item.successful,
    total: item.totalAttempts
  }));

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold">Mutation Success Rate</h3>
          <p className="text-sm text-muted-foreground">Evolution strategy effectiveness</p>
        </div>
        <Sparkles className="w-5 h-5 text-primary" />
      </div>

      <div className="h-[300px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              labelLine={false}
              label={({ name, value }) => `${name}: ${value.toFixed(1)}%`}
              outerRadius={80}
              fill="#8884d8"
              dataKey="value"
            >
              {chartData.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
            <Tooltip 
              contentStyle={{
                backgroundColor: 'var(--card)',
                border: '1px solid var(--border)',
                borderRadius: '0.5rem'
              }}
              formatter={(value: number, name: string, props: any) => [
                `${value.toFixed(1)}% (${props.payload.successful}/${props.payload.total})`,
                'Success Rate'
              ]}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-4 space-y-2">
        {data.map((mutation, index) => (
          <div key={mutation.mutationType} className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: COLORS[index % COLORS.length] }}
              />
              <span className="text-muted-foreground">{mutation.mutationType}</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-xs">{mutation.successful}/{mutation.totalAttempts}</span>
              <span className="font-semibold">{mutation.successRate.toFixed(1)}%</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
};
