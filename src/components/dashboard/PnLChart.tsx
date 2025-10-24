"use client";

import { Card } from "@/components/ui/card";
import { ChartDataPoint } from "@/hooks/useDashboardData";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { BarChart3 } from "lucide-react";

interface PnLChartProps {
  data: ChartDataPoint[];
}

export function PnLChart({ data }: PnLChartProps) {
  return (
    <Card className="p-4 sm:p-6">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 className="w-5 h-5 text-primary" />
        <h2 className="text-xl font-bold">Daily P&L</h2>
      </div>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <XAxis 
              dataKey="time" 
              stroke="#8ba69a"
              style={{ fontSize: '12px' }}
            />
            <YAxis 
              stroke="#8ba69a"
              style={{ fontSize: '12px' }}
              tickFormatter={(value) => `$${value}`}
            />
            <Tooltip 
              contentStyle={{
                backgroundColor: '#233d3d',
                border: '1px solid #3a5555',
                borderRadius: '8px',
                color: '#e8f5e9',
              }}
              formatter={(value: number) => [`$${value.toLocaleString()}`, 'P&L']}
            />
            <Bar dataKey="value" radius={[8, 8, 0, 0]}>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.value >= 0 ? '#66bb6a' : '#ef5350'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
