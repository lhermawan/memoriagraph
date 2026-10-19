import React, { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import { 
  Application, 
  Container, 
  Graphics, 
  Sprite, 
  Text, 
  TextStyle, 
  Texture 
} from 'pixi.js';
import type { GraphNode, GraphEdge, PhysicsParams } from '../types/graph';
import type { WorkerInMessage, WorkerOutMessage } from '../workers/graphPhysics.worker';
import { GraphControls } from './GraphControls';

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNode: GraphNode | null;
  hoveredNode: GraphNode | null;
  highlightedIds?: Set<string>;
  onSelectNode: (node: GraphNode | null) => void;
  onHoverNode: (node: GraphNode | null) => void;
  isDarkMode: boolean;
}

export const GraphCanvas: React.FC<GraphCanvasProps> = ({
  nodes,
  edges,
  selectedNode,
  hoveredNode,
  highlightedIds,
  onSelectNode,
  onHoverNode,
  isDarkMode,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const workerRef = useRef<Worker | null>(null);
  const appRef = useRef<Application | null>(null);
  const viewportRef = useRef<Container | null>(null);
  const edgesGraphicsRef = useRef<Graphics | null>(null);

  // Sprite & Label references by Node ID
  const nodeSpritesRef = useRef<Map<string, Sprite>>(new Map());
  const labelTextsRef = useRef<Map<string, Text>>(new Map());
  const nodePositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map());

  // Interaction State
  const [showLabels, setShowLabels] = useState(true);
  const [params, setParams] = useState<PhysicsParams>({
    repelStrength: -280,
    linkDistance: 110,
    centerGravity: 0.06,
    collideRadius: 18,
    nodeSizeMult: 1.0,
  });

  const isPanningRef = useRef(false);
  const panStartRef = useRef({ x: 0, y: 0 });
  const hoveredNodeIdRef = useRef<string | null>(null);
  const selectedNodeIdRef = useRef<string | null>(null);

  // Sync selectedNode to ref
  useEffect(() => {
    selectedNodeIdRef.current = selectedNode ? selectedNode.id : null;
  }, [selectedNode]);

  // Sync hoveredNode to ref
  useEffect(() => {
    hoveredNodeIdRef.current = hoveredNode ? hoveredNode.id : null;
  }, [hoveredNode]);

  // 1. Pre-computed Adjacency Map (1-hop neighbors)
  const adjacencyMap = useMemo(() => {
    const map = new Map<string, Set<string>>();
    nodes.forEach((n) => map.set(n.id, new Set()));
    edges.forEach((e) => {
      map.get(e.source)?.add(e.target);
      map.get(e.target)?.add(e.source);
    });
    return map;
  }, [nodes, edges]);

  // Convert hex color to number
  const hexToNumber = (hex: string) => {
    if (!hex || !hex.startsWith('#')) return 0x00f0ff;
    return parseInt(hex.slice(1), 16);
  };

  // 2. Zoom-Based Label Opacity (Level of Detail)
  const updateLabelVisibility = useCallback(() => {
    const viewport = viewportRef.current;
    if (!viewport) return;

    const scale = viewport.scale.x;
    const hoveredId = hoveredNodeIdRef.current;
    const neighbors = hoveredId ? adjacencyMap.get(hoveredId) : null;

    labelTextsRef.current.forEach((label, id) => {
      const isSpotlight = id === hoveredId || (neighbors && neighbors.has(id));

      if (isSpotlight) {
        label.visible = true;
        label.alpha = 1.0;
        return;
      }

      if (!showLabels || scale < 0.38) {
        label.visible = false;
        label.alpha = 0;
      } else {
        label.visible = true;
        label.alpha = Math.min(1, (scale - 0.38) / 0.45);
      }
    });
  }, [adjacencyMap, showLabels]);

  // 3. Batch Draw Edges
  const drawEdges = useCallback(() => {
    const graphics = edgesGraphicsRef.current;
    if (!graphics) return;

    graphics.clear();

    const hoveredId = hoveredNodeIdRef.current;
    const selectedId = selectedNodeIdRef.current;
    const focusId = hoveredId || selectedId;
    const neighbors = focusId ? adjacencyMap.get(focusId) : null;

    const posMap = nodePositionsRef.current;
    const edgeBaseColor = isDarkMode ? 0x8b97b8 : 0x5b6785;

    edges.forEach((edge) => {
      const a = posMap.get(edge.source);
      const b = posMap.get(edge.target);
      if (!a || !b) return;

      const isConnectedToFocus =
        focusId !== null &&
        (edge.source === focusId || edge.target === focusId);

      const isConnectedToNeighbor =
        focusId !== null &&
        neighbors &&
        neighbors.has(edge.source) &&
        neighbors.has(edge.target);

      const isHighlighted =
        highlightedIds &&
        highlightedIds.has(edge.source) &&
        highlightedIds.has(edge.target);

      if (isConnectedToFocus || isHighlighted) {
        graphics.setStrokeStyle({
          width: 2.2,
          color: 0x00f0ff,
          alpha: 0.95,
        });
      } else if (isConnectedToNeighbor) {
        graphics.setStrokeStyle({
          width: 1.5,
          color: 0x00ff88,
          alpha: 0.7,
        });
      } else if (focusId !== null) {
        graphics.setStrokeStyle({
          width: 0.8,
          color: edgeBaseColor,
          alpha: 0.05,
        });
      } else {
        graphics.setStrokeStyle({
          width: 1.0,
          color: edgeBaseColor,
          alpha: 0.22,
        });
      }

      graphics.moveTo(a.x, a.y);
      graphics.lineTo(b.x, b.y);
      graphics.stroke();
    });
  }, [edges, adjacencyMap, highlightedIds, isDarkMode]);

  // 4. Update Node Spotlight Alpha
  const updateSpotlight = useCallback(() => {
    const hoveredId = hoveredNodeIdRef.current;
    const selectedId = selectedNodeIdRef.current;
    const focusId = hoveredId || selectedId;
    const neighbors = focusId ? adjacencyMap.get(focusId) : null;

    nodeSpritesRef.current.forEach((sprite, id) => {
      const isFocus = id === focusId;
      const isNeighbor = neighbors && neighbors.has(id);
      const isHigh = highlightedIds && highlightedIds.has(id);

      if (focusId === null && (!highlightedIds || highlightedIds.size === 0)) {
        sprite.alpha = 1.0;
        sprite.scale.set(params.nodeSizeMult);
      } else if (isFocus) {
        sprite.alpha = 1.0;
        sprite.scale.set(params.nodeSizeMult * 1.35);
      } else if (isNeighbor || isHigh) {
        sprite.alpha = 1.0;
        sprite.scale.set(params.nodeSizeMult * 1.15);
      } else {
        sprite.alpha = 0.15;
        sprite.scale.set(params.nodeSizeMult * 0.9);
      }
    });

    drawEdges();
    updateLabelVisibility();
  }, [adjacencyMap, highlightedIds, params.nodeSizeMult, drawEdges, updateLabelVisibility]);

  // 5. Initialize PixiJS Application & Web Worker
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let isDestroyed = false;

    // Create Web Worker
    const worker = new Worker(
      new URL('../workers/graphPhysics.worker.ts', import.meta.url),
      { type: 'module' }
    );
    workerRef.current = worker;

    // Create PixiJS Application
    const app = new Application();
    appRef.current = app;

    let circleTexture: Texture | null = null;

    const initPixi = async () => {
      await app.init({
        antialias: true,
        autoDensity: true,
        resolution: window.devicePixelRatio || 1,
        backgroundColor: isDarkMode ? 0x070b14 : 0xf3f6fc,
        resizeTo: container,
      });

      if (isDestroyed) {
        app.destroy(true, { children: true });
        return;
      }

      container.appendChild(app.canvas);

      // Pre-generate Sharp Circle Texture once for all nodes
      const circleGraphics = new Graphics();
      circleGraphics.circle(32, 32, 32);
      circleGraphics.fill({ color: 0xffffff });
      circleTexture = app.renderer.generateTexture(circleGraphics);
      circleGraphics.destroy();

      // Camera Viewport Container
      const viewport = new Container();
      viewport.position.set(container.clientWidth / 2, container.clientHeight / 2);
      viewport.scale.set(0.85);
      app.stage.addChild(viewport);
      viewportRef.current = viewport;

      // 1. Edges Graphics Layer
      const edgesGraphics = new Graphics();
      viewport.addChild(edgesGraphics);
      edgesGraphicsRef.current = edgesGraphics;

      // 2. Nodes Sprites Layer
      const nodesContainer = new Container();
      viewport.addChild(nodesContainer);

      // 3. Labels Container Layer
      const labelsContainer = new Container();
      viewport.addChild(labelsContainer);

      // Populate Node Sprites & Labels
      const spritesMap = new Map<string, Sprite>();
      const labelsMap = new Map<string, Text>();
      const posMap = new Map<string, { x: number; y: number }>();

      nodes.forEach((n) => {
        const radius = (6 + (n.val || 10) * 0.35);
        const nodeColor = hexToNumber(n.color);

        // Sprite
        const sprite = new Sprite(circleTexture!);
        sprite.anchor.set(0.5);
        sprite.tint = nodeColor;
        sprite.width = radius * 2;
        sprite.height = radius * 2;
        sprite.eventMode = 'static';
        sprite.cursor = 'pointer';

        // Interactive Events
        let isNodeDragging = false;

        sprite.on('pointerover', () => {
          hoveredNodeIdRef.current = n.id;
          onHoverNode(n);
          updateSpotlight();
        });

        sprite.on('pointerout', () => {
          if (hoveredNodeIdRef.current === n.id) {
            hoveredNodeIdRef.current = null;
            onHoverNode(null);
            updateSpotlight();
          }
        });

        sprite.on('pointerdown', (e) => {
          e.stopPropagation();
          isNodeDragging = true;
          onSelectNode(n);
          updateSpotlight();

          // Transform mouse position to world coordinates
          const localPos = viewport.toLocal(e.global);
          worker.postMessage({
            type: 'DRAG_START',
            id: n.id,
            x: localPos.x,
            y: localPos.y,
          } as WorkerInMessage);
        });

        const handleGlobalMove = (e: any) => {
          if (!isNodeDragging) return;
          const localPos = viewport.toLocal(e.global);
          worker.postMessage({
            type: 'DRAG_MOVE',
            id: n.id,
            x: localPos.x,
            y: localPos.y,
          } as WorkerInMessage);
        };

        const handleGlobalUp = () => {
          if (!isNodeDragging) return;
          isNodeDragging = false;
          worker.postMessage({
            type: 'DRAG_END',
            id: n.id,
          } as WorkerInMessage);
        };

        sprite.on('globalpointermove', handleGlobalMove);
        sprite.on('pointerup', handleGlobalUp);
        sprite.on('pointerupoutside', handleGlobalUp);

        nodesContainer.addChild(sprite);
        spritesMap.set(n.id, sprite);

        // Text Label
        const titleText = n.name.split(': ').slice(1).join(': ') || n.name;
        const shortTitle = titleText.length > 28 ? titleText.slice(0, 26) + '…' : titleText;

        const label = new Text({
          text: shortTitle,
          style: new TextStyle({
            fontFamily: 'Inter, system-ui, sans-serif',
            fontSize: 10,
            fill: isDarkMode ? 0xe6ecff : 0x101833,
            align: 'center',
          }),
        });
        label.anchor.set(0.5, 0);
        labelsContainer.addChild(label);
        labelsMap.set(n.id, label);

        posMap.set(n.id, { x: 0, y: 0 });
      });

      nodeSpritesRef.current = spritesMap;
      labelTextsRef.current = labelsMap;
      nodePositionsRef.current = posMap;

      // Handle Worker Output Messages (Tick)
      worker.onmessage = (e: MessageEvent<WorkerOutMessage>) => {
        const msg = e.data;
        if (msg.type === 'TICK') {
          msg.positions.forEach((p) => {
            const sprite = spritesMap.get(p.id);
            const label = labelsMap.get(p.id);
            posMap.set(p.id, { x: p.x, y: p.y });

            if (sprite) {
              sprite.position.set(p.x, p.y);
            }
            if (label && sprite) {
              label.position.set(p.x, p.y + sprite.height / 2 + 3);
            }
          });

          drawEdges();
        }
      };

      // Send initial data to Web Worker
      worker.postMessage({
        type: 'INIT_GRAPH',
        nodes: nodes.map((n) => ({ id: n.id, val: n.val })),
        links: edges.map((e) => ({ source: e.source, target: e.target, type: e.type })),
        params,
        width: container.clientWidth,
        height: container.clientHeight,
      } as WorkerInMessage);

      // Initial Label Visibility
      updateLabelVisibility();
    };

    initPixi();

    // 6. Camera Pan & Zoom Event Handlers (Canvas Background)
    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      const viewport = viewportRef.current;
      if (!viewport) return;

      const rect = container.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      const zoomFactor = e.deltaY < 0 ? 1.14 : 1 / 1.14;
      const currentScale = viewport.scale.x;
      const newScale = Math.min(4.5, Math.max(0.18, currentScale * zoomFactor));

      const worldX = (mouseX - viewport.x) / currentScale;
      const worldY = (mouseY - viewport.y) / currentScale;

      viewport.scale.set(newScale);
      viewport.x = mouseX - worldX * newScale;
      viewport.y = mouseY - worldY * newScale;

      updateLabelVisibility();
    };

    const handlePointerDown = (e: PointerEvent) => {
      // Background panning
      isPanningRef.current = true;
      panStartRef.current = { x: e.clientX, y: e.clientY };
    };

    const handlePointerMove = (e: PointerEvent) => {
      if (!isPanningRef.current) return;
      const viewport = viewportRef.current;
      if (!viewport) return;

      const dx = e.clientX - panStartRef.current.x;
      const dy = e.clientY - panStartRef.current.y;
      panStartRef.current = { x: e.clientX, y: e.clientY };

      viewport.x += dx;
      viewport.y += dy;
    };

    const handlePointerUp = () => {
      isPanningRef.current = false;
    };

    container.addEventListener('wheel', handleWheel, { passive: false });
    container.addEventListener('pointerdown', handlePointerDown);
    window.addEventListener('pointermove', handlePointerMove);
    window.addEventListener('pointerup', handlePointerUp);

    // ResizeObserver
    const resizeObserver = new ResizeObserver(() => {
      if (appRef.current && appRef.current.renderer) {
        appRef.current.renderer.resize(container.clientWidth, container.clientHeight);
      }
    });
    resizeObserver.observe(container);

    return () => {
      isDestroyed = true;
      container.removeEventListener('wheel', handleWheel);
      container.removeEventListener('pointerdown', handlePointerDown);
      window.removeEventListener('pointermove', handlePointerMove);
      window.removeEventListener('pointerup', handlePointerUp);
      resizeObserver.disconnect();

      if (workerRef.current) {
        workerRef.current.terminate();
        workerRef.current = null;
      }

      if (circleTexture) {
        circleTexture.destroy(true);
      }

      if (appRef.current) {
        appRef.current.destroy(true, { children: true });
        appRef.current = null;
      }
    };
  }, [nodes, edges, isDarkMode]); // eslint-disable-line react-hooks/exhaustive-deps

  // 7. Update physics parameters in worker
  const handleUpdateParams = (newParams: Partial<PhysicsParams>) => {
    setParams((prev) => {
      const merged = { ...prev, ...newParams };
      if (workerRef.current) {
        workerRef.current.postMessage({
          type: 'UPDATE_PARAMS',
          params: newParams,
        } as WorkerInMessage);
      }
      return merged;
    });
  };

  // 8. Focus camera smoothly on a specific node
  const handleFocusNode = (nodeId: string) => {
    const pos = nodePositionsRef.current.get(nodeId);
    const viewport = viewportRef.current;
    const container = containerRef.current;
    if (!pos || !viewport || !container) return;

    const targetNode = nodes.find((n) => n.id === nodeId);
    if (targetNode) onSelectNode(targetNode);

    // Smoothly pan camera to target position
    const targetScale = 1.3;
    const targetX = container.clientWidth / 2 - pos.x * targetScale;
    const targetY = container.clientHeight / 2 - pos.y * targetScale;

    viewport.scale.set(targetScale);
    viewport.position.set(targetX, targetY);

    updateSpotlight();
    updateLabelVisibility();
  };

  // 9. Reset Camera / Fit to Screen
  const handleResetCamera = () => {
    const viewport = viewportRef.current;
    const container = containerRef.current;
    if (!viewport || !container) return;

    viewport.scale.set(0.85);
    viewport.position.set(container.clientWidth / 2, container.clientHeight / 2);

    updateSpotlight();
    updateLabelVisibility();
  };

  // 10. Reheat Simulation
  const handleReheatSimulation = () => {
    if (workerRef.current) {
      workerRef.current.postMessage({
        type: 'REHEAT',
        alpha: 0.5,
      } as WorkerInMessage);
    }
  };

  return (
    <div className="relative w-full h-full cyber-grid overflow-hidden">
      {/* PixiJS WebGL Canvas Container */}
      <div ref={containerRef} className="w-full h-full block touch-none cursor-grab" />

      {/* Obsidian-Style Floating Controls */}
      <GraphControls
        nodes={nodes}
        params={params}
        onUpdateParams={handleUpdateParams}
        onFocusNode={handleFocusNode}
        onResetCamera={handleResetCamera}
        onReheatSimulation={handleReheatSimulation}
        showLabels={showLabels}
        onToggleLabels={() => {
          setShowLabels((prev) => !prev);
          updateLabelVisibility();
        }}
      />
    </div>
  );
};
