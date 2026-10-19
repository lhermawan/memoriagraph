import React, { useState, useEffect, useMemo, useCallback } from 'react';
import type { GraphNode, GraphEdge, BankId } from './types/graph';
import { fetchCockpitGraph } from './services/api';
import { Header } from './components/Header';
import { GraphCanvas } from './components/GraphCanvas';
import { InspectorDrawer } from './components/InspectorDrawer';
import { RecallSearch } from './components/RecallSearch';
import { IngestModal } from './components/IngestModal';

export const App: React.FC = () => {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [selectedBank, setSelectedBank] = useState<BankId | 'all'>('all');
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);
  const [highlightedIds, setHighlightedIds] = useState<Set<string>>(new Set());
  const [isLive, setIsLive] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Modals state
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isIngestOpen, setIsIngestOpen] = useState(false);

  // Theme state
  const [isDarkMode, setIsDarkMode] = useState(() => {
    return localStorage.getItem('mg_theme') !== 'light';
  });

  // Apply theme class
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
      localStorage.setItem('mg_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
      localStorage.setItem('mg_theme', 'light');
    }
  }, [isDarkMode]);

  // Load Graph Data
  const loadData = useCallback(async (bank?: BankId | 'all') => {
    setIsRefreshing(true);
    try {
      const { data, isLive: liveStatus } = await fetchCockpitGraph(
        bank && bank !== 'all' ? bank : undefined
      );
      setNodes(data.nodes);
      setEdges(data.links);
      setIsLive(liveStatus);

      // If selectedNode is no longer in nodes, deselect
      if (selectedNode) {
        const stillExists = data.nodes.find((n) => n.id === selectedNode.id);
        if (!stillExists) setSelectedNode(null);
      }
    } catch (err) {
      console.error('Failed to load cockpit graph data:', err);
    } finally {
      setIsRefreshing(false);
    }
  }, [selectedNode]);

  useEffect(() => {
    loadData(selectedBank);
  }, [selectedBank, loadData]);

  // Map of nodes for quick reference
  const nodeMap = useMemo(() => {
    const map = new Map<string, GraphNode>();
    nodes.forEach((n) => map.set(n.id, n));
    return map;
  }, [nodes]);

  // Handle Ingest of new memory
  const handleMemoryIngested = (newMemory: GraphNode) => {
    setNodes((prev) => [newMemory, ...prev]);
    setSelectedNode(newMemory);
    newMemory.flash = 1;
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-cyber-bg text-cyber-text">
      {/* Top Cybernetic Header */}
      <Header
        selectedBank={selectedBank}
        onSelectBank={setSelectedBank}
        isLive={isLive}
        isDarkMode={isDarkMode}
        onToggleTheme={() => setIsDarkMode((prev) => !prev)}
        onRefresh={() => loadData(selectedBank)}
        onOpenSearch={() => setIsSearchOpen(true)}
        onOpenIngest={() => setIsIngestOpen(true)}
        isRefreshing={isRefreshing}
      />

      {/* Main Workspace (Canvas + Inspector) */}
      <main className="flex-1 flex flex-col md:flex-row min-h-0 relative overflow-hidden">
        {/* Force-directed Graph Canvas */}
        <div className="flex-1 h-full min-h-0 relative">
          <GraphCanvas
            nodes={nodes}
            edges={edges}
            selectedNode={selectedNode}
            hoveredNode={hoveredNode}
            highlightedIds={highlightedIds}
            onSelectNode={setSelectedNode}
            onHoverNode={setHoveredNode}
            isDarkMode={isDarkMode}
          />
        </div>

        {/* Sidebar Inspector Drawer */}
        <InspectorDrawer
          node={selectedNode}
          edges={edges}
          onSelectNode={setSelectedNode}
          nodeMap={nodeMap}
        />
      </main>

      {/* Modals */}
      <RecallSearch
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        selectedBank={selectedBank}
        onHighlightNodes={setHighlightedIds}
      />

      <IngestModal
        isOpen={isIngestOpen}
        onClose={() => setIsIngestOpen(false)}
        onMemoryIngested={handleMemoryIngested}
      />
    </div>
  );
};

export default App;
