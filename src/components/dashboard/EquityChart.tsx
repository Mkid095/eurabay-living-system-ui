"use client";

import { Card } from "@/components/ui/card";
import { ChartDataPoint } from "@/hooks/useDashboardData";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import { TrendingUp } from "lucide-react";

interface EquityChartProps {
  data: ChartDataPoint[];
}

export function EquityChart({ data }: EquityChartProps) {
  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-xl font-bold mb-1">Portfolio Equity</h2>
          <p className="text-sm text-muted-foreground">24-hour performance</p>
        </div>
        <div className="flex items-center gap-2 text-profit">
          <TrendingUp className="w-5 h-5" />
          <span className="text-xl font-bold">+5.91%</span>
        </div>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <defs>
              <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#c4f54d" stopOpacity={0.3} />
                <stop offset="100%" stopColor="#4caf50" stopOpacity={0.05} />
              </linearGradient>
            </defs>
            <XAxis 
              dataKey="time" 
              stroke="#8ba69a"
              style={{ fontSize: '12px' }}
            />
            <YAxis 
              stroke="#8ba69a"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: '#233d3d',
                border: '1px solid #3a5555',
                borderRadius: '8px',
                color: '#e8f5e9',
              }}
              formatter={(value: number) => [`$${value.toLocaleString()}`, 'Equity']}
            />
            <Area 
              type="monotone" 
              dataKey="value" 
              stroke="#c4f54d" 
              strokeWidth={3}
              fill="url(#equityGradient)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
