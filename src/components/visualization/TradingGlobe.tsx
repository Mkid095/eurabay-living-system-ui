/**
 * TradingGlobe Component
 *
 * Interactive 3D globe visualization for global trading activity.
 * Displays trade markers on globe at market locations with color-coded P&L and volume-based sizing.
 *
 * Features:
 * - Interactive 3D globe with earth texture
 * - Trade markers positioned by volatility indices (V10=Asia, V25=Europe, V50=Americas, etc)
 * - Color-coded markers by P&L (green=profit, red=loss)
 * - Size markers by trade volume
 * - Globe rotation via drag
 * - Zoom via scroll
 * - Orbit controls for camera manipulation
 * - Ambient and directional lighting
 * - Stars background
 * - Window resize handling
 * - Loading and error states
 */

'use client';

import React, { Suspense, useCallback, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { OrbitControls, Stars, Sphere, Html } from '@react-three/drei';
import { Mesh, Group } from 'three';
import * as THREE from 'three';

/**
 * Trade data structure for globe markers
 */
export interface TradeMarker {
  id: string;
  symbol: string;
  volatilityIndex: 'V10' | 'V25' | 'V50' | 'V75' | 'V100';
  pnl: number;
  volume: number;
  price: number;
  side: 'BUY' | 'SELL';
}

/**
 * Component props
 */
export interface TradingGlobeProps {
  /** Array of trade markers to display on the globe */
  trades?: TradeMarker[];
  /** Whether the globe is loading data */
  isLoading?: boolean;
  /** Error message if data loading failed */
  error?: string | null;
  /** Height of the canvas container */
  height?: string | number;
  /** CSS class name for styling */
  className?: string;
}

/**
 * Volatility index to geographic coordinates mapping
 * V10 = Asia, V25 = Europe, V50 = Americas, V75 = Middle East, V100 = Africa
 */
const VOLATILITY_COORDINATES: Record<string, { lat: number; lon: number }> = {
  V10: { lat: 35.6762, lon: 139.6503 },  // Tokyo (Asia)
  V25: { lat: 51.5074, lon: -0.1278 },   // London (Europe)
  V50: { lat: 40.7128, lon: -74.0060 },  // New York (Americas)
  V75: { lat: 25.2048, lon: 55.2708 },   // Dubai (Middle East)
  V100: { lat: -26.2041, lon: 28.0473 }, // Johannesburg (Africa)
};

/**
 * Convert latitude/longitude to 3D sphere coordinates
 */
function latLonToVector3(lat: number, lon: number, radius: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lon + 180) * (Math.PI / 180);

  const x = -(radius * Math.sin(phi) * Math.cos(theta));
  const y = radius * Math.cos(phi);
  const z = radius * Math.sin(phi) * Math.sin(theta);

  return new THREE.Vector3(x, y, z);
}

/**
 * Earth sphere component with texture
 */
function EarthSphere({ radius = 5 }: { radius?: number }) {
  const meshRef = useRef<Mesh>(null);

  // Slowly rotate the earth
  useFrame((state, delta) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += delta * 0.05;
    }
  });

  return (
    <Sphere ref={meshRef} args={[radius, 64, 64]}>
      <meshPhongMaterial
        color="#1a365d"
        emissive="#0a1628"
        specular="#4a5568"
        shininess={15}
        wireframe={false}
      />
    </Sphere>
  );
}

/**
 * Trade marker component
 */
function TradeMarker({ trade, radius = 5 }: { trade: TradeMarker; radius?: number }) {
  const meshRef = useRef<Mesh>(null);
  const [hovered, setHovered] = useState(false);
  const groupRef = useRef<Group>(null);

  const coords = VOLATILITY_COORDINATES[trade.volatilityIndex];
  const position = useMemo(
    () => latLonToVector3(coords.lat, coords.lon, radius + 0.1),
    [coords, radius]
  );

  // Size based on volume (scale between 0.1 and 0.5)
  const size = useMemo(() => {
    const minVolume = 1000;
    const maxVolume = 100000;
    const normalizedVolume = Math.min(Math.max((trade.volume - minVolume) / (maxVolume - minVolume), 0), 1);
    return 0.1 + normalizedVolume * 0.4;
  }, [trade.volume]);

  // Color based on P&L
  const color = useMemo(() => {
    return trade.pnl >= 0 ? '#10b981' : '#ef4444'; // green for profit, red for loss
  }, [trade.pnl]);

  // Pulse animation for hovered marker
  useFrame((state) => {
    if (groupRef.current && hovered) {
      const scale = 1 + Math.sin(state.clock.elapsedTime * 3) * 0.2;
      groupRef.current.scale.setScalar(scale);
    } else if (groupRef.current) {
      groupRef.current.scale.setScalar(1);
    }
  });

  return (
    <group ref={groupRef} position={position}>
      <mesh
        ref={meshRef}
        scale={size}
        onPointerOver={() => setHovered(true)}
        onPointerOut={() => setHovered(false)}
      >
        <sphereGeometry args={[1, 16, 16]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={hovered ? 0.8 : 0.3}
          transparent
          opacity={0.9}
        />
      </mesh>

      {/* Tooltip */}
      {hovered && (
        <Html
          position={[0, size + 0.2, 0]}
          center
          distanceFactor={10}
          style={{
            pointerEvents: 'none',
            transition: 'all 0.2s',
          }}
        >
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
            }}
          >
            <div style={{ fontWeight: 600, marginBottom: '4px' }}>{trade.symbol}</div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
              <span style={{ color: '#94a3b8' }}>Side:</span>
              <span style={{ color: trade.side === 'BUY' ? '#10b981' : '#ef4444', fontWeight: 500 }}>
                {trade.side}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
              <span style={{ color: '#94a3b8' }}>P&L:</span>
              <span style={{ color, fontWeight: 600 }}>
                {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(2)}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
              <span style={{ color: '#94a3b8' }}>Volume:</span>
              <span>{trade.volume.toLocaleString()}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
              <span style={{ color: '#94a3b8' }}>Price:</span>
              <span>${trade.price.toFixed(2)}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
              <span style={{ color: '#94a3b8' }}>Index:</span>
              <span>{trade.volatilityIndex}</span>
            </div>
          </div>
        </Html>
      )}
    </group>
  );
}

/**
 * Scene component with lighting and controls
 */
function Scene({
  trades,
  radius = 5,
}: {
  trades: TradeMarker[];
  radius?: number;
}) {
  const { camera } = useThree();

  // Set initial camera position
  useMemo(() => {
    camera.position.set(0, 5, 15);
    camera.lookAt(0, 0, 0);
  }, [camera]);

  return (
    <>
      {/* Ambient light for overall illumination */}
      <ambientLight intensity={0.3} />

      {/* Directional light simulating the sun */}
      <directionalLight
        position={[10, 10, 10]}
        intensity={1.5}
        castShadow
        color="#ffffff"
      />

      {/* Secondary directional light for fill */}
      <directionalLight
        position={[-10, -5, -10]}
        intensity={0.5}
        color="#4a5568"
      />

      {/* Earth sphere */}
      <EarthSphere radius={radius} />

      {/* Trade markers */}
      {trades.map((trade) => (
        <TradeMarker key={trade.id} trade={trade} radius={radius} />
      ))}

      {/* Stars background */}
      <Stars
        radius={100}
        depth={50}
        count={5000}
        factor={4}
        saturation={0}
        fade={true}
        speed={1}
      />

      {/* Orbit controls for camera manipulation */}
      <OrbitControls
        enableDamping
        dampingFactor={0.05}
        rotateSpeed={0.5}
        zoomSpeed={0.8}
        minDistance={8}
        maxDistance={25}
        enablePan={false}
      />
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
          Loading 3D Globe...
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
          Failed to Load Globe
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
            <circle cx="12" cy="12" r="10" />
            <path d="M2 12h20" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
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
          No active trades to display
        </div>
      </div>
    </div>
  );
}

/**
 * Main TradingGlobe component
 */
export function TradingGlobe({
  trades = [],
  isLoading = false,
  error = null,
  height = '600px',
  className = '',
}: TradingGlobeProps) {
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

  // Show loading state
  if (isLoading) {
    return <div style={containerStyle}>{isLoading && <LoadingSkeleton />}</div>;
  }

  // Show error state
  if (error) {
    return <div style={containerStyle}>{error && <ErrorState error={error} />}</div>;
  }

  // Show empty state
  if (trades.length === 0) {
    return <div style={containerStyle}><EmptyState /></div>;
  }

  return (
    <div style={containerStyle} className={className}>
      <Canvas
        camera={{ position: [0, 5, 15], fov: 45 }}
        gl={{
          antialias: true,
          alpha: true,
          powerPreference: 'high-performance',
        }}
        dpr={[1, 2]} // Optimize for retina displays
        performance={{ min: 0.5 }} // Maintain 60 FPS
      >
        <Suspense fallback={null}>
          <Scene trades={trades} radius={5} />
        </Suspense>
      </Canvas>

      {/* Legend overlay */}
      <div
        style={{
          position: 'absolute',
          bottom: '16px',
          left: '16px',
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
          Market Regions
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {Object.entries(VOLATILITY_COORDINATES).map(([index, coords]) => (
            <div
              key={index}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                fontSize: '11px',
                color: '#94a3b8',
              }}
            >
              <div
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  background: index === 'V10' ? '#3b82f6' :
                             index === 'V25' ? '#10b981' :
                             index === 'V50' ? '#f59e0b' :
                             index === 'V75' ? '#f97316' : '#ef4444',
                }}
              />
              <span>
                {index} ({index === 'V10' ? 'Asia' :
                          index === 'V25' ? 'Europe' :
                          index === 'V50' ? 'Americas' :
                          index === 'V75' ? 'Middle East' : 'Africa'})
              </span>
            </div>
          ))}
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
          P&L
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#10b981',
              }}
            />
            <span style={{ fontSize: '11px', color: '#94a3b8' }}>Profit</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <div
              style={{
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: '#ef4444',
              }}
            />
            <span style={{ fontSize: '11px', color: '#94a3b8' }}>Loss</span>
          </div>
        </div>
      </div>

      {/* Controls hint */}
      <div
        style={{
          position: 'absolute',
          top: '16px',
          right: '16px',
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
        Drag to rotate • Scroll to zoom
      </div>
    </div>
  );
}

/**
 * Default export for convenience
 */
export default TradingGlobe;
