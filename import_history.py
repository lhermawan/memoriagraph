import os
import json
from server import add_entity, add_relation

BRAIN_DIR = r"C:\Users\koval\.gemini\antigravity\brain"

def process_history():
    print("Memulai pemindaian riwayat percakapan masa lalu Anda...")
    count = 0
    
    # Ambil semua folder di dalam direktori brain
    for folder in os.listdir(BRAIN_DIR):
        transcript_path = os.path.join(BRAIN_DIR, folder, ".system_generated", "logs", "transcript.jsonl")
        
        if os.path.exists(transcript_path):
            try:
                with open(transcript_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        data = json.loads(line)
                        
                        # Cari prompt pertama yang Anda ketik di setiap percakapan
                        if data.get("source") == "USER_EXPLICIT" and data.get("type") == "USER_INPUT":
                            content = data.get("content", "").strip()
                            if content:
                                # Buat judul ringkas dari prompt pertama
                                title = content[:40].replace("\n", " ").strip()
                                if len(content) > 40:
                                    title += "..."
                                
                                # Jangan masukkan percakapan kosong
                                if len(title) > 5:
                                    print(f"Menemukan riwayat: {title}")
                                    add_entity(title, 'Past_Conversation', 'Riwayat obrolan')
                                    add_relation('User', title, 'PERNAH_MEMBAHAS')
                                    count += 1
                            break # Hanya ambil pesan pertama untuk merepresentasikan topik utama chat
            except Exception as e:
                pass # Abaikan jika ada error format json di log lama
                
    print(f"\n✅ SELESAI! {count} riwayat topik percakapan masa lalu telah diserap ke dalam MemoriaGraph.")

if __name__ == "__main__":
    process_history()
