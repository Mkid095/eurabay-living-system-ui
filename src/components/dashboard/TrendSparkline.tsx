"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface TrendSparklineProps {
  /** Array of price data points */
  data: number[];
  /** Color for the line (green for bullish, red for bearish, gray for neutral) */
  color?: string;
  /** Optional additional className */
  className?: string;
}

/**
 * TrendSparkline component
 * Renders a small line chart showing recent price movement
 */
export function TrendSparkline({ data, color = "#22c55e", className }: TrendSparklineProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || data.length === 0) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Set canvas size with device pixel ratio for sharpness
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    // Clear canvas
    ctx.clearRect(0, 0, rect.width, rect.height);

    // Calculate min and max for scaling
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1; // Prevent division by zero

    // Padding
    const padding = 2;
    const chartWidth = rect.width - padding * 2;
    const chartHeight = rect.height - padding * 2;

    // Convert data point to canvas coordinates
    const getX = (index: number) => padding + (index / (data.length - 1)) * chartWidth;
    const getY = (value: number) => padding + chartHeight - ((value - min) / range) * chartHeight;

    // Draw the line
    ctx.beginPath();
    ctx.strokeStyle = color;
    ctx.lineWidth = 1.5;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";

    data.forEach((value, index) => {
      const x = getX(index);
      const y = getY(value);

      if (index === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    });

    ctx.stroke();

    // Draw gradient fill below the line
    const gradient = ctx.createLinearGradient(0, 0, 0, rect.height);
    gradient.addColorStop(0, color + "20"); // 20% opacity
    gradient.addColorStop(1, color + "00"); // 0% opacity

    ctx.lineTo(getX(data.length - 1), rect.height);
    ctx.lineTo(getX(0), rect.height);
    ctx.closePath();
    ctx.fillStyle = gradient;
    ctx.fill();
  }, [data, color]);

  if (data.length === 0) {
    return null;
  }

  return (
    <canvas
      ref={canvasRef}
      className={cn("w-full h-full", className)}
      style={{ width: "60px", height: "24px" }}
    />
  );
}
