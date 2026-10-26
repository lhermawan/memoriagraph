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

interface EdgePhoton {
  sourceId: string;
  targetId: string;
  edgeType: string;
  progress: number;
  speed: number;
  size: number;
}

interface StarParticle {
  x: number;
  y: number;
  radius: number;
  baseAlpha: number;
  twinkleSpeed: number;
  phase: number;
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
  const pulseGraphicsRef = useRef<Graphics | null>(null);
  const starfieldGraphicsRef = useRef<Graphics | null>(null);
  const edgeBadgesContainerRef = useRef<Container | null>(null);
  const aurasContainerRef = useRef<Container | null>(null);
  const nodesContainerRef = useRef<Container | null>(null);
  const labelsContainerRef = useRef<Container | null>(null);
  const circleTextureRef = useRef<Texture | null>(null);
  const auraTextureRef = useRef<Texture | null>(null);
  const isFirstMountRef = useRef<boolean>(true);
  const nodesRef = useRef(nodes);
  const edgesRef = useRef(edges);

  useEffect(() => {
    nodesRef.current = nodes;
    edgesRef.current = edges;
  }, [nodes, edges]);

  // Sprite & Label references by Node ID
  const nodeSpritesRef = useRef<Map<string, Sprite>>(new Map());
  const nodeAuraSpritesRef = useRef<Map<string, Sprite>>(new Map());
  const labelTextsRef = useRef<Map<string, Text>>(new Map());
  const nodePositionsRef = useRef<Map<string, { x: number; y: number }>>(new Map());
  const hubDegreeMapRef = useRef<Map<string, number>>(new Map());
  const photonsRef = useRef<EdgePhoton[]>([]);

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

  // 1. Pre-computed Adjacency Map & Hub Degree Map
  const { adjacencyMap, degreeMap } = useMemo(() => {
    const adj = new Map<string, Set<string>>();
    const deg = new Map<string, number>();
    nodes.forEach((n) => {
      adj.set(n.id, new Set());
      deg.set(n.id, 0);
    });
    edges.forEach((e) => {
      adj.get(e.source)?.add(e.target);
      adj.get(e.target)?.add(e.source);
      deg.set(e.source, (deg.get(e.source) || 0) + 1);
      deg.set(e.target, (deg.get(e.target) || 0) + 1);
    });
    return { adjacencyMap: adj, degreeMap: deg };
  }, [nodes, edges]);

  // Keep degreeMap in ref for ticker loop
  useEffect(() => {
    hubDegreeMapRef.current = degreeMap;
  }, [degreeMap]);

  // Convert hex color string to number
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
    const selectedId = selectedNodeIdRef.current;
    const focusId = hoveredId || selectedId;
    const neighbors = focusId ? adjacencyMap.get(focusId) : null;

    labelTextsRef.current.forEach((label, id) => {
      const isSpotlight = id === focusId || (neighbors && neighbors.has(id));

      if (isSpotlight) {
        label.visible = true;
        label.alpha = 1.0;
        return;
      }

      if (!showLabels || scale < 0.35) {
        label.visible = false;
        label.alpha = 0;
      } else {
        label.visible = true;
        label.alpha = Math.min(1, (scale - 0.35) / 0.45);
      }
    });
  }, [adjacencyMap, showLabels]);

  // 3. Update Semantic Edge Badges (Floating Pills when Focus Active)
  const updateEdgeBadges = useCallback(() => {
    const container = edgeBadgesContainerRef.current;
    if (!container) return;

    // Clear previous badges
    container.removeChildren();

    const hoveredId = hoveredNodeIdRef.current;
    const selectedId = selectedNodeIdRef.current;
    const focusId = hoveredId || selectedId;
    if (!focusId) return;

    const posMap = nodePositionsRef.current;

    // Find edges connected to focusId
    edges.forEach((edge) => {
      if (edge.source !== focusId && edge.target !== focusId) return;

      const a = posMap.get(edge.source);
      const b = posMap.get(edge.target);
      if (!a || !b) return;

      const midX = (a.x + b.x) / 2;
      const midY = (a.y + b.y) / 2;

      const badgeContainer = new Container();
      badgeContainer.position.set(midX, midY);

      const typeText = edge.type || 'CONNECTS_TO';
      const cleanType = typeText.length > 20 ? typeText.slice(0, 18) + '…' : typeText;

      const text = new Text({
        text: cleanType,
        style: new TextStyle({
          fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
          fontSize: 8.5,
          fontWeight: '700',
          fill: isDarkMode ? 0x00ffcc : 0x0284c7,
          letterSpacing: 0.6,
        }),
      });
      text.anchor.set(0.5);

      const paddingX = 7;
      const paddingY = 3.5;
      const badgeW = text.width + paddingX * 2;
      const badgeH = text.height + paddingY * 2;

      const bg = new Graphics();
      bg.roundRect(-badgeW / 2, -badgeH / 2, badgeW, badgeH, 4);
      bg.fill({ color: isDarkMode ? 0x070e1e : 0xffffff, alpha: 0.92 });
      bg.setStrokeStyle({
        width: 1.2,
        color: isDarkMode ? 0x00ffcc : 0x0284c7,
        alpha: 0.85,
      });
      bg.stroke();

      badgeContainer.addChild(bg);
      badgeContainer.addChild(text);
      container.addChild(badgeContainer);
    });
  }, [edges, isDarkMode]);

  // 4. Batch Draw Base Edges
  const drawEdges = useCallback(() => {
    const graphics = edgesGraphicsRef.current;
    if (!graphics) return;

    graphics.clear();

    const hoveredId = hoveredNodeIdRef.current;
    const selectedId = selectedNodeIdRef.current;
    const focusId = hoveredId || selectedId;
    const neighbors = focusId ? adjacencyMap.get(focusId) : null;

    const posMap = nodePositionsRef.current;
    const edgeBaseColor = isDarkMode ? 0x22365c : 0x94a3b8;

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
          width: 2.4,
          color: 0x00f0ff,
          alpha: 0.95,
        });
      } else if (isConnectedToNeighbor) {
        graphics.setStrokeStyle({
          width: 1.6,
          color: 0x00ff88,
          alpha: 0.75,
        });
      } else if (focusId !== null) {
        graphics.setStrokeStyle({
          width: 0.8,
          color: edgeBaseColor,
          alpha: 0.08,
        });
      } else {
        graphics.setStrokeStyle({
          width: 1.1,
          color: edgeBaseColor,
          alpha: isDarkMode ? 0.28 : 0.45,
        });
      }

      graphics.moveTo(a.x, a.y);
      graphics.lineTo(b.x, b.y);
      graphics.stroke();
    });

    updateEdgeBadges();
  }, [edges, adjacencyMap, highlightedIds, isDarkMode, updateEdgeBadges]);

  // 5. Update Node Spotlight Alpha
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
        sprite.scale.set(params.nodeSizeMult * 1.4);
      } else if (isNeighbor || isHigh) {
        sprite.alpha = 1.0;
        sprite.scale.set(params.nodeSizeMult * 1.18);
      } else {
        sprite.alpha = 0.14;
        sprite.scale.set(params.nodeSizeMult * 0.88);
      }
    });

    drawEdges();
    updateLabelVisibility();
  }, [adjacencyMap, highlightedIds, params.nodeSizeMult, drawEdges, updateLabelVisibility]);

  // 6. Pre-generate Textures
  const createCircleTexture = (app: Application, radius = 32): Texture => {
    const circleGraphics = new Graphics();
    circleGraphics.circle(radius, radius, radius);
    circleGraphics.fill({ color: 0xffffff });
    const tex = app.renderer.generateTexture(circleGraphics);
    circleGraphics.destroy();
    return tex;
  };

  const createAuraTexture = (radius = 56): Texture => {
    const canvas = document.createElement('canvas');
    canvas.width = radius * 2;
    canvas.height = radius * 2;
    const ctx = canvas.getContext('2d');
    if (ctx) {
      const grad = ctx.createRadialGradient(radius, radius, 0, radius, radius, radius);
      grad.addColorStop(0, 'rgba(255, 255, 255, 0.95)');
      grad.addColorStop(0.25, 'rgba(255, 255, 255, 0.55)');
      grad.addColorStop(0.55, 'rgba(255, 255, 255, 0.20)');
      grad.addColorStop(0.85, 'rgba(255, 255, 255, 0.05)');
      grad.addColorStop(1, 'rgba(255, 255, 255, 0)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, radius * 2, radius * 2);
    }
    return Texture.from(canvas);
  };

  // Reusable node sprite & label creation helper
  const createNodeVisuals = useCallback(
    (
      n: GraphNode,
      deg: number,
      circleTexture: Texture,
      auraTexture: Texture,
      viewport: Container,
      worker: Worker,
      aurasContainer: Container,
      nodesContainer: Container,
      labelsContainer: Container
    ) => {
      const radius = 6 + (n.val || 10) * 0.35;
      const nodeColor = hexToNumber(n.color);
      const isHub = deg >= 5 || (n.val || 10) >= 20;

      // Aura Sprite
      const auraSprite = new Sprite(auraTexture);
      auraSprite.anchor.set(0.5);
      auraSprite.tint = nodeColor;
      auraSprite.width = radius * 3.8;
      auraSprite.height = radius * 3.8;
      auraSprite.alpha = isHub ? 0.55 : 0.22;
      aurasContainer.addChild(auraSprite);

      // Core Node Sprite
      const sprite = new Sprite(circleTexture);
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

        const localPos = viewport.toLocal(e.global);
        worker.postMessage({
          type: 'DRAG_START',
          id: n.id,
          x: localPos.x,
          y: localPos.y,
        } as WorkerInMessage);
      });

      const handleGlobalMove = (e: { global: { x: number; y: number } }) => {
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

      // High-Contrast Hierarchy Text Label with Protective Stroke Outline
      const titleText = n.name.split(': ').slice(1).join(': ') || n.name;
      const shortTitle = titleText.length > 28 ? titleText.slice(0, 26) + '…' : titleText;

      const fontSize = isHub ? 11.5 : (deg >= 3 ? 10 : 9);
      const fontWeight = isHub ? '700' : (deg >= 3 ? '600' : '500');

      const label = new Text({
        text: shortTitle,
        style: new TextStyle({
          fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
          fontSize,
          fontWeight: fontWeight as TextStyle['fontWeight'],
          fill: isDarkMode ? 0xf0f5ff : 0x0f172a,
          stroke: {
            color: isDarkMode ? 0x050811 : 0xffffff,
            width: isDarkMode ? 3.6 : 3.0,
            join: 'round',
          },
          align: 'center',
        }),
      });
      label.anchor.set(0.5, 0);
      labelsContainer.addChild(label);

      return { auraSprite, sprite, label };
    },
    [isDarkMode, onHoverNode, onSelectNode, updateSpotlight]
  );

  // 7. Initialize PixiJS Application, Web Worker, & 60 FPS Render Ticker
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
    let auraTexture: Texture | null = null;

    const initPixi = async () => {
      await app.init({
        antialias: true,
        autoDensity: true,
        resolution: window.devicePixelRatio || 1,
        backgroundColor: isDarkMode ? 0x050811 : 0xf4f7fc,
        resizeTo: container,
      });

      if (isDestroyed) {
        app.destroy(true, { children: true });
        return;
      }

      container.appendChild(app.canvas);

      // Generate sharp circle & smooth radial aura textures
      circleTexture = createCircleTexture(app, 32);
      auraTexture = createAuraTexture(56);

      // A. Starfield / Cosmic Dust Background Layer
      const starfieldGraphics = new Graphics();
      app.stage.addChild(starfieldGraphics);
      starfieldGraphicsRef.current = starfieldGraphics;

      const stars: StarParticle[] = [];
      const starCount = 130;
      for (let i = 0; i < starCount; i++) {
        stars.push({
          x: Math.random() * container.clientWidth,
          y: Math.random() * container.clientHeight,
          radius: 0.75 + Math.random() * 1.5,
          baseAlpha: 0.15 + Math.random() * 0.45,
          twinkleSpeed: 1.2 + Math.random() * 2.5,
          phase: Math.random() * Math.PI * 2,
        });
      }

      // B. Camera Viewport Container
      const viewport = new Container();
      viewport.position.set(container.clientWidth / 2, container.clientHeight / 2);
      viewport.scale.set(0.85);
      app.stage.addChild(viewport);
      viewportRef.current = viewport;

      // 1. Edges Graphics Layer (Base lines)
      const edgesGraphics = new Graphics();
      viewport.addChild(edgesGraphics);
      edgesGraphicsRef.current = edgesGraphics;

      // 2. Pulse Graphics Layer (Additive Traveling Photons & Comet Tails)
      const pulseGraphics = new Graphics();
      pulseGraphics.blendMode = 'add';
      viewport.addChild(pulseGraphics);
      pulseGraphicsRef.current = pulseGraphics;

      // 3. Node Aura Sprites Layer (Additive Radial Breathing Glows)
      const aurasContainer = new Container();
      aurasContainer.blendMode = 'add';
      viewport.addChild(aurasContainer);

      // 4. Node Sprites Layer (Circles)
      const nodesContainer = new Container();
      viewport.addChild(nodesContainer);

      // 5. Semantic Edge Badges Layer (Floating Relation Pills)
      const edgeBadgesContainer = new Container();
      viewport.addChild(edgeBadgesContainer);
      edgeBadgesContainerRef.current = edgeBadgesContainer;

      // 6. Labels Container Layer (Text with Stroke Outline)
      const labelsContainer = new Container();
      viewport.addChild(labelsContainer);

      aurasContainerRef.current = aurasContainer;
      nodesContainerRef.current = nodesContainer;
      labelsContainerRef.current = labelsContainer;
      circleTextureRef.current = circleTexture;
      auraTextureRef.current = auraTexture;

      // Populate Initial Node Sprites, Auras & High-Contrast Labels
      const spritesMap = new Map<string, Sprite>();
      const aurasMap = new Map<string, Sprite>();
      const labelsMap = new Map<string, Text>();
      const posMap = new Map<string, { x: number; y: number }>();

      nodesRef.current.forEach((n) => {
        const degree = degreeMap.get(n.id) || 0;
        const { auraSprite, sprite, label } = createNodeVisuals(
          n,
          degree,
          circleTexture!,
          auraTexture!,
          viewport,
          worker,
          aurasContainer,
          nodesContainer,
          labelsContainer
        );

        spritesMap.set(n.id, sprite);
        aurasMap.set(n.id, auraSprite);
        labelsMap.set(n.id, label);
        posMap.set(n.id, { x: 0, y: 0 });
      });

      nodeSpritesRef.current = spritesMap;
      nodeAuraSpritesRef.current = aurasMap;
      labelTextsRef.current = labelsMap;
      nodePositionsRef.current = posMap;

      // Initialize Photons Pool for Edges
      const photons: EdgePhoton[] = [];
      edgesRef.current.forEach((edge) => {
        const count = Math.random() > 0.4 ? 2 : 1;
        for (let i = 0; i < count; i++) {
          photons.push({
            sourceId: edge.source,
            targetId: edge.target,
            edgeType: edge.type || 'CONNECTS_TO',
            progress: Math.random(),
            speed: 0.18 + Math.random() * 0.26,
            size: 1.8 + Math.random() * 1.4,
          });
        }
      });
      photonsRef.current = photons;

      // Handle Worker Output Messages (Tick)
      worker.onmessage = (e: MessageEvent<WorkerOutMessage>) => {
        const msg = e.data;
        if (msg.type === 'TICK') {
          msg.positions.forEach((p) => {
            const sprite = nodeSpritesRef.current.get(p.id);
            const aura = nodeAuraSpritesRef.current.get(p.id);
            const label = labelTextsRef.current.get(p.id);
            nodePositionsRef.current.set(p.id, { x: p.x, y: p.y });

            if (sprite) {
              sprite.position.set(p.x, p.y);
            }
            if (aura) {
              aura.position.set(p.x, p.y);
            }
            if (label && sprite) {
              label.position.set(p.x, p.y + sprite.height / 2 + 3);
            }
          });

          drawEdges();
        }
      };

      // Continuous 60 FPS Render Loop via app.ticker
      let elapsedSeconds = 0;
      app.ticker.add((ticker) => {
        const dt = ticker.deltaTime / 60;
        elapsedSeconds += dt;

        // 1. Animate Cosmic Starfield Dust
        starfieldGraphics.clear();
        const starColor = isDarkMode ? 0x00f0ff : 0x0284c7;

        for (let i = 0; i < stars.length; i++) {
          const star = stars[i];
          const twinkle = Math.sin(elapsedSeconds * star.twinkleSpeed + star.phase) * 0.15;
          const currentAlpha = Math.max(0.05, Math.min(0.85, star.baseAlpha + twinkle));

          starfieldGraphics.circle(star.x, star.y, star.radius);
          starfieldGraphics.fill({
            color: starColor,
            alpha: isDarkMode ? currentAlpha : currentAlpha * 0.6,
          });
        }

        // 2. Animate Traveling Photons & Comet Tails along Edges
        pulseGraphics.clear();
        const currentPhotons = photonsRef.current;
        const focusId = hoveredNodeIdRef.current || selectedNodeIdRef.current;
        const isFocusActive = focusId !== null;

        for (let i = 0; i < currentPhotons.length; i++) {
          const p = currentPhotons[i];
          const isEdgeConnectedToFocus =
            isFocusActive && (p.sourceId === focusId || p.targetId === focusId);

          // Speed boost and particle size spike for focused connections
          const currentSpeed = isEdgeConnectedToFocus ? p.speed * 2.4 : p.speed;
          p.progress = (p.progress + currentSpeed * dt) % 1.0;

          const a = posMap.get(p.sourceId);
          const b = posMap.get(p.targetId);
          if (!a || !b) continue;

          const px = a.x + (b.x - a.x) * p.progress;
          const py = a.y + (b.y - a.y) * p.progress;

          const photonColor = isEdgeConnectedToFocus
            ? 0x00ffcc
            : isDarkMode
            ? 0x00f0ff
            : 0x0284c7;

          const photonAlpha = isEdgeConnectedToFocus
            ? 1.0
            : isFocusActive
            ? 0.08
            : isDarkMode
            ? 0.75
            : 0.55;

          const particleRadius = isEdgeConnectedToFocus ? p.size * 1.45 : p.size;

          // Head of photon
          pulseGraphics.circle(px, py, particleRadius);
          pulseGraphics.fill({ color: photonColor, alpha: photonAlpha });

          // Glowing Comet Tail
          const tailProgress = Math.max(0, p.progress - 0.075);
          const tx = a.x + (b.x - a.x) * tailProgress;
          const ty = a.y + (b.y - a.y) * tailProgress;

          pulseGraphics.setStrokeStyle({
            width: isEdgeConnectedToFocus ? 2.4 : 1.2,
            color: photonColor,
            alpha: photonAlpha * 0.45,
          });
          pulseGraphics.moveTo(tx, ty);
          pulseGraphics.lineTo(px, py);
          pulseGraphics.stroke();
        }

        // 3. Animate Breathing Aura Glows on Hubs & Focused Nodes
        aurasMap.forEach((auraSprite, id) => {
          const isFocus = id === focusId;
          const degree = hubDegreeMapRef.current.get(id) || 0;
          const isHub = degree >= 5;

          if (isFocus || isHub) {
            auraSprite.visible = true;
            const breath = Math.sin(elapsedSeconds * 2.8 + (id.charCodeAt(0) % 7)) * 0.2;
            const baseScale = isFocus ? 1.45 : 1.15;
            auraSprite.scale.set(baseScale + breath * 0.15);
            auraSprite.alpha = isFocus
              ? Math.min(1.0, 0.75 + breath)
              : Math.min(0.65, 0.38 + breath * 0.4);
          } else if (isFocusActive) {
            auraSprite.visible = false;
          } else {
            auraSprite.visible = true;
            auraSprite.alpha = 0.18;
          }
        });
      });

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

    // 8. Camera Pan & Zoom Event Handlers (Canvas Background)
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

      if (circleTextureRef.current) {
        circleTextureRef.current.destroy(true);
        circleTextureRef.current = null;
      }
      if (auraTextureRef.current) {
        auraTextureRef.current.destroy(true);
        auraTextureRef.current = null;
      }

      if (appRef.current) {
        appRef.current.destroy(true, { children: true });
        appRef.current = null;
      }

      aurasContainerRef.current = null;
      nodesContainerRef.current = null;
      labelsContainerRef.current = null;
      isFirstMountRef.current = true;
    };
  }, [isDarkMode]); // eslint-disable-line react-hooks/exhaustive-deps

  // 8. Seamless Incremental Reconciliation when nodes/edges update (Zero-Blink)
  useEffect(() => {
    if (isFirstMountRef.current) {
      isFirstMountRef.current = false;
      return;
    }

    const worker = workerRef.current;
    const viewport = viewportRef.current;
    const aurasContainer = aurasContainerRef.current;
    const nodesContainer = nodesContainerRef.current;
    const labelsContainer = labelsContainerRef.current;
    const circleTexture = circleTextureRef.current;
    const auraTexture = auraTextureRef.current;

    if (!worker || !viewport || !aurasContainer || !nodesContainer || !labelsContainer || !circleTexture || !auraTexture) {
      return;
    }

    const currentSprites = nodeSpritesRef.current;
    const currentAuras = nodeAuraSpritesRef.current;
    const currentLabels = labelTextsRef.current;
    const currentPositions = nodePositionsRef.current;

    const nextNodeIds = new Set(nodes.map((n) => n.id));

    // A. Remove deleted nodes from Pixi stage and tracking maps
    currentSprites.forEach((sprite, id) => {
      if (!nextNodeIds.has(id)) {
        nodesContainer.removeChild(sprite);
        sprite.destroy();
        currentSprites.delete(id);

        const aura = currentAuras.get(id);
        if (aura) {
          aurasContainer.removeChild(aura);
          aura.destroy();
          currentAuras.delete(id);
        }

        const label = currentLabels.get(id);
        if (label) {
          labelsContainer.removeChild(label);
          label.destroy();
          currentLabels.delete(id);
        }

        currentPositions.delete(id);
      }
    });

    // B. Add new nodes or update existing nodes without disturbing positions
    nodes.forEach((n) => {
      const deg = degreeMap.get(n.id) || 0;
      if (!currentSprites.has(n.id)) {
        const { auraSprite, sprite, label } = createNodeVisuals(
          n,
          deg,
          circleTexture,
          auraTexture,
          viewport,
          worker,
          aurasContainer,
          nodesContainer,
          labelsContainer
        );

        currentAuras.set(n.id, auraSprite);
        currentSprites.set(n.id, sprite);
        currentLabels.set(n.id, label);

        const initX = (Math.random() - 0.5) * 80;
        const initY = (Math.random() - 0.5) * 80;
        currentPositions.set(n.id, { x: initX, y: initY });
        sprite.position.set(initX, initY);
        auraSprite.position.set(initX, initY);
        label.position.set(initX, initY + sprite.height / 2 + 3);
      } else {
        const sprite = currentSprites.get(n.id);
        const aura = currentAuras.get(n.id);
        const nodeColor = hexToNumber(n.color);
        if (sprite) sprite.tint = nodeColor;
        if (aura) aura.tint = nodeColor;
      }
    });

    // C. Update edge photons pool
    const nextPhotons: EdgePhoton[] = [];
    edges.forEach((edge) => {
      const count = Math.random() > 0.4 ? 2 : 1;
      for (let i = 0; i < count; i++) {
        nextPhotons.push({
          sourceId: edge.source,
          targetId: edge.target,
          edgeType: edge.type || 'CONNECTS_TO',
          progress: Math.random(),
          speed: 0.18 + Math.random() * 0.26,
          size: 1.8 + Math.random() * 1.4,
        });
      }
    });
    photonsRef.current = nextPhotons;

    // D. Send incremental delta to Web Worker
    worker.postMessage({
      type: 'UPDATE_DATA',
      nodes: nodes.map((n) => ({ id: n.id, val: n.val })),
      links: edges.map((e) => ({ source: e.source, target: e.target, type: e.type })),
    } as WorkerInMessage);

    // E. Redraw base edges and update highlights seamlessly
    drawEdges();
    updateSpotlight();
    updateLabelVisibility();
  }, [nodes, edges, degreeMap, createNodeVisuals, drawEdges, updateSpotlight, updateLabelVisibility]);

  // 9. Update physics parameters in worker
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

  // 10. Focus camera smoothly on a specific node
  const handleFocusNode = (nodeId: string) => {
    const pos = nodePositionsRef.current.get(nodeId);
    const viewport = viewportRef.current;
    const container = containerRef.current;
    if (!pos || !viewport || !container) return;

    const targetNode = nodes.find((n) => n.id === nodeId);
    if (targetNode) onSelectNode(targetNode);

    const targetScale = 1.3;
    const targetX = container.clientWidth / 2 - pos.x * targetScale;
    const targetY = container.clientHeight / 2 - pos.y * targetScale;

    viewport.scale.set(targetScale);
    viewport.position.set(targetX, targetY);

    updateSpotlight();
    updateLabelVisibility();
  };

  // 11. Reset Camera / Fit to Screen
  const handleResetCamera = () => {
    const viewport = viewportRef.current;
    const container = containerRef.current;
    if (!viewport || !container) return;

    viewport.scale.set(0.85);
    viewport.position.set(container.clientWidth / 2, container.clientHeight / 2);

    updateSpotlight();
    updateLabelVisibility();
  };

  // 12. Reheat Simulation
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
