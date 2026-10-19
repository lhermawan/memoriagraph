"""
MemoriaGraph 3.1.2 - High Performance HTTP API Gateway (Port 8085)
Serving 9Router Pre-Injection, AI-SRE Watchdog, and Cybernetic Cockpit Visualizer
Protected by Tailscale Security Middleware (100.64.0.0/10 Mesh Only)
"""
import os
import sys
import ipaddress
from starlette.applications import Starlette
from starlette.responses import JSONResponse, RedirectResponse
from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
import uvicorn
import dotenv

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if '/opt/memoriagraph' not in sys.path:
    sys.path.insert(0, '/opt/memoriagraph')

dotenv.load_dotenv(os.path.join(CURRENT_DIR, ".env"))
dotenv.load_dotenv("/opt/memoriagraph/.env")

try:
    import server
except Exception as e:
    server = None
    print(f"⚠️ [http_service] Server module unavailable ({e}), running in standalone gateway mode.", file=sys.stderr)

from src.graph_visualizer import get_cockpit_graph_data

# Tailscale CGNAT subnet (100.64.0.0 - 100.127.255.255)
TAILSCALE_SUBNET = ipaddress.ip_network("100.64.0.0/10")

class TailscaleSecurityMiddleware:
    """
    Law of Security-First:
    Membatasi akses API Gateway & Cockpit HANYA untuk client yang berada di jaringan Tailscale mesh
    (subnet 100.64.0.0/10) atau loopback lokal (127.0.0.1 / localhost).
    Permintaan dari public IP / non-Tailscale langsung ditolak dengan HTTP 403 Forbidden.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            client = scope.get("client")
            client_ip_str = client[0] if client else ""
            
            # Periksa header x-forwarded-for atau x-real-ip jika ada reverse proxy
            headers = dict(scope.get("headers", []))
            forwarded = headers.get(b"x-forwarded-for", b"").decode("utf-8")
            if forwarded:
                client_ip_str = forwarded.split(",")[0].strip()

            is_allowed = False
            if client_ip_str in ("127.0.0.1", "::1", "localhost", "testclient", ""):
                is_allowed = True
            else:
                try:
                    ip_obj = ipaddress.ip_address(client_ip_str)
                    if ip_obj.is_loopback or ip_obj in TAILSCALE_SUBNET:
                        is_allowed = True
                except ValueError:
                    is_allowed = False

            if not is_allowed:
                response = JSONResponse(
                    {
                        "error": "403 Forbidden: Akses Ditolak.",
                        "reason": "MemoriaGraph Cockpit & API hanya dapat diakses melalui jaringan privat Tailscale Mesh (100.x.x.x).",
                        "client_ip": client_ip_str
                    },
                    status_code=403
                )
                return await response(scope, receive, send)

        return await self.app(scope, receive, send)

async def health(request):
    return JSONResponse({
        "status": "healthy",
        "service": "MemoriaGraph 3.1.2",
        "engine": "4-Way Hybrid Recall (RRF) with LRU Cache",
        "security": "Tailscale Mesh Protected (100.64.0.0/10)",
        "has_mcp_server": server is not None,
        "pid": os.getpid()
    })

async def http_recall(request):
    q = request.query_params.get("query", "")
    limit = int(request.query_params.get("limit", "5"))
    bank = request.query_params.get("bank", "")
    mode = request.query_params.get("mode", "hybrid")
    compact = request.query_params.get("compact", "true").lower() == "true"
    if not q:
        return JSONResponse({"error": "Missing 'query' parameter"}, status_code=400)
    
    if server and hasattr(server, 'recall'):
        result = server.recall(query=q, limit=limit, bank_id=bank, mode=mode, compact=compact)
    else:
        result = f"🔍 [Offline Mock] Recall for query '{q}' in bank '{bank or 'all'}'. Backend running without active MCP module."
    return JSONResponse({"query": q, "bank": bank, "result": result})

async def http_retain(request):
    try:
        body = await request.json()
        content = body.get("content", "")
        bank = body.get("bank_id", "general")
        category = body.get("category", "PROBLEM_SOLVING")
        title = body.get("title", "")
        heuristic = body.get("heuristic", "")
        decision = body.get("decision", "")
        outcome_status = body.get("outcome_status", "UNKNOWN")
        attempts = body.get("attempts", "")
        record_type = body.get("record_type", "")
        provenance = body.get("provenance", "")
        if not content:
            return JSONResponse({"error": "Missing 'content' parameter"}, status_code=400)
        
        if server and hasattr(server, 'retain'):
            msg = server.retain(
                content=content,
                bank_id=bank,
                category=category,
                title=title,
                heuristic=heuristic,
                decision=decision,
                attempts=attempts,
                outcome_status=outcome_status,
                record_type=record_type,
                provenance=provenance,
                async_mode=True
            )
            if msg.startswith("🚫 [IngestionGate:"):
                return JSONResponse({"status": "rejected", "error": msg}, status_code=422)
            return JSONResponse({"status": "success", "message": msg})
        else:
            return JSONResponse({
                "status": "success", 
                "message": f"✅ [Gateway Mock] Memori '{title or 'Baru'}' berhasil diterima di buffer memory bank {bank}."
            })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

async def http_cockpit_data(request):
    bank = request.query_params.get("bank", None)
    limit = int(request.query_params.get("limit", "200"))
    data = get_cockpit_graph_data(limit_nodes=limit, bank_filter=bank)
    return JSONResponse(data)

async def root_redirect(request):
    return RedirectResponse(url="/cockpit")

# Routes setup
routes = [
    Route("/health", health),
    Route("/recall", http_recall),
    Route("/retain", http_retain, methods=["POST"]),
    Route("/api/graph/cockpit", http_cockpit_data),
]

# Static mounting for Cockpit bundle
dist_dir = os.path.join(CURRENT_DIR, "cockpit", "dist")
if os.path.isdir(dist_dir):
    routes.append(Mount("/cockpit", StaticFiles(directory=dist_dir, html=True), name="cockpit"))
    routes.append(Route("/", root_redirect))

# Enable Tailscale Security and CORS middlewares
middleware = [
    Middleware(TailscaleSecurityMiddleware),
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
]

app = Starlette(routes=routes, middleware=middleware)

if __name__ == "__main__":
    host = os.getenv("MEMORIAGRAPH_HTTP_HOST", "0.0.0.0")
    port = int(os.getenv("MEMORIAGRAPH_HTTP_PORT", "8085"))
    print(f"🚀 MemoriaGraph 3.1.2 HTTP API & Cockpit listening on http://{host}:{port}", file=sys.stderr)
    print("🔒 Protected by Tailscale Mesh Firewall (100.64.0.0/10 & Localhost Only)", file=sys.stderr)
    uvicorn.run(app, host=host, port=port, log_level="warning")
