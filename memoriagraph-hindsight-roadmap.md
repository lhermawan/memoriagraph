# 🗺️ ROADMAP UPGRADE MEMORIAGRAPH: HINDSIGHT-INSPIRED EVOLUTION (V2.5 ➔ V3.0)
> **Author:** Maskii & Friday (Antigravity AI)  
> **Status:** 🟡 STRATEGIC PLANNING & ARCHITECTURAL ROADMAP (Eksekusi Ditahan / On-Hold)  
> **Target Database:** Neo4j Community Edition (`memoriagraph-neo4j`) & `/opt/memoriagraph`  
> **Inspirasi Riset:** Vectorize.io Hindsight Architecture (*LongMemEval 94.6% SOTA*)  
> **Tanggal Rilis Dokumen:** 28 September 2026  

---

## 1. FILOSOFI & LATAR BELAKANG
> *"Lebih baik bersiap dengan matang daripada terburu-buru eksekusi lalu sibuk memadamkan api."* — Maskii

MemoriaGraph 2.0 telah berhasil membangun fondasi kognitif yang kuat (label epistemik `:Fact`, `:Observation`, `:Inference`, non-linear problem-solving, dan eksplorasi ide). Namun, berdasarkan temuan empiris kemarin (seperti kasus kata kunci `friday-hologram-hud` dan `agenda besok` yang sempat luput), kita melihat celah besar pada **mekanisme temu-kembali (*Retrieval Engine*)** dan **statisnya keyakinan agen (*Static Beliefs*)**.

Roadmap ini menyusun langkah-langkah terukur untuk mengadopsi pilar terbaik dari **Hindsight (Vectorize.io)** ke dalam fondasi graf Neo4j kita tanpa merusak data historis yang sudah ada.

---

## 2. PILAR UTAMA UPGRADE

```
                       MEMORIAGRAPH 3.0 ARCHITECTURE
┌─────────────────────────────────────────────────────────────────────────────┐
│                            CANONICAL API FACADE                             │
│       client.retain()      │      client.recall()     │   client.reflect()  │
└──────────────┬─────────────┴─────────────┬────────────┴─────────────┬───────┘
               │                           │                          │
               ▼                           ▼                          │
┌──────────────────────────────┐ ┌──────────────────────────────────┐ │
│     BIOMIMETIC MEMORY BANKS  │ │    4-WAY HYBRID RECALL ENGINE    │ │
│  • bank: "infra-sre"         │ │  1. Fulltext Index (BM25)        │ │
│  • bank: "ai-hud"            │ │  2. Graph Traversal (Cypher)     │ │
│  • bank: "research-personal" │ │  3. Temporal Window Slicing      │ │
│  • bank: "csirt-security"    │ │  4. Dense Semantic Vector        │ │
└──────────────┬───────────────┘ └─────────────────┬────────────────┘ │
               │                                   ▼                  │
               │                    ┌───────────────────────────────┐ │
               │                    │ RECIPROCAL RANK FUSION (RRF)  │ │
               │                    │        Score Normalizer       │ │
               │                    └──────────────┬────────────────┘ │
               │                                   │                  │
               ▼                                   ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                 NEO4J NATIVE GRAPH & BELIEF REVISION ENGINE                 │
│   • Episode / Attempts / Decisions / Outcomes (Historical Substrate)        │
│   • Observations & Mental Models (Confidence Score & Evidence Counter)      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. DETAIL SPESIFIKASI & ANALISIS POTENSI TROUBLE (RISK MITIGATION)

### PILAR 1: 4-Way Hybrid Recall Engine
* **Konsep:** Tidak lagi mengandalkan single Cypher query. Saat mencari memori, 4 jalur berjalan paralel:
  1. **BM25 Fulltext Index:** Mencari kecocokan token persis di properti `name`, `title`, `description`, `heuristic`.
  2. **Multi-Hop Graph Traversal:** Melompat 1–2 tingkat relasi dari entitas yang cocok.
  3. **Temporal Filtering:** Memfilter berdasarkan `timestamp` dan konteks waktu dinamis (*"hari ini"*, *"minggu lalu"*, *"besok"*).
  4. **Semantic Similarity:** Kemiripan embedding vektor.
  *Hasil digabungkan menggunakan algoritma **Reciprocal Rank Fusion (RRF)**:*
  $$RRF\_Score(d) = \sum_{m \in M} \frac{1}{k + r_m(d)} \quad (k = 60)$$
* ⚠️ **Potensi Trouble & Risiko:**
  * *Trouble:* Index Fulltext Neo4j bisa gagal mengenali istilah gabungan (misal `friday-hologram-hud` atau variabel kode `send_reminder.js`).
  * *Mitigasi:* Gunakan custom analyzer tokenizer di Neo4j (`cjk` atau custom char-filter) dan siapkan fallback regex pre-processing sebelum query fulltext dijalankan.

---

### PILAR 2: Dynamic Belief Revision & Evidence Counter
* **Konsep:** Mengubah node `:Reflection` dan `:Pattern` dari catatan statis menjadi **Mental Model yang berevolusi**.
  * Setiap heuristik memiliki properti:
    * `evidence_count` (integer, bertambah setiap kali heuristik terbukti benar di insiden baru).
    * `confidence_score` (float 0.0 – 1.0).
    * `status` (`CANDIDATE` ➔ `OBSERVED` ➔ `HIGH_CONFIDENCE`).
    * `counter_evidence_count` (bertambah jika solusi yang disarankan ternyata gagal).
* ⚠️ **Potensi Trouble & Risiko:**
  * *Trouble:* Fluktuasi liar (*score oscillation*) jika satu insiden anomali langsung merusak keyakinan yang sudah terbukti puluhan kali.
  * *Mitigasi:* Gunakan fungsi peredam logaritmik (*logarithmic dampening*). Butuh minimal 3 konfirmasi berturut-turut untuk naik tingkat, dan kegagalan tunggal hanya menurunkan skor secara fraksional (tidak langsung menghapus heuristik).

---

### PILAR 3: Context Isolation (Memory Banks)
* **Konsep:** Membagi graf menjadi partisi logis berbasis `bank_id`:
  * `bank: "infra-sre"`: Log patroli watchdog, status PM2, metrik RAM/Disk server.
  * `bank: "ai-hud"`: Proyek hardware, Three.js, visual command center.
  * `bank: "research-personal"`: Eksperimen model AI, campaign TryBuzzer, ide bisnis.
* ⚠️ **Potensi Trouble & Risiko:**
  * *Trouble:* Agen terisolasi terlalu ketat sehingga tidak bisa menghubungkan dua domain (contoh: HUD di `ai-hud` tidak bisa membaca status server di `infra-sre`).
  * *Mitigasi:* Sediakan parameter multi-bank query (`banks: ["ai-hud", "infra-sre"]`) sehingga agen bisa melintasi batas partisi jika diminta secara eksplisit.

---

### PILAR 4: Canonical 3-Verb API Facade (`retain`, `recall`, `reflect`)
* **Konsep:** Menstandarkan tool MCP ke tiga fungsi utama:
  * `client.retain(content, bank_id, context)`
  * `client.recall(query, bank_id, limit)`
  * `client.reflect(question, bank_id)`
  * *Tool lama (`get_context`, `query_dss`, `record_cognitive_episode`) tetap dipertahankan 100% sebagai alias backward-compatible.*
* ⚠️ **Potensi Trouble & Risiko:**
  * *Trouble:* Breaking changes pada script automasi yang sudah berjalan (seperti `patrol-hub.js` atau Antigravity Desktop).
  * *Mitigasi:* Terapkan arsitektur **Facade Pattern** — fungsi baru dibungkus di atas engine lama tanpa mengubah endpoint MCP yang sudah ada.

---

## 4. TAHAPAN EKSEKUSI BERTAHAP (EXECUTION PHASES)

> [!IMPORTANT]
> Seluruh tahapan di bawah ini **TIDAK AKAN DIEKSEKUSI SEKARANG**. Tahapan ini menjadi panduan saat Bos Maskii sudah siap memberikan lampu hijau.

```
FASE 1: PRE-FLIGHT & BACKUP
├─ 1. Backup dump penuh Neo4j database (`backup_pre_v3.0.dump`)
└─ 2. Audit skema constraint & index eksisting di `schema_init.py`

FASE 2: FULLTEXT & RECALL TESTBED (ISOLASI)
├─ 1. Buat Neo4j Fulltext Search Index pada properti text penting
├─ 2. Buat script uji retrieval mandiri (`test_hybrid_recall.py`) di luar production
└─ 3. Benchmark akurasi pencarian kata kunci sulit (edge cases)

FASE 3: BELIEF REVISION & EVIDENCE DYNAMICS
├─ 1. Tambahkan migrasi properti `confidence_score` & `evidence_count` pada node Reflection
├─ 2. Hubungkan fungsi konfirmasi otomatis di `episode_manager.py`
└─ 3. Simulasi penguatan & pelemahan heuristik

FASE 4: MULTI-BANK PARTITIONING & FACADE API
├─ 1. Tambahkan properti `bank_id` pada seluruh entitas dan episode
├─ 2. Implementasi wrapper `retain`, `recall`, `reflect` di `server.py`
└─ 3. Uji coba backward compatibility dari Antigravity Desktop & CLI

FASE 5: REVIEW & DRIFT OBSERVATION (30 HARI)
└─ Pantau stabilitas memori, performa query latency (<50ms), dan akurasi jawaban agen
```

---

## 5. DOKUMEN & FILE TERKAIT
* **Roadmap File:** [memoriagraph-hindsight-roadmap.md](file:///home/maskii/Private-key/memoriagraph-hindsight-roadmap.md)
* **Master To-Do & Spec:** [to-do.md](file:///home/maskii/Private-key/to-do.md)
* **Memori Source Code:** [server.py](file:///opt/memoriagraph/server.py) & [dss_engine.py](file:///opt/memoriagraph/src/dss_engine.py)
