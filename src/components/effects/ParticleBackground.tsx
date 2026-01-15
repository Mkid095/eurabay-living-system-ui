/**
 * ParticleBackground Component
 *
 * Ambient particle background for visual appeal using tsparticles.
 * Features floating particles with mouse interaction and theme-aware styling.
 *
 * Features:
 * - Lightweight particle system for performance
 * - Floating particles with slow movement
 * - Mouse interaction (repel particles on hover)
 * - Theme colors (green particles on dark background)
 * - Configurable particle count, speed, size, and opacity
 * - Particle links (lines between nearby particles)
 * - Performance optimization (disable on low-end devices)
 * - Absolute positioning with inset-0
 * - Pointer-events-none to not block interactions
 */

'use client';

import React, { useCallback, useMemo, useState, useEffect } from 'react';
import Particles, { initParticlesEngine } from '@tsparticles/react';
import { type Container, type Engine } from '@tsparticles/engine';
import { loadSlim } from '@tsparticles/slim';
import { useTheme } from 'next-themes';

/**
 * Component props
 */
export interface ParticleBackgroundProps {
  /** Number of particles to display (default: 50) */
  particleCount?: number;
  /** Particle speed multiplier (default: 0.5) */
  particleSpeed?: number;
  /** Particle size range in pixels (default: 1-3) */
  particleSizeRange?: [number, number];
  /** Particle opacity (default: 0.3) */
  particleOpacity?: number;
  /** Distance to draw links between particles in pixels (default: 150) */
  linkDistance?: number;
  /** Link opacity (default: 0.2) */
  linkOpacity?: number;
  /** Enable mouse interaction (default: true) */
  enableMouseInteraction?: boolean;
  /** CSS class name for styling */
  className?: string;
  /** Enable performance optimization for low-end devices (default: true) */
  enablePerformanceOptimization?: boolean;
}

/**
 * Check if device is low-end for performance optimization
 */
function isLowEndDevice(): boolean {
  if (typeof window === 'undefined') return false;

  // Check hardware concurrency
  const cpuCores = navigator.hardwareConcurrency || 2;
  if (cpuCores <= 2) return true;

  // Check device memory (if available)
  const deviceMemory = (navigator as any).deviceMemory;
  if (deviceMemory && deviceMemory <= 2) return true;

  // Check for mobile devices
  const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
    navigator.userAgent
  );
  if (isMobile) return true;

  return false;
}

/**
 * Main ParticleBackground component
 */
export function ParticleBackground({
  particleCount = 50,
  particleSpeed = 0.5,
  particleSizeRange = [1, 3],
  particleOpacity = 0.3,
  linkDistance = 150,
  linkOpacity = 0.2,
  enableMouseInteraction = true,
  className = '',
  enablePerformanceOptimization = true,
}: ParticleBackgroundProps) {
  const [init, setInit] = useState(false);
  const { theme } = useTheme();
  const [isLowEnd, setIsLowEnd] = useState(false);

  // Initialize tsparticles engine
  useEffect(() => {
    let mounted = true;

    initParticlesEngine(async (engine: Engine) => {
      await loadSlim(engine);
      if (mounted) {
        setInit(true);
      }
    });

    return () => {
      mounted = false;
    };
  }, []);

  // Check device performance on mount
  useEffect(() => {
    if (enablePerformanceOptimization) {
      setIsLowEnd(isLowEndDevice());
    }
  }, [enablePerformanceOptimization]);

  // Particles loaded callback
  const particlesLoaded = useCallback(async (container?: Container): Promise<void> => {
    // Particles loaded successfully
  }, []);

  // Particle configuration optimized for performance and visual appeal
  const particlesConfig = useMemo(() => {
    // Disable particles on low-end devices if optimization is enabled
    if (enablePerformanceOptimization && isLowEnd) {
      return null;
    }

    const isDark = theme === 'dark';

    return {
      // Particle settings
      particles: {
        number: {
          value: particleCount,
          density: {
            enable: true,
            width: 800,
            height: 800,
          },
        },
        color: {
          value: isDark ? '#10b981' : '#059669', // Green theme color
        },
        shape: {
          type: 'circle' as const,
        },
        opacity: {
          value: particleOpacity,
          random: false,
          anim: {
            enable: false,
            speed: 1,
            opacity_min: 0.1,
            sync: false,
          },
        },
        size: {
          value: particleSizeRange[0],
          random: {
            enable: true,
            minimumValue: particleSizeRange[0],
            maximumValue: particleSizeRange[1],
          },
          anim: {
            enable: false,
            speed: 10,
            size_min: 0.1,
            sync: false,
          },
        },
        links: {
          enable: true,
          distance: linkDistance,
          color: isDark ? '#10b981' : '#059669',
          opacity: linkOpacity,
          width: 1,
          triangles: {
            enable: false,
          },
        },
        move: {
          enable: true,
          speed: particleSpeed,
          direction: 'none' as const,
          random: false,
          straight: false,
          outModes: {
            default: 'out' as const,
          },
          attract: {
            enable: false,
            rotateX: 600,
            rotateY: 1200,
          },
        },
      },
      // Interactivity
      interactivity: {
        events: {
          onHover: {
            enable: enableMouseInteraction,
            mode: 'repulse' as const,
          },
          onClick: {
            enable: false,
            mode: 'push' as const,
          },
          resize: {
            enable: true,
          },
        },
        modes: {
          repulse: {
            distance: 100,
            duration: 0.4,
          },
          push: {
            quantity: 4,
          },
        },
      },
      // Detect retina displays
      detectRetina: true,
      // Background color (transparent to let theme background show)
      background: {
        color: 'transparent',
      },
    };
  }, [
    particleCount,
    particleSpeed,
    particleSizeRange,
    particleOpacity,
    linkDistance,
    linkOpacity,
    enableMouseInteraction,
    enablePerformanceOptimization,
    isLowEnd,
    theme,
  ]);

  // Don't render if not initialized or if low-end device with optimization
  if (!init || particlesConfig === null) {
    return null;
  }

  const containerStyle: React.CSSProperties = useMemo(
    () => ({
      position: 'absolute',
      inset: 0,
      width: '100%',
      height: '100%',
      pointerEvents: 'none',
      zIndex: 0,
    }),
    []
  );

  return (
    <div style={containerStyle} className={className}>
      <Particles
        id="tsparticles"
        particlesLoaded={particlesLoaded}
        options={particlesConfig}
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
        }}
      />
    </div>
  );
}

/**
 * Default export for convenience
 */
export default ParticleBackground;
