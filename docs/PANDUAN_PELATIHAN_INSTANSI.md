# 📘 Panduan Pelatihan & Adopsi MemoriaGraph untuk Instansi Pemerintah & Organisasi
> **Pedoman Implementasi "Second Brain" Birokrasi & Kedaulatan Pengetahuan Berbasis Graf Kognitif**  
> *Versi: 3.0.0 | Standar: Open-Source Enterprise & Gov-Tech*

---

## 🏛️ 1. Latar Belakang: Mengapa Instansi Butuh MemoriaGraph?

### ⚠️ Masalah Klasik di Instansi Pemerintah:
1. **Knowledge Lost upon Rotation (Kehilangan Pengetahuan Saat Mutasi):**  
   Ketika ASN atau staf teknis dirotasi atau purna tugas, seluruh riwayat penanganan kendala, konfigurasi server, dan trik mengatasi masalah (*heuristik*) sering kali ikut hilang. Tim baru harus belajar dari nol melalui *trial-and-error* yang memakan waktu dan biaya.
2. **Ketergantungan pada Solusi Cloud Publik:**  
   Banyak staf menggunakan AI publik gratisan untuk merangkum dokumen kedinasan, yang berisiko melanggar **UU No. 27 Tahun 2022 tentang Perlindungan Data Pribadi (UU PDP)** dan keamanan informasi negara.
3. **Biaya Fine-Tuning LLM yang Sangat Mahal:**  
   Melatih model AI mandiri (*fine-tuning*) membutuhkan investasi GPU miliaran rupiah dan datanya cepat usang (*out-of-date*) serta rentan halusinasi.

### 💡 Solusi MemoriaGraph:
MemoriaGraph tidak melatih bobot model AI dari nol, melainkan membangun **Substrat Memori Jangka Panjang Eksternal** berbasis Graf Kognitif (Neo4j) yang:
* **100% On-Premise & Zero-Cost:** Berjalan di server lokal/jaringan privat instansi (Tailscale/LAN).
* **Anti-Bocor (Zero-Secret Sanitizer):** Token, password, dan NIK otomatis disanitasi sebelum tersimpan.
* **Belajar Terus-Menerus:** Semakin sering instansi menghadapi insiden dan mencatat solusinya, AI instansi semakin cerdas dan matang.

---

## 🧠 2. Peta Arsitektur Memori Instansi

```
  ┌────────────────────────────────────────────────────────────────────────┐
  │                           SUMBER PENGETAHUAN DINAS                     │
  │   [SOP & Regulasi]      [Tiket Helpdesk / Insiden]     [Keputusan Rapat]│
  └───────────────────────────────────┬────────────────────────────────────┘
                                      │
                                      ▼
                        ┌───────────────────────────┐
                        │   ANTI-SLOP IMMUNE GATE   │
                        │ • Sanitasi Kredensial/NIK │
                        │ • Pangkas Basa-Basi AI    │
                        │ • Epistemic Grounding     │
                        └─────────────┬─────────────┘
                                      │
                                      ▼
       ┌─────────────────────────────────────────────────────────────┐
       │             PARTISI KAMAR OTAK (MEMORY BANKS)               │
       │                                                             │
       │  [Bank: spbe-layanan]     [Bank: csirt-keamanan]            │
       │  • SOP Aplikasi Publik    • Log Insiden Defacement/Malware  │
       │  • Alur Integrasi API     • Konfigurasi Firewall & SSL      │
       │                                                             │
       │  [Bank: infra-server]     [Bank: regulasi-kebijakan]        │
       │  • Topologi Server & VM   • Perbup, Perda, Surat Edaran     │
       │  • Prosedur Restart PM2   • Tupoksi & Struktur Organisasi   │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │   4-WAY HYBRID RECALL    │
                         │ (BM25 + Graph + Vector)  │
                         └────────────┬─────────────┘
                                      │
                                      ▼
  ┌────────────────────────────────────────────────────────────────────────┐
  │                    PEMANFAATAN OLEH ASN & PIMPINAN                     │
  │ • Konsultasi SOP Instan       • Keputusan Berbasis Bukti (DSS)         │
  │ • Tanya Jawab via Telegram    • Antigravity Desktop / Web Portal       │
  └────────────────────────────────────────────────────────────────────────┘
```

---

## 🗂️ 3. Langkah 1: Membagi "Kamar Otak" (Memory Banks Partitioning)

Sebelum memasukkan data, instansi harus membagi domain kerja ke dalam **Memory Bank ID**. Ini bertujuan agar memori tidak bercampur aduk (*context leakage*).

### Rekomendasi Partisi untuk Pemerintah Daerah / OPD:

| Bank ID | Domain Kerja | Contoh Konten yang Disimpan |
| :--- | :--- | :--- |
| `spbe-layanan` | Aplikasi & Layanan Publik | Alur registrasi aplikasi, integrasi Satu Data, API gateway. |
| `csirt-keamanan` | Keamanan Informasi & Sandi | Laporan insiden siber, hasil audit pentest, penanganan malware. |
| `infra-server` | Infrastruktur & Jaringan | IP server, topologi fiber optic, prosedur reboot, backup data. |
| `regulasi-kebijakan` | Tata Kelola & Aturan | Perda, Perbup SPBE, SOP kedinasan, SK Tim Pelaksana. |
| `kepegawaian-sdm` | Pengembangan Aparatur | Jadwal diklat, kurikulum kompetensi digital, rekap sertifikasi. |

---

## 📥 4. Langkah 2: Memasukkan Pengetahuan Dasar (Baseline Training)

Untuk melatih otak MemoriaGraph dengan dokumen baku (SOP, regulasi, panduan teknis), gunakan fungsi **`retain()`**.

### Contoh Kasus 1: Memasukkan SOP Penanganan Gangguan Server
Staf instansi menjalankan perintah atau prompt:

```python
from src.hybrid_recall import HybridRecallEngine
# Atau melalui tool MCP: retain()
retain(
    bank_id="infra-server",
    category="SOP",
    title="SOP Pemulihan Service Aplikasi SPBE yang Mandek (Port 3400)",
    content="Jika service API tidak merespons (fetch failed), periksa status systemd: 'systemctl status ai-sre-daemon'. Lakukan restart dengan 'systemctl restart ai-sre-daemon'. Pastikan port 3400 kembali listening pada 127.0.0.1. Jalankan patrol-hub.js untuk memverifikasi pemulihan.",
    heuristic="Jangan me-restart seluruh VM server jika hanya satu sub-service daemon yang mandek; periksa unit systemd terlebih dahulu."
)
```

### ✍️ Tips Menulis Konten Pelatihan yang Efektif:
* **Fokus pada Fakta Operasional:** Tuliskan perintah konkret, nama service, dan indikator keberhasilan.
* **Sertakan Heuristik:** Tuliskan pelajaran praktis (*rule of thumb*) di parameter `heuristic` agar AI memahami konteks "mengapa" langkah itu diambil.
* **Hindari Bahasa Bunga:** Filter *Anti-Slop* akan otomatis membuang kalimat basa-basi seperti *"Dengan hormat, berikut kami sampaikan..."*. Tulis langsung intinya.

---

## 🧪 5. Langkah 3: Melatih Otak dari Pengalaman Nyata (Experiential Learning)

Kekuatan utama MemoriaGraph adalah kemampuannya merekam **Episode Pemecahan Masalah** lengkap dengan riwayat kegagalan dan keberhasilannya.

Setiap kali tim menyelesaikan insiden atau proyek baru, rekam menggunakan **`record_cognitive_episode`**:

### Format Baku Episode Kognitif:
```json
{
  "title": "Penanganan Lonjakan RAM pada Server Basis Data Pelayanan",
  "category": "SRE_INCIDENT",
  "context": "infra-server",
  "problem_description": "RAM server mencapai 92% dan memicu alert darurat ke WhatsApp tim teknis.",
  "problem_severity": "HIGH",
  "attempts": [
    {
      "number": 1,
      "hypothesis": "Lonjakan terjadi karena kebocoran memory pada process Node.js.",
      "action": "Restart process PM2 ID 4 secara manual.",
      "result": "RAM turun sesaat ke 45%, namun naik kembali ke 88% dalam 15 menit.",
      "status": "FAILED"
    },
    {
      "number": 2,
      "hypothesis": "Kueri database yang tidak memiliki indeks menyebabkan full-table scan berulang.",
      "action": "Jalankan profiling kueri lambat dan buat B-Tree Index pada kolom 'nik_warga'.",
      "result": "Beban CPU turun 70% dan RAM stabil permanen pada 42%.",
      "status": "SUCCESS"
    }
  ],
  "decision_choice": "Menerapkan Indexing pada database dan menambahkan limit memory di konfigurasi PM2.",
  "decision_rationale": "Mengatasi akar masalah pemrosesan query lambat daripada sekadar merestart process berulang.",
  "outcome_status": "SUCCESS",
  "reflection_heuristic": "Jika RAM melonjak cepat kembali setelah PM2 restart, periksa kueri database tanpa indeks sebelum menyimpulkan kebocoran kode."
}
```

> 🌟 **Hasilnya bagi Instansi:** Ketika tahun depan ada staf baru yang menghadapi lonjakan RAM serupa, AI tidak akan menyarankan "coba restart server", melainkan langsung menyarankan: *"Berdasarkan insiden lalu, periksa indeks kueri database terlebih dahulu sebelum restart."*

---

## ⚖️ 6. Langkah 4: Manajemen Siklus Keyakinan (Belief Revision)

Dalam birokrasi, prosedur kerja dapat berubah atau usang. MemoriaGraph memiliki fitur **Belief Revision Engine** yang mengatur kematangan pengetahuan:

```
[CANDIDATE]  ──(Berhasil berulang kali)──►  [OBSERVED]  ──(Terbukti stabil)──►  [HIGH_CONFIDENCE (Pattern)]
     │
     └──(Mengalami kegagalan / usang)──►  [CONTESTED]  ────►  [DEPRECATED]
```

### 1. Memperkuat Solusi Teruji (`reinforce_belief`):
Jika sebuah SOP atau instruksi berhasil menyelesaikan masalah dinas:
* Panggil: `reinforce_belief(identifier="ID_HEURISTIK", details="Berhasil diterapkan pada audit SPBE 2026")`
* Skor keyakinan (*confidence score*) akan naik secara logaritmik.
* Jika sudah terbukti $\ge 3$ kali, statusnya naik menjadi **`HIGH_CONFIDENCE (Pattern)`** permanen.

### 2. Mengoreksi / Menantang Solusi yang Usang (`challenge_belief`):
Jika suatu aturan atau perintah sudah tidak relevan (misal regulasi berubah atau perintah gagal):
* Panggil: `challenge_belief(identifier="ID_HEURISTIK", failure_reason="Aturan Perbup lama telah digantikan Perbup No. 15 Tahun 2026")`
* Skor keyakinan akan diturunkan melalui formula **Hysteresis**.
* Jika kegagalan berulang, statusnya menjadi **`CONTESTED`** atau **`DEPRECATED`** sehingga AI tidak akan merekomendasikan cara lama tersebut lagi kepada pimpinan.

---

## 🔍 7. Langkah 5: Cara Staf & Pimpinan Bertanya ke Otak Instansi

Setelah otak dilatih, seluruh ASN dapat memanfaatkannya melalui antarmuka apa pun (Telegram Bot, Web Portal, Antigravity Desktop):

### 1. Pencarian Informasi Kontekstual (`recall`):
* **Prompt Staf:** *"Friday, bagaimana alur pengajuan integrasi API aplikasi OPD ke Satu Data Ciamis?"*
* **Cara Kerja AI:** Memanggil `recall(query="alur pengajuan integrasi API Satu Data", bank_id="spbe-layanan")`.
* **Output:** Jawaban padat langsung merujuk pada SOP dan Perbup yang tersimpan di memori.

### 2. Konsultasi Pemecahan Masalah / DSS (`query_dss`):
* **Prompt Pimpinan/Kabid:** *"Aplikasi presensi pegawai lambat saat jam masuk kantor, apa preseden solusi yang pernah berhasil?"*
* **Cara Kerja AI:** Memanggil `query_dss(situation_description="aplikasi presensi lambat jam masuk", context="infra-server")`.
* **Output:** Menyajikan persentase keberhasilan historis, riwayat keputusan masa lalu, dan heuristik penanganannya.

---

## 📋 8. Formulir Template Latihan Mandiri Instansi

Cetak atau bagikan template ini kepada tim teknis/staf dinas setiap kali ada pembelajaran atau penyelesaian masalah:

```
========================================================================
             LEMBAR KERJA PEMBELAJARAN KOGNITIF INSTANSI
========================================================================
1. Judul Insiden / Aktivitas : ________________________________________
2. Domain / Memory Bank      : [ ] spbe-layanan      [ ] csirt-keamanan
                               [ ] infra-server      [ ] regulasi-kebijakan
3. Masalah yang Dihadapi     : ________________________________________
4. Tingkat Urgensi           : [ ] RENDAH   [ ] SEDANG   [ ] KRITIS
5. Percobaan Solusi:
   • Percobaan 1: _________________________________ (Hasil: GAGAL/SUKSES)
   • Percobaan 2: _________________________________ (Hasil: GAGAL/SUKSES)
6. Keputusan Akhir Terbaik   : ________________________________________
7. Alasan Keputusan          : ________________________________________
8. Pelajaran Emas (Heuristik):
   "Jika ______________________________________________________________
    Maka sebaiknya ____________________________________________________"
========================================================================
```
*Inputkan hasil lembar kerja ini ke MemoriaGraph via bot Telegram dinas atau Antigravity CLI.*

---

## 🔒 9. Kepatuhan Regulasi & Standar Keamanan
1. **UU PDP (Pelindungan Data Pribadi):** Data warga, identitas privat, dan NIK disanitasi secara deterministik sebelum menyentuh database graf.
2. **Kedaulatan Data (Data Sovereignty):** Tidak ada data dinas yang dikirim ke server AI pihak ketiga tanpa enkripsi. Seluruh memori graf tersimpan di lingkungan privat pemerintah daerah.
3. **Audit Trail Lengkap:** Setiap penambahan, penguatan, atau koreksi memori mencatat *timestamp* dan identitas agen pengunggah untuk keperluan akuntabilitas birokrasi.

---
*Dokumen ini merupakan bagian dari repositori open-source MemoriaGraph 3.0.*  
*Inisiatif: Maskii Studio & Friday Gov-AI Research Lab.*
