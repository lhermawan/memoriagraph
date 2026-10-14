import threading
import queue
import time
import sys
from typing import Callable, Any

class BackgroundHarvester:
    """
    MemoriaGraph 3.0 Async Background Harvester (Pilar 2)
    Memindahkan tugas berat (vector cache sync, graph clustering, deep re-ranking)
    ke background queue agar eksekusi MCP tool selesai dalam <15ms.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BackgroundHarvester, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.task_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True, name="MemoriaHarvester")
        self.worker_thread.start()
        self.is_running = True
        self._initialized = True
        print("🌱 [Harvester] MemoriaGraph Async Background Harvester aktif!", file=sys.stderr)

    def submit(self, name: str, func: Callable, *args, **kwargs):
        """Submit a background job"""
        self.task_queue.put((name, func, args, kwargs))

    def _worker_loop(self):
        while True:
            try:
                name, func, args, kwargs = self.task_queue.get()
                t0 = time.time()
                try:
                    func(*args, **kwargs)
                    duration = time.time() - t0
                    print(f"⚡ [Harvester] Job '{name}' selesai dalam {duration:.3f}s", file=sys.stderr)
                except Exception as err:
                    print(f"❌ [Harvester] Job '{name}' gagal: {err}", file=sys.stderr)
                finally:
                    self.task_queue.task_done()
            except Exception as loop_err:
                print(f"⚠️ [Harvester] Worker loop exception: {loop_err}", file=sys.stderr)
                time.sleep(0.5)

# Global singleton
harvester = BackgroundHarvester()