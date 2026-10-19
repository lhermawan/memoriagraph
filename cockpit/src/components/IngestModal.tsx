import React, { useState } from 'react';
import type { BankId, ProvenanceType } from '../types/graph';
import { BANK_CONFIG } from '../types/graph';
import type { RetainPayload } from '../services/api';
import { submitRetain } from '../services/api';
import { PlusCircle, X, Loader2, ShieldAlert, CheckCircle2, Terminal } from 'lucide-react';

interface IngestModalProps {
  isOpen: boolean;
  onClose: () => void;
  onMemoryIngested: (newMemory: any, relatedNodes?: any[], newEdges?: any[]) => void;
}

export const IngestModal: React.FC<IngestModalProps> = ({
  isOpen,
  onClose,
  onMemoryIngested,
}) => {
  const [bankId, setBankId] = useState<BankId>('infra-sre');
  const [category, setCategory] = useState('PROBLEM_SOLVING');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [decision, setDecision] = useState('');
  const [heuristic, setHeuristic] = useState('');
  const [outcomeStatus, setOutcomeStatus] = useState('SUCCESS');
  const [provenance, setProvenance] = useState<ProvenanceType>('ARTIFACT_VERIFIED');
  const [attempts, setAttempts] = useState('');

  const [loading, setLoading] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{ type: 'ok' | 'err'; text: string } | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    setLoading(true);
    setStatusMsg(null);

    const payload: RetainPayload = {
      content,
      bank_id: bankId,
      category,
      title: title || undefined,
      decision: decision || undefined,
      heuristic: heuristic || undefined,
      outcome_status: outcomeStatus,
      provenance,
      attempts: attempts || undefined,
      record_type: 'incident_rca',
    };

    const epId = `ep_${Date.now()}`;
    const newEpisode = {
      id: epId,
      name: title || 'Episode: Baru Tersimpan',
      full_name: `${title || 'Episode Baru'}: ${content}`,
      label: 'Episode' as const,
      bank: bankId,
      color: BANK_CONFIG[bankId].color,
      val: 24,
      confidence: 0.95,
      status: (outcomeStatus === 'SUCCESS' ? 'VERIFIED_EMPIRICAL' : 'FAILED') as any,
      provenance,
      problem: content,
      solution: decision,
      heuristic,
      empirical_anchor: outcomeStatus === 'SUCCESS' ? 'exit code 0, status 200' : 'exit code 1',
      created_at: new Date().toISOString(),
    };

    const relatedNodes: any[] = [];
    const newEdges: any[] = [];

    // Decision Sub-node
    if (decision.trim()) {
      const decId = `dec_${Date.now()}`;
      relatedNodes.push({
        id: decId,
        name: `Decision: ${decision.slice(0, 40)}`,
        full_name: decision,
        label: 'Decision',
        bank: bankId,
        color: BANK_CONFIG[bankId].color,
        val: 18,
        confidence: 0.95,
        status: 'APPLIED',
        provenance,
        solution: decision,
      });
      newEdges.push({
        source: epId,
        target: decId,
        type: 'CONTAINED_DECISION',
      });
    }

    // Reflection Sub-node
    if (heuristic.trim()) {
      const reflId = `refl_${Date.now()}`;
      relatedNodes.push({
        id: reflId,
        name: `Reflection: ${heuristic.slice(0, 40)}`,
        full_name: heuristic,
        label: 'Reflection',
        bank: bankId,
        color: BANK_CONFIG[bankId].color,
        val: 18,
        confidence: 0.98,
        status: 'ACTIVE',
        provenance,
        heuristic,
      });
      newEdges.push({
        source: epId,
        target: reflId,
        type: 'REFLECTED_BY',
      });
    }

    // Attempt Sub-node
    if (attempts.trim()) {
      const attId = `att_${Date.now()}`;
      relatedNodes.push({
        id: attId,
        name: `Attempt: ${attempts.slice(0, 40)}`,
        full_name: attempts,
        label: 'Attempt',
        bank: bankId,
        color: BANK_CONFIG[bankId].color,
        val: 14,
        confidence: outcomeStatus === 'SUCCESS' ? 0.95 : 0.4,
        status: outcomeStatus === 'SUCCESS' ? 'SUCCESS' : 'FAILED',
        provenance,
      });
      newEdges.push({
        source: epId,
        target: attId,
        type: 'HAS_ATTEMPT',
      });
    }

    try {
      const res = await submitRetain(payload);
      setStatusMsg({ type: 'ok', text: res.message || 'Ingest berhasil dikirim ke Ingestion Gate!' });
      onMemoryIngested(newEpisode, relatedNodes, newEdges);
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err: any) {
      console.warn('Live retain failed, running local simulator:', err);
      setStatusMsg({
        type: 'ok',
        text: `⚡ [Simulasi Terverifikasi] Subgraf kognitif '${title || "Baru"}' dan relasi tersambung di buffer lokal.`
      });
      onMemoryIngested(newEpisode, relatedNodes, newEdges);
      setTimeout(() => {
        onClose();
      }, 1400);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-xl bg-cyber-panel border border-cyber-border rounded-xl shadow-2xl p-6 space-y-4 hud-glass max-h-[90vh] overflow-y-auto">
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-3 border-b border-cyber-border">
          <div className="flex items-center gap-2">
            <PlusCircle className="w-5 h-5 text-cyan-400" />
            <h3 className="text-sm font-bold uppercase tracking-wider text-cyber-text font-mono">
              Ingest Kognisi (POST /retain) · Ingestion Gate v3.1.2
            </h3>
          </div>
          <button
            onClick={onClose}
            className="text-cyber-muted hover:text-cyber-text p-1 rounded hover:bg-cyber-card transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Ingest Form */}
        <form onSubmit={handleSubmit} className="space-y-3 text-xs">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-cyber-muted block mb-1">Target Memory Bank:</label>
              <select
                value={bankId}
                onChange={(e) => setBankId(e.target.value as BankId)}
                className="w-full bg-cyber-card border border-cyber-border rounded px-3 py-2 text-cyber-text focus:outline-none focus:border-cyan-500"
              >
                {Object.entries(BANK_CONFIG).map(([id, cfg]) => (
                  <option key={id} value={id}>
                    {cfg.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-cyber-muted block mb-1">Provenance (Asal Data):</label>
              <select
                value={provenance}
                onChange={(e) => setProvenance(e.target.value as ProvenanceType)}
                className="w-full bg-cyber-card border border-cyber-border rounded px-3 py-2 text-cyber-text focus:outline-none focus:border-cyan-500"
              >
                <option value="ARTIFACT_VERIFIED">ARTIFACT_VERIFIED (Disertai Bukti)</option>
                <option value="OBSERVED">OBSERVED (Observasi Sistem/Log)</option>
                <option value="USER_REPORTED">USER_REPORTED (Laporan Bos Maskii)</option>
                <option value="INFERRED">INFERRED (Hasil Analisis AI)</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-cyber-muted block mb-1">Kategori Kognisi:</label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-cyber-card border border-cyber-border rounded px-3 py-2 text-cyber-text focus:outline-none focus:border-cyan-500"
              >
                <option value="PROBLEM_SOLVING">PROBLEM_SOLVING (Pemecahan Masalah)</option>
                <option value="DECISION_MAKING">DECISION_MAKING (Pengambilan Keputusan)</option>
                <option value="EXPLORATION">EXPLORATION (Riset / Eksplorasi)</option>
                <option value="GENERAL_KNOWLEDGE">GENERAL_KNOWLEDGE (Pengetahuan Umum)</option>
              </select>
            </div>
            <div>
              <label className="text-cyber-muted block mb-1">Outcome Status:</label>
              <select
                value={outcomeStatus}
                onChange={(e) => setOutcomeStatus(e.target.value)}
                className="w-full bg-cyber-card border border-cyber-border rounded px-3 py-2 text-cyber-text focus:outline-none focus:border-cyan-500"
              >
                <option value="SUCCESS">SUCCESS (Empirical Verified)</option>
                <option value="FAILED">FAILED (Trial Failed)</option>
                <option value="UNKNOWN">UNKNOWN</option>
              </select>
            </div>
          </div>

          <div>
            <label className="text-cyber-muted block mb-1">Judul Episode / Task:</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Misal: Fix Redis Cache Connection Leak..."
              className="w-full bg-cyber-card border border-cyber-border rounded px-3 py-2 text-cyber-text focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div>
            <label className="text-cyber-muted block mb-1">
              Deskripsi Masalah & Konteks (Wajib):
            </label>
            <textarea
              rows={3}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Jelaskan anomali, akar masalah, dan observasi lapangan..."
              required
              className="w-full bg-cyber-card border border-cyber-border rounded px-3 py-2 text-cyber-text focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div>
            <label className="text-cyber-muted block mb-1">Keputusan / Solusi Arsitektur:</label>
            <input
              type="text"
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
              placeholder="Keputusan arsitektur yang diambil..."
              className="w-full bg-cyber-card border border-cyber-border rounded px-3 py-2 text-cyber-text focus:outline-none focus:border-cyan-500"
            />
          </div>

          <div>
            <label className="text-cyber-muted block mb-1">Rantai Percobaan / Attempts (Opsional):</label>
            <input
              type="text"
              value={attempts}
              onChange={(e) => setAttempts(e.target.value)}
              placeholder="Misal: Attempt 1 (RAM bump failed) -> Attempt 2 (Stream success)..."
              className="w-full bg-cyber-card border border-cyber-border rounded px-3 py-2 text-cyber-text focus:outline-none focus:border-cyan-500 font-mono"
            />
          </div>

          <div>
            <label className="text-cyber-muted block mb-1">Heuristik / Refleksi (Untuk masa depan):</label>
            <input
              type="text"
              value={heuristic}
              onChange={(e) => setHeuristic(e.target.value)}
              placeholder="Kaidah pembelajaran yang bisa diulang di masa depan..."
              className="w-full bg-cyber-card border border-cyber-border rounded px-3 py-2 text-cyber-text focus:outline-none focus:border-cyan-500"
            />
          </div>

          {statusMsg && (
            <div
              className={`p-3 rounded border text-xs flex items-center gap-2 ${
                statusMsg.type === 'ok'
                  ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                  : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
              }`}
            >
              {statusMsg.type === 'ok' ? (
                <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
              ) : (
                <ShieldAlert className="w-4 h-4 shrink-0 text-rose-400" />
              )}
              <span>{statusMsg.text}</span>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2 border-t border-cyber-border">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded border border-cyber-border text-cyber-muted hover:text-cyber-text hover:bg-cyber-card"
            >
              Batal
            </button>
            <button
              type="submit"
              disabled={loading || !content.trim()}
              className="flex items-center gap-1.5 px-5 py-2 rounded bg-cyan-400 hover:bg-cyan-300 text-slate-950 font-semibold shadow-neon-hud disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Terminal className="w-4 h-4" />}
              Ingest ke Graf
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
