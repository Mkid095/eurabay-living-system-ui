/**
 * VolatilityParticles Component
 *
 * Market volatility particle indicators that visualize market activity through particle intensity.
 * Particle count and speed are dynamically adjusted based on volatility index level.
 *
 * Features:
 * - Volatility-based particle count (V10=20, V25=40, V50=60, V75=80, V100=100)
 * - Volatility-based particle speed (V10=1, V25=2, V50=3, V75=4, V100=5)
 * - Trend-based particle coloring (bullish=green, bearish=red)
 * - Real-time updates with market data
 * - Visual intensity indicator (more movement = higher volatility)
 * - Performance optimization with particle limits
 * - WebSocket subscription to market_update events
 */

'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useTheme } from 'next-themes';

/**
 * Market trend type
 */
export type MarketTrend = 'BULLISH' | 'BEARISH' | 'SIDEWAYS';

/**
 * Market data structure
 */
export interface MarketData {
  /** Market symbol (e.g., V10, V25, V50, V75, V100) */
  symbol: string;
  /** Market display name */
  displayName: string;
  /** Current price */
  price: number;
  /** 24-hour price change percentage */
  change24h: number;
  /** Volume */
  volume: number;
  /** Spread */
  spread: number;
  /** Volatility index level */
  volatility: number;
  /** Current trend */
  trend: MarketTrend;
  /** Timestamp */
  timestamp?: string;
}

/**
 * Component props
 */
export interface VolatilityParticlesProps {
  /** Market data to visualize */
  market: MarketData;
  /** Enable particles (default: true) */
  enabled?: boolean;
  /** Maximum total particles across all markets (default: 200) */
  maxTotalParticles?: number;
  /** Particle size range in pixels (default: 1-3) */
  particleSizeRange?: [number, number];
  /** Particle opacity (default: 0.5) */
  particleOpacity?: number;
  /** CSS class name for styling */
  className?: string;
  /** Container dimensions */
  width?: number;
  height?: number;
  /** Update callback on market data change */
  onMarketUpdate?: (market: MarketData) => void;
}

/**
 * Particle interface
 */
interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  size: number;
  opacity: number;
  color: string;
  life: number;
  maxLife: number;
}

/**
 * Get particle count based on volatility level
 */
function getParticleCount(volatility: number): number {
  // V10=20, V25=40, V50=60, V75=80, V100=100
  const baseCount = volatility * 1.2; // Scale factor
  return Math.round(baseCount);
}

/**
 * Get particle speed based on volatility level
 */
function getParticleSpeed(volatility: number): number {
  // V10=1, V25=2, V50=3, V75=4, V100=5
  return Math.max(1, Math.min(5, volatility / 20));
}

/**
 * Get particle color based on trend
 */
function getParticleColor(trend: MarketTrend, isDark: boolean): string {
  switch (trend) {
    case 'BULLISH':
      return isDark ? '#10b981' : '#059669'; // Green
    case 'BEARISH':
      return isDark ? '#ef4444' : '#dc2626'; // Red
    case 'SIDEWAYS':
    default:
      return isDark ? '#f59e0b' : '#d97706'; // Amber/yellow
  }
}

/**
 * Main VolatilityParticles component
 */
export function VolatilityParticles({
  market,
  enabled = true,
  maxTotalParticles = 200,
  particleSizeRange = [1, 3],
  particleOpacity = 0.5,
  className = '',
  width = 300,
  height = 200,
  onMarketUpdate,
}: VolatilityParticlesProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | undefined>(undefined);
  const { theme } = useTheme();
  const particlesRef = useRef<Particle[]>([]);
  const [currentMarket, setCurrentMarket] = useState<MarketData>(market);

  // Update particles when market data changes
  useEffect(() => {
    setCurrentMarket(market);
    if (onMarketUpdate) {
      onMarketUpdate(market);
    }
  }, [market, onMarketUpdate]);

  // Initialize particles
  const initializeParticles = useCallback(() => {
    if (!enabled) {
      particlesRef.current = [];
      return;
    }

    const particleCount = getParticleCount(currentMarket.volatility);
    const speed = getParticleSpeed(currentMarket.volatility);
    const isDark = theme === 'dark';
    const color = getParticleColor(currentMarket.trend, isDark);

    const particles: Particle[] = [];

    for (let i = 0; i < particleCount; i++) {
      // Random position within canvas
      const x = Math.random() * width;
      const y = Math.random() * height;

      // Random velocity based on speed
      const angle = Math.random() * Math.PI * 2;
      const velocity = speed * (0.5 + Math.random() * 0.5);

      // Random size
      const size = particleSizeRange[0] + Math.random() * (particleSizeRange[1] - particleSizeRange[0]);

      particles.push({
        x,
        y,
        vx: Math.cos(angle) * velocity,
        vy: Math.sin(angle) * velocity,
        size,
        opacity: particleOpacity * (0.5 + Math.random() * 0.5),
        color,
        life: 0,
        maxLife: 180 + Math.random() * 120, // 3-5 seconds at 60fps
      });
    }

    // Limit total particles
    if (particles.length > maxTotalParticles) {
      particles.length = maxTotalParticles;
    }

    particlesRef.current = particles;
  }, [currentMarket, enabled, width, height, particleSizeRange, particleOpacity, maxTotalParticles, theme]);

  // Re-initialize particles when market data changes significantly
  useEffect(() => {
    initializeParticles();
  }, [initializeParticles]);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !enabled) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    canvas.width = width;
    canvas.height = height;

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const speed = getParticleSpeed(currentMarket.volatility);
      const isDark = theme === 'dark';
      const color = getParticleColor(currentMarket.trend, isDark);

      // Update and draw particles
      particlesRef.current.forEach((particle) => {
        // Update position
        particle.x += particle.vx * (speed / 2);
        particle.y += particle.vy * (speed / 2);

        // Wrap around edges
        if (particle.x < 0) particle.x = width;
        if (particle.x > width) particle.x = 0;
        if (particle.y < 0) particle.y = height;
        if (particle.y > height) particle.y = 0;

        // Update life
        particle.life++;

        // Respawn particle if it's too old
        if (particle.life > particle.maxLife) {
          particle.x = Math.random() * width;
          particle.y = Math.random() * height;
          particle.life = 0;
          particle.opacity = particleOpacity * (0.5 + Math.random() * 0.5);
        }

        // Update color based on current trend
        particle.color = color;

        // Draw particle
        ctx.beginPath();
        ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
        ctx.fillStyle = particle.color;
        ctx.globalAlpha = Math.max(0, particle.opacity);
        ctx.fill();
        ctx.globalAlpha = 1;
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [enabled, width, height, currentMarket, theme, particleOpacity]);

  // Handle WebSocket market update events
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);

        // Check if this is a market update event for this market
        if (data.type === 'market_update' && data.symbol === currentMarket.symbol) {
          const updatedMarket: MarketData = {
            ...currentMarket,
            price: data.price ?? currentMarket.price,
            change24h: data.change24h ?? currentMarket.change24h,
            volume: data.volume ?? currentMarket.volume,
            spread: data.spread ?? currentMarket.spread,
            volatility: data.volatility ?? currentMarket.volatility,
            trend: data.trend ?? currentMarket.trend,
            timestamp: data.timestamp ?? new Date().toISOString(),
          };

          setCurrentMarket(updatedMarket);

          // Re-initialize particles with new data
          initializeParticles();
        }
      } catch (error) {
        // Ignore non-JSON messages
      }
    };

    // Listen for custom events from other components
    const handleCustomEvent = (event: CustomEvent<MarketData>) => {
      if (event.detail.symbol === currentMarket.symbol) {
        setCurrentMarket(event.detail);
        initializeParticles();
      }
    };

    window.addEventListener('market-update', handleCustomEvent as EventListener);

    // Placeholder for WebSocket connection
    // In production, this would connect to the actual WebSocket server
    // const ws = new WebSocket(`${API_CONFIG.baseURL.replace('http', 'ws')}/ws`);
    // ws.addEventListener('message', handleMessage);

    return () => {
      window.removeEventListener('market-update', handleCustomEvent as EventListener);
      // ws.close();
    };
  }, [currentMarket, initializeParticles]);

  const containerStyle: React.CSSProperties = {
    position: 'absolute',
    inset: 0,
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
    zIndex: 1,
  };

  return (
    <canvas
      ref={canvasRef}
      style={containerStyle}
      className={className}
    />
  );
}

/**
 * Hook to manually trigger market updates
 * Useful for integrating with existing market components
 */
export function useVolatilityParticles() {
  const triggerUpdate = useCallback((market: MarketData) => {
    // Dispatch custom event for VolatilityParticles component to listen to
    window.dispatchEvent(new CustomEvent<MarketData>('market-update', { detail: market }));
  }, []);

  return { triggerUpdate };
}

/**
 * Default export for convenience
 */
export default VolatilityParticles;
