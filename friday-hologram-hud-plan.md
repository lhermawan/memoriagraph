# 🎙️ FRIDAY HOLOGRAPHIC HUD & VOICE COMMAND CENTER
> **Target Perangkat:** PC Rumah Maskii (Ryzen 5 5500 + NVIDIA RTX 3050 6GB + 16GB RAM + Monitor 144Hz)  
> **Konektivitas:** Tailscale Mesh ke Server `vm-maskii` (32GB RAM / 100.79.34.4)  
> **Status:** Siap Dieksekusi Kapan Saja di PC Rumah  
> **Author:** Maskii & Friday (Antigravity AI)  

---

## 1. VISI & KONSEP SISTEM
Mengubah workstation PC rumah menjadi **Iron Man-Style AI Command Center**:
* **Visual**: Tampilan antarmuka holografis futuristik (Arc Reactor HUD melayang) berjalan 144 FPS di monitor ViewSonic 24" IPS.
* **Audio**: Mengaktifkan asisten suara dengan panggilan: **"Hey Friday"**.
* **Integrasi Server**: Menghubungkan perintah suara PC rumah langsung ke **AI-SRE Daemon** dan **MemoriaGraph 2.0** di server `vm-maskii` via Tailscale secara Zero Trust (Ed25519).

---

## 2. ARSITEKTUR INTEGRASI

```
[Suara Maskii di PC Rumah: "Hey Friday, tampilkan status server"]
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│ PC RUMAH: BROWSER (Chrome/Edge 144Hz - http://localhost:5173)│
│ • Web Speech API / Faster-Whisper (Deteksi "Hey Friday")    │
│ • React + Three.js 3D Animated Arc Reactor Core             │
│ • Glassmorphic Telemetry Cards & Audio Waveform             │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼ (HTTP Fetch via Tailscale)
┌─────────────────────────────────────────────────────────────┐
│ SERVER VM-MASKII (100.79.34.4:3400 - AI-SRE DAEMON)          │
│ • Otentikasi: Ed25519 Private Key Maskii                    │
│ • Endpoint  : /api/all (Metrics PM2, RAM, Disk, SSL)        │
│ • Database  : MemoriaGraph 2.0 (Neo4j localhost:7687)       │
└─────────────────────────────┬───────────────────────────────┘
                              │
                              ▼ (JSON Data Telemetri)
┌─────────────────────────────────────────────────────────────┐
│ RESPON KEMBALI KE PC RUMAH:                                 │
│ 1. VISUAL: Slide-in Panel Status Server & Meteran Circular  │
│ 2. AUDIO : Friday merespons via TTS Speaker PC              │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. LANGKAH SETUP STEP-BY-STEP DI PC RUMAH (WINDOWS)

### Langkah 1: Clone Repositori Dasar
Buka Terminal (PowerShell / Git Bash) di PC rumah:
```powershell
# Masuk ke direktori project Anda
cd D:\Projects   # atau folder pilihan Anda
git clone https://github.com/adewaskar/jarvis.git friday-hud
cd friday-hud
npm install
```

### Langkah 2: Ganti Wake Word ke "Hey Friday"
Buka file pendeteksi suara di project (biasanya di `src/hooks/useSpeechRecognition.js` atau `src/App.jsx`):
```javascript
// Ganti baris pengecekan wake word:
// DARI:
if (transcript.toLowerCase().includes("hey jarvis"))
// MENJADI:
if (transcript.toLowerCase().includes("hey friday") || transcript.toLowerCase().includes("friday"))
```

### Langkah 3: Tambahkan Handler Pemanggilan SRE Server
Di dalam file pemroses perintah suara (atau backend server lokal):
```javascript
// Fungsi untuk memanggil telemetri server vm-maskii
async function fetchServerStatus() {
  try {
    const res = await fetch("http://100.79.34.4:3400/api/all", {
      headers: {
        "x-agent-id": "maskii"
      }
    });
    const data = await res.json();
    return data.data;
  } catch (err) {
    console.error("Gagal terhubung ke vm-maskii:", err);
    return null;
  }
}
```

### Langkah 4: Tambahkan Komponen Visual Glassmorphic Card
Tampilkan kartu saat perintah `tampilkan status server` diterima:
* **Production Node**: Status 14/14 PM2 Online, RAM 46%.
* **AI Hub VM**: Status Optimal, RAM 7%, Disk 15%.
* **Hypervisor R740**: Uptime 81 Hari.

### Langkah 5: Jalankan & Nikmati di Layar 144Hz
```powershell
npm start
```
Buka Google Chrome di `http://localhost:5173`, tekan tombol **INITIALISE**, izinkan akses Microphone, lalu coba ucapkan:
> *"Hey Friday, tolong tampilkan status monitoring server."*

---

## 4. DAFTAR PERINTAH SUARA (VOICE COMMANDS)

| Perintah Suara | Respon Visual di Layar | Respon Suara Friday |
| :--- | :--- | :--- |
| **"Hey Friday, status server"** | Muncul kartu telemetri Production, VM-Maskii, & PowerEdge | *"Semua server dalam kondisi prima dan beroperasi normal, Bos."* |
| **"Hey Friday, cek memori"** | Muncul gauge penggunaan RAM server & PC lokal | *"Kapasitas memori server sangat lega, penggunaan berada di angka 7 persen."* |
| **"Hey Friday, bagaimana heuristik terakhir?"** | Menampilkan kartu heuristik dari MemoriaGraph 2.0 | *"Heuristik terakhir: Selalu verifikasi environment GOPATH sebelum mengulang instalasi Go tools."* |
| **"Friday, tutup tampilan / stand down"** | Panel telemetri memudar (*fade out*), kembali ke inti reaktor | *"Standby mode aktif, Bos."* |

---

## 5. CARA MEMANGGIL RENCANA INI NANTI DARI PC RUMAH

Kapan pun Bos Maskii sudah di depan PC rumah, cukup panggil saya lewat terminal atau chat:

```bash
# Opsi 1: Panggil lewat CLI MemoriaGraph
memoria dss "rencana friday voice hologram hud"

# Opsi 2: Buka file dokumentasi ini langsung
# File tersimpan permanen di server dan MemoriaGraph!
```
Atau cukup bilang di chat: **"Friday, buka rencana HUD kemarin"** — saya akan langsung memandu eksekusi step-by-step-nya! 🚀
