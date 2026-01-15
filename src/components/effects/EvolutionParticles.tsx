/**
 * EvolutionParticles Component
 *
 * Particle effects for visual feedback during evolution cycles.
 * Creates DNA-like double helix spiral animations with generation-based colors.
 *
 * Features:
 * - DNA-like double helix spiral animation
 * - Generation-based color changes (1-10=blue, 11-20=green, 21+=gold)
 * - Particle stream representing features mutating
 * - Burst effect on cycle completion
 * - Feature success/failure color indication
 * - Smooth transitions between evolution states
 * - WebSocket subscription to evolution_event and generation_changed events
 */

'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useTheme } from 'next-themes';

/**
 * Evolution event type
 */
export type EvolutionEventType = 'CYCLE_START' | 'CYCLE_COMPLETE' | 'FEATURE_MUTATING' | 'FEATURE_SUCCESS' | 'FEATURE_FAILURE';

/**
 * Evolution event data structure
 */
export interface EvolutionEvent {
  /** Event ID */
  id: string;
  /** Event type */
  type: EvolutionEventType;
  /** Current generation */
  generation: number;
  /** Feature name (for mutation events) */
  featureName?: string;
  /** Success/failure indication */
  success?: boolean;
  /** Timestamp */
  timestamp: string;
  /** Source position (for animation origin) */
  position?: { x: number; y: number };
}

/**
 * Component props
 */
export interface EvolutionParticlesProps {
  /** Particle count for evolution effects (default: 150) */
  particleCount?: number;
  /** Particle speed (default: 2) */
  particleSpeed?: number;
  /** Animation duration per cycle in seconds (default: 3) */
  animationDuration?: number;
  /** Particle size range in pixels (default: 2-5) */
  particleSizeRange?: [number, number];
  /** Particle opacity (default: 0.6) */
  particleOpacity?: number;
  /** CSS class name for styling */
  className?: string;
  /** Custom events (optional, for testing) */
  customEvents?: EvolutionEvent[];
}

/**
 * Particle interface
 */
interface Particle {
  x: number;
  y: number;
  z: number;
  angle: number;
  radius: number;
  speed: number;
  size: number;
  opacity: number;
  color: string;
  life: number;
  maxLife: number;
  strand: 0 | 1; // Which DNA strand (0 or 1)
  state: 'helix' | 'stream' | 'burst';
}

/**
 * Active animation state
 */
interface AnimationState {
  isActive: boolean;
  startTime: number;
  generation: number;
  eventType: EvolutionEventType;
  featureName?: string;
  success?: boolean;
}

/**
 * Get color based on generation
 */
function getGenerationColor(generation: number, isDark: boolean): string {
  // 1-10 = blue, 11-20 = green, 21+ = gold
  if (generation <= 10) {
    return isDark ? '#3b82f6' : '#2563eb'; // Blue
  }
  if (generation <= 20) {
    return isDark ? '#10b981' : '#059669'; // Green
  }
  return isDark ? '#f59e0b' : '#d97706'; // Gold/amber
}

/**
 * Get color for feature success/failure
 */
function getFeatureColor(success: boolean, isDark: boolean): string {
  return success
    ? isDark ? '#10b981' : '#059669' // Green for success
    : isDark ? '#ef4444' : '#dc2626'; // Red for failure
}

/**
 * Main EvolutionParticles component
 */
export function EvolutionParticles({
  particleCount = 150,
  particleSpeed = 2,
  animationDuration = 3,
  particleSizeRange = [2, 5],
  particleOpacity = 0.6,
  className = '',
  customEvents = [],
}: EvolutionParticlesProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animationRef = useRef<number | undefined>(undefined);
  const { theme } = useTheme();
  const particlesRef = useRef<Particle[]>([]);
  const animationStateRef = useRef<AnimationState>({
    isActive: false,
    startTime: 0,
    generation: 1,
    eventType: 'CYCLE_START',
  });

  // Initialize DNA helix particles
  const initializeHelixParticles = useCallback((
    generation: number,
    isDark: boolean
  ) => {
    const particles: Particle[] = [];
    const color = getGenerationColor(generation, isDark);

    for (let i = 0; i < particleCount; i++) {
      const angle = (i / particleCount) * Math.PI * 8; // 4 full rotations
      const strand: 0 | 1 = i % 2 as 0 | 1;

      particles.push({
        x: 0,
        y: 0,
        z: 0,
        angle,
        radius: 50 + Math.random() * 30,
        speed: particleSpeed * (0.8 + Math.random() * 0.4),
        size: particleSizeRange[0] + Math.random() * (particleSizeRange[1] - particleSizeRange[0]),
        opacity: particleOpacity * (0.5 + Math.random() * 0.5),
        color,
        life: 0,
        maxLife: animationDuration * 60,
        strand,
        state: 'helix',
      });
    }

    return particles;
  }, [particleCount, particleSpeed, particleSizeRange, particleOpacity, animationDuration]);

  // Initialize mutation stream particles
  const initializeStreamParticles = useCallback((
    generation: number,
    isDark: boolean,
    featureName: string
  ) => {
    const particles: Particle[] = [];
    const color = getGenerationColor(generation, isDark);

    for (let i = 0; i < particleCount; i++) {
      particles.push({
        x: Math.random() * 200 - 100,
        y: Math.random() * 200 - 100,
        z: 0,
        angle: Math.random() * Math.PI * 2,
        radius: 30 + Math.random() * 20,
        speed: particleSpeed * (0.5 + Math.random() * 0.5),
        size: particleSizeRange[0] + Math.random() * (particleSizeRange[1] - particleSizeRange[0]),
        opacity: particleOpacity * (0.4 + Math.random() * 0.4),
        color,
        life: 0,
        maxLife: animationDuration * 60,
        strand: i % 2 as 0 | 1,
        state: 'stream',
      });
    }

    return particles;
  }, [particleCount, particleSpeed, particleSizeRange, particleOpacity, animationDuration]);

  // Initialize burst particles for cycle completion
  const initializeBurstParticles = useCallback((
    generation: number,
    isDark: boolean,
    success: boolean
  ) => {
    const particles: Particle[] = [];
    const color = success
      ? getFeatureColor(true, isDark)
      : getFeatureColor(false, isDark);

    for (let i = 0; i < particleCount; i++) {
      const angle = Math.random() * Math.PI * 2;
      const speed = particleSpeed * 2 * (0.5 + Math.random() * 0.5);

      particles.push({
        x: 0,
        y: 0,
        z: 0,
        angle,
        radius: 10 + Math.random() * 20,
        speed,
        size: particleSizeRange[0] + Math.random() * (particleSizeRange[1] - particleSizeRange[0]),
        opacity: particleOpacity,
        color,
        life: 0,
        maxLife: animationDuration * 60,
        strand: i % 2 as 0 | 1,
        state: 'burst',
      });
    }

    return particles;
  }, [particleCount, particleSpeed, particleSizeRange, particleOpacity, animationDuration]);

  // Trigger evolution animation
  const triggerEvolution = useCallback((event: EvolutionEvent) => {
    const isDark = theme === 'dark';
    const state = animationStateRef.current;

    // Update animation state
    animationStateRef.current = {
      isActive: true,
      startTime: Date.now(),
      generation: event.generation,
      eventType: event.type,
      featureName: event.featureName,
      success: event.success,
    };

    // Initialize particles based on event type
    switch (event.type) {
      case 'CYCLE_START':
        particlesRef.current = initializeHelixParticles(event.generation, isDark);
        break;
      case 'FEATURE_MUTATING':
        particlesRef.current = initializeStreamParticles(
          event.generation,
          isDark,
          event.featureName || 'feature'
        );
        break;
      case 'CYCLE_COMPLETE':
        particlesRef.current = initializeBurstParticles(
          event.generation,
          isDark,
          event.success ?? true
        );
        break;
      case 'FEATURE_SUCCESS':
      case 'FEATURE_FAILURE':
        particlesRef.current = initializeBurstParticles(
          event.generation,
          isDark,
          event.type === 'FEATURE_SUCCESS'
        );
        break;
    }
  }, [theme, initializeHelixParticles, initializeStreamParticles, initializeBurstParticles]);

  // Handle custom events (for testing)
  useEffect(() => {
    if (customEvents.length > 0) {
      customEvents.forEach((event, index) => {
        setTimeout(() => triggerEvolution(event), index * 100);
      });
    }
  }, [customEvents, triggerEvolution]);

  // Handle WebSocket evolution events
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);

        // Check if this is an evolution event we care about
        if (data.type === 'evolution_event' || data.type === 'generation_changed') {
          const evolutionEvent: EvolutionEvent = {
            id: data.id || `ev-${Date.now()}`,
            type: data.eventType || 'CYCLE_START',
            generation: data.generation || 1,
            featureName: data.featureName,
            success: data.success,
            timestamp: data.timestamp || new Date().toISOString(),
          };

          triggerEvolution(evolutionEvent);
        }
      } catch (error) {
        // Ignore non-JSON messages
      }
    };

    // Listen for custom events from other components
    const handleCustomEvent = (event: CustomEvent<EvolutionEvent>) => {
      triggerEvolution(event.detail);
    };

    window.addEventListener('evolution-particles', handleCustomEvent as EventListener);

    // Placeholder for WebSocket connection
    // In production, this would connect to the actual WebSocket server
    // const ws = new WebSocket(`${API_CONFIG.baseURL.replace('http', 'ws')}/ws`);
    // ws.addEventListener('message', handleMessage);

    return () => {
      window.removeEventListener('evolution-particles', handleCustomEvent as EventListener);
      // ws.close();
    };
  }, [triggerEvolution]);

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

    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    const animate = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const state = animationStateRef.current;
      const isDark = theme === 'dark';
      const elapsed = Date.now() - state.startTime;

      // Check if animation should end
      if (elapsed > animationDuration * 1000 && state.isActive) {
        state.isActive = false;
        particlesRef.current = [];
      }

      // Update and draw particles
      particlesRef.current.forEach((particle, index) => {
        particle.life++;

        // Calculate life percentage for opacity
        const lifePercent = particle.life / particle.maxLife;

        if (particle.state === 'helix') {
          // DNA double helix animation
          const progress = elapsed / (animationDuration * 1000);
          const rotation = progress * Math.PI * 4;

          particle.angle += particle.speed * 0.02;

          // Calculate helix position
          const helixAngle = particle.angle + rotation;
          const helixOffset = particle.strand === 0 ? 0 : Math.PI;

          particle.x = centerX + Math.cos(helixAngle + helixOffset) * particle.radius;
          particle.y = centerY + Math.sin(helixAngle + helixOffset) * particle.radius * 0.3 + (index / particleCount) * canvas.height - canvas.height / 2;

          // Fade in then out
          particle.opacity = particleOpacity * Math.sin(lifePercent * Math.PI);

        } else if (particle.state === 'stream') {
          // Mutation stream animation
          particle.angle += particle.speed * 0.01;

          // Spiral outward
          const streamRadius = particle.radius * (1 + lifePercent * 2);
          particle.x = centerX + Math.cos(particle.angle) * streamRadius;
          particle.y = centerY + Math.sin(particle.angle) * streamRadius;

          // Fade out over time
          particle.opacity = particleOpacity * (1 - lifePercent);

        } else if (particle.state === 'burst') {
          // Burst animation
          const burstAngle = particle.angle;
          const burstSpeed = particle.speed * (1 + lifePercent * 2);

          particle.x += Math.cos(burstAngle) * burstSpeed;
          particle.y += Math.sin(burstAngle) * burstSpeed;

          // Fade out over time
          particle.opacity = particleOpacity * (1 - lifePercent);
        }

        // Draw particle
        if (particle.opacity > 0) {
          ctx.beginPath();
          ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
          ctx.fillStyle = particle.color;
          ctx.globalAlpha = Math.max(0, particle.opacity);
          ctx.fill();
          ctx.globalAlpha = 1;
        }
      });

      // Draw DNA connections for helix state
      if (state.isActive && state.eventType === 'CYCLE_START') {
        const isDark = theme === 'dark';
        const linkColor = isDark ? 'rgba(59, 130, 246, 0.2)' : 'rgba(37, 99, 235, 0.2)';

        for (let i = 0; i < particlesRef.current.length - 1; i++) {
          const p1 = particlesRef.current[i];
          const p2 = particlesRef.current[i + 1];

          if (p1.state === 'helix' && p2.state === 'helix' && p1.strand !== p2.strand) {
            const dist = Math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2);

            if (dist < 100) {
              ctx.beginPath();
              ctx.moveTo(p1.x, p1.y);
              ctx.lineTo(p2.x, p2.y);
              ctx.strokeStyle = linkColor;
              ctx.globalAlpha = Math.max(0, (p1.opacity + p2.opacity) / 2 * (1 - dist / 100));
              ctx.lineWidth = 1;
              ctx.stroke();
              ctx.globalAlpha = 1;
            }
          }
        }
      }

      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [theme, particleOpacity, animationDuration]);

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
 * Hook to manually trigger evolution particles
 * Useful for integrating with existing evolution components
 */
export function useEvolutionParticles() {
  const triggerEvolution = useCallback((event: EvolutionEvent) => {
    // Dispatch custom event for EvolutionParticles component to listen to
    window.dispatchEvent(new CustomEvent<EvolutionEvent>('evolution-particles', { detail: event }));
  }, []);

  return { triggerEvolution };
}

/**
 * Default export for convenience
 */
export default EvolutionParticles;
