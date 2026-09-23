import json
from server import add_entity, add_relation

# Data JSON hasil dari gh repo list lhermawan
repos_json = '''[{"description":"Config files for my GitHub profile.","name":"lhermawan","primaryLanguage":null},{"description":"Integrated Dynamic Archival Information System (Sistem Informasi Kearsipan Dinamis).","name":"SIKANDI","primaryLanguage":{"name":"Blade"}},{"description":"Python Agent for SIKANDI Security Operations Center","name":"SIKANDI-Agent","primaryLanguage":{"name":"Python"}},{"description":"Multi-tenant Attendance & Shift Management System with dynamic Rule Engine.","name":"sams-project","primaryLanguage":{"name":"TypeScript"}},{"description":"Area Traffic Control System - Smart City traffic management implementation.","name":"atcs","primaryLanguage":{"name":"HTML"}},{"description":"Personal Operating System for Work, Development, Business & Digital Presence","name":"maski-studio","primaryLanguage":{"name":"TypeScript"}},{"description":"Lightweight Attendance System for employee tracking.","name":"Absensi","primaryLanguage":{"name":"PHP"}},{"description":"Centralized Agenda and Scheduling Hub for organizational management.","name":"agenda-hub","primaryLanguage":{"name":"TypeScript"}},{"description":"Real-time match control and scoring system for sports events.","name":"live-match-control","primaryLanguage":{"name":"TypeScript"}},{"description":"Digital Guest Book and Visitor Management System.","name":"smart-guest","primaryLanguage":{"name":"TypeScript"}},{"description":"Sistem Informasi Manajemen Pengunjung & Reservasi Terintegrasi","name":"SIMPATI","primaryLanguage":{"name":"Blade"}},{"description":"Tournament Management System for Mobile Legends competitions.","name":"Tournament-ML","primaryLanguage":{"name":"TypeScript"}},{"description":"Automated WhatsApp Bot for business and utility services.","name":"whatsapp-bot","primaryLanguage":{"name":"HTML"}},{"description":"Sistem Informasi Pertanggungjawaban Anggaran","name":"SIPENA","primaryLanguage":{"name":"PHP"}},{"description":"Laboratory Scanning and Sample Management System.","name":"ScanLab","primaryLanguage":{"name":"Go"}},{"description":"Streamlined data entry system for administrative workflows.","name":"Masukin-V2","primaryLanguage":{"name":"PHP"}},{"description":"Security scanning tool for local environments and desktop apps.","name":"DevSecOps-Desktop-Scanner","primaryLanguage":{"name":"Dart"}},{"description":"E-commerce platform for local Galuh regional products.","name":"Galuh-Mart","primaryLanguage":{"name":"Dart"}},{"description":"Digital broadcasting and streaming platform for Galuh region.","name":"GaluhCast","primaryLanguage":{"name":"Dart"}},{"description":"Agenda and activity management for BPKD (Local Finance Agency).","name":"agenda-bpkd","primaryLanguage":{"name":"PHP"}},{"description":"Digital asset streaming and distribution system.","name":"aset-streaming","primaryLanguage":{"name":"TypeScript"}},{"description":"Mobile application for Sandikami information services.","name":"Sandikami-Mobile","primaryLanguage":{"name":"Dart"}},{"description":"Streamlined data entry system for administrative workflows.","name":"MasukinApp","primaryLanguage":{"name":"Kotlin"}},{"description":"Cloud-based attendance and time-tracking platform.","name":"Hadir.in","primaryLanguage":{"name":"PHP"}},{"description":"Online reservation system for Diskominfo facility and services.","name":"reservasi-diskominfo","primaryLanguage":{"name":"JavaScript"}},{"description":"Schedule management","name":"Jadwal","primaryLanguage":{"name":"PHP"}},{"description":"Encryption and security system for government communications.","name":"Persandian","primaryLanguage":{"name":"Python"}},{"description":"Electronic office system for village administration (E-Office Desa).","name":"e-office-desa","primaryLanguage":{"name":"TypeScript"}}]'''

repos = json.loads(repos_json)
languages = set()

print("Menganalisis GitHub lhermawan...")

for r in repos:
    lang = r.get('primaryLanguage')
    if lang:
        languages.add(lang['name'])

# 1. Tambah Node Bahasa (Tech Stack)
for l in languages:
    add_entity(l, 'Language', 'Bahasa Pemrograman')
    add_relation('User', l, 'MENGUASAI')

# 2. Tambah Node Repositori Terpilih
for r in repos:
    name = r.get('name')
    desc = r.get('description', '')
    if not desc: desc = 'Repositori GitHub'
    # Buat Node Repo
    add_entity(name, 'Repository', desc[:60])
    # Sambungkan User -> Repo
    add_relation('User', name, 'MEMBUAT_REPO')
    
    # Sambungkan Repo -> Bahasa
    lang = r.get('primaryLanguage')
    if lang:
        add_relation(name, lang['name'], 'DITULIS_DENGAN')

print(f'Selesai! Berhasil memetakan {len(repos)} repository dan {len(languages)} bahasa pemrograman!')
