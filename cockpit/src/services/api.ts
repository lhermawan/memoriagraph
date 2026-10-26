import type { CockpitGraphData } from '../types/graph';
import { MOCK_GRAPH_DATA } from './mockData';

// Base URL defaults to window location origin or port 8085
const API_BASE = import.meta.env.VITE_API_URL || '';

export interface RetainPayload {
  content: string;
  bank_id?: string;
  category?: string;
  title?: string;
  heuristic?: string;
  decision?: string;
  outcome_status?: string;
  attempts?: string;
  record_type?: string;
  provenance?: string;
}

export interface RecallResult {
  query: string;
  bank?: string;
  result: string;
}

export async function fetchCockpitGraph(bankFilter?: string): Promise<{ data: CockpitGraphData; isLive: boolean }> {
  try {
    const url = new URL(`${API_BASE}/api/graph/cockpit`, window.location.origin);
    if (bankFilter && bankFilter !== 'all') {
      url.searchParams.set('bank', bankFilter);
    }
    const response = await fetch(url.toString(), {
      headers: { 'Accept': 'application/json' },
      signal: AbortSignal.timeout(3500),
    });

    if (!response.ok) {
      throw new Error(`HTTP error ${response.status}`);
    }

    const json = await response.json();
    if (json && json.ok && Array.isArray(json.nodes) && json.nodes.length > 0) {
      return { data: json, isLive: true };
    }
    throw new Error('Empty or invalid response from backend');
  } catch (err) {
    console.warn('[Cockpit API] Live backend unavailable, fallback to v3.2.0 mock data:', err);
    // Filter mock data by bank if requested
    if (bankFilter && bankFilter !== 'all') {
      const filteredNodes = MOCK_GRAPH_DATA.nodes.filter(n => n.bank === bankFilter);
      const nodeIds = new Set(filteredNodes.map(n => n.id));
      const filteredLinks = MOCK_GRAPH_DATA.links.filter(l => nodeIds.has(l.source) && nodeIds.has(l.target));
      return {
        data: {
          ...MOCK_GRAPH_DATA,
          bank_filter: bankFilter,
          total_nodes: filteredNodes.length,
          total_links: filteredLinks.length,
          nodes: filteredNodes,
          links: filteredLinks,
        },
        isLive: false,
      };
    }
    return { data: MOCK_GRAPH_DATA, isLive: false };
  }
}

export async function queryRecall(query: string, bank?: string): Promise<RecallResult> {
  const url = new URL(`${API_BASE}/recall`, window.location.origin);
  url.searchParams.set('query', query);
  url.searchParams.set('limit', '5');
  url.searchParams.set('compact', 'true');
  if (bank && bank !== 'all') {
    url.searchParams.set('bank', bank);
  }

  const response = await fetch(url.toString(), {
    headers: { 'Accept': 'application/json' },
    signal: AbortSignal.timeout(5000),
  });

  if (!response.ok) {
    throw new Error(`Recall error: ${response.statusText}`);
  }
  return response.json();
}

export async function submitRetain(payload: RetainPayload): Promise<{ status: string; message: string }> {
  const response = await fetch(`${API_BASE}/retain`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
    signal: AbortSignal.timeout(5000),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || 'Gagal menyimpan memori ke Ingestion Gate');
  }
  return data;
}
