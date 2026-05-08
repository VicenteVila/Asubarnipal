"""API REST para Asubarnipal - Endpoints externos."""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import config
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Asubarnipal API",
    version="1.0.0",
    description="API REST del Agente Karpathy Wiki"
)


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


@app.get("/")
async def root():
    return {
        "name": "Asubarnipal API",
        "version": "1.0.0",
        "status": "online",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "uptime": time.time(),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/command", response_model=CommandResponse)
async def execute_command(req: CommandRequest):
    """Ejecutar un comando via API."""
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
        command=cmd
    )


@app.get("/status")
async def get_status():
    """Estado del agente."""
    state_file = config.AGENT_STATE_FILE
    heartbeat_file = config.HEARTBEAT_FILE
    
    state = {}
    heartbeat = {}
    
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except:
            pass
    
    if heartbeat_file.exists():
        try:
            heartbeat = json.loads(heartbeat_file.read_text())
        except:
            pass
    
    return {
        "alive": state.get("alive", False),
        "last_alive": state.get("last_alive"),
        "failure_count": state.get("failure_count", 0),
        "success_count": state.get("success_count", 0),
        "heartbeat": heartbeat,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/stats")
async def get_stats():
    """Estadísticas del wiki."""
    wiki_dir = config.WIKI_DIR
    raw_dir = config.RAW_DIR
    
    wiki_count = len(list(wiki_dir.glob("*.md"))) if wiki_dir.exists() else 0
    raw_count = len(list(raw_dir.glob("*.md"))) if raw_dir.exists() else 0
    
    return {
        "wiki_notes": wiki_count,
        "raw_sources": raw_count,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/feeds")
async def list_feeds():
    """Listar suscripciones RSS."""
    from core.feed_tracker import FeedTracker
    
    tracker = FeedTracker()
    return {
        "feeds": tracker.get_subscriptions(),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/feeds/subscribe")
async def subscribe_feed(sub: FeedSubscription):
    """Suscribirse a un feed RSS."""
    from core.feed_tracker import FeedTracker
    
    tracker = FeedTracker()
    result = tracker.subscribe(sub.url, sub.name)
    
    return {
        "success": result,
        "feed": sub.url,
        "name": sub.name,
        "timestamp": datetime.now().isoformat()
    }


@app.post("/feeds/unsubscribe")
async def unsubscribe_feed(url: str):
    """Cancelar suscripción."""
    from core.feed_tracker import FeedTracker
    
    tracker = FeedTracker()
    result = tracker.unsubscribe(url)
    
    return {
        "success": result,
        "feed": url,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/feeds/check", response_model=list[AlertResponse])
async def check_feed_updates():
    """Verificar actualizaciones de feeds."""
    from core.feed_tracker import FeedTracker
    
    tracker = FeedTracker()
    updates = tracker.check_updates()
    
    return [
        AlertResponse(
            feed=u["feed"],
            title=u.get("title", ""),
            link=u.get("link", ""),
            published=u.get("published", "")
        )
        for u in updates
    ]


@app.get("/history")
async def get_command_history(limit: int = 50):
    """Historial de comandos."""
    history_file = config.DATA_DIR / "command_history.json"
    
    if not history_file.exists():
        return {"commands": [], "timestamp": datetime.now().isoformat()}
    
    try:
        history = json.loads(history_file.read_text())
        return {
            "commands": history[-limit:],
            "total": len(history),
            "timestamp": datetime.now().isoformat()
        }
    except:
        return {"commands": [], "timestamp": datetime.now().isoformat()}


@app.post("/history/add")
async def add_to_history(command: str, user_id: Optional[str] = None):
    """Añadir comando al historial."""
    from core.command_history import CommandHistory
    
    history = CommandHistory()
    history.add(command, user_id)
    
    return {
        "success": True,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/logs")
async def get_logs(lines: int = 100, level: Optional[str] = None):
    """Obtener logs del agente."""
    log_file = config.LOG_FILE
    
    if not log_file.exists():
        return {"logs": [], "timestamp": datetime.now().isoformat()}
    
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            all_logs = f.readlines()[-lines:]
        
        logs = []
        for line in all_logs:
            if line.strip():
                logs.append(line.strip())
        
        return {
            "logs": logs,
            "count": len(logs),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {"logs": [], "error": str(e), "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)