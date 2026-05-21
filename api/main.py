"""API REST para Asubarnipal - Endpoints externos."""

import json
import logging
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import config
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.middleware import RateLimitMiddleware, MetricsMiddleware, init_metrics, get_metrics_middleware

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Asubarnipal API",
    version="2.0.0",
    description="API REST del Agente Asubarnipal",
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


class CommandRequest(BaseModel):
    command: str
    user_id: Optional[str] = None


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
    uptime = time.time() - _START_TIME
    return {
        "status": "healthy",
        "uptime_seconds": round(uptime, 1),
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/metrics")
async def get_metrics():
    return metrics.get_metrics()


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
        try:
            state = json.loads(state_file.read_text())
        except Exception:
            pass

    if heartbeat_file.exists():
        try:
            heartbeat = json.loads(heartbeat_file.read_text())
        except Exception:
            pass

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
async def add_to_history(command: str, user_id: Optional[str] = None):
    from core.command_history import CommandHistory

    history = CommandHistory()
    history.add(command, user_id)

    return {
        "success": True,
        "timestamp": datetime.now().isoformat(),
    }


@app.get("/logs")
async def get_logs(lines: int = 100, level: Optional[str] = None):
    log_file = config.LOG_FILE

    if not log_file.exists():
        return {"logs": [], "timestamp": datetime.now().isoformat()}

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_logs = f.readlines()[-lines:]

        logs = []
        for line in all_logs:
            if line.strip():
                if level is None or level.upper() in line.upper():
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
