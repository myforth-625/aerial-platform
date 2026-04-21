import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { load as loadAMap } from '@amap/amap-jsapi-loader';
import type { FrameData, NodeData, NodeType } from '../types';

interface AmapSceneProps {
  frame: FrameData | null;
  center: [number, number];
}

const AMAP_KEY = 'bfde0ca55786014629f9c94b47499dce';
const AMAP_SECURITY = '148ca7df2257ce0f876af06e5b0a1e41';

const MODEL_CONFIG: Record<
  NodeType,
  { path: string; scale: number; rotationX: number }
> = {
  UAV: { path: '/models/drone/scene.gltf', scale: 2, rotationX: Math.PI / 2 },
  HAP: { path: '/models/hot_air_balloon/scene.gltf', scale: 3, rotationX: Math.PI / 2 },
  GROUND_STATION: {
    path: '/models/broadcast_tower/scene.gltf',
    scale: 0.05,
    rotationX: Math.PI / 2
  },
  TERMINAL: { path: '/models/cell_phone/scene.gltf', scale: 6, rotationX: Math.PI / 2 }
};

const LINK_COLOR = 0x15b324;

interface ModelCache {
  [key: string]: THREE.Group;
}

export default function AmapScene({ frame, center }: AmapSceneProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<any>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const customCoordsRef = useRef<any>(null);
  const modelCacheRef = useRef<ModelCache>({});
  const nodeGroupsRef = useRef<Map<string, THREE.Group>>(new Map());
  const linkLinesRef = useRef<THREE.Line[]>([]);
  const pendingFrameRef = useRef<FrameData | null>(null);
  const modelsReadyRef = useRef(false);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let disposed = false;

    (window as any)._AMapSecurityConfig = { securityJsCode: AMAP_SECURITY };

    loadAMap({
      key: AMAP_KEY,
      version: '2.0',
      plugins: []
    })
      .then((AMap: any) => {
        if (disposed) return;

        const map = new AMap.Map(container, {
          viewMode: '3D',
          zoom: 14,
          pitch: 50,
          center,
          rotateEnable: true,
          pitchEnable: true,
          showLabel: true
        });
        mapRef.current = map;

        AMap.plugin(['AMap.ToolBar', 'AMap.Scale', 'AMap.ControlBar'], () => {
          map.addControl(new AMap.ToolBar());
          map.addControl(new AMap.Scale());
          map.addControl(new AMap.ControlBar());
        });

        const customCoords = map.customCoords;
        customCoords.setCenter(center);
        customCoordsRef.current = customCoords;

        let camera: THREE.PerspectiveCamera | null = null;
        let renderer: THREE.WebGLRenderer | null = null;

        const gllayer = new AMap.GLCustomLayer({
          zIndex: 99,
          init: (gl: WebGLRenderingContext) => {
            camera = new THREE.PerspectiveCamera(
              60,
              window.innerWidth / window.innerHeight,
              100,
              1 << 30
            );
            renderer = new THREE.WebGLRenderer({
              context: gl,
              alpha: true,
              antialias: true
            });
            renderer.autoClear = false;

            const scene = new THREE.Scene();
            sceneRef.current = scene;

            scene.add(new THREE.AmbientLight(0xffffff, 0.7));
            const dLight = new THREE.DirectionalLight(0xffffff, 1.2);
            dLight.position.set(0, 0, 500);
            dLight.lookAt(0, 0, 0);
            scene.add(dLight);

            preloadModels().then(() => {
              modelsReadyRef.current = true;
              if (pendingFrameRef.current) {
                renderFrame(pendingFrameRef.current);
                pendingFrameRef.current = null;
              }
              map.render();
            });
          },
          render: () => {
            if (!renderer || !camera || !sceneRef.current) return;
            renderer.resetState();

            customCoords.setCenter(center);
            const { near, far, fov, up, lookAt, position } = customCoords.getCameraParams();

            const size = map.getSize?.();
            const w = size?.getWidth ? size.getWidth() : container.clientWidth;
            const h = size?.getHeight ? size.getHeight() : container.clientHeight;
            camera.aspect = w / h;
            camera.near = near;
            camera.far = far;
            camera.fov = fov;
            camera.position.set(position[0], position[1], position[2]);
            camera.up.set(up[0], up[1], up[2]);
            camera.lookAt(lookAt[0], lookAt[1], lookAt[2]);
            camera.updateProjectionMatrix();

            renderer.render(sceneRef.current, camera);
            renderer.resetState();
          }
        });

        map.add(gllayer);

        const animate = () => {
          if (disposed) return;
          map.render();
          requestAnimationFrame(animate);
        };
        animate();
      })
      .catch((err: any) => {
        console.error('[AmapScene] AMap load failed:', err);
      });

    return () => {
      disposed = true;
      linkLinesRef.current = [];
      nodeGroupsRef.current.clear();
      if (sceneRef.current) {
        while (sceneRef.current.children.length > 0) {
          sceneRef.current.remove(sceneRef.current.children[0]);
        }
        sceneRef.current = null;
      }
      if (mapRef.current) {
        mapRef.current.destroy?.();
        mapRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When center changes (e.g. switching scenarios) re-center the map
  useEffect(() => {
    if (mapRef.current && center) {
      mapRef.current.setCenter?.(center);
      customCoordsRef.current?.setCenter?.(center);
    }
  }, [center]);

  // Render each incoming frame
  useEffect(() => {
    if (!frame) return;
    if (!modelsReadyRef.current || !sceneRef.current || !customCoordsRef.current) {
      pendingFrameRef.current = frame;
      return;
    }
    renderFrame(frame);
  }, [frame]);

  async function preloadModels() {
    const loader = new GLTFLoader();
    const entries = Object.entries(MODEL_CONFIG) as [NodeType, typeof MODEL_CONFIG[NodeType]][];
    await Promise.all(
      entries.map(
        ([type, cfg]) =>
          new Promise<void>(resolve => {
            loader.load(
              cfg.path,
              gltf => {
                modelCacheRef.current[type] = gltf.scene;
                resolve();
              },
              undefined,
              err => {
                console.warn(`[AmapScene] failed to load ${cfg.path}`, err);
                resolve();
              }
            );
          })
      )
    );
  }

  function renderFrame(frameData: FrameData) {
    const scene = sceneRef.current;
    const customCoords = customCoordsRef.current;
    if (!scene || !customCoords) return;

    const incomingIds = new Set(frameData.nodes.map(n => n.id));
    const nodeGroups = nodeGroupsRef.current;

    // Convert all node lng/lat to scene coordinates in one call
    const projected: Record<string, [number, number]> = {};
    if (frameData.nodes.length > 0) {
      const lngLats = frameData.nodes.map(n => [n.lng, n.lat]);
      const coords: number[][] = customCoords.lngLatsToCoords(lngLats);
      frameData.nodes.forEach((n, i) => {
        projected[n.id] = [coords[i][0], coords[i][1]];
      });
    }

    // Upsert node groups
    frameData.nodes.forEach(node => {
      const [x, y] = projected[node.id];
      const existing = nodeGroups.get(node.id);
      if (existing) {
        existing.position.set(x, y, node.height);
        return;
      }
      const group = createNodeGroup(node);
      if (!group) return;
      group.position.set(x, y, node.height);
      nodeGroups.set(node.id, group);
      scene.add(group);
    });

    // Remove nodes no longer present
    [...nodeGroups.entries()].forEach(([id, group]) => {
      if (!incomingIds.has(id)) {
        scene.remove(group);
        nodeGroups.delete(id);
      }
    });

    // Rebuild link lines (simpler than diffing)
    linkLinesRef.current.forEach(line => scene.remove(line));
    linkLinesRef.current = [];

    const nodeLookup = new Map(frameData.nodes.map(n => [n.id, n] as [string, NodeData]));
    frameData.links.forEach(link => {
      const src = nodeLookup.get(link.sourceId);
      const tgt = nodeLookup.get(link.targetId);
      if (!src || !tgt) return;
      const [sx, sy] = projected[src.id];
      const [tx, ty] = projected[tgt.id];
      const geometry = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(sx, sy, src.height),
        new THREE.Vector3(tx, ty, tgt.height)
      ]);
      const material = new THREE.LineBasicMaterial({ color: LINK_COLOR });
      const line = new THREE.Line(geometry, material);
      scene.add(line);
      linkLinesRef.current.push(line);
    });

    mapRef.current?.render?.();
  }

  function createNodeGroup(node: NodeData): THREE.Group | null {
    const base = modelCacheRef.current[node.type];
    if (!base) return null;
    const cfg = MODEL_CONFIG[node.type];
    const model = base.clone(true);
    const group = new THREE.Group();
    group.add(model);
    group.scale.set(cfg.scale, cfg.scale, cfg.scale);
    group.rotation.x = cfg.rotationX;
    group.userData = { type: node.type, id: node.id };
    return group;
  }

  return <div ref={containerRef} className="three-container" id="amap-container" />;
}
