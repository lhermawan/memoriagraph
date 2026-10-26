import React, { useState, useMemo } from 'react';
import type { GraphNode, PhysicsParams } from '../types/graph';
import { 
  Sliders, 
  Search, 
  Flame, 
  ChevronDown, 
  ChevronUp, 
  Maximize2, 
  Eye,
  EyeOff
} from 'lucide-react';

interface GraphControlsProps {
  nodes: GraphNode[];
  params: PhysicsParams;
  onUpdateParams: (params: Partial<PhysicsParams>) => void;
  onFocusNode: (nodeId: string) => void;
  onResetCamera: () => void;
  onReheatSimulation: () => void;
  showLabels: boolean;
  onToggleLabels: () => void;
}

export const GraphControls: React.FC<GraphControlsProps> = ({
  nodes,
  params,
  onUpdateParams,
  onFocusNode,
  onResetCamera,
  onReheatSimulation,
  showLabels,
  onToggleLabels,
}) => {
  const [isOpen, setIsOpen] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  // Search filter
  const searchResults = useMemo(() => {
    if (!searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase();
    return nodes
      .filter((n) => n.name.toLowerCase().includes(q) || (n.full_name && n.full_name.toLowerCase().includes(q)))
      .slice(0, 6);
  }, [nodes, searchQuery]);

  return (
    <div className="absolute top-4 left-4 z-20 flex flex-col gap-2 max-w-xs w-72 select-none">
      {/* Search Bar */}
      <div className="relative bg-slate-900/85 backdrop-blur-md border border-slate-700/60 rounded-xl shadow-2xl p-2 text-xs flex items-center gap-2">
        <Search className="w-4 h-4 text-slate-400 shrink-0 ml-1" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => {
            setSearchQuery(e.target.value);
            setIsSearching(true);
          }}
          onFocus={() => setIsSearching(true)}
          placeholder="Cari simpul di kanvas..."
          className="w-full bg-transparent border-none text-slate-100 placeholder:text-slate-500 focus:outline-none font-mono text-[11px]"
        />
        {searchQuery && (
          <button
            onClick={() => {
              setSearchQuery('');
              setIsSearching(false);
            }}
            className="text-slate-400 hover:text-slate-200 px-1 font-bold text-xs"
          >
            ×
          </button>
        )}

        {/* Autocomplete Dropdown */}
        {isSearching && searchResults.length > 0 && (
          <div className="absolute top-full left-0 right-0 mt-1 bg-slate-900/95 backdrop-blur-md border border-slate-700/70 rounded-xl shadow-2xl overflow-hidden py-1 z-30">
            {searchResults.map((n) => (
              <div
                key={n.id}
                onClick={() => {
                  onFocusNode(n.id);
                  setSearchQuery(n.name.split(': ').slice(1).join(': ') || n.name);
                  setIsSearching(false);
                }}
                className="px-3 py-1.5 hover:bg-slate-800/80 cursor-pointer flex items-center justify-between text-[11px] transition-colors"
              >
                <div className="flex items-center gap-2 truncate">
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: n.color }} />
                  <span className="text-slate-200 truncate">{n.name}</span>
                </div>
                <span className="text-[9px] font-mono text-slate-400 uppercase shrink-0 ml-2">{n.label}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Floating Control Card ala Obsidian */}
      <div className="bg-slate-900/85 backdrop-blur-md border border-slate-700/60 rounded-xl shadow-2xl text-xs overflow-hidden transition-all">
        {/* Card Header */}
        <div 
          onClick={() => setIsOpen((prev) => !prev)}
          className="px-3.5 py-2.5 flex items-center justify-between cursor-pointer hover:bg-slate-800/50 transition-colors"
        >
          <div className="flex items-center gap-2 font-mono font-semibold text-slate-300 tracking-wide text-[11px]">
            <Sliders className="w-3.5 h-3.5 text-cyan-400" />
            <span>GRAF FISIKA & KAMERA</span>
          </div>
          <button className="text-slate-400 hover:text-slate-200">
            {isOpen ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
        </div>

        {/* Card Body */}
        {isOpen && (
          <div className="p-3.5 pt-1 space-y-3 border-t border-slate-800/80">
            {/* Repel Force */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                <span>Repel (Gaya Tolak):</span>
                <span className="text-cyan-400 font-bold">{params.repelStrength}</span>
              </div>
              <input
                type="range"
                min="-800"
                max="-40"
                step="20"
                value={params.repelStrength}
                onChange={(e) => onUpdateParams({ repelStrength: Number(e.target.value) })}
                className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
              />
            </div>

            {/* Link Distance */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                <span>Link Distance (Jarak):</span>
                <span className="text-cyan-400 font-bold">{params.linkDistance}px</span>
              </div>
              <input
                type="range"
                min="40"
                max="260"
                step="10"
                value={params.linkDistance}
                onChange={(e) => onUpdateParams({ linkDistance: Number(e.target.value) })}
                className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
              />
            </div>

            {/* Node Size Multiplier */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                <span>Node Scale:</span>
                <span className="text-cyan-400 font-bold">{params.nodeSizeMult.toFixed(2)}x</span>
              </div>
              <input
                type="range"
                min="0.3"
                max="1.8"
                step="0.05"
                value={params.nodeSizeMult}
                onChange={(e) => onUpdateParams({ nodeSizeMult: Number(e.target.value) })}
                className="w-full h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
              />
            </div>

            {/* Actions Bar */}
            <div className="grid grid-cols-3 gap-1.5 pt-2 border-t border-slate-800/80 text-[10px]">
              <button
                onClick={onResetCamera}
                className="flex items-center justify-center gap-1 p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
                title="Fit to Screen & Reset View"
              >
                <Maximize2 className="w-3 h-3 text-cyan-400" />
                <span>Fit</span>
              </button>

              <button
                onClick={onReheatSimulation}
                className="flex items-center justify-center gap-1 p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
                title="Reheat simulasi fisika"
              >
                <Flame className="w-3 h-3 text-amber-400" />
                <span>Reheat</span>
              </button>

              <button
                onClick={onToggleLabels}
                className="flex items-center justify-center gap-1 p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
                title="Toggle teks label"
              >
                {showLabels ? <Eye className="w-3 h-3 text-emerald-400" /> : <EyeOff className="w-3 h-3 text-slate-500" />}
                <span>Labels</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
