import React, { useState } from 'react';
import type { BankId } from '../types/graph';
import { BANK_CONFIG } from '../types/graph';
import type { RecallResult } from '../services/api';
import { queryRecall } from '../services/api';
import { Search, X, Loader2, Sparkles, Target } from 'lucide-react';

interface RecallSearchProps {
  isOpen: boolean;
  onClose: () => void;
  selectedBank: BankId | 'all';
  onHighlightNodes: (nodeIds: Set<string>) => void;
}

export const RecallSearch: React.FC<RecallSearchProps> = ({
  isOpen,
  onClose,
  selectedBank,
  onHighlightNodes,
}) => {
  const [query, setQuery] = useState('');
  const [bank, setBank] = useState<string>(selectedBank === 'all' ? '' : selectedBank);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<RecallResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await queryRecall(query, bank || undefined);
      setResult(data);

      // Extract matching node labels or keywords from result and trigger highlight
      const rawText = data.result.toLowerCase();
      const matchedIds = new Set<string>();

      // Simple keyword matching to highlight relevant nodes in canvas
      if (rawText.includes('oom') || rawText.includes('heap') || rawText.includes('export')) {
        matchedIds.add('ep_sre_oom_worker');
        matchedIds.add('prob_oom_heap');
        matchedIds.add('att_increase_ram');
        matchedIds.add('att_stream_pipeline');
        matchedIds.add('dec_use_stream_ndjson');
        matchedIds.add('refl_stream_first');
      }
      if (rawText.includes('postgres') || rawText.includes('pgbouncer') || rawText.includes('connection')) {
        matchedIds.add('ep_db_pool_exhaustion');
        matchedIds.add('dec_pg_bouncer_pool');
        matchedIds.add('ent_postgres_db');
      }
      if (rawText.includes('jwt') || rawText.includes('clock') || rawText.includes('auth')) {
        matchedIds.add('ep_jwt_clock_skew');
        matchedIds.add('ent_auth_gateway');
      }
      if (rawText.includes('friday') || rawText.includes('audio') || rawText.includes('dotpals')) {
        matchedIds.add('ep_friday_dotpals_audio');
        matchedIds.add('pat_friday_governance');
      }

      onHighlightNodes(matchedIds);
    } catch (err: any) {
      console.warn('Live recall failed, simulating query match locally:', err);
      // Fallback search simulation for offline demo
      const matchedIds = new Set<string>();
      const q = query.toLowerCase();
      if (q.includes('oom') || q.includes('stream') || q.includes('ram') || q.includes('sre')) {
        matchedIds.add('ep_sre_oom_worker');
        matchedIds.add('prob_oom_heap');
        matchedIds.add('att_stream_pipeline');
        matchedIds.add('refl_stream_first');
        setResult({
          query,
          bank,
          result: `🔍 **[Local Hybrid Recall Mock Result]**\n- **Episode:** Batch Export Worker OOM Termination (Score: 0.98)\n- **Decision:** Adopt NDJSON Streaming Over In-Memory Buffers\n- **Reflection #42:** Always Stream Payloads > 50MB (Confidence: 0.99)\n- **Empirical Proof:** exit code 0, status 200 OK, 500k rows streamed in 4.2s`
        });
      } else if (q.includes('db') || q.includes('postgres') || q.includes('pool')) {
        matchedIds.add('ep_db_pool_exhaustion');
        matchedIds.add('dec_pg_bouncer_pool');
        matchedIds.add('ent_postgres_db');
        setResult({
          query,
          bank,
          result: `🔍 **[Local Hybrid Recall Mock Result]**\n- **Episode:** PostgreSQL Connection Starvation (Score: 0.92)\n- **Decision:** Introduce PgBouncer Transaction Pooling on port 6432\n- **Empirical Proof:** Active connections dropped from 100 to 14`
        });
      } else {
        setResult({
          query,
          bank,
          result: `🔍 **[Local Hybrid Recall Mock Result]**\n- Topik "${query}" dievaluasi via 4-Way Hybrid Recall (BM25 + Cypher + Temporal + FastEmbed ONNX).`
        });
      }
      onHighlightNodes(matchedIds);
    } finally {
      setLoading(false);
    }
  };

  const handleClearHighlight = () => {
    onHighlightNodes(new Set());
    setResult(null);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-xl bg-cyber-panel border border-cyber-border rounded-xl shadow-2xl p-6 space-y-4 hud-glass">
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-3 border-b border-cyber-border">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-cyan-400" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-cyber-text font-mono">
              4-Way Hybrid Recall Search
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-cyber-muted hover:text-cyber-text p-1 rounded hover:bg-cyber-card transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search Form */}
        <form onSubmit={handleSearch} className="space-y-3">
          <div className="relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Cari solusi / heuristik (mis: 'OOM worker', 'postgres connection', 'jwt skew')..."
              className="w-full bg-cyber-card/80 border border-cyber-border rounded-lg pl-10 pr-4 py-2.5 text-xs text-cyber-text placeholder:text-cyber-muted/60 focus:outline-none focus:border-cyan-500 font-mono"
              autoFocus
            />
            <Search className="w-4 h-4 text-cyber-muted absolute left-3 top-3" />
          </div>

          <div className="flex items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-cyber-muted">Bank:</span>
              <select
                value={bank}
                onChange={(e) => setBank(e.target.value)}
                className="bg-cyber-card border border-cyber-border rounded px-2 py-1 text-cyber-text text-xs focus:outline-none focus:border-cyan-500"
              >
                <option value="">Semua Bank</option>
                {Object.entries(BANK_CONFIG).map(([id, cfg]) => (
                  <option key={id} value={id}>
                    {cfg.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              {result && (
                <button
                  type="button"
                  onClick={handleClearHighlight}
                  className="px-3 py-1.5 rounded border border-cyber-border text-cyber-muted hover:text-cyber-text hover:bg-cyber-card"
                >
                  Clear Highlight
                </button>
              )}
              <button
                type="submit"
                disabled={loading || !query.trim()}
                className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-semibold shadow-neon-hud disabled:opacity-50"
              >
                {loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Target className="w-3.5 h-3.5" />}
                Pindai Graf
              </button>
            </div>
          </div>
        </form>

        {/* Results Area */}
        {result && (
          <div className="mt-4 p-4 rounded-lg bg-cyber-card/70 border border-cyan-500/30 space-y-2">
            <span className="text-[11px] font-semibold text-cyan-400 uppercase tracking-wider block">
              Hasil Recall Engine:
            </span>
            <pre className="text-xs font-mono text-cyber-text whitespace-pre-wrap leading-relaxed max-h-56 overflow-y-auto">
              {result.result}
            </pre>
          </div>
        )}

        {error && (
          <div className="p-3 rounded bg-rose-500/10 border border-rose-500/30 text-xs text-rose-400">
            {error}
          </div>
        )}
      </div>
    </div>
  );
};
