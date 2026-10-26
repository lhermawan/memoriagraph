# MemoriaGraph 3.2.0 - 1-Click Windows PowerShell Installer
# Jalankan skrip ini dengan klik kanan -> "Run with PowerShell" atau jalankan .\install.ps1

$ErrorActionPreference = "Stop"

# 1. Konfigurasi encoding konsol agar UTF-8 aktif penuh
try {
    [Console]::InputEncoding = [System.Text.Encoding]::UTF8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch { }

$env:PYTHONIOENCODING = "utf-8"

# Karakter dinamis tanpa ketergantungan encoding file
$brain = try { [char]::ConvertFromUtf32(0x1F9E0) } catch { "[*]" }

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "$brain MemoriaGraph 3.2.0 - Windows 1-Click Installer" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 2. Cek keberadaan Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[X] Python tidak ditemukan di sistem ini." -ForegroundColor Red
    Write-Host "Silakan instal Python 3.10+ dari https://www.python.org/downloads/ dan pastikan centang 'Add Python to PATH'." -ForegroundColor Yellow
    Read-Host "Tekan Enter untuk keluar..."
    Exit 1
}

# 3. Pindah ke direktori repository
$repoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($repoDir) {
    Set-Location $repoDir
}

# 4. Jalankan installer Python interaktif
python installer.py

Write-Host "`nSelesai! Terima kasih telah menggunakan MemoriaGraph." -ForegroundColor Green
Read-Host "Tekan Enter untuk menutup jendela ini..."
