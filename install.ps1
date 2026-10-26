# MemoriaGraph 3.2.0 - 1-Click Windows PowerShell Installer
# Jalankan skrip ini dengan klik kanan -> "Run with PowerShell" atau jalankan .\install.ps1

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "🧠 MemoriaGraph 3.2.0 - Windows 1-Click Installer" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# 1. Cek keberadaan Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "❌ Python tidak ditemukan di sistem ini." -ForegroundColor Red
    Write-Host "Silakan instal Python 3.10+ dari https://www.python.org/downloads/ dan pastikan centang 'Add Python to PATH'." -ForegroundColor Yellow
    Read-Host "Tekan Enter untuk keluar..."
    Exit 1
}

# 2. Pindah ke direktori repository
$repoDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $repoDir

# 3. Jalankan installer Python interaktif
python installer.py

Write-Host "`nSelesai! Terima kasih telah menggunakan MemoriaGraph." -ForegroundColor Green
Read-Host "Tekan Enter untuk menutup jendela ini..."
