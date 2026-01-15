/**
 * CelebrationParticles Component
 *
 * Performance celebration particle effects for visual feedback on achievements.
 * Creates celebratory confetti bursts on significant wins and milestone achievements.
 *
 * Features:
 * - Confetti burst on significant wins (>$100 profit)
 * - Trigger on milestone achievements (100 trades, 90% win rate, etc)
 * - Multiple particle types (confetti squares, stars, sparks)
 * - Customizable celebration thresholds
 * - Enable/disable toggle in settings
 * - Gravity effect to particles
 * - Fade out particles over 3 seconds
 * - WebSocket subscription to performance_update events
 */

'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useTheme } from 'next-themes';

/**
 * Particle type for celebrations
 */
export type ParticleType = 'confetti' | 'star' | 'spark';

/**
 * Milestone type for celebration triggers
 */
export type MilestoneType =
  | 'profit_threshold'
  | 'trade_count'
  | 'win_rate'
  | 'streak'
  | 'custom';

/**
 * Performance event data structure
 */
export interface PerformanceEvent {
  /** Event ID */
  id: string;
  /** Milestone type */
  milestone: MilestoneType;
  /** Event value (e.g., profit amount, trade count, win rate) */
  value: number;
  /** Event message */
  message?: string;
  /** Timestamp */
  timestamp?: string;
  /** Source position (for animation origin) */
  position?: { x: number; y: number };
}

/**
 * Component props
 */
export interface CelebrationParticlesProps {
  /** Enable celebration effects (default: true) */
  enabled?: boolean;
  /** Minimum profit threshold for celebration (default: 100) */
  profitThreshold?: number;
  /** Trade count milestone (default: 100) */
  tradeCountMilestone?: number;
  /** Win rate milestone (default: 90) */
  winRateMilestone?: number;
  /** Maximum concurrent celebrations (default: 3) */
  maxConcurrentCelebrations?: number;
  /** Particle count per celebration (default: 200) */
  particleCount?: number;
  /** Particle speed (default: 4) */
  particleSpeed?: number;
  /** Particle size range in pixels (default: 3-8) */
  particleSizeRange?: [number, number];
  /** Gravity effect (default: 0.15) */
  gravity?: number;
  /** Fade out duration in seconds (default: 3) */
  fadeOutDuration?: number;
  /** CSS class name for styling */
  className?: string;
  /** Custom events (optional, for testing) */
  customEvents?: PerformanceEvent[];
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
  type: ParticleType;
  rotation: number;
  rotationSpeed: number;
}

/**
 * Active celebration interface
 */
interface ActiveCelebration {
  id: string;
  particles: Particle[];
  createdAt: number;
}

/**
 * Celebration color palette
 */
const CELEBRATION_COLORS = [
  '#10b981', // Green
  '#059669', // Dark green
  '#3b82f6', // Blue
  '#6366f1', // Indigo
  '#8b5cf6', // Violet
  '#a855f7', // Purple
  '#f59e0b', // Amber
  '#ef4444', // Red
  '#ec4899', // Pink
  '#14b8a6', // Teal
];

/**
 * Get celebration colors based on theme
 */
function getCelebrationColors(isDark: boolean): string[] {
  return CELEBRATION_COLORS;
}

/**
 * Draw confetti square
 */
function drawConfetti(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  color: string,
  rotation: number
) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rotation);
  ctx.fillStyle = color;
  ctx.globalAlpha = ctx.globalAlpha;
  ctx.fillRect(-size / 2, -size / 2, size, size);
  ctx.restore();
}

/**
 * Draw star shape
 */
function drawStar(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  color: string,
  rotation: number
) {
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(rotation);
  ctx.beginPath();
  const spikes = 5;
  const outerRadius = size;
  const innerRadius = size / 2;

  for (let i = 0; i < spikes * 2; i++) {
    const radius = i % 2 === 0 ? outerRadius : innerRadius;
    const angle = (Math.PI / spikes) * i - Math.PI / 2;
    const px = Math.cos(angle) * radius;
    const py = Math.sin(angle) * radius;

    if (i === 0) {
      ctx.moveTo(px, py);
    } else {
      ctx.lineTo(px, py);
    }
  }

  ctx.closePath();
  ctx.fillStyle = color;
  ctx.globalAlpha = ctx.globalAlpha;
  ctx.fill();
  ctx.restore();
}

/**
 * Draw spark
 */
function drawSpark(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  size: number,
  color: string
) {
  ctx.beginPath();
  ctx.arc(x, y, size / 2, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.globalAlpha = ctx.globalAlpha;
  ctx.fill();

  // Add glow effect
  ctx.beginPath();
  ctx.arc(x, y, size, 0, Math.PI * 2);
  ctx.fillStyle = color;
  ctx.globalAlpha = ctx.globalAlpha * 0.3;
  ctx.fill();
}

/**
 * Check if performance event meets celebration threshold
 */
function meetsCelebrationThreshold(
  event: PerformanceEvent,
  profitThreshold: number,
  tradeCountMilestone: number,
  winRateMilestone: number
): boolean {
  switch (event.milestone) {
    case 'profit_threshold':
      return event.value >= profitThreshold;
    case 'trade_count':
      return event.value >= tradeCountMilestone;
    case 'win_rate':
      return event.value >= winRateMilestone;
    case 'streak':
      return event.value >= 5; // 5 win streak
    case 'custom':
      return true; // Custom events always trigger
    default:
      return false;
  }
}

/**
 * Main CelebrationParticles component
 */
export function CelebrationParticles({
  enabled = true,
  profitThreshold = 100,
  tradeCountMilestone = 100,
  winRateMilestone = 90,
  maxConcurrentCelebrations = 3,
  particleCount = 200,
  particleSpeed = 4,
  particleSizeRange = [3, 8],
  gravity = 0.15,
  fadeOutDuration = 3,
  className = '',
  customEvents = [],
}: CelebrationParticlesProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | undefined>(undefined);
  const { theme } = useTheme();
  const celebrationsRef = useRef<Map<string, ActiveCelebration>>(new Map());

  // Create celebration particles
  const createCelebrationParticles = useCallback((
    x: number,
    y: number
  ): Particle[] => {
    const isDark = theme === 'dark';
    const colors = getCelebrationColors(isDark);
    const particles: Particle[] = [];

    // Particle type distribution: 60% confetti, 25% stars, 15% sparks
    const confettiCount = Math.floor(particleCount * 0.6);
    const starCount = Math.floor(particleCount * 0.25);
    const sparkCount = particleCount - confettiCount - starCount;

    // Create confetti particles
    for (let i = 0; i < confettiCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = particleSpeed * (0.5 + Math.random() * 0.5);
      const size = particleSizeRange[0] + Math.random() * (particleSizeRange[1] - particleSizeRange[0]);

      particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 2, // Initial upward velocity
        size,
        opacity: 1,
        life: 0,
        maxLife: fadeOutDuration * 60, // Convert to frames (assuming 60fps)
        color: colors[Math.floor(Math.random() * colors.length)],
        type: 'confetti',
        rotation: Math.random() * Math.PI * 2,
        rotationSpeed: (Math.random() - 0.5) * 0.2,
      });
    }

    // Create star particles
    for (let i = 0; i < starCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = particleSpeed * (0.6 + Math.random() * 0.4);
      const size = particleSizeRange[0] + Math.random() * (particleSizeRange[1] - particleSizeRange[0]);

      particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 1.5,
        size,
        opacity: 1,
        life: 0,
        maxLife: fadeOutDuration * 60,
        color: colors[Math.floor(Math.random() * colors.length)],
        type: 'star',
        rotation: Math.random() * Math.PI * 2,
        rotationSpeed: (Math.random() - 0.5) * 0.15,
      });
    }

    // Create spark particles
    for (let i = 0; i < sparkCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = particleSpeed * (0.7 + Math.random() * 0.3);
      const size = (particleSizeRange[0] + Math.random() * (particleSizeRange[1] - particleSizeRange[0])) * 0.7;

      particles.push({
        x,
        y,
        vx: Math.cos(angle) * speed,
        vy: Math.sin(angle) * speed - 1,
        size,
        opacity: 1,
        life: 0,
        maxLife: fadeOutDuration * 60,
        color: colors[Math.floor(Math.random() * colors.length)],
        type: 'spark',
        rotation: 0,
        rotationSpeed: 0,
      });
    }

    return particles;
  }, [theme, particleCount, particleSpeed, particleSizeRange, fadeOutDuration]);

  // Trigger a new celebration
  const triggerCelebration = useCallback((event: PerformanceEvent) => {
    if (!enabled) return;

    // Check if event meets threshold
    if (!meetsCelebrationThreshold(event, profitThreshold, tradeCountMilestone, winRateMilestone)) {
      return;
    }

    // Check if we've exceeded max concurrent celebrations
    if (celebrationsRef.current.size >= maxConcurrentCelebrations) {
      // Remove oldest celebration
      const oldestId = Array.from(celebrationsRef.current.entries())
        .sort(([, a], [, b]) => a.createdAt - b.createdAt)[0]?.[0];
      if (oldestId) {
        celebrationsRef.current.delete(oldestId);
      }
    }

    const celebrationId = `${event.id}-${Date.now()}`;

    // Default to center of screen if no position provided
    const x = event.position?.x ?? window.innerWidth / 2;
    const y = event.position?.y ?? window.innerHeight / 3;

    // Create particles
    const particles = createCelebrationParticles(x, y);

    // Add to active celebrations
    celebrationsRef.current.set(celebrationId, {
      id: celebrationId,
      particles,
      createdAt: Date.now(),
    });

    // Log celebration for debugging
    console.log(`[CelebrationParticles] Triggered celebration for milestone: ${event.milestone}, value: ${event.value}`);
  }, [enabled, profitThreshold, tradeCountMilestone, winRateMilestone, maxConcurrentCelebrations, createCelebrationParticles]);

  // Handle custom events (for testing)
  useEffect(() => {
    if (customEvents.length > 0) {
      customEvents.forEach((event, index) => {
        setTimeout(() => triggerCelebration(event), index * 100);
      });
    }
  }, [customEvents, triggerCelebration]);

  // Handle WebSocket performance update events
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);

        // Check if this is a performance update event
        if (data.type === 'performance_update') {
          const performanceEvent: PerformanceEvent = {
            id: data.id || `perf-${Date.now()}`,
            milestone: data.milestone || 'profit_threshold',
            value: data.value || 0,
            message: data.message,
            timestamp: data.timestamp || new Date().toISOString(),
          };

          triggerCelebration(performanceEvent);
        }
      } catch (error) {
        // Ignore non-JSON messages
      }
    };

    // Listen for custom events from other components
    const handleCustomEvent = (event: CustomEvent<PerformanceEvent>) => {
      triggerCelebration(event.detail);
    };

    window.addEventListener('celebration-trigger', handleCustomEvent as EventListener);

    // Placeholder for WebSocket connection
    // In production, this would connect to the actual WebSocket server
    // const ws = new WebSocket(`${API_CONFIG.baseURL.replace('http', 'ws')}/ws`);
    // ws.addEventListener('message', handleMessage);

    return () => {
      window.removeEventListener('celebration-trigger', handleCustomEvent as EventListener);
      // ws.close();
    };
  }, [triggerCelebration]);

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
      const celebrationIdsToRemove: string[] = [];

      // Update and draw each celebration
      celebrationsRef.current.forEach((celebration, celebrationId) => {
        let allParticlesDead = true;

        celebration.particles.forEach((particle) => {
          // Update position
          particle.x += particle.vx;
          particle.y += particle.vy;

          // Apply gravity
          particle.vy += gravity;

          // Update rotation
          particle.rotation += particle.rotationSpeed;

          // Update life
          particle.life++;

          // Calculate opacity based on life
          const lifePercent = particle.life / particle.maxLife;
          particle.opacity = 1 - lifePercent;

          // Check bounds and bounce off bottom
          if (particle.y > canvas.height - particle.size) {
            particle.y = canvas.height - particle.size;
            particle.vy *= -0.5; // Bounce with damping
          }

          if (particle.life < particle.maxLife) {
            allParticlesDead = false;

            // Draw particle based on type
            ctx.globalAlpha = Math.max(0, particle.opacity);

            switch (particle.type) {
              case 'confetti':
                drawConfetti(ctx, particle.x, particle.y, particle.size, particle.color, particle.rotation);
                break;
              case 'star':
                drawStar(ctx, particle.x, particle.y, particle.size, particle.color, particle.rotation);
                break;
              case 'spark':
                drawSpark(ctx, particle.x, particle.y, particle.size, particle.color);
                break;
            }

            ctx.globalAlpha = 1;
          }
        });

        // Remove celebration if all particles are dead or celebration is too old
        if (allParticlesDead || now - celebration.createdAt > fadeOutDuration * 1000) {
          celebrationIdsToRemove.push(celebrationId);
        }
      });

      // Remove dead celebrations
      celebrationIdsToRemove.forEach((id) => {
        celebrationsRef.current.delete(id);
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
  }, [gravity, fadeOutDuration]);

  const containerStyle: React.CSSProperties = {
    position: 'fixed',
    inset: 0,
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
    zIndex: 9999,
  };

  if (!enabled) {
    return null;
  }

  return (
    <canvas
      ref={canvasRef}
      style={containerStyle}
      className={className}
    />
  );
}

/**
 * Hook to manually trigger celebrations
 * Useful for integrating with existing performance components
 */
export function useCelebrationParticles() {
  const triggerCelebration = useCallback((event: PerformanceEvent) => {
    // Dispatch custom event for CelebrationParticles component to listen to
    window.dispatchEvent(new CustomEvent<PerformanceEvent>('celebration-trigger', { detail: event }));
  }, []);

  return { triggerCelebration };
}

/**
 * Default export for convenience
 */
export default CelebrationParticles;
