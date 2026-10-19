import React from 'react';
import type { GraphNode, GraphEdge } from '../types/graph';
import { BANK_CONFIG } from '../types/graph';
import { 
  ShieldCheck, 
  Activity, 
  Cpu, 
  AlertTriangle, 
  CheckCircle2, 
  XCircle, 
  Share2, 
  Fingerprint, 
  Terminal,
  Zap,
  HelpCircle,
  X
} from 'lucide-react';

interface InspectorDrawerProps {
  node: GraphNode | null;
  edges: GraphEdge[];
  onSelectNode: (node: GraphNode | null) => void;
  nodeMap: Map<string, GraphNode>;
}

export const InspectorDrawer: React.FC<InspectorDrawerProps> = ({
  node,
  edges,
  onSelectNode,
  nodeMap,
}) => {
  if (!node) {
    return (
      <aside className="w-80 md:w-96 border-l border-cyber-border bg-cyber-panel/95 hud-glass p-5 overflow-y-auto flex flex-col justify-between">
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Cpu className="w-5 h-5 text-cyan-400 animate-pulse" />
            <h2 className="text-sm font-semibold tracking-wider text-cyber-text uppercase">
              Kognisi Inspector
            </h2>
          </div>
          <div className="text-xs text-cyber-muted space-y-3 leading-relaxed">
            <p>
              Klik salah satu simpul graf untuk menginspeksi rantai kognitif, heuristik, bukti empiris, dan hubungan relasi Neo4j.
            </p>
            <div className="p-3 bg-cyber-card/60 border border-cyber-border/70 rounded-lg space-y-2">
              <span className="text-[11px] font-semibold text-cyber-text uppercase tracking-wide flex items-center gap-1.5">
                <Share2 className="w-3.5 h-3.5 text-cyan-400" /> Morfologi Simpul (Shape)
              </span>
              <ul className="text-[11px] space-y-1 text-cyber-muted">
                <li><b className="text-cyber-text">Lingkaran:</b> Episode, Problem, Reflection</li>
                <li><b className="text-cyber-text">Belah Ketupat:</b> Decision (Keputusan)</li>
                <li><b className="text-cyber-text">Kotak:</b> Attempt (Percobaan Solusi)</li>
                <li><b className="text-cyber-text">Persegi Bulat:</b> Entity (Service, Database)</li>
                <li><b className="text-cyber-text">Hexagon:</b> Crystallized Pattern</li>
              </ul>
            </div>
            <div className="p-3 bg-cyber-card/60 border border-cyber-border/70 rounded-lg space-y-2">
              <span className="text-[11px] font-semibold text-cyber-text uppercase tracking-wide flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-emerald-400" /> Synaptic Pulses
              </span>
              <p className="text-[11px]">
                Partikel neon yang mengalir di sepanjang garis menggambarkan aliran transfer memori & asosiasi aktif antar simpul di MemoriaGraph.
              </p>
            </div>
          </div>
        </div>

        <div className="pt-4 border-t border-cyber-border text-[11px] text-cyber-muted/80 flex items-center justify-between">
          <span>MemoriaGraph 3.1.2</span>
          <span className="flex items-center gap-1 text-emerald-400">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" /> Substrate Ready
          </span>
        </div>
      </aside>
    );
  }

  // Find connections
  const connectedEdges = edges.filter((e) => e.source === node.id || e.target === node.id);
  const bankInfo = BANK_CONFIG[node.bank] || { name: node.bank, color: node.color };

  // Status icon and color mapping
  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'VERIFIED_EMPIRICAL':
      case 'SUCCESS':
      case 'RESOLVED':
      case 'HEALTHY':
        return {
          icon: <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />,
          color: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
        };
      case 'FAILED':
      case 'REJECTED':
        return {
          icon: <XCircle className="w-3.5 h-3.5 text-rose-400" />,
          color: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
        };
      case 'QUARANTINED':
      case 'CONFIRMED':
        return {
          icon: <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />,
          color: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
        };
      case 'ACCEPTED_SHADOW':
        return {
          icon: <Activity className="w-3.5 h-3.5 text-cyan-400" />,
          color: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
        };
      default:
        return {
          icon: <HelpCircle className="w-3.5 h-3.5 text-slate-400" />,
          color: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
        };
    }
  };

  const statusBadge = getStatusBadge(node.status);
  const confidencePercent = Math.round(node.confidence * 100);

  return (
    <aside className="w-80 md:w-96 border-l border-cyber-border bg-cyber-panel/95 hud-glass p-5 overflow-y-auto flex flex-col gap-5">
      {/* Top Header */}
      <div>
        <div className="flex items-start justify-between gap-2 mb-2">
          <span 
            className="text-[10px] font-mono font-bold uppercase tracking-wider px-2 py-0.5 rounded border"
            style={{ 
              borderColor: node.color, 
              color: node.color, 
              backgroundColor: `${node.color}15` 
            }}
          >
            {node.label}
          </span>
          <button
            onClick={() => onSelectNode(null)}
            className="text-cyber-muted hover:text-cyber-text p-1 rounded hover:bg-cyber-card transition-colors"
            title="Tutup Inspector"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <h2 
          className="text-base font-semibold tracking-wide text-cyber-text leading-snug break-words"
          style={{ textShadow: `0 0 16px ${node.color}40` }}
        >
          {node.full_name || node.name}
        </h2>

        {/* Badges Bar */}
        <div className="flex flex-wrap items-center gap-1.5 mt-3">
          <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded border border-cyber-border bg-cyber-card/60 text-cyber-muted">
            <span className="w-2 h-2 rounded-full" style={{ backgroundColor: bankInfo.color }} />
            {bankInfo.name}
          </span>

          <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded border ${statusBadge.color}`}>
            {statusBadge.icon}
            {node.status}
          </span>

          {node.provenance && (
            <span className="inline-flex items-center gap-1 px-2 py-0.5 text-[11px] rounded border border-purple-500/30 bg-purple-500/10 text-purple-300">
              <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
              {node.provenance}
            </span>
          )}
        </div>
      </div>

      {/* Epistemic Confidence Meter */}
      <div className="p-3 bg-cyber-card/70 border border-cyber-border rounded-lg space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-cyber-muted font-medium flex items-center gap-1">
            <Activity className="w-3.5 h-3.5 text-cyan-400" /> Epistemic Confidence
          </span>
          <span className="font-mono font-bold text-cyber-text">{confidencePercent}%</span>
        </div>
        <div className="w-full bg-cyber-border/60 h-2 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${confidencePercent}%`,
              backgroundColor: node.color,
              boxShadow: `0 0 8px ${node.color}`,
            }}
          />
        </div>
        <div className="flex justify-between text-[10px] text-cyber-muted/80 font-mono">
          <span>0.0 CANDIDATE</span>
          <span>0.5 OBSERVED</span>
          <span>1.0 CRYSTALLIZED</span>
        </div>
      </div>

      {/* Empirical Anchor Verification (v3.1.2 Grounding) */}
      {node.empirical_anchor && (
        <div className="p-3 bg-emerald-950/20 border border-emerald-500/30 rounded-lg space-y-1.5">
          <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wide flex items-center gap-1.5">
            <Terminal className="w-3.5 h-3.5 text-emerald-400" /> Empirical Anchor (Grounding)
          </span>
          <p className="text-xs font-mono text-emerald-300 bg-cyber-bg/70 p-2 rounded border border-emerald-500/20">
            {node.empirical_anchor}
          </p>
        </div>
      )}

      {/* Dedupe Fingerprint */}
      {node.dedupe_fingerprint && (
        <div className="p-3 bg-cyber-card/50 border border-cyber-border/70 rounded-lg space-y-1">
          <span className="text-[10px] uppercase font-mono text-cyber-muted flex items-center gap-1">
            <Fingerprint className="w-3 h-3 text-cyan-400" /> Dedupe Fingerprint
          </span>
          <p className="text-xs font-mono text-cyan-300 truncate">
            {node.dedupe_fingerprint}
          </p>
        </div>
      )}

      {/* Problem, Mitigation & Solution Content */}
      <div className="space-y-3 text-xs leading-relaxed">
        {node.problem && (
          <div className="p-3 bg-cyber-card/40 border-l-2 border-amber-400 rounded-r-lg space-y-1">
            <b className="text-amber-400 uppercase tracking-wider text-[11px] block">Problem Anomali</b>
            <p className="text-cyber-text/90">{node.problem}</p>
          </div>
        )}

        {node.mitigation && (
          <div className="p-3 bg-cyber-card/40 border-l-2 border-cyan-400 rounded-r-lg space-y-1">
            <b className="text-cyan-400 uppercase tracking-wider text-[11px] block">Mitigasi Taktis</b>
            <p className="text-cyber-text/90">{node.mitigation}</p>
          </div>
        )}

        {node.solution && (
          <div className="p-3 bg-cyber-card/40 border-l-2 border-emerald-400 rounded-r-lg space-y-1">
            <b className="text-emerald-400 uppercase tracking-wider text-[11px] block">Solusi Definitif</b>
            <p className="text-cyber-text/90">{node.solution}</p>
          </div>
        )}

        {node.heuristic && (
          <div className="p-3 bg-purple-950/20 border-l-2 border-purple-400 rounded-r-lg space-y-1">
            <b className="text-purple-400 uppercase tracking-wider text-[11px] block">Heuristik Kognitif</b>
            <p className="text-purple-200">{node.heuristic}</p>
          </div>
        )}
      </div>

      {/* Connected Graph Neighbors */}
      <div className="space-y-2 pt-2 border-t border-cyber-border">
        <div className="flex items-center justify-between text-xs text-cyber-muted">
          <span className="font-semibold text-cyber-text uppercase tracking-wide flex items-center gap-1.5">
            <Share2 className="w-3.5 h-3.5 text-cyan-400" /> Relasi Terhubung ({connectedEdges.length})
          </span>
        </div>

        <ul className="space-y-1.5">
          {connectedEdges.map((e, idx) => {
            const isOutgoing = e.source === node.id;
            const targetId = isOutgoing ? e.target : e.source;
            const neighbor = nodeMap.get(targetId);
            if (!neighbor) return null;

            return (
              <li
                key={`${e.source}-${e.target}-${idx}`}
                onClick={() => onSelectNode(neighbor)}
                className="group flex items-center justify-between p-2 rounded bg-cyber-card/40 hover:bg-cyber-card border border-cyber-border/60 hover:border-cyan-500/50 cursor-pointer transition-all text-xs"
              >
                <div className="flex items-center gap-2 truncate">
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: neighbor.color }}
                  />
                  <span className="truncate text-cyber-text group-hover:text-cyan-300">
                    {neighbor.name.split(': ').slice(1).join(': ') || neighbor.name}
                  </span>
                </div>
                <span className="text-[10px] font-mono text-cyber-muted/80 group-hover:text-cyber-muted shrink-0 ml-2">
                  {isOutgoing ? `→ ${e.type}` : `← ${e.type}`}
                </span>
              </li>
            );
          })}
        </ul>
      </div>
    </aside>
  );
};
