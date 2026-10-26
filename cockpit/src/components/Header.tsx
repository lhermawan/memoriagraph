import React from 'react';
import type { BankId } from '../types/graph';
import { BANK_CONFIG } from '../types/graph';
import { 
  Zap, 
  Search, 
  Sun, 
  Moon, 
  RefreshCw, 
  Radio, 
  PlusCircle
} from 'lucide-react';

interface HeaderProps {
  selectedBank: BankId | 'all';
  onSelectBank: (bank: BankId | 'all') => void;
  isLive: boolean;
  isDarkMode: boolean;
  onToggleTheme: () => void;
  onRefresh: () => void;
  onOpenSearch: () => void;
  onOpenIngest: () => void;
  isRefreshing?: boolean;
  autoSync: boolean;
  onToggleAutoSync: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  selectedBank,
  onSelectBank,
  isLive,
  isDarkMode,
  onToggleTheme,
  onRefresh,
  onOpenSearch,
  onOpenIngest,
  isRefreshing = false,
  autoSync,
  onToggleAutoSync,
}) => {
  return (
    <header className="h-16 border-b border-cyber-border bg-cyber-panel/90 hud-glass px-4 md:px-6 flex items-center justify-between gap-4 z-10 shrink-0">
      {/* Brand & Version */}
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-neon-hud text-cyber-bg font-bold">
          <Zap className="w-5 h-5 fill-current" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-sm md:text-base font-bold tracking-wider text-cyber-text uppercase font-mono">
              MemoriaGraph
            </h1>
            <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
              v3.2.0
            </span>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-cyber-muted">
            <span>Cognitive Cockpit</span>
            <span className="text-cyber-border">•</span>
            {isLive ? (
              <span className="inline-flex items-center gap-1 text-emerald-400 font-mono">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                Live Port 8085
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-cyan-400 font-mono">
                <Radio className="w-3 h-3 text-cyan-400" />
                Standalone Mock
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Biomimetic Bank Chips */}
      <div className="hidden lg:flex items-center gap-1.5 overflow-x-auto py-1">
        <button
          onClick={() => onSelectBank('all')}
          className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-all ${
            selectedBank === 'all'
              ? 'bg-cyber-text text-cyber-bg border-cyber-text font-semibold shadow-sm'
              : 'border-cyber-border text-cyber-muted hover:text-cyber-text hover:border-cyber-muted'
          }`}
        >
          All Banks
        </button>

        {(Object.entries(BANK_CONFIG) as [BankId, typeof BANK_CONFIG[BankId]][]).map(([id, cfg]) => {
          const active = selectedBank === id;
          return (
            <button
              key={id}
              onClick={() => onSelectBank(active ? 'all' : id)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all ${
                active
                  ? 'border-transparent font-semibold shadow-md'
                  : 'border-cyber-border text-cyber-muted hover:text-cyber-text hover:border-cyber-muted'
              }`}
              style={{
                backgroundColor: active ? `${cfg.color}25` : undefined,
                borderColor: active ? cfg.color : undefined,
                color: active ? cfg.color : undefined,
              }}
            >
              <i
                className="w-2 h-2 rounded-full inline-block"
                style={{
                  backgroundColor: cfg.color,
                  boxShadow: active ? `0 0 8px ${cfg.color}` : 'none',
                }}
              />
              {cfg.name}
            </button>
          );
        })}
      </div>

      {/* Action Buttons */}
      <div className="flex items-center gap-2">
        <button
          onClick={onOpenSearch}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-cyber-border text-cyber-muted hover:text-cyber-text hover:border-cyan-500/50 hover:bg-cyber-card/60 transition-all"
          title="Search Memory via 4-Way Hybrid Recall"
        >
          <Search className="w-3.5 h-3.5 text-cyan-400" />
          <span className="hidden sm:inline">Recall Search</span>
        </button>

        <button
          onClick={onOpenIngest}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-cyan-400 text-slate-950 hover:bg-cyan-300 shadow-neon-hud transition-all active:scale-95"
          title="Ingest Memory to Ingestion Gate"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Ingest (POST /retain)</span>
        </button>

        <button
          onClick={onToggleAutoSync}
          className={`flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-mono rounded-lg border transition-all ${
            autoSync
              ? 'bg-emerald-500/10 border-emerald-500/50 text-emerald-400 shadow-sm'
              : 'border-cyber-border text-cyber-muted hover:text-cyber-text hover:bg-cyber-card'
          }`}
          title="Toggle Auto-Sync Polling (Pindai otomatis graf tiap 12 detik)"
        >
          <span className={`w-2 h-2 rounded-full ${autoSync ? 'bg-emerald-400 animate-ping' : 'bg-cyber-muted'}`} />
          <span className="hidden xl:inline">Auto-Sync {autoSync ? 'ON' : 'OFF'}</span>
        </button>

        <button
          onClick={onRefresh}
          disabled={isRefreshing}
          className="p-2 rounded-lg border border-cyber-border text-cyber-muted hover:text-cyber-text hover:border-cyber-muted hover:bg-cyber-card transition-all"
          title="Refresh Graph"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-cyan-400' : ''}`} />
        </button>

        <button
          onClick={onToggleTheme}
          className="p-2 rounded-lg border border-cyber-border text-cyber-muted hover:text-cyber-text hover:border-cyber-muted hover:bg-cyber-card transition-all"
          title={isDarkMode ? 'Beralih ke Light Mode' : 'Beralih ke Dark Mode'}
        >
          {isDarkMode ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-cyan-400" />}
        </button>
      </div>
    </header>
  );
};
