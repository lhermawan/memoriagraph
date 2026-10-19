import { 
  forceSimulation, 
  forceLink, 
  forceManyBody, 
  forceCenter, 
  forceCollide,
  type Simulation,
  type SimulationNodeDatum,
  type SimulationLinkDatum
} from 'd3-force';

export interface WorkerNode extends SimulationNodeDatum {
  id: string;
  val?: number;
  r?: number;
}

export interface WorkerLink extends SimulationLinkDatum<WorkerNode> {
  source: string | WorkerNode;
  target: string | WorkerNode;
  type?: string;
}

export interface PhysicsParams {
  repelStrength: number;
  linkDistance: number;
  centerGravity: number;
  collideRadius: number;
  nodeSizeMult: number;
}

export type WorkerInMessage = 
  | { 
      type: 'INIT_GRAPH'; 
      nodes: { id: string; val?: number; x?: number; y?: number }[]; 
      links: { source: string; target: string; type?: string }[];
      params: PhysicsParams;
      width: number;
      height: number;
    }
  | { type: 'UPDATE_PARAMS'; params: Partial<PhysicsParams> }
  | { type: 'DRAG_START'; id: string; x: number; y: number }
  | { type: 'DRAG_MOVE'; id: string; x: number; y: number }
  | { type: 'DRAG_END'; id: string }
  | { type: 'REHEAT'; alpha?: number };

export type WorkerOutMessage = 
  | {
      type: 'TICK';
      positions: { id: string; x: number; y: number }[];
    }
  | {
      type: 'SIMULATION_END';
    };

let simulation: Simulation<WorkerNode, WorkerLink> | null = null;
let nodeMap = new Map<string, WorkerNode>();
let nodesList: WorkerNode[] = [];
let linksList: WorkerLink[] = [];

let currentParams: PhysicsParams = {
  repelStrength: -280,
  linkDistance: 100,
  centerGravity: 0.05,
  collideRadius: 18,
  nodeSizeMult: 1.0,
};

let centerWidth = 800;
let centerHeight = 600;

function initSimulation(
  rawNodes: { id: string; val?: number; x?: number; y?: number }[],
  rawLinks: { source: string; target: string; type?: string }[],
  params: PhysicsParams,
  width: number,
  height: number
) {
  if (simulation) {
    simulation.stop();
  }

  currentParams = { ...params };
  centerWidth = width;
  centerHeight = height;

  nodeMap.clear();
  nodesList = rawNodes.map((n) => {
    const node: WorkerNode = {
      id: n.id,
      x: n.x ?? width / 2 + (Math.random() - 0.5) * 300,
      y: n.y ?? height / 2 + (Math.random() - 0.5) * 300,
      val: n.val ?? 10,
      r: (6 + (n.val ?? 10) * 0.35) * currentParams.nodeSizeMult,
    };
    nodeMap.set(n.id, node);
    return node;
  });

  linksList = rawLinks.map((l) => ({
    source: l.source,
    target: l.target,
    type: l.type,
  }));

  const linkForce = forceLink<WorkerNode, WorkerLink>(linksList)
    .id((d) => d.id)
    .distance(currentParams.linkDistance);

  const chargeForce = forceManyBody<WorkerNode>()
    .strength(currentParams.repelStrength)
    .distanceMax(1200);

  const collideForce = forceCollide<WorkerNode>()
    .radius((d) => (d.r ?? 12) + currentParams.collideRadius)
    .iterations(2);

  const centerForce = forceCenter<WorkerNode>(centerWidth / 2, centerHeight / 2)
    .strength(currentParams.centerGravity);

  simulation = forceSimulation<WorkerNode, WorkerLink>(nodesList)
    .force('link', linkForce)
    .force('charge', chargeForce)
    .force('collide', collideForce)
    .force('center', centerForce)
    .alphaDecay(0.022)
    .velocityDecay(0.35);

  simulation.on('tick', () => {
    const positions = nodesList.map((n) => ({
      id: n.id,
      x: n.x ?? 0,
      y: n.y ?? 0,
    }));

    self.postMessage({
      type: 'TICK',
      positions,
    } as WorkerOutMessage);
  });

  simulation.on('end', () => {
    self.postMessage({ type: 'SIMULATION_END' } as WorkerOutMessage);
  });
}

function updateParams(params: Partial<PhysicsParams>) {
  if (!simulation) return;

  currentParams = { ...currentParams, ...params };

  const linkForce = simulation.force('link') as ReturnType<typeof forceLink<WorkerNode, WorkerLink>>;
  if (linkForce && params.linkDistance !== undefined) {
    linkForce.distance(currentParams.linkDistance);
  }

  const chargeForce = simulation.force('charge') as ReturnType<typeof forceManyBody<WorkerNode>>;
  if (chargeForce && params.repelStrength !== undefined) {
    chargeForce.strength(currentParams.repelStrength);
  }

  const centerForce = simulation.force('center') as ReturnType<typeof forceCenter<WorkerNode>>;
  if (centerForce && params.centerGravity !== undefined) {
    centerForce.strength(currentParams.centerGravity);
  }

  const collideForce = simulation.force('collide') as ReturnType<typeof forceCollide<WorkerNode>>;
  if (collideForce && (params.collideRadius !== undefined || params.nodeSizeMult !== undefined)) {
    nodesList.forEach((n) => {
      n.r = (6 + (n.val ?? 10) * 0.35) * currentParams.nodeSizeMult;
    });
    collideForce.radius((d) => (d.r ?? 12) + currentParams.collideRadius);
  }

  simulation.alpha(0.3).restart();
}

self.onmessage = (e: MessageEvent<WorkerInMessage>) => {
  const msg = e.data;
  switch (msg.type) {
    case 'INIT_GRAPH':
      initSimulation(msg.nodes, msg.links, msg.params, msg.width, msg.height);
      break;

    case 'UPDATE_PARAMS':
      updateParams(msg.params);
      break;

    case 'DRAG_START': {
      if (!simulation) break;
      const node = nodeMap.get(msg.id);
      if (node) {
        node.fx = msg.x;
        node.fy = msg.y;
        simulation.alphaTarget(0.25).restart();
      }
      break;
    }

    case 'DRAG_MOVE': {
      const node = nodeMap.get(msg.id);
      if (node) {
        node.fx = msg.x;
        node.fy = msg.y;
      }
      break;
    }

    case 'DRAG_END': {
      if (!simulation) break;
      const node = nodeMap.get(msg.id);
      if (node) {
        node.fx = null;
        node.fy = null;
        simulation.alphaTarget(0);
      }
      break;
    }

    case 'REHEAT': {
      if (simulation) {
        simulation.alpha(msg.alpha ?? 0.4).restart();
      }
      break;
    }
  }
};
