/**
 * TradeBurst Component
 *
 * Particle burst effect for trade execution visual feedback.
 * Creates animated particle bursts when trades execute with color-coding by direction.
 *
 * Features:
 * - Particle burst on trade execution event
 * - Color-coded by trade direction (BUY=green, SELL=red)
 * - Size proportional to trade volume
 * - Animated burst from trade card position outward
 * - Multiple concurrent bursts supported (max 5)
 * - Optional sound effect on burst
 * - Fade out particles over 2 seconds
 * - WebSocket subscriptions for trade events
 */

'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useTheme } from 'next-themes';

/**
 * Trade direction type
 */
export type TradeDirection = 'BUY' | 'SELL';

/**
 * Trade event data structure
 */
export interface TradeEvent {
  /** Trade ID/ticket */
  id: string;
  /** Trade direction */
  direction: TradeDirection;
  /** Trade volume (affects burst size) */
  volume: number;
  /** Trade symbol */
  symbol: string;
  /** Trade price */
  price: number;
  /** Event type */
  type: 'mt5_order_opened' | 'trade_update';
  /** Timestamp */
  timestamp: string;
  /** Source position (for animation origin) */
  position?: { x: number; y: number };
}

/**
 * Component props
 */
export interface TradeBurstProps {
  /** Enable sound effect on burst (default: false) */
  enableSound?: boolean;
  /** Maximum concurrent bursts (default: 5) */
  maxConcurrentBursts?: number;
  /** Particle count per burst (default: 100) */
  particleCount?: number;
  /** Particle speed (default: 3) */
  particleSpeed?: number;
  /** Particle size range in pixels (default: 2-6) */
  particleSizeRange?: [number, number];
  /** Particle opacity (default: 0.8) */
  particleOpacity?: number;
  /** Fade out duration in seconds (default: 2) */
  fadeOutDuration?: number;
  /** CSS class name for styling */
  className?: string;
  /** Custom trade events (optional, for testing) */
  customEvents?: TradeEvent[];
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
  life: number;
  maxLife: number;
  color: string;
}

/**
 * Active burst interface
 */
interface ActiveBurst {
  id: string;
  particles: Particle[];
  createdAt: number;
}

/**
 * Get burst color based on trade direction
 */
function getBurstColor(direction: TradeDirection, isDark: boolean): string {
  if (direction === 'BUY') {
    return isDark ? '#10b981' : '#059669'; // Green for BUY
  }
  return isDark ? '#ef4444' : '#dc2626'; // Red for SELL
}

/**
 * Get burst size multiplier based on trade volume
 */
function getBurstSizeMultiplier(volume: number): number {
  // Scale multiplier: 0.01 lot = 1x, 1.0 lot = 2x, 10+ lots = 3x
  if (volume <= 0.01) return 1;
  if (volume <= 1.0) return 1 + volume;
  return 2 + Math.min(volume / 5, 1);
}

/**
 * Main TradeBurst component
 */
export function TradeBurst({
  enableSound = false,
  maxConcurrentBursts = 5,
  particleCount = 100,
  particleSpeed = 3,
  particleSizeRange = [2, 6],
  particleOpacity = 0.8,
  fadeOutDuration = 2,
  className = '',
  customEvents = [],
}: TradeBurstProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | undefined>(undefined);
  const { theme } = useTheme();
  const burstsRef = useRef<Map<string, ActiveBurst>>(new Map());
  const audioContextRef = useRef<AudioContext | null>(null);

  // Initialize audio context on first user interaction
  useEffect(() => {
    const handleUserInteraction = () => {
      if (!audioContextRef.current && enableSound) {
        try {
          audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)();
        } catch (error) {
          console.warn('AudioContext not supported:', error);
        }
      }
    };

    window.addEventListener('click', handleUserInteraction);
    window.addEventListener('keydown', handleUserInteraction);

    return () => {
      window.removeEventListener('click', handleUserInteraction);
      window.removeEventListener('keydown', handleUserInteraction);
    };
  }, [enableSound]);

  // Play sound effect (optional)
  const playSound = useCallback((direction: TradeDirection) => {
    if (!enableSound || !audioContextRef.current) return;

    try {
      const ctx = audioContextRef.current;
      const oscillator = ctx.createOscillator();
      const gainNode = ctx.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(ctx.destination);

      // Different tones for BUY vs SELL
      oscillator.frequency.value = direction === 'BUY' ? 880 : 440; // A5 vs A4
      oscillator.type = 'sine';

      // Fade out quickly
      gainNode.gain.setValueAtTime(0.1, ctx.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);

      oscillator.start(ctx.currentTime);
      oscillator.stop(ctx.currentTime + 0.1);
    } catch (error) {
      // Silently fail if audio not supported
      console.warn('Audio playback failed:', error);
    }
  }, [enableSound]);

  // Create particles for a burst
  const createBurstParticles = useCallback((
    x: number,
    y: number,
    color: string,
    sizeMultiplier: number
  ): Particle[] => {
    const particles: Particle[] = [];

    for (let i = 0; i < particleCount; i++) {
      // Random angle for burst direction
      const angle = Math.random() * Math.PI * 2;
      // Random speed with some variance
      const speed = particleSpeed * (0.5 + Math.random() * 0.5);
      // Random size
      const size = (particleSizeRange[0] + Math.random() * (particleSizeRange[1] - particleSizeRange[0])) * sizeMultiplier;

      particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed,
        size,
        opacity: particleOpacity,
        life: 0,
        maxLife: fadeOutDuration * 60, // Convert to frames (assuming 60fps)
        color,
      });
    }

    return particles;
  }, [particleCount, particleSpeed, particleSizeRange, particleOpacity, fadeOutDuration]);

  // Trigger a new burst
  const triggerBurst = useCallback((event: TradeEvent) => {
    const burstId = `${event.id}-${Date.now()}`;
    const isDark = theme === 'dark';
    const color = getBurstColor(event.direction, isDark);
    const sizeMultiplier = getBurstSizeMultiplier(event.volume);

    // Default to center of screen if no position provided
    const x = event.position?.x ?? window.innerWidth / 2;
    const y = event.position?.y ?? window.innerHeight / 2;

    // Create particles
    const particles = createBurstParticles(x, y, color, sizeMultiplier);

    // Add to active bursts
    burstsRef.current.set(burstId, {
      id: burstId,
      particles,
      createdAt: Date.now(),
    });

    // Play sound if enabled
    playSound(event.direction);
  }, [theme, createBurstParticles, playSound]);

  // Handle custom events (for testing)
  useEffect(() => {
    if (customEvents.length > 0) {
      customEvents.forEach((event, index) => {
        setTimeout(() => triggerBurst(event), index * 100);
      });
    }
  }, [customEvents, triggerBurst]);

  // Handle WebSocket trade events
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);

        // Check if this is a trade event we care about
        if (data.type === 'mt5_order_opened' || data.type === 'trade_update') {
          const tradeEvent: TradeEvent = {
            id: data.ticket || data.id,
            direction: data.direction || data.side,
            volume: data.volume || data.lots || 1,
            symbol: data.symbol,
            price: data.price,
            type: data.type,
            timestamp: data.timestamp || new Date().toISOString(),
          };

          triggerBurst(tradeEvent);
        }
      } catch (error) {
        // Ignore non-JSON messages
      }
    };

    // Listen for custom events from other components
    const handleCustomEvent = (event: CustomEvent<TradeEvent>) => {
      triggerBurst(event.detail);
    };

    window.addEventListener('trade-burst', handleCustomEvent as EventListener);

    // Placeholder for WebSocket connection
    // In production, this would connect to the actual WebSocket server
    // const ws = new WebSocket(`${API_CONFIG.baseURL.replace('http', 'ws')}/ws`);
    // ws.addEventListener('message', handleMessage);

    return () => {
      window.removeEventListener('trade-burst', handleCustomEvent as EventListener);
      // ws.close();
    };
  }, [triggerBurst]);

  // Animation loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Set canvas size
    const resizeCanvas = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const now = Date.now();
      const burstIdsToRemove: string[] = [];

      // Update and draw each burst
      burstsRef.current.forEach((burst, burstId) => {
        let allParticlesDead = true;

        burst.particles.forEach((particle) => {
          // Update particle
          particle.x += particle.vx;
          particle.y += particle.vy;
          particle.life++;

          // Calculate opacity based on life
          const lifePercent = particle.life / particle.maxLife;
          particle.opacity = particleOpacity * (1 - lifePercent);

          if (particle.life < particle.maxLife) {
            allParticlesDead = false;

            // Draw particle
            ctx.beginPath();
            ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
            ctx.fillStyle = particle.color;
            ctx.globalAlpha = Math.max(0, particle.opacity);
            ctx.fill();
            ctx.globalAlpha = 1;
          }
        });

        // Remove burst if all particles are dead or burst is too old
        if (allParticlesDead || now - burst.createdAt > fadeOutDuration * 1000) {
          burstIdsToRemove.push(burstId);
        }
      });

      // Remove dead bursts
      burstIdsToRemove.forEach((id) => {
        burstsRef.current.delete(id);
      });

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [particleOpacity, fadeOutDuration]);

  const containerStyle: React.CSSProperties = {
    position: 'fixed',
    inset: 0,
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
    zIndex: 9999,
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
 * Hook to manually trigger trade bursts
 * Useful for integrating with existing trade components
 */
export function useTradeBurst() {
  const triggerBurst = useCallback((event: TradeEvent) => {
    // Dispatch custom event for TradeBurst component to listen to
    window.dispatchEvent(new CustomEvent<TradeEvent>('trade-burst', { detail: event }));
  }, []);

  return { triggerBurst };
}

/**
 * Default export for convenience
 */
export default TradeBurst;
