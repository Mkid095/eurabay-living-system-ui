/**
 * InteractiveCharts3D Component
 *
 * Interactive 3D charts for feature analysis and optimization landscape:
 * - 3D scatter plot for feature analysis
 * - 3D surface plot for optimization landscape
 * - Interactive tooltips on hover
 * - Click to drill down to feature detail
 * - View toggle (2D/3D)
 * - Loading skeleton and error state with fallback to 2D
 *
 * Features:
 * - Map features to X, Y, Z axes
 * - Color points by success rate
 * - Size points by usage count
 * - Display fitness function as height map
 * - Support rotation, zoom, pan
 * - Synchronize with 2D charts where applicable
 */

'use client';

import React, { Suspense, useCallback, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Html, Text, Grid, Line } from '@react-three/drei';
import { Mesh, Group, Vector3 } from 'three';
import * as THREE from 'three';

/**
 * Feature data structure for scatter plot
 */
export interface FeatureData {
  id: string;
  name: string;
  x: number;
  y: number;
  z: number;
  successRate: number;
  usageCount: number;
  description?: string;
  category?: string;
}

/**
 * Optimization landscape data structure for surface plot
 */
export interface OptimizationLandscape {
  points: Array<{
    x: number;
    y: number;
    z: number;
    fitness: number;
  }>;
  width: number;
  height: number;
  resolution?: number;
}

/**
 * Component props
 */
export interface InteractiveCharts3DProps {
  /** Feature data for scatter plot */
  features?: FeatureData[];
  /** Optimization landscape data for surface plot */
  landscape?: OptimizationLandscape;
  /** Whether the component is loading data */
  isLoading?: boolean;
  /** Error message if data loading failed */
  error?: string | null;
  /** Height of the canvas container */
  height?: string | number;
  /** CSS class name for styling */
  className?: string;
  /** Callback when feature is clicked */
  onFeatureClick?: (feature: FeatureData) => void;
  /** Callback when view mode changes */
  onViewModeChange?: (mode: '2d' | '3d') => void;
  /** Initial view mode */
  initialViewMode?: '2d' | '3d';
  /** Chart type to display */
  chartType?: 'scatter' | 'surface' | 'both';
}

/**
 * Get color based on success rate
 */
function getSuccessRateColor(successRate: number): string {
  if (successRate >= 0.7) return '#10b981';
  if (successRate >= 0.5) return '#3b82f6';
  if (successRate >= 0.3) return '#f59e0b';
  return '#ef4444';
}

/**
 * 3D Scatter point component
 */
function ScatterPoint3D({
  data,
  onHover,
  onClick
}: {
  data: FeatureData;
  onHover?: (id: string | null) => void;
  onClick?: (data: FeatureData) => void;
}) {
  const meshRef = useRef<Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const color = getSuccessRateColor(data.successRate);
  const size = 0.2 + (data.usageCount / 100) * 0.5;

  const handlePointerOver = useCallback(() => {
    setHovered(true);
    onHover?.(data.id);
  }, [data.id, onHover]);

  const handlePointerOut = useCallback(() => {
    setHovered(false);
    onHover?.(null);
  }, [onHover]);

  const handleClick = useCallback(() => {
    onClick?.(data);
  }, [data, onClick]);

  useFrame((state) => {
    if (meshRef.current && hovered) {
      meshRef.current.rotation.y = state.clock.elapsedTime * 2;
    }
  });

  return (
    <group position={[data.x, data.y, data.z]}>
      <mesh
        ref={meshRef}
        scale={hovered ? size * 1.5 : size}
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
        onClick={handleClick}
      >
        <sphereGeometry args={[1, 16, 16]} />
        <meshStandardMaterial
          color={hovered ? '#ffffff' : color}
          emissive={color}
          emissiveIntensity={hovered ? 0.8 : 0.4}
          metalness={0.3}
          roughness={0.4}
          transparent
          opacity={0.9}
        />
      </mesh>

      {/* Tooltip on hover */}
      {hovered && (
        <Html position={[0, size + 0.5, 0]} center distanceFactor={10}>
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.95)',
              border: `2px solid ${color}`,
              borderRadius: '8px',
              padding: '12px',
              color: '#f1f5f9',
              fontFamily: 'system-ui, -apple-system, sans-serif',
              fontSize: '13px',
              minWidth: '200px',
              maxWidth: '280px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
              pointerEvents: 'none',
            }}
          >
            <div
              style={{
                fontWeight: 600,
                marginBottom: '8px',
                fontSize: '14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <span>{data.name}</span>
              {data.category && (
                <span
                  style={{
                    fontSize: '10px',
                    background: '#334155',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    textTransform: 'uppercase',
                  }}
                >
                  {data.category}
                </span>
              )}
            </div>

            {data.description && (
              <div
                style={{
                  fontSize: '11px',
                  color: '#94a3b8',
                  marginBottom: '10px',
                  lineHeight: '1.4',
                }}
              >
                {data.description}
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div
                style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}
              >
                <span style={{ color: '#94a3b8' }}>Success Rate:</span>
                <span style={{ color, fontWeight: 600 }}>
                  {(data.successRate * 100).toFixed(1)}%
                </span>
              </div>
              <div
                style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}
              >
                <span style={{ color: '#94a3b8' }}>Usage Count:</span>
                <span style={{ fontWeight: 600 }}>{data.usageCount}</span>
              </div>
              <div
                style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px' }}
              >
                <span style={{ color: '#94a3b8' }}>Position:</span>
                <span style={{ fontFamily: 'monospace', fontSize: '11px' }}>
                  ({data.x.toFixed(1)}, {data.y.toFixed(1)}, {data.z.toFixed(1)})
                </span>
              </div>
            </div>

            <div
              style={{
                marginTop: '10px',
                padding: '6px',
                background: 'rgba(59, 130, 246, 0.1)',
                borderRadius: '4px',
                fontSize: '11px',
                color: '#60a5fa',
                textAlign: 'center',
                fontWeight: 500,
              }}
            >
              Click for details
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}

/**
 * 3D Surface plot component for optimization landscape
 */
function SurfacePlot3D({
  data,
  onHover
}: {
  data: OptimizationLandscape;
  onHover?: (point: { x: number; y: number; z: number; fitness: number } | null) => void;
}) {
  const meshRef = useRef<Mesh>(null);
  const [hoveredPoint, setHoveredPoint] = useState<Vector3 | null>(null);
  const resolution = data.resolution || 30;

  const geometry = useMemo(() => {
    const geo = new THREE.PlaneGeometry(data.width, data.height, resolution, resolution);
    const positions = geo.attributes.position.array as Float32Array;

    for (let i = 0; i < positions.length; i += 3) {
      const x = positions[i];
      const y = positions[i + 1];

      const point = data.points.find(p =>
        Math.abs(p.x - x) < 0.3 && Math.abs(p.y - y) < 0.3
      );

      if (point) {
        positions[i + 2] = point.z;
      }
    }

    geo.computeVertexNormals();
    return geo;
  }, [data, resolution]);

  const { colorArray, maxFitness } = useMemo(() => {
    const arr: number[] = [];
    let maxFit = 0;

    for (let i = 0; i < data.points.length; i++) {
      const value = data.points[i].fitness;
      maxFit = Math.max(maxFit, value);
    }

    for (let i = 0; i < data.points.length; i++) {
      const value = data.points[i].fitness;
      const normalizedValue = value / maxFit;
      const hue = 0.7 - normalizedValue * 0.5;
      const color = new THREE.Color().setHSL(hue, 0.9, 0.5);
      arr.push(color.r, color.g, color.b);
    }

    return { colorArray: new Float32Array(arr), maxFitness: maxFit };
  }, [data]);

  const handlePointerMove = useCallback((e: any) => {
    setHoveredPoint(e.point);
    const point = data.points.find(p =>
      Math.abs(p.x - e.point.x) < 0.5 &&
      Math.abs(p.y - (-e.point.z)) < 0.5
    );
    if (point) {
      onHover?.({ ...point, z: e.point.y });
    }
  }, [data.points, onHover]);

  const handlePointerOut = useCallback(() => {
    setHoveredPoint(null);
    onHover?.(null);
  }, [onHover]);

  return (
    <group>
      <mesh
        ref={meshRef}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, 0, 0]}
        onPointerMove={handlePointerMove}
        onPointerOut={handlePointerOut}
      >
        <planeGeometry args={[data.width, data.height, resolution, resolution]} />
        <meshStandardMaterial
          color="#3b82f6"
          emissive="#1e40af"
          emissiveIntensity={0.2}
          metalness={0.4}
          roughness={0.4}
          wireframe={false}
          side={THREE.DoubleSide}
          transparent
          opacity={0.85}
        />
      </mesh>

      {/* Color gradient overlay based on fitness */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.02, 0]}>
        <planeGeometry args={[data.width, data.height, resolution, resolution]} />
        <meshBasicMaterial
          vertexColors
          transparent
          opacity={0.6}
        />
      </mesh>

      {/* Wireframe overlay */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.03, 0]}>
        <planeGeometry args={[data.width, data.height, resolution / 2, resolution / 2]} />
        <meshBasicMaterial
          color="#60a5fa"
          wireframe
          transparent
          opacity={0.2}
        />
      </mesh>

      {/* Peak marker */}
      {data.points.reduce((max, p) => p.fitness > max.fitness ? p : max, data.points[0]) && (
        <PeakMarker
          point={data.points.reduce((max, p) => p.fitness > max.fitness ? p : max, data.points[0])}
        />
      )}

      {hoveredPoint && (
        <mesh position={[hoveredPoint.x, hoveredPoint.y + 0.5, -hoveredPoint.z]}>
          <sphereGeometry args={[0.2, 8, 8]} />
          <meshStandardMaterial
            color="#ffffff"
            emissive="#ffffff"
            emissiveIntensity={0.8}
          />
        </mesh>
      )}
    </group>
  );
}

/**
 * Peak marker component
 */
function PeakMarker({ point }: { point: { x: number; y: number; z: number; fitness: number } }) {
  const [hovered, setHovered] = useState(false);

  return (
    <group position={[point.x, point.z, -point.y]}>
      <mesh
        scale={hovered ? 0.4 : 0.3}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <coneGeometry args={[1, 2, 4]} />
        <meshStandardMaterial
          color="#f59e0b"
          emissive="#f59e0b"
          emissiveIntensity={0.6}
        />
      </mesh>

      {hovered && (
        <Html position={[0, 1.5, 0]} center distanceFactor={10}>
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.95)',
              border: '2px solid #f59e0b',
              borderRadius: '8px',
              padding: '10px',
              color: '#f1f5f9',
              fontFamily: 'system-ui, -apple-system, sans-serif',
              fontSize: '12px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
              pointerEvents: 'none',
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: '4px' }}>Global Maximum</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px' }}>
              <span style={{ color: '#94a3b8' }}>Fitness:</span>
              <span style={{ color: '#10b981', fontWeight: 600 }}>
                {point.fitness.toFixed(3)}
              </span>
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}

/**
 * Scene component with all visualizations
 */
function Scene({
  features,
  landscape,
  chartType,
  hoveredFeature,
  onFeatureHover,
  onFeatureClick,
  onLandscapeHover
}: {
  features: FeatureData[];
  landscape: OptimizationLandscape;
  chartType: 'scatter' | 'surface' | 'both';
  hoveredFeature: string | null;
  onFeatureHover: (id: string | null) => void;
  onFeatureClick: (feature: FeatureData) => void;
  onLandscapeHover: (point: { x: number; y: number; z: number; fitness: number } | null) => void;
}) {
  const { camera } = useThree();

  return (
    <>
      {/* Ambient light */}
      <ambientLight intensity={0.4} />

      {/* Main directional light */}
      <directionalLight
        position={[10, 10, 10]}
        intensity={1.2}
        castShadow
        color="#ffffff"
      />

      {/* Fill light */}
      <directionalLight
        position={[-10, 5, -10]}
        intensity={0.6}
        color="#4a5568"
      />

      {/* Ground grid */}
      <Grid
        args={[20, 20]}
        cellSize={1}
        cellThickness={0.5}
        cellColor="#1e293b"
        sectionSize={5}
        sectionThickness={1}
        sectionColor="#334155"
        fadeDistance={25}
        fadeStrength={1}
        followCamera={false}
        infiniteGrid
      />

      {/* Axis labels */}
      <Text
        position={[10, 0, 0]}
        fontSize={0.4}
        color="#64748b"
        anchorX="center"
        anchorY="middle"
      >
        X
      </Text>
      <Text
        position={[0, 10, 0]}
        fontSize={0.4}
        color="#64748b"
        anchorX="center"
        anchorY="middle"
      >
        Y
      </Text>
      <Text
        position={[0, 0, 10]}
        fontSize={0.4}
        color="#64748b"
        anchorX="center"
        anchorY="middle"
      >
        Z
      </Text>

      {/* Scatter plot */}
      {(chartType === 'scatter' || chartType === 'both') && (
        <group position={[0, 2, 0]}>
          {features.map((feature) => (
            <ScatterPoint3D
              key={feature.id}
              data={feature}
              onHover={onFeatureHover}
              onClick={onFeatureClick}
            />
          ))}
        </group>
      )}

      {/* Surface plot */}
      {(chartType === 'surface' || chartType === 'both') && (
        <group position={[0, -2, 0]}>
          <SurfacePlot3D data={landscape} onHover={onLandscapeHover} />
        </group>
      )}

      {/* Orbit controls */}
      <OrbitControls
        enableDamping
        dampingFactor={0.05}
        rotateSpeed={0.5}
        zoomSpeed={0.8}
        minDistance={5}
        maxDistance={25}
        enablePan={true}
        panSpeed={0.5}
      />
    </>
  );
}

/**
 * 2D fallback scatter plot
 */
function ScatterPlot2D({
  features,
  onFeatureClick
}: {
  features: FeatureData[];
  onFeatureClick?: (feature: FeatureData) => void;
}) {
  const svgWidth = 800;
  const svgHeight = 500;
  const padding = 60;

  const xScale = (val: number) =>
    padding + ((val + 10) / 20) * (svgWidth - 2 * padding);
  const yScale = (val: number) =>
    svgHeight - padding - ((val + 10) / 20) * (svgHeight - 2 * padding);

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: '#0f172a',
        borderRadius: '12px',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <svg
        width="100%"
        height="100%"
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        style={{ maxHeight: '500px' }}
      >
        {/* Grid lines */}
        {[0, 1, 2, 3, 4, 5].map((i) => {
          const x = padding + (i / 5) * (svgWidth - 2 * padding);
          return (
            <line
              key={`v-${i}`}
              x1={x}
              y1={padding}
              x2={x}
              y2={svgHeight - padding}
              stroke="#1e293b"
              strokeWidth="1"
            />
          );
        })}
        {[0, 1, 2, 3, 4, 5].map((i) => {
          const y = padding + (i / 5) * (svgHeight - 2 * padding);
          return (
            <line
              key={`h-${i}`}
              x1={padding}
              y1={y}
              x2={svgWidth - padding}
              y2={y}
              stroke="#1e293b"
              strokeWidth="1"
            />
          );
        })}

        {/* Axes */}
        <line
          x1={padding}
          y1={svgHeight - padding}
          x2={svgWidth - padding}
          y2={svgHeight - padding}
          stroke="#64748b"
          strokeWidth="2"
        />
        <line
          x1={padding}
          y1={padding}
          x2={padding}
          y2={svgHeight - padding}
          stroke="#64748b"
          strokeWidth="2"
        />

        {/* Axis labels */}
        <text
          x={svgWidth / 2}
          y={svgHeight - 15}
          fill="#94a3b8"
          fontSize="14"
          textAnchor="middle"
          fontFamily="system-ui, -apple-system, sans-serif"
        >
          Feature Value (X)
        </text>
        <text
          x={15}
          y={svgHeight / 2}
          fill="#94a3b8"
          fontSize="14"
          textAnchor="middle"
          fontFamily="system-ui, -apple-system, sans-serif"
          transform={`rotate(-90, 15, ${svgHeight / 2})`}
        >
          Performance (Y)
        </text>

        {/* Data points */}
        {features.map((feature) => {
          const cx = xScale(feature.x);
          const cy = yScale(feature.y);
          const r = 6 + (feature.usageCount / 100) * 12;
          const color = getSuccessRateColor(feature.successRate);

          return (
            <g key={feature.id}>
              <circle
                cx={cx}
                cy={cy}
                r={r}
                fill={color}
                fillOpacity="0.7"
                stroke={color}
                strokeWidth="2"
                style={{ cursor: 'pointer' }}
                onClick={() => onFeatureClick?.(feature)}
              />
            </g>
          );
        })}
      </svg>

      {/* Legend */}
      <div
        style={{
          display: 'flex',
          gap: '24px',
          marginTop: '16px',
          fontSize: '12px',
          color: '#94a3b8',
          fontFamily: 'system-ui, -apple-system, sans-serif',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#10b981' }} />
          <span>High Success (&ge;70%)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#3b82f6' }} />
          <span>Good Success (50-70%)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#f59e0b' }} />
          <span>Low Success (30-50%)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: '#ef4444' }} />
          <span>Poor Success (&lt;30%)</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Loading skeleton component
 */
function LoadingSkeleton() {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#0f172a',
        borderRadius: '12px',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '16px',
        }}
      >
        <div
          style={{
            width: '48px',
            height: '48px',
            border: '3px solid #1e40af',
            borderTopColor: '#3b82f6',
            borderRadius: '50%',
            animation: 'spin 1s linear infinite',
          }}
        />
        <div
          style={{
            color: '#94a3b8',
            fontSize: '14px',
            fontWeight: 500,
            fontFamily: 'system-ui, -apple-system, sans-serif',
          }}
        >
          Loading 3D Charts...
        </div>
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    </div>
  );
}

/**
 * Error state component
 */
function ErrorState({ error }: { error: string }) {
  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#1a0f0f',
        borderRadius: '12px',
        border: '1px solid #7f1d1d',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '12px',
          padding: '24px',
          maxWidth: '320px',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            width: '48px',
            height: '48px',
            borderRadius: '50%',
            background: '#7f1d1d',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fca5a5',
            fontSize: '24px',
            fontWeight: 600,
          }}
        >
          !
        </div>
        <div
          style={{
            color: '#fca5a5',
            fontSize: '16px',
            fontWeight: 600,
            fontFamily: 'system-ui, -apple-system, sans-serif',
          }}
        >
          Failed to Load Charts
        </div>
        <div
          style={{
            color: '#d4a5a5',
            fontSize: '13px',
            fontFamily: 'system-ui, -apple-system, sans-serif',
            lineHeight: '1.5',
          }}
        >
          {error}
        </div>
      </div>
    </div>
  );
}

/**
 * Main InteractiveCharts3D component
 */
export function InteractiveCharts3D({
  features,
  landscape,
  isLoading = false,
  error = null,
  height = '600px',
  className = '',
  onFeatureClick,
  onViewModeChange,
  initialViewMode = '3d',
  chartType = 'both',
}: InteractiveCharts3DProps) {
  const [viewMode, setViewMode] = useState<'2d' | '3d'>(initialViewMode);
  const [hoveredFeature, setHoveredFeature] = useState<string | null>(null);
  const [hoveredLandscape, setHoveredLandscape] = useState<{
    x: number;
    y: number;
    z: number;
    fitness: number;
  } | null>(null);

  const containerStyle: React.CSSProperties = useMemo(
    () => ({
      width: '100%',
      height: typeof height === 'number' ? `${height}px` : height,
      position: 'relative' as const,
      borderRadius: '12px',
      overflow: 'hidden',
    }),
    [height]
  );

  const defaultFeatures: FeatureData[] = useMemo(
    () =>
      Array.from({ length: 20 }, (_, i) => ({
        id: `feature-${i}`,
        name: `Feature ${i + 1}`,
        x: (Math.random() - 0.5) * 20,
        y: (Math.random() - 0.5) * 20,
        z: (Math.random() - 0.5) * 20,
        successRate: Math.random(),
        usageCount: Math.floor(Math.random() * 100),
        description: `Analysis feature ${i + 1} for performance tracking`,
        category: ['Technical', 'Fundamental', 'Sentiment'][i % 3],
      })),
    []
  );

  const defaultLandscape: OptimizationLandscape = useMemo(
    () => ({
      points: Array.from({ length: 400 }, (_, i) => {
        const x = (i % 20) - 10;
        const y = Math.floor(i / 20) - 10;
        const z = Math.sin(x * 0.3) * 3 + Math.cos(y * 0.3) * 3;
        const fitness = (z + 6) / 12;
        return { x, y, z, fitness };
      }),
      width: 20,
      height: 20,
      resolution: 30,
    }),
    []
  );

  const displayFeatures = features ?? defaultFeatures;
  const displayLandscape = landscape ?? defaultLandscape;

  const handleViewModeChange = useCallback(
    (mode: '2d' | '3d') => {
      setViewMode(mode);
      onViewModeChange?.(mode);
    },
    [onViewModeChange]
  );

  const handleFeatureClick = useCallback(
    (feature: FeatureData) => {
      onFeatureClick?.(feature);
    },
    [onFeatureClick]
  );

  const handleExportImage = useCallback(() => {
    const canvas = document.querySelector('canvas');
    if (canvas) {
      const link = document.createElement('a');
      link.download = `interactive-charts-${Date.now()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    }
  }, []);

  // Show loading state
  if (isLoading) {
    return <div style={containerStyle}>{isLoading && <LoadingSkeleton />}</div>;
  }

  // Show error state with 2D fallback
  if (error) {
    return (
      <div style={containerStyle} className={className}>
        <ScatterPlot2D features={displayFeatures} onFeatureClick={handleFeatureClick} />
      </div>
    );
  }

  // Determine if showing 2D or 3D view
  const is2DView = viewMode === '2d';

  return (
    <div style={containerStyle} className={className}>
      {/* View toggle */}
      <div
        style={{
          position: 'absolute',
          top: '16px',
          right: '16px',
          zIndex: 10,
          display: 'flex',
          gap: '8px',
          background: 'rgba(15, 23, 42, 0.9)',
          backdropFilter: 'blur(8px)',
          border: '1px solid #334155',
          borderRadius: '8px',
          padding: '6px',
          fontFamily: 'system-ui, -apple-system, sans-serif',
        }}
      >
        <button
          onClick={() => handleViewModeChange('2d')}
          style={{
            background: is2DView ? '#3b82f6' : 'transparent',
            color: '#f1f5f9',
            border: 'none',
            borderRadius: '4px',
            padding: '6px 12px',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => {
            if (!is2DView) {
              e.currentTarget.style.background = '#1e293b';
            }
          }}
          onMouseLeave={(e) => {
            if (!is2DView) {
              e.currentTarget.style.background = 'transparent';
            }
          }}
        >
          2D View
        </button>
        <button
          onClick={() => handleViewModeChange('3d')}
          style={{
            background: !is2DView ? '#3b82f6' : 'transparent',
            color: '#f1f5f9',
            border: 'none',
            borderRadius: '4px',
            padding: '6px 12px',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.2s',
          }}
          onMouseEnter={(e) => {
            if (is2DView) {
              e.currentTarget.style.background = '#1e293b';
            }
          }}
          onMouseLeave={(e) => {
            if (is2DView) {
              e.currentTarget.style.background = 'transparent';
            }
          }}
        >
          3D View
        </button>
      </div>

      {/* 2D View */}
      {is2DView ? (
        <ScatterPlot2D features={displayFeatures} onFeatureClick={handleFeatureClick} />
      ) : null}

      {/* 3D View */}
      {!is2DView ? (
        <>
          {/* Export button */}
          <button
            onClick={handleExportImage}
            style={{
              position: 'absolute',
              bottom: '16px',
              right: '16px',
              zIndex: 10,
              background: '#3b82f6',
              color: '#ffffff',
              border: 'none',
              borderRadius: '8px',
              padding: '8px 16px',
              fontSize: '12px',
              fontWeight: 600,
              cursor: 'pointer',
              fontFamily: 'system-ui, -apple-system, sans-serif',
              transition: 'all 0.2s',
              boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#2563eb';
              e.currentTarget.style.transform = 'translateY(-1px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#3b82f6';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            Export Image
          </button>

          {/* Legend */}
          <div
            style={{
              position: 'absolute',
              top: '16px',
              left: '16px',
              zIndex: 10,
              background: 'rgba(15, 23, 42, 0.9)',
              backdropFilter: 'blur(8px)',
              border: '1px solid #334155',
              borderRadius: '8px',
              padding: '12px',
              fontFamily: 'system-ui, -apple-system, sans-serif',
            }}
          >
            <div
              style={{
                color: '#f1f5f9',
                fontSize: '12px',
                fontWeight: 600,
                marginBottom: '8px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Success Rate
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} />
                <span style={{ fontSize: '11px', color: '#94a3b8' }}>High (&ge;70%)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#3b82f6' }} />
                <span style={{ fontSize: '11px', color: '#94a3b8' }}>Good (50-70%)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b' }} />
                <span style={{ fontSize: '11px', color: '#94a3b8' }}>Low (30-50%)</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ef4444' }} />
                <span style={{ fontSize: '11px', color: '#94a3b8' }}>Poor (&lt;30%)</span>
              </div>
            </div>

            <div
              style={{
                marginTop: '12px',
                paddingTop: '8px',
                borderTop: '1px solid #334155',
                color: '#f1f5f9',
                fontSize: '12px',
                fontWeight: 600,
                marginBottom: '8px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Point Size
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>Based on usage count</div>

            <div
              style={{
                marginTop: '12px',
                paddingTop: '8px',
                borderTop: '1px solid #334155',
                color: '#f1f5f9',
                fontSize: '12px',
                fontWeight: 600,
                marginBottom: '8px',
                textTransform: 'uppercase',
                letterSpacing: '0.05em',
              }}
            >
              Visualizations
            </div>
            <div style={{ fontSize: '11px', color: '#94a3b8' }}>
              {chartType === 'scatter' && 'Scatter Plot'}
              {chartType === 'surface' && 'Optimization Surface'}
              {chartType === 'both' && 'Scatter + Surface'}
            </div>
          </div>

          {/* Controls hint */}
          <div
            style={{
              position: 'absolute',
              bottom: '16px',
              left: '16px',
              background: 'rgba(15, 23, 42, 0.9)',
              backdropFilter: 'blur(8px)',
              border: '1px solid #334155',
              borderRadius: '8px',
              padding: '8px 12px',
              fontSize: '11px',
              color: '#64748b',
              fontFamily: 'system-ui, -apple-system, sans-serif',
              zIndex: 10,
            }}
          >
            Drag to rotate • Scroll to zoom • Right-click to pan • Click point for details
          </div>

          <Canvas
            camera={{ position: [12, 10, 12], fov: 45 }}
            gl={{
              antialias: true,
              alpha: true,
              powerPreference: 'high-performance',
              preserveDrawingBuffer: true,
            }}
            dpr={[1, 2]}
            performance={{ min: 0.5 }}
          >
            <Suspense fallback={null}>
              <Scene
                features={displayFeatures}
                landscape={displayLandscape}
                chartType={chartType}
                hoveredFeature={hoveredFeature}
                onFeatureHover={setHoveredFeature}
                onFeatureClick={handleFeatureClick}
                onLandscapeHover={setHoveredLandscape}
              />
            </Suspense>
          </Canvas>
        </>
      ) : null}
    </div>
  );
}

/**
 * Default export for convenience
 */
export default InteractiveCharts3D;
