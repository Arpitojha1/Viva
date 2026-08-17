import { useRef, useMemo, useEffect, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Points, PointMaterial } from '@react-three/drei';
import * as THREE from 'three';

const PARTICLE_COUNT = 5000;

function getDocPositions() {
  const pos = new Float32Array(PARTICLE_COUNT * 3);
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    pos[i * 3] = (Math.random() - 0.5) * 4.0;       // width
    pos[i * 3 + 1] = (Math.random() - 0.5) * 5.5;   // height
    pos[i * 3 + 2] = (Math.random() - 0.5) * 0.1;   // depth
  }
  return pos;
}

function getCloudPositions() {
  const pos = new Float32Array(PARTICLE_COUNT * 3);
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const theta = Math.random() * 2 * Math.PI;
    const phi = Math.acos((Math.random() * 2) - 1);
    const r = Math.cbrt(Math.random()) * 4.5; 
    pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    pos[i * 3 + 2] = r * Math.cos(phi);
  }
  return pos;
}

function getQuestionMarkPositions() {
  const pos = new Float32Array(PARTICLE_COUNT * 3);
  for (let i = 0; i < PARTICLE_COUNT; i++) {
    const p = Math.random();
    let x = 0, y = 0, z = (Math.random() - 0.5) * 0.4;
    
    // Fuzzy volume around the core skeleton
    const thickness = Math.random() * 0.5; 
    const angleOffset = Math.random() * Math.PI * 2;
    const tx = Math.cos(angleOffset) * thickness;
    const ty = Math.sin(angleOffset) * thickness;

    if (p < 0.15) {
      // Dot (circle at 0, -2.5)
      const r = Math.random() * 0.45;
      const a = Math.random() * Math.PI * 2;
      x = Math.cos(a) * r;
      y = -2.6 + Math.sin(a) * r;
    } else if (p < 0.35) {
      // Stem (line from 0,0 down to 0,-1.5)
      x = tx;
      y = -1.5 + Math.random() * 1.5 + ty;
    } else {
      // Hook (arc from -PI/2 to PI*1.1)
      // Center at (0, 1.5), radius 1.5
      const t = -Math.PI / 2 + Math.random() * (Math.PI * 1.6);
      const r = 1.5 + (Math.random() - 0.5) * 0.55;
      x = Math.cos(t) * r;
      y = 1.5 + Math.sin(t) * r;
    }

    pos[i * 3] = x;
    pos[i * 3 + 1] = y + 0.5; // Offset slightly up for overall centering
    pos[i * 3 + 2] = z;
  }
  return pos;
}

function SceneLogic() {
  const pointsRef = useRef<THREE.Points>(null);
  const glassRef = useRef<THREE.Mesh>(null);
  const groupRef = useRef<THREE.Group>(null);
  
  const [phase, setPhase] = useState(0);

  const positions = useMemo(() => {
    return {
      doc: getDocPositions(),
      cloud: getCloudPositions(),
      qmark: getQuestionMarkPositions(),
    };
  }, []);

  // Initialize with document positions
  const currentPositions = useMemo(() => new Float32Array(positions.doc), [positions]);

  useEffect(() => {
    const interval = setInterval(() => {
      setPhase(p => (p + 1) % 3);
    }, 4500); // cycle every 4.5s
    return () => clearInterval(interval);
  }, []);

  useFrame((state, delta) => {
    // 1. Camera / Group Parallax
    if (groupRef.current) {
      const targetX = (state.pointer.x * state.viewport.width) / 20;
      const targetY = (state.pointer.y * state.viewport.height) / 20;
      groupRef.current.rotation.y = THREE.MathUtils.lerp(groupRef.current.rotation.y, targetX, 0.05);
      groupRef.current.rotation.x = THREE.MathUtils.lerp(groupRef.current.rotation.x, -targetY, 0.05);
    }

    // 2. Morphing Particles
    if (pointsRef.current) {
      const geo = pointsRef.current.geometry;
      const arr = geo.attributes.position.array as Float32Array;
      
      let targetArr = positions.doc;
      if (phase === 1) targetArr = positions.cloud;
      if (phase === 2) targetArr = positions.qmark;

      for (let i = 0; i < PARTICLE_COUNT * 3; i++) {
        arr[i] = THREE.MathUtils.lerp(arr[i], targetArr[i], 0.06);
        // Add minimal organic noise
        arr[i] += (Math.random() - 0.5) * 0.01;
      }
      geo.attributes.position.needsUpdate = true;
      
      // Slight overall rotation
      pointsRef.current.rotation.y = state.clock.elapsedTime * 0.15;
    }

    // 3. Fade Glass Material
    if (glassRef.current) {
      const material = glassRef.current.material as THREE.MeshPhysicalMaterial;
      const wireframeMaterial = (glassRef.current.children[0] as THREE.Mesh).material as THREE.MeshBasicMaterial;
      
      // Glass is visible in phase 0 (Document), hidden otherwise
      const targetOpacity = phase === 0 ? 0.8 : 0.0;
      const targetWireOpacity = phase === 0 ? 0.1 : 0.0;
      
      material.opacity = THREE.MathUtils.lerp(material.opacity, targetOpacity, 0.08);
      wireframeMaterial.opacity = THREE.MathUtils.lerp(wireframeMaterial.opacity, targetWireOpacity, 0.08);
    }
  });

  return (
    <group ref={groupRef}>
      <Float speed={2} rotationIntensity={0.2} floatIntensity={0.5}>
        <mesh ref={glassRef} position={[0, 0, 0]}>
          <planeGeometry args={[4.2, 5.7]} />
          <meshPhysicalMaterial
            color="#ffffff"
            metalness={0.1}
            roughness={0.05}
            transmission={0.9} 
            ior={1.5}
            thickness={0.5}
            transparent
            opacity={0.8}
          />
          <mesh position={[0, 0, 0.01]}>
            <planeGeometry args={[4.1, 5.6]} />
            <meshBasicMaterial color="#ffffff" wireframe transparent opacity={0.1} />
          </mesh>
        </mesh>
      </Float>

      <Points ref={pointsRef} positions={currentPositions} stride={3} frustumCulled={false}>
        <PointMaterial
          transparent
          color="#3b82f6"
          size={0.04}
          sizeAttenuation={true}
          depthWrite={false}
          opacity={0.7}
          blending={THREE.AdditiveBlending}
        />
      </Points>
    </group>
  );
}

export function HeroScene() {
  return (
    <div className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
      <Canvas camera={{ position: [0, 0, 10], fov: 45 }}>
        <ambientLight intensity={0.5} />
        <directionalLight position={[10, 10, 5]} intensity={1} />
        <directionalLight position={[-10, -10, -5]} intensity={0.5} color="#3b82f6" />
        
        <SceneLogic />
      </Canvas>
    </div>
  );
}
