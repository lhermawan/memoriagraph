# ⚡ MemoriaGraph 3.1 Benchmark & Verification Suite

Dokumentasi resmi pengujian performa, integritas memori kognitif, dan verifikasi DevSecOps MemoriaGraph v3.1 di bawah tata kelola **Friday Protocol**.

---

## 📁 Struktur Direktori

```
benchmarks/
├── README.md               # Panduan eksekusi dan metodologi benchmark
└── results/
    ├── baseline.json       # Telemetri pengukuran sebelum refactoring
    ├── post-fix.json       # Telemetri pengukuran setelah implementasi perbaikan
    └── comparison.json     # Komparasi sebelum vs sesudah (delta & quality gain)
```

---

## 🚀 Cara Menjalankan Benchmark

### 1. Prasyarat Lingkungan
- Runtime: Python 3.12+ (disarankan di `vm-maskii` venv)
- Neo4j: Enterprise v5.x aktif pada `bolt://127.0.0.1:7687`
- Dependensi: `pytest`, `fastembed`, `neo4j`, `numpy`

### 2. Menjalankan Regression & Integrity Suite
```bash
pytest -v tests/
```
Output yang diharapkan: **21 passed** dalam <5 detik.

### 3. Menjalankan Latency & Drift Benchmark
```bash
python benchmark_v3.py
```

Metrik yang diuji:
1. **4-Way Hybrid Recall (RRF)**: Mengukur cold-start dan warm query latency pada 5 query representatif (target: <100 ms).
2. **Personal DSS Query**: Mengukur kecepatan agregasi preseden masa lalu dan rekam jejak hasil (target: <20 ms).
3. **Dynamic Belief Revision Index**: Mengukur listing 20 heuristik dan crystallized pattern aktif (target: <15 ms).
4. **3D WebGL Graph Exporter**: Mengukur pembentukan payload topologis 100 node untuk Friday HUD (target: <50 ms).
5. **Anti-Slop & Epistemic Gate**: Mengukur throughput pembersihan teks dan klasifikasi kelas epistemik (target: >3.000 ops/detik).
