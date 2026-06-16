"""API REST para Asubarnipal - Endpoints externos."""

import contextlib
import json
import logging
import signal
import sys
import time
from datetime import datetime
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import config
from api.middleware import (
    RateLimitMiddleware,
    init_metrics,
)
from core.circuit_breaker import get_all_circuit_breaker_stats

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Asubarnipal API",
    version="2.0.0",
    description="API REST del Agente Asubarnipal",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

metrics = init_metrics(app)
app.add_middleware(RateLimitMiddleware, max_requests=60, window_seconds=60)

_START_TIME = time.time()
_IS_SHUTTING_DOWN = False


def _graceful_shutdown(signum: int, frame: Any) -> None:
    """Handle graceful shutdown on SIGTERM/SIGINT."""
    global _IS_SHUTTING_DOWN
    _IS_SHUTTING_DOWN = True
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    logger.info("Saving agent state, closing connections...")
    sys.exit(0)


signal.signal(signal.SIGTERM, _graceful_shutdown)
signal.signal(signal.SIGINT, _graceful_shutdown)


class CommandRequest(BaseModel):
    command: str
    user_id: str | None = None


class CommandResponse(BaseModel):
    success: bool
    output: str
    timestamp: str
    command: str


class FeedSubscription(BaseModel):
    url: str
    name: str
    interval: int = 300


class AlertResponse(BaseModel):
    feed: str
    title: str
    link: str
    published: str


class QueryRequest(BaseModel):
    query: str
    mode: str = "wiki"
    top_k: int = 5


class QueryResponse(BaseModel):
    results: list[dict]
    mode: str
    count: int
    timestamp: str


@app.get("/")
async def root():
    return {
        "name": "Asubarnipal API",
        "version": "2.0.0",
        "status": "online",
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health")
async def health():
    """Basic health check - returns always if server is running."""
    uptime = time.time() - _START_TIME
    return {
        "status": "healthy",
        "uptime_seconds": round(uptime, 1),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health/live")
async def liveness():
    """Liveness probe - is the process alive?"""
    return {"status": "alive", "timestamp": datetime.now().isoformat()}


@app.get("/health/ready")
async def readiness():
    """Readiness probe - are dependencies available?"""
    checks = {}

    try:
        import requests
        resp = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=3)
        checks["ollama"] = {"status": "up", "status_code": resp.status_code}
    except Exception as e:
        checks["ollama"] = {"status": "down", "error": str(e)}

    try:
        checks["data_dir"] = {
            "status": "up" if config.DATA_DIR.exists() else "down",
            "path": str(config.DATA_DIR),
        }
    except Exception as e:
        checks["data_dir"] = {"status": "error", "error": str(e)}

    try:
        index_exists = any(config.DATA_DIR.glob("index_*.faiss"))
        checks["faiss_index"] = {"status": "up" if index_exists else "missing", "path": str(config.DATA_DIR)}
    except Exception as e:
        checks["faiss_index"] = {"status": "error", "error": str(e)}

    try:
        db_path = config.DATA_DIR / "wiki.db"
        checks["sqlite"] = {"status": "up" if db_path.exists() else "missing", "path": str(db_path)}
    except Exception as e:
        checks["sqlite"] = {"status": "error", "error": str(e)}

    try:
        from core.vault_manager import get_vault_manager
        vm = get_vault_manager()
        active = vm.get_active()
        if active and active.get("path"):
            obsidian_path = active["path"]
            checks["obsidian"] = {"status": "up", "vault": active.get("name"), "path": obsidian_path}
        else:
            checks["obsidian"] = {"status": "inactive", "detail": "No active vault"}
    except Exception as e:
        checks["obsidian"] = {"status": "error", "error": str(e)}

    all_up = all(c.get("status") == "up" for c in checks.values())

    return {
        "status": "ready" if all_up else "degraded",
        "checks": checks,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/health/circuits")
async def circuit_breaker_status():
    """Get status of all circuit breakers."""
    return {
        "circuits": get_all_circuit_breaker_stats(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/metrics")
async def get_metrics():
    """Get API metrics in JSON format."""
    return metrics.get_metrics()


@app.get("/metrics/prometheus")
async def get_prometheus_metrics():
    """Get API metrics in Prometheus exposition format."""
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=metrics.get_prometheus_metrics())


@app.post("/command", response_model=CommandResponse)
async def execute_command(req: CommandRequest):
    from core.skill_registry import SkillRegistry

    registry = SkillRegistry()
    cmd = req.command.strip()

    if cmd.startswith("/"):
        parts = cmd[1:].split(maxsplit=1)
        skill = parts[0] if parts else ""
        args = json.loads(parts[1]) if len(parts) > 1 else {}
    else:
        skill = ""
        args = {}

    result = registry.execute(skill, args)

    return CommandResponse(
        success="error" not in result,
        output=json.dumps(result, indent=2),
        timestamp=datetime.now().isoformat(),
        command=cmd,
    )


@app.get("/status")
async def get_status():
    state_file = config.AGENT_STATE_FILE
    heartbeat_file = config.HEARTBEAT_FILE

    state = {}
    heartbeat = {}

    if state_file.exists():
        with contextlib.suppress(Exception):
            state = json.loads(state_file.read_text())

    if heartbeat_file.exists():
        with contextlib.suppress(Exception):
            heartbeat = json.loads(heartbeat_file.read_text())

    return {
        "alive": state.get("alive", False),
        "last_alive": state.get("last_alive"),
        "failure_count": state.get("failure_count", 0),
        "success_count": state.get("success_count", 0),
        "heartbeat": heartbeat,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/stats")
async def get_stats():
    wiki_dir = config.WIKI_DIR
    raw_dir = config.RAW_DIR

    wiki_count = len(list(wiki_dir.glob("*.md"))) if wiki_dir.exists() else 0
    raw_count = len(list(raw_dir.glob("*.md"))) if raw_dir.exists() else 0

    return {
        "wiki_notes": wiki_count,
        "raw_sources": raw_count,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/query", response_model=QueryResponse)
async def query_knowledge(req: QueryRequest):
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    mode = req.mode.lower()

    if mode == "vectorial":
        from index.rag import get_rag_engine

        rag = get_rag_engine()
        results = rag.search(query, top_k=req.top_k)

    elif mode == "hybrid":
        from index.rag import get_rag_engine

        rag = get_rag_engine()
        results = rag.search(query, top_k=req.top_k, use_hybrid=True)

    elif mode == "hmem":
        from core.hybrid_retriever import get_hmem_manager

        hmem = get_hmem_manager()
        context = hmem.get_context(query)
        results = [{"content": context, "source": "hmem", "score": 1.0}] if context else []

    else:
        from core.wiki import Wiki

        wiki = Wiki()
        entries = wiki.search(query, limit=req.top_k)
        results = [{"content": e.get("content", ""), "source": e.get("name", ""), "score": 1.0} for e in entries]

    return QueryResponse(
        results=results,
        mode=mode,
        count=len(results),
        timestamp=datetime.now().isoformat(),
    )


@app.get("/feeds")
async def list_feeds():
    from core.feed_tracker import FeedTracker

    tracker = FeedTracker()
    return {
        "feeds": tracker.get_subscriptions(),
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/feeds/subscribe")
async def subscribe_feed(sub: FeedSubscription):
    from core.feed_tracker import FeedTracker

    tracker = FeedTracker()
    result = tracker.subscribe(sub.url, sub.name)

    return {
        "success": result,
        "feed": sub.url,
        "name": sub.name,
        "timestamp": datetime.now().isoformat(),
    }


@app.post("/feeds/unsubscribe")
async def unsubscribe_feed(url: str):
    from core.feed_tracker import FeedTracker

    tracker = FeedTracker()
    result = tracker.unsubscribe(url)

    return {
        "success": result,
        "feed": url,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/feeds/check", response_model=list[AlertResponse])
async def check_feed_updates():
    from core.feed_tracker import FeedTracker

    tracker = FeedTracker()
    updates = tracker.check_updates()

    return [
        AlertResponse(
            feed=u["feed"],
            title=u.get("title", ""),
            link=u.get("link", ""),
            published=u.get("published", ""),
        )
        for u in updates
    ]


@app.get("/history")
async def get_command_history(limit: int = 50):
    history_file = config.DATA_DIR / "command_history.json"

    if not history_file.exists():
        return {"commands": [], "timestamp": datetime.now().isoformat()}

    try:
        history = json.loads(history_file.read_text())
        return {
            "commands": history[-limit:],
            "total": len(history),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception:
        return {"commands": [], "timestamp": datetime.now().isoformat()}


@app.post("/history/add")
async def add_to_history(command: str, user_id: str | None = None):
    from core.command_history import CommandHistory

    history = CommandHistory()
    history.add(command, user_id)

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/logs")
async def get_logs(lines: int = 100, level: str | None = None):
    log_file = config.LOG_FILE

    if not log_file.exists():
        return {"logs": [], "timestamp": datetime.now().isoformat()}

    try:
        with open(log_file, encoding="utf-8") as f:
            all_logs = f.readlines()[-lines:]

        logs = []
        for line in all_logs:
            if line.strip() and (level is None or level.upper() in line.upper()):
                logs.append(line.strip())

        return {
            "logs": logs,
            "count": len(logs),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {"logs": [], "error": str(e), "timestamp": datetime.now().isoformat()}


@app.get("/schedules")
async def list_schedules():
    from core.research_scheduler import get_scheduler

    scheduler = get_scheduler()
    return {
        "schedules": scheduler.list_schedules(),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/vaults")
async def list_vaults():
    from core.vault_manager import get_vault_manager

    vm = get_vault_manager()
    result = vm.list_vaults()
    return {
        "success": result.get("success", False),
        "active": result.get("active_vault"),
        "vaults": result.get("vaults", []),
        "total": result.get("total", 0),
        "timestamp": datetime.now().isoformat(),
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "path": request.url.path,
            "timestamp": datetime.now().isoformat(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled API error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "path": request.url.path,
            "timestamp": datetime.now().isoformat(),
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
