"""
MemoriaGraph 3.1.2 - High Performance HTTP API Gateway (Port 8085)
Serving 9Router Pre-Injection, AI-SRE Watchdog, and Mesh Services
"""
import os
import sys
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn

sys.path.insert(0, '/opt/memoriagraph')
import server

async def health(request):
    return JSONResponse({
        "status": "healthy",
        "service": "MemoriaGraph 3.1.2",
        "engine": "4-Way Hybrid Recall (RRF) with LRU Cache",
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
    result = server.recall(query=q, limit=limit, bank_id=bank, mode=mode, compact=compact)
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
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

app = Starlette(routes=[
    Route("/health", health),
    Route("/recall", http_recall),
    Route("/retain", http_retain, methods=["POST"]),
])

if __name__ == "__main__":
    print("🚀 MemoriaGraph 3.1.2 HTTP API listening on http://0.0.0.0:8085", file=sys.stderr)
    uvicorn.run(app, host="0.0.0.0", port=8085, log_level="warning")
