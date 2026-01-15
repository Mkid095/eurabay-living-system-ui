/**
 * PerformanceMetrics3D Component
 *
 * 3D visualization for system performance metrics including:
 * - 3D bar chart for performance metrics (return, Sharpe, max drawdown, win rate)
 * - 3D surface plot for equity growth
 * - 3D timeline for generation progression
 *
 * Features:
 * - Interactive 3D charts with rotation, zoom, and pan
 * - Color-coded bars by value (green=good, red=bad)
 * - Height labels on bars
 * - Export 3D scene as image
 * - View controls (reset, top, front, side)
 * - Loading and error states
 */

'use client';

import React, { Suspense, useCallback, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Html, Text, Grid, Line } from '@react-three/drei';
import { Mesh, Group, Vector3 } from 'three';
import * as THREE from 'three';

/**
 * Performance metrics data structure
 */
export interface PerformanceMetrics {
  totalReturn: number;
  sharpeRatio: number;
  maxDrawdown: number;
  winRate: number;
}

/**
 * Bar chart data structure
 */
export interface BarData {
  id: string;
  label: string;
  value: number;
  color: string;
  position: [number, number, number];
  targetValue?: number;
  threshold?: {
    good: number;
    bad: number;
  };
}

/**
 * Surface plot data structure for equity growth
 */
export interface SurfaceData {
  points: Array<{
    x: number;
    y: number;
    z: number;
  }>;
  width: number;
  height: number;
}

/**
 * Timeline data structure for generation progression
 */
export interface TimelineData {
  id: string;
  label: string;
  value: number;
  generation: number;
  position: [number, number, number];
  timestamp: number;
}

/**
 * Component props
 */
export interface PerformanceMetrics3DProps {
  /** Performance metrics to visualize */
  metrics?: PerformanceMetrics;
  /** Equity growth data for surface plot */
  equityData?: SurfaceData;
  /** Generation progression data for timeline */
  timelineData?: TimelineData[];
  /** Whether the component is loading data */
  isLoading?: boolean;
  /** Error message if data loading failed */
  error?: string | null;
  /** Height of the canvas container */
  height?: string | number;
  /** CSS class name for styling */
  className?: string;
}

/**
 * Default performance metrics thresholds
 */
const DEFAULT_THRESHOLDS = {
  totalReturn: { good: 10, bad: 0 },
  sharpeRatio: { good: 2, bad: 1 },
  maxDrawdown: { good: -10, bad: -25 },
  winRate: { good: 60, bad: 40 },
};

/**
 * Get color based on value thresholds
 */
function getValueColor(value: number, threshold: { good: number; bad: number }): string {
  if (threshold.good > threshold.bad) {
    if (value >= threshold.good) return '#10b981';
    if (value <= threshold.bad) return '#ef4444';
    return '#f59e0b';
  } else {
    if (value <= threshold.good) return '#10b981';
    if (value >= threshold.bad) return '#ef4444';
    return '#f59e0b';
  }
}

/**
 * 3D Bar component with height label
 */
function Bar3D({
  data,
  onHover
}: {
  data: BarData;
  onHover?: (id: string | null) => void;
}) {
  const meshRef = useRef<Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const color = hovered ? '#ffffff' : data.color;
  const height = Math.max(Math.abs(data.value), 0.1);
  const yPos = height / 2;

  const handlePointerOver = useCallback(() => {
    setHovered(true);
    onHover?.(data.id);
  }, [data.id, onHover]);

  const handlePointerOut = useCallback(() => {
    setHovered(false);
    onHover?.(null);
  }, [onHover]);

  return (
    <group position={data.position}>
      <mesh
        ref={meshRef}
        position={[0, yPos, 0]}
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
      >
        <boxGeometry args={[0.8, height, 0.8]} />
        <meshStandardMaterial
          color={color}
          emissive={data.color}
          emissiveIntensity={hovered ? 0.5 : 0.2}
          metalness={0.3}
          roughness={0.4}
          transparent
          opacity={0.9}
        />
      </mesh>

      {/* Height label */}
      <Text
        position={[0, height + 0.3, 0]}
        fontSize={0.3}
        color="#f1f5f9"
        anchorX="center"
        anchorY="middle"
        outlineWidth={0.02}
        outlineColor="#0f172a"
      >
        {data.value.toFixed(2)}
      </Text>

      {/* Label below bar */}
      <Text
        position={[0, -0.3, 0]}
        fontSize={0.2}
        color="#94a3b8"
        anchorX="center"
        anchorY="middle"
      >
        {data.label}
      </Text>

      {/* Tooltip on hover */}
      {hovered && (
        <Html position={[0, height + 0.8, 0]} center distanceFactor={8}>
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.95)',
              border: `1px solid ${data.color}`,
              borderRadius: '8px',
              padding: '12px',
              color: '#f1f5f9',
              fontFamily: 'system-ui, -apple-system, sans-serif',
              fontSize: '13px',
              minWidth: '160px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
              pointerEvents: 'none',
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: '8px', fontSize: '14px' }}>
              {data.label}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#94a3b8' }}>Value:</span>
              <span style={{ color: data.color, fontWeight: 600 }}>
                {data.value.toFixed(2)}
              </span>
            </div>
            {data.threshold && (
              <div style={{ marginTop: '8px', fontSize: '11px', color: '#64748b' }}>
                Good: {data.threshold.good} | Bad: {data.threshold.bad}
              </div>
            )}
          </div>
        </Html>
      )}
    </group>
  );
}

/**
 * 3D Surface plot component for equity growth
 */
function SurfacePlot3D({
  data,
  onHover
}: {
  data: SurfaceData;
  onHover?: (point: { x: number; y: number; z: number } | null) => void;
}) {
  const meshRef = useRef<Mesh>(null);
  const [hoveredPoint, setHoveredPoint] = useState<Vector3 | null>(null);

  const geometry = useMemo(() => {
    const geo = new THREE.PlaneGeometry(data.width, data.height, 20, 20);
    const positions = geo.attributes.position.array as Float32Array;

    for (let i = 0; i < positions.length; i += 3) {
      const x = positions[i];
      const y = positions[i + 1];

      const point = data.points.find(p =>
        Math.abs(p.x - x) < 0.5 && Math.abs(p.y - y) < 0.5
      );

      if (point) {
        positions[i + 2] = point.z;
      }
    }

    geo.computeVertexNormals();
    return geo;
  }, [data]);

  const colors = useMemo(() => {
    const colorArray: number[] = [];
    const points = data.points;

    for (let i = 0; i < points.length; i++) {
      const value = points[i].z;
      const normalizedValue = (value + 10) / 20;
      const color = new THREE.Color().setHSL(0.3 - normalizedValue * 0.3, 0.8, 0.5);
      colorArray.push(color.r, color.g, color.b);
    }

    return new Float32Array(colorArray);
  }, [data]);

  return (
    <group>
      <mesh
        ref={meshRef}
        rotation={[-Math.PI / 2, 0, 0]}
        position={[0, 0, 0]}
        onPointerMove={(e) => {
          setHoveredPoint(e.point);
          onHover?.({ x: e.point.x, y: e.point.y, z: e.point.z });
        }}
        onPointerOut={() => {
          setHoveredPoint(null);
          onHover?.(null);
        }}
      >
        <planeGeometry args={[data.width, data.height, 20, 20]} />
        <meshStandardMaterial
          color="#3b82f6"
          emissive="#1e40af"
          emissiveIntensity={0.2}
          metalness={0.5}
          roughness={0.3}
          wireframe={false}
          side={THREE.DoubleSide}
          transparent
          opacity={0.8}
        />
      </mesh>

      {/* Wireframe overlay */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.01, 0]}>
        <planeGeometry args={[data.width, data.height, 10, 10]} />
        <meshBasicMaterial
          color="#60a5fa"
          wireframe
          transparent
          opacity={0.3}
        />
      </mesh>

      {hoveredPoint && (
        <mesh position={[hoveredPoint.x, hoveredPoint.z + 0.5, hoveredPoint.y]}>
          <sphereGeometry args={[0.15, 8, 8]} />
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
 * 3D Timeline component for generation progression
 */
function Timeline3D({
  data,
  onHover
}: {
  data: TimelineData[];
  onHover?: (id: string | null) => void;
}) {
  const groupRef = useRef<Group>(null);

  const linePoints = useMemo(() => {
    return data.map(d => new THREE.Vector3(...d.position));
  }, [data]);

  return (
    <group ref={groupRef}>
      {/* Timeline path */}
      <Line
        points={linePoints.map(p => [p.x, p.y, p.z] as [number, number, number])}
        color="#3b82f6"
        lineWidth={2}
      />

      {/* Timeline markers */}
      {data.map((item) => (
        <TimelineMarker
          key={item.id}
          data={item}
          onHover={onHover}
        />
      ))}
    </group>
  );
}

/**
 * Individual timeline marker
 */
function TimelineMarker({
  data,
  onHover
}: {
  data: TimelineData;
  onHover?: (id: string | null) => void;
}) {
  const meshRef = useRef<Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const size = 0.3 + (data.value / 100) * 0.3;
  const color = data.value >= 0 ? '#10b981' : '#ef4444';

  const handlePointerOver = useCallback(() => {
    setHovered(true);
    onHover?.(data.id);
  }, [data.id, onHover]);

  const handlePointerOut = useCallback(() => {
    setHovered(false);
    onHover?.(null);
  }, [onHover]);

  return (
    <group position={data.position}>
      <mesh
        ref={meshRef}
        scale={hovered ? size * 1.3 : size}
        onPointerOver={handlePointerOver}
        onPointerOut={handlePointerOut}
      >
        <sphereGeometry args={[1, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={hovered ? 0.6 : 0.3}
        />
      </mesh>

      {/* Generation label */}
      <Text
        position={[0, 0.5, 0]}
        fontSize={0.2}
        color="#94a3b8"
        anchorX="center"
        anchorY="middle"
      >
        Gen {data.generation}
      </Text>

      {/* Tooltip */}
      {hovered && (
        <Html position={[0, 1, 0]} center distanceFactor={8}>
          <div
            style={{
              background: 'rgba(15, 23, 42, 0.95)',
              border: `1px solid ${color}`,
              borderRadius: '8px',
              padding: '12px',
              color: '#f1f5f9',
              fontFamily: 'system-ui, -apple-system, sans-serif',
              fontSize: '13px',
              minWidth: '160px',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
              pointerEvents: 'none',
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: '8px', fontSize: '14px' }}>
              {data.label}
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#94a3b8' }}>Generation:</span>
              <span>{data.generation}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
              <span style={{ color: '#94a3b8' }}>Value:</span>
              <span style={{ color, fontWeight: 600 }}>
                {data.value >= 0 ? '+' : ''}{data.value.toFixed(2)}
              </span>
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}

/**
 * View controls type
 */
type ViewPosition = 'default' | 'top' | 'front' | 'side';

/**
 * Scene component with all visualizations
 */
function Scene({
  metrics,
  equityData,
  timelineData,
  viewPosition,
  onViewChange
}: {
  metrics: PerformanceMetrics;
  equityData: SurfaceData;
  timelineData: TimelineData[];
  viewPosition: ViewPosition;
  onViewChange: (view: ViewPosition) => void;
}) {
  const { camera } = useThree();
  const [hoveredBar, setHoveredBar] = useState<string | null>(null);
  const [hoveredPoint, setHoveredPoint] = useState<{ x: number; y: number; z: number } | null>(null);
  const [hoveredTimeline, setHoveredTimeline] = useState<string | null>(null);

  const barData = useMemo<BarData[]>(() => {
    return [
      {
        id: 'totalReturn',
        label: 'Return %',
        value: metrics.totalReturn,
        color: getValueColor(metrics.totalReturn, DEFAULT_THRESHOLDS.totalReturn),
        position: [-3, 0, -3],
        threshold: DEFAULT_THRESHOLDS.totalReturn,
      },
      {
        id: 'sharpeRatio',
        label: 'Sharpe',
        value: metrics.sharpeRatio,
        color: getValueColor(metrics.sharpeRatio, DEFAULT_THRESHOLDS.sharpeRatio),
        position: [-1, 0, -3],
        threshold: DEFAULT_THRESHOLDS.sharpeRatio,
      },
      {
        id: 'maxDrawdown',
        label: 'Max DD %',
        value: metrics.maxDrawdown,
        color: getValueColor(metrics.maxDrawdown, DEFAULT_THRESHOLDS.maxDrawdown),
        position: [1, 0, -3],
        threshold: DEFAULT_THRESHOLDS.maxDrawdown,
      },
      {
        id: 'winRate',
        label: 'Win Rate %',
        value: metrics.winRate,
        color: getValueColor(metrics.winRate, DEFAULT_THRESHOLDS.winRate),
        position: [3, 0, -3],
        threshold: DEFAULT_THRESHOLDS.winRate,
      },
    ];
  }, [metrics]);

  const cameraPositions: Record<ViewPosition, [number, number, number]> = {
    default: [8, 8, 8],
    top: [0, 15, 0],
    front: [0, 2, 12],
    side: [12, 2, 0],
  };

  useMemo(() => {
    const targetPos = cameraPositions[viewPosition];
    camera.position.set(...targetPos);
    camera.lookAt(0, 0, 0);
  }, [camera, viewPosition]);

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

      {/* Bar chart for performance metrics */}
      <group position={[0, 0, 2]}>
        {barData.map((bar) => (
          <Bar3D key={bar.id} data={bar} onHover={setHoveredBar} />
        ))}
      </group>

      {/* Surface plot for equity growth */}
      <group position={[0, -2, -2]}>
        <SurfacePlot3D data={equityData} onHover={setHoveredPoint} />
      </group>

      {/* Timeline for generation progression */}
      <group position={[0, 1, -5]}>
        <Timeline3D data={timelineData} onHover={setHoveredTimeline} />
      </group>

      {/* Orbit controls */}
      <OrbitControls
        enableDamping
        dampingFactor={0.05}
        rotateSpeed={0.5}
        zoomSpeed={0.8}
        minDistance={5}
        maxDistance={20}
        enablePan={true}
        panSpeed={0.5}
      />

      {/* View controls overlay */}
      <Html position={[0, 0, 0]} fullscreen>
        <div
          style={{
            position: 'absolute',
            bottom: '16px',
            left: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
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
            View Controls
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <button
              onClick={() => onViewChange('default')}
              style={{
                background: viewPosition === 'default' ? '#3b82f6' : '#1e293b',
                color: '#f1f5f9',
                border: '1px solid #334155',
                borderRadius: '4px',
                padding: '6px 12px',
                fontSize: '11px',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#2563eb';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = viewPosition === 'default' ? '#3b82f6' : '#1e293b';
              }}
            >
              Default View
            </button>
            <button
              onClick={() => onViewChange('top')}
              style={{
                background: viewPosition === 'top' ? '#3b82f6' : '#1e293b',
                color: '#f1f5f9',
                border: '1px solid #334155',
                borderRadius: '4px',
                padding: '6px 12px',
                fontSize: '11px',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#2563eb';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = viewPosition === 'top' ? '#3b82f6' : '#1e293b';
              }}
            >
              Top View
            </button>
            <button
              onClick={() => onViewChange('front')}
              style={{
                background: viewPosition === 'front' ? '#3b82f6' : '#1e293b',
                color: '#f1f5f9',
                border: '1px solid #334155',
                borderRadius: '4px',
                padding: '6px 12px',
                fontSize: '11px',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#2563eb';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = viewPosition === 'front' ? '#3b82f6' : '#1e293b';
              }}
            >
              Front View
            </button>
            <button
              onClick={() => onViewChange('side')}
              style={{
                background: viewPosition === 'side' ? '#3b82f6' : '#1e293b',
                color: '#f1f5f9',
                border: '1px solid #334155',
                borderRadius: '4px',
                padding: '6px 12px',
                fontSize: '11px',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = '#2563eb';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = viewPosition === 'side' ? '#3b82f6' : '#1e293b';
              }}
            >
              Side View
            </button>
          </div>
        </div>

        {/* Legend */}
        <div
          style={{
            position: 'absolute',
            top: '16px',
            right: '16px',
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
            Performance
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981' }} />
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Good</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#f59e0b' }} />
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Moderate</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#ef4444' }} />
              <span style={{ fontSize: '11px', color: '#94a3b8' }}>Bad</span>
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
            Visualizations
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '11px', color: '#94a3b8' }}>
            <div>Bars: Key Metrics</div>
            <div>Surface: Equity Growth</div>
            <div>Line: Generations</div>
          </div>
        </div>

        {/* Controls hint */}
        <div
          style={{
            position: 'absolute',
            top: '16px',
            left: '16px',
            background: 'rgba(15, 23, 42, 0.9)',
            backdropFilter: 'blur(8px)',
            border: '1px solid #334155',
            borderRadius: '8px',
            padding: '8px 12px',
            fontSize: '11px',
            color: '#64748b',
            fontFamily: 'system-ui, -apple-system, sans-serif',
          }}
        >
          Drag to rotate • Scroll to zoom • Right-click to pan
        </div>
      </Html>
    </>
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
          Loading 3D Performance Metrics...
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
          Failed to Load Metrics
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
 * Empty state component
 */
function EmptyState() {
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
            width: '64px',
            height: '64px',
            borderRadius: '50%',
            background: '#1e293b',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: '2px solid #334155',
          }}
        >
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#64748b"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <line x1="3" y1="9" x2="21" y2="9" />
            <line x1="9" y1="21" x2="9" y2="9" />
          </svg>
        </div>
        <div
          style={{
            color: '#94a3b8',
            fontSize: '14px',
            fontWeight: 500,
            fontFamily: 'system-ui, -apple-system, sans-serif',
          }}
        >
          No performance data available
        </div>
      </div>
    </div>
  );
}

/**
 * Main PerformanceMetrics3D component
 */
export function PerformanceMetrics3D({
  metrics,
  equityData,
  timelineData,
  isLoading = false,
  error = null,
  height = '600px',
  className = '',
}: PerformanceMetrics3DProps) {
  const [viewPosition, setViewPosition] = useState<ViewPosition>('default');

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

  const defaultMetrics: PerformanceMetrics = useMemo(
    () => ({
      totalReturn: 15.5,
      sharpeRatio: 2.3,
      maxDrawdown: -8.2,
      winRate: 65.0,
    }),
    []
  );

  const defaultEquityData: SurfaceData = useMemo(
    () => ({
      points: Array.from({ length: 100 }, (_, i) => ({
        x: (i % 10) - 5,
        y: Math.floor(i / 10) - 5,
        z: Math.sin(i * 0.3) * 3 + Math.cos(i * 0.2) * 2,
      })),
      width: 10,
      height: 10,
    }),
    []
  );

  const defaultTimelineData: TimelineData[] = useMemo(
    () => Array.from({ length: 10 }, (_, i) => ({
      id: `gen-${i}`,
      label: `Generation ${i}`,
      value: Math.random() * 40 - 10,
      generation: i,
      position: [(i - 5) * 1.5, Math.random() * 2 - 1, 0] as [number, number, number],
      timestamp: Date.now() - (10 - i) * 86400000,
    })),
    []
  );

  const displayMetrics = metrics ?? defaultMetrics;
  const displayEquityData = equityData ?? defaultEquityData;
  const displayTimelineData = timelineData ?? defaultTimelineData;

  const handleExportImage = useCallback(() => {
    const canvas = document.querySelector('canvas');
    if (canvas) {
      const link = document.createElement('a');
      link.download = `performance-metrics-${Date.now()}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    }
  }, []);

  // Show loading state
  if (isLoading) {
    return <div style={containerStyle}>{isLoading && <LoadingSkeleton />}</div>;
  }

  // Show error state
  if (error) {
    return <div style={containerStyle}>{error && <ErrorState error={error} />}</div>;
  }

  // Show empty state
  if (!metrics && !equityData && !timelineData) {
    return <div style={containerStyle}><EmptyState /></div>;
  }

  return (
    <div style={containerStyle} className={className}>
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

      <Canvas
        camera={{ position: [8, 8, 8], fov: 45 }}
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
            metrics={displayMetrics}
            equityData={displayEquityData}
            timelineData={displayTimelineData}
            viewPosition={viewPosition}
            onViewChange={setViewPosition}
          />
        </Suspense>
      </Canvas>
    </div>
  );
}

/**
 * Default export for convenience
 */
export default PerformanceMetrics3D;
