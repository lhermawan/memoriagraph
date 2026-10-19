import React, { useRef, useEffect, useState, useCallback } from 'react';
import type { GraphNode, GraphEdge } from '../types/graph';

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

interface Particle {
  edge: GraphEdge;
  t: number;
  dir: number;
  speed: number;
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
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Pan & Zoom state
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const isPanningRef = useRef(false);
  const startPanRef = useRef({ x: 0, y: 0 });

  // Dragging state
  const dragNodeRef = useRef<GraphNode | null>(null);
  const hasMovedRef = useRef(false);
  const particlesRef = useRef<Particle[]>([]);
  const lastSpawnRef = useRef(0);
  const animFrameRef = useRef<number | null>(null);

  // Node Map by ID
  const nodeMapRef = useRef<Map<string, GraphNode>>(new Map());

  // Initialize node physics properties
  useEffect(() => {
    const nodeMap = new Map<string, GraphNode>();
    nodes.forEach((n) => {
      nodeMap.set(n.id, n);
      if (n.r === undefined) n.r = 8 + (n.val || 10) * 0.45;
      if (n.ph === undefined) n.ph = Math.random();
      if (n.x === undefined || n.y === undefined) {
        n.x = (window.innerWidth / 2) + (Math.random() - 0.5) * 400;
        n.y = (window.innerHeight / 2) + (Math.random() - 0.5) * 400;
        n.vx = 0;
        n.vy = 0;
        n.flash = 0;
      }
    });
    nodeMapRef.current = nodeMap;

    // Attach node references to edges
    edges.forEach((e) => {
      e.a = nodeMap.get(e.source);
      e.b = nodeMap.get(e.target);
    });
  }, [nodes, edges]);

  // Particle Spawner
  const spawnParticle = useCallback((edge: GraphEdge) => {
    if (!edge || !edge.a || !edge.b) return;
    particlesRef.current.push({
      edge,
      t: 0,
      dir: Math.random() < 0.5 ? 1 : -1,
      speed: 0.007 + Math.random() * 0.008,
    });
  }, []);

  // Neighbors lookup
  const getNeighbors = useCallback(
    (targetNode: GraphNode) => {
      return edges.filter((e) => e.a === targetNode || e.b === targetNode);
    },
    [edges]
  );

  // Draw node shape
  const drawNodeShape = (ctx: CanvasRenderingContext2D, n: GraphNode, r: number) => {
    ctx.beginPath();
    const x = n.x || 0;
    const y = n.y || 0;

    if (n.label === 'Decision') {
      // Diamond
      ctx.moveTo(x, y - r * 1.3);
      ctx.lineTo(x + r * 1.3, y);
      ctx.lineTo(x, y + r * 1.3);
      ctx.lineTo(x - r * 1.3, y);
      ctx.closePath();
    } else if (n.label === 'Attempt') {
      // Square
      ctx.rect(x - r * 0.9, y - r * 0.9, r * 1.8, r * 1.8);
    } else if (n.label === 'Entity') {
      // Rounded Rectangle
      if (ctx.roundRect) {
        ctx.roundRect(x - r * 1.1, y - r * 0.8, r * 2.2, r * 1.6, 6);
      } else {
        ctx.rect(x - r * 1.1, y - r * 0.8, r * 2.2, r * 1.6);
      }
    } else if (n.label === 'Pattern') {
      // Hexagon
      const sides = 6;
      for (let i = 0; i < sides; i++) {
        const angle = (i * 2 * Math.PI) / sides;
        const px = x + r * 1.25 * Math.cos(angle);
        const py = y + r * 1.25 * Math.sin(angle);
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
    } else {
      // Circle for Episode, Problem, Reflection, etc.
      ctx.arc(x, y, r, 0, Math.PI * 2);
    }
  };

  // Convert hex color to rgba
  const hexToRgba = (hex: string, alpha: number) => {
    if (!hex || !hex.startsWith('#')) return `rgba(0, 240, 255, ${alpha})`;
    const n = parseInt(hex.slice(1), 16);
    return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
  };

  // Physics simulation tick
  const tickPhysics = useCallback(
    (width: number, height: number) => {
      const centerX = width / 2;
      const centerY = height / 2;

      // 1. Repulsion between nodes
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        if (a.x === undefined || a.y === undefined) continue;

        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          if (b.x === undefined || b.y === undefined) continue;

          let dx = a.x - b.x;
          let dy = a.y - b.y;
          const d2 = dx * dx + dy * dy + 60;
          const d = Math.sqrt(d2);
          const force = 4800 / d2;
          dx /= d;
          dy /= d;

          a.vx = (a.vx || 0) + dx * force;
          a.vy = (a.vy || 0) + dy * force;
          b.vx = (b.vx || 0) - dx * force;
          b.vy = (b.vy || 0) - dy * force;
        }

        // Center gravity
        a.vx = (a.vx || 0) + (centerX - a.x) * 0.0018;
        a.vy = (a.vy || 0) + (centerY - a.y) * 0.0018;
      }

      // 2. Spring forces along edges
      edges.forEach((e) => {
        if (!e.a || !e.b || e.a.x === undefined || e.b.x === undefined) return;
        const dx = e.b.x - e.a.x;
        const dy = (e.b.y || 0) - (e.a.y || 0);
        const d = Math.hypot(dx, dy) || 1;
        const springForce = (d - 130) * 0.014;
        const fx = (dx / d) * springForce;
        const fy = (dy / d) * springForce;

        e.a.vx = (e.a.vx || 0) + fx;
        e.a.vy = (e.a.vy || 0) + fy;
        e.b.vx = (e.b.vx || 0) - fx;
        e.b.vy = (e.b.vy || 0) - fy;
      });

      // 3. Integration & Damping
      nodes.forEach((n) => {
        if (n === dragNodeRef.current) {
          n.vx = 0;
          n.vy = 0;
          return;
        }
        n.vx = (n.vx || 0) * 0.85;
        n.vy = (n.vy || 0) * 0.85;
        n.x = (n.x || 0) + (n.vx || 0);
        n.y = (n.y || 0) + (n.vy || 0);

        // Bounding
        n.x = Math.max(40, Math.min(width - 40, n.x));
        n.y = Math.max(40, Math.min(height - 40, n.y));
      });
    },
    [nodes, edges]
  );

  // Main Render Loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animId: number;

    const render = (time: number) => {
      const width = canvas.clientWidth;
      const height = canvas.clientHeight;
      const dpr = window.devicePixelRatio || 1;

      if (canvas.width !== width * dpr || canvas.height !== height * dpr) {
        canvas.width = width * dpr;
        canvas.height = height * dpr;
      }

      ctx.save();
      ctx.setTransform(dpr * zoom, 0, 0, dpr * zoom, pan.x * dpr, pan.y * dpr);
      ctx.clearRect(
        -pan.x / zoom,
        -pan.y / zoom,
        width / zoom,
        height / zoom
      );

      // Advance physics
      tickPhysics(width, height);

      // Determine active focus neighborhood
      const focus = selectedNode || hoveredNode;
      const focusNeighbors = focus ? new Set([focus, ...getNeighbors(focus).flatMap((e) => [e.a, e.b])]) : null;

      const edgeBaseColor = isDarkMode ? '140, 160, 210' : '80, 95, 140';

      // 1. Draw Edges
      edges.forEach((e) => {
        if (!e.a || !e.b || e.a.x === undefined || e.b.x === undefined) return;
        const isFocusLink =
          focusNeighbors &&
          focusNeighbors.has(e.a) &&
          focusNeighbors.has(e.b) &&
          (e.a === focus || e.b === focus);

        const isHighlighted =
          highlightedIds && highlightedIds.has(e.a.id) && highlightedIds.has(e.b.id);

        let strokeColor = `rgba(${edgeBaseColor}, 0.15)`;
        let lineWidth = 1.0;

        if (isFocusLink || isHighlighted) {
          strokeColor = hexToRgba(e.a.color || '#00f0ff', 0.65);
          lineWidth = 2.2;
        } else if (focus) {
          strokeColor = `rgba(${edgeBaseColor}, 0.05)`;
        }

        ctx.strokeStyle = strokeColor;
        ctx.lineWidth = lineWidth;
        ctx.beginPath();
        ctx.moveTo(e.a.x, e.a.y || 0);
        ctx.lineTo(e.b.x, e.b.y || 0);
        ctx.stroke();

        // Edge label if hovered / focused
        if (isFocusLink) {
          const midX = (e.a.x + e.b.x) / 2;
          const midY = ((e.a.y || 0) + (e.b.y || 0)) / 2;
          ctx.font = '10px monospace';
          ctx.fillStyle = isDarkMode ? 'rgba(230, 236, 255, 0.7)' : 'rgba(16, 24, 51, 0.7)';
          ctx.textAlign = 'center';
          ctx.fillText(e.type, midX, midY - 4);
        }
      });

      // 2. Spawn and Draw Synaptic Particles
      if (time - lastSpawnRef.current > 320 && edges.length > 0) {
        lastSpawnRef.current = time;
        const randomEdge = edges[Math.floor(Math.random() * edges.length)];
        spawnParticle(randomEdge);
      }

      for (let i = particlesRef.current.length - 1; i >= 0; i--) {
        const p = particlesRef.current[i];
        p.t += p.speed;

        if (p.t >= 1) {
          const target = p.dir > 0 ? p.edge.b : p.edge.a;
          if (target) target.flash = 1;
          particlesRef.current.splice(i, 1);
          continue;
        }

        if (!p.edge.a || !p.edge.b || p.edge.a.x === undefined || p.edge.b.x === undefined) continue;

        const fraction = p.dir > 0 ? p.t : 1 - p.t;
        const px = p.edge.a.x + (p.edge.b.x - p.edge.a.x) * fraction;
        const py = (p.edge.a.y || 0) + ((p.edge.b.y || 0) - (p.edge.a.y || 0)) * fraction;
        const source = p.dir > 0 ? p.edge.a : p.edge.b;

        ctx.fillStyle = source.color || '#00f0ff';
        ctx.shadowColor = source.color || '#00f0ff';
        ctx.shadowBlur = 10;
        ctx.beginPath();
        ctx.arc(px, py, 2.8, 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }

      // 3. Draw Nodes
      nodes.forEach((n) => {
        if (n.x === undefined || n.y === undefined) return;

        const isDim =
          (focus && focusNeighbors && !focusNeighbors.has(n)) ||
          (highlightedIds && highlightedIds.size > 0 && !highlightedIds.has(n.id));

        const isFailed = n.status === 'FAILED';
        const alpha = isDim ? 0.16 : 1.0;
        const radius = n.r || 14;

        n.flash = (n.flash || 0) * 0.94;

        // Expanding Pulse Aura (if not failed and not dimmed)
        if (!isDim && !isFailed) {
          const phase = ((time / 1600) + (n.ph || 0)) % 1;
          ctx.strokeStyle = hexToRgba(n.color, (1 - phase) * 0.6);
          ctx.lineWidth = 1.6;
          ctx.beginPath();
          ctx.arc(n.x, n.y, radius + phase * 24, 0, Math.PI * 2);
          ctx.stroke();
        }

        // Flash Glow
        if ((n.flash || 0) > 0.02 && !isDim) {
          ctx.fillStyle = hexToRgba(n.color, (n.flash || 0) * 0.4);
          ctx.beginPath();
          ctx.arc(n.x, n.y, radius + 8 + (1 - (n.flash || 0)) * 14, 0, Math.PI * 2);
          ctx.fill();
        }

        // Main Node Body
        const effectiveRadius = radius * (1 + (n.flash || 0) * 0.16);
        ctx.shadowColor = n.color;
        ctx.shadowBlur = isDim ? 0 : isFailed ? 3 : 16;

        drawNodeShape(ctx, n, effectiveRadius);
        ctx.fillStyle = isFailed
          ? `rgba(100, 116, 139, ${alpha})`
          : hexToRgba(n.color, 0.28 * alpha + 0.08);
        ctx.fill();
        ctx.shadowBlur = 0;

        // Node Outline
        ctx.lineWidth = n === selectedNode ? 3.2 : 1.8;
        ctx.strokeStyle = isFailed
          ? `rgba(148, 163, 184, ${alpha})`
          : hexToRgba(n.color, alpha);
        ctx.stroke();

        // Node Label
        if (
          !isDim &&
          (n.label === 'Episode' ||
            n === hoveredNode ||
            n === selectedNode ||
            (focusNeighbors && focusNeighbors.has(n)) ||
            (highlightedIds && highlightedIds.has(n.id)))
        ) {
          ctx.font = '11px system-ui, sans-serif';
          ctx.textAlign = 'center';
          ctx.fillStyle = isDarkMode ? '#e6ecff' : '#101833';

          const text = n.name.split(': ').slice(1).join(': ') || n.name;
          const truncated = text.length > 30 ? text.slice(0, 28) + '…' : text;
          ctx.fillText(truncated, n.x, n.y + effectiveRadius + 15);
        }
      });

      ctx.restore();
      animId = requestAnimationFrame(render);
    };

    animId = requestAnimationFrame(render);
    animFrameRef.current = animId;

    return () => {
      cancelAnimationFrame(animId);
    };
  }, [
    nodes,
    edges,
    selectedNode,
    hoveredNode,
    highlightedIds,
    isDarkMode,
    zoom,
    pan,
    tickPhysics,
    getNeighbors,
    spawnParticle,
  ]);

  // Pointer Picking Math
  const pickNode = (clientX: number, clientY: number): GraphNode | null => {
    const canvas = canvasRef.current;
    if (!canvas) return null;
    const rect = canvas.getBoundingClientRect();
    const x = (clientX - rect.left - pan.x) / zoom;
    const y = (clientY - rect.top - pan.y) / zoom;

    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i];
      if (n.x === undefined || n.y === undefined) continue;
      const hitRadius = (n.r || 14) + 8;
      const dist = Math.hypot(n.x - x, n.y - y);
      if (dist <= hitRadius) {
        return n;
      }
    }
    return null;
  };

  // Pointer Event Listeners
  const handlePointerDown = (e: React.PointerEvent) => {
    const picked = pickNode(e.clientX, e.clientY);
    hasMovedRef.current = false;

    if (picked) {
      dragNodeRef.current = picked;
      if (canvasRef.current) {
        canvasRef.current.setPointerCapture(e.pointerId);
        canvasRef.current.style.cursor = 'grabbing';
      }
    } else {
      // Pan canvas
      isPanningRef.current = true;
      startPanRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
      if (canvasRef.current) {
        canvasRef.current.style.cursor = 'move';
      }
    }
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (dragNodeRef.current) {
      hasMovedRef.current = true;
      const canvas = canvasRef.current;
      if (!canvas) return;
      const rect = canvas.getBoundingClientRect();
      dragNodeRef.current.x = (e.clientX - rect.left - pan.x) / zoom;
      dragNodeRef.current.y = (e.clientY - rect.top - pan.y) / zoom;
    } else if (isPanningRef.current) {
      setPan({
        x: e.clientX - startPanRef.current.x,
        y: e.clientY - startPanRef.current.y,
      });
    } else {
      const hovered = pickNode(e.clientX, e.clientY);
      onHoverNode(hovered);
      if (canvasRef.current) {
        canvasRef.current.style.cursor = hovered ? 'pointer' : 'grab';
      }
    }
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (!hasMovedRef.current && !isPanningRef.current) {
      const clicked = pickNode(e.clientX, e.clientY);
      onSelectNode(clicked);
      if (clicked) clicked.flash = 1;
    }
    dragNodeRef.current = null;
    isPanningRef.current = false;
    if (canvasRef.current) {
      canvasRef.current.style.cursor = 'grab';
    }
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom((prev) => Math.min(2.5, Math.max(0.4, prev * zoomFactor)));
  };

  const handleResetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  return (
    <div ref={containerRef} className="relative w-full h-full cyber-grid overflow-hidden">
      <canvas
        ref={canvasRef}
        className="w-full h-full block touch-none cursor-grab"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onWheel={handleWheel}
      />

      {/* Canvas Viewport HUD Controls */}
      <div className="absolute left-4 bottom-4 flex items-center gap-2 bg-cyber-panel/85 hud-glass border border-cyber-border rounded-lg px-3 py-1.5 text-xs text-cyber-muted shadow-lg">
        <span>Zoom: {Math.round(zoom * 100)}%</span>
        <button
          onClick={handleResetView}
          className="ml-2 hover:text-cyan-400 border border-cyber-border/70 rounded px-2 py-0.5 transition-colors"
          title="Reset Pan & Zoom"
        >
          Reset View
        </button>
        <span className="text-[11px] opacity-75 hidden md:inline ml-2">
          | Drag simpul · Scroll zoom · Drag background geser
        </span>
      </div>
    </div>
  );
};
