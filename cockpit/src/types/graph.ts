export type CognitiveType = 
  | 'Episode' 
  | 'Problem' 
  | 'Attempt' 
  | 'Decision' 
  | 'Reflection' 
  | 'Pattern' 
  | 'Entity' 
  | 'Action' 
  | 'Outcome'
  | 'Curiosity'
  | 'Prototype'
  | 'Project';

export type BankId = 
  | 'infra-sre' 
  | 'csirt-security' 
  | 'ai-hud' 
  | 'research-personal' 
  | 'general';

export type IngestionStatus = 
  | 'VERIFIED_EMPIRICAL'
  | 'ACCEPTED_SHADOW'
  | 'QUARANTINED'
  | 'REJECTED'
  | 'RESOLVED'
  | 'FAILED'
  | 'SUCCESS'
  | 'APPLIED'
  | 'ACTIVE'
  | 'HEALTHY'
  | 'CONFIRMED'
  | 'AUTO_INGESTED';

export type ProvenanceType = 
  | 'OBSERVED' 
  | 'USER_REPORTED' 
  | 'INFERRED' 
  | 'ARTIFACT_VERIFIED';

export interface GraphNode {
  id: string;
  name: string;
  full_name?: string;
  label: CognitiveType;
  bank: BankId;
  color: string;
  val: number;
  confidence: number;
  status: IngestionStatus;
  provenance?: ProvenanceType;
  record_type?: string;
  dedupe_fingerprint?: string;
  problem?: string;
  mitigation?: string;
  solution?: string;
  heuristic?: string;
  empirical_anchor?: string;
  created_at?: string;
  // Physics engine runtime state
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  r?: number;
  flash?: number;
  ph?: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  // Runtime references
  a?: GraphNode;
  b?: GraphNode;
}

export interface CockpitGraphData {
  ok: boolean;
  service?: string;
  version?: string;
  total_nodes: number;
  total_links: number;
  bank_filter: string;
  clusters: string[];
  nodes: GraphNode[];
  links: GraphEdge[];
}

export const BANK_CONFIG: Record<BankId, { name: string; color: string; desc: string }> = {
  'infra-sre': {
    name: 'Infra SRE',
    color: '#00ff88',
    desc: 'Automated Operations, PM2, V8 Heap, Database Pooling & Incidents',
  },
  'csirt-security': {
    name: 'CSIRT Security',
    color: '#ff0055',
    desc: 'Defense, Auth Gateway, JWT Skew, Sanitizer & Ingestion Gate',
  },
  'ai-hud': {
    name: 'AI HUD / Friday',
    color: '#00f0ff',
    desc: 'F.R.I.D.A.Y. Cybernetic Core, Three.js WebGL & Dotpals Mesh',
  },
  'research-personal': {
    name: 'Research & Labs',
    color: '#b000ff',
    desc: 'Autonomous Exploration, LLM Heuristics & Experimental Models',
  },
  'general': {
    name: 'General Substrate',
    color: '#ffaa00',
    desc: 'Core Epistemology, Common Entities & Persistent Memory',
  },
};


export interface PhysicsParams {
  repelStrength: number;
  linkDistance: number;
  centerGravity: number;
  collideRadius: number;
  nodeSizeMult: number;
}
