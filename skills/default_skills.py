"""Operational Skills - Funciones ejecutables para el agente."""

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import config

logger = logging.getLogger(__name__)

# Importar memoria mejorada
try:
    from core.memory import EnhancedMemory
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False


# =============================================================================
# SKILLS DE ARCHIVO
# =============================================================================

def run_command(command: str) -> dict:
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[:5000] if result.stdout else "",
            "stderr": result.stderr[:1000] if result.stderr else "",
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Command timed out after 120s"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def read_file(path: str) -> dict:
    """Read a file and return its contents."""
    try:
        p = Path(path)
        if not p.exists():
            return {"success": False, "error": f"File not found: {path}"}
        
        content = p.read_text(encoding="utf-8")
        lines = content.split("\n")
        
        return {
            "success": True,
            "path": str(p),
            "lines": len(lines),
            "chars": len(content),
            "preview": content[:2000],
            "content": content if len(content) < 50000 else content[-50000:],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def write_file(path: str, content: str, append: bool = False) -> dict:
    """Write content to a file."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        
        mode = "a" if append else "w"
        with open(p, mode, encoding="utf-8") as f:
            f.write(content)
        
        return {
            "success": True,
            "path": str(p),
            "bytes": len(content.encode("utf-8")),
            "lines": len(content.split("\n")),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_files(pattern: str = "*", path: str = ".") -> dict:
    """List files matching a pattern."""
    try:
        base = Path(path)
        files = list(base.glob(pattern))
        
        result = []
        for f in files[:50]:
            stat = f.stat() if f.is_file() else None
            result.append({
                "name": f.name,
                "path": str(f),
                "size": stat.st_size if stat else 0,
                "is_dir": f.is_dir(),
            })
        
        return {"success": True, "files": result, "count": len(result)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_in_files(pattern: str, path: str = ".", extensions: str = ".py,.md,.txt") -> dict:
    """Search for a pattern in files."""
    try:
        results = []
        exts = [e.strip() for e in extensions.split(",")]
        
        for ext in exts:
            for p in Path(path).rglob(f"*{ext}"):
                try:
                    content = p.read_text(encoding="utf-8", errors="ignore")
                    for i, line in enumerate(content.split("\n"), 1):
                        if re.search(pattern, line, re.IGNORECASE):
                            results.append({
                                "file": str(p),
                                "line": i,
                                "text": line.strip()[:100],
                            })
                            if len(results) >= 100:
                                break
                except Exception:
                    pass
        
        return {"success": True, "results": results, "count": len(results)}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# SKILLS DE MEMORIA
# =============================================================================

def remember(content: str, category: str = "fact", priority: int = 5) -> dict:
    """Remember a piece of information."""
    if not MEMORY_AVAILABLE:
        return {"success": False, "error": "Memory module not available"}
    
    try:
        memory = EnhancedMemory()
        mem = memory.add(content, category, priority)
        return {"success": True, "memory_id": mem.get("id"), "content": content}
    except Exception as e:
        return {"success": False, "error": str(e)}


def recall(query: str, limit: int = 5) -> dict:
    """Recall memories matching a query."""
    if not MEMORY_AVAILABLE:
        return {"success": False, "error": "Memory module not available"}
    
    try:
        memory = EnhancedMemory()
        results = memory.search(query, limit=limit)
        return {
            "success": True,
            "results": [
                {"id": r.get("id"), "content": r.get("content"), "category": r.get("category")}
                for r in results
            ],
            "count": len(results),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_memories(limit: int = 10, category: Optional[str] = None) -> dict:
    """Get recent memories."""
    if not MEMORY_AVAILABLE:
        return {"success": False, "error": "Memory module not available"}
    
    try:
        memory = EnhancedMemory()
        recent = memory.get_recent(limit, category)
        return {
            "success": True,
            "memories": recent,
            "count": len(recent),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def memory_stats() -> dict:
    """Get memory statistics."""
    if not MEMORY_AVAILABLE:
        return {"success": False, "error": "Memory module not available"}
    
    try:
        memory = EnhancedMemory()
        stats = memory.get_stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# SKILLS DE WIKI
# =============================================================================

def get_wiki_stats() -> dict:
    """Get wiki statistics."""
    try:
        wiki_dir = config.WIKI_DIR
        raw_dir = config.RAW_DIR
        
        wiki_notes = len(list(wiki_dir.glob("*.md"))) if wiki_dir.exists() else 0
        raw_sources = len(list(raw_dir.glob("*.md"))) if raw_dir.exists() else 0
        
        return {
            "success": True,
            "wiki_notes": wiki_notes,
            "raw_sources": raw_sources,
            "wiki_path": str(wiki_dir),
            "raw_path": str(raw_dir),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def search_wiki(query: str, limit: int = 10) -> dict:
    """Search wiki notes."""
    try:
        results = []
        wiki_dir = config.WIKI_DIR
        
        if not wiki_dir.exists():
            return {"success": False, "error": "Wiki directory not found"}
        
        query_lower = query.lower()
        for md_file in wiki_dir.glob("*.md"):
            try:
                content = md_file.read_text(encoding="utf-8")
                if query_lower in content.lower():
                    results.append({
                        "title": md_file.stem,
                        "path": str(md_file),
                        "preview": content[:200],
                    })
                    if len(results) >= limit:
                        break
            except Exception:
                pass
        
        return {"success": True, "results": results, "count": len(results)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def create_wiki_note(title: str, content: str, tipo: str = "note") -> dict:
    """Create a new wiki note."""
    try:
        wiki_dir = config.WIKI_DIR
        wiki_dir.mkdir(parents=True, exist_ok=True)
        
        filename = re.sub(r'[^\w\s-]', '', title.lower()).strip().replace(' ', '_')
        filepath = wiki_dir / f"{filename}.md"
        
        frontmatter = f"""---
title: {title}
tipo: {tipo}
estado: draft
fecha_ingesta: {datetime.now().strftime('%Y-%m-%d')}
tags: []
---

{content}
"""
        filepath.write_text(frontmatter, encoding="utf-8")
        
        return {"success": True, "path": str(filepath), "title": title}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# SKILLS DE SISTEMA
# =============================================================================

def get_system_info() -> dict:
    """Get system information."""
    try:
        import psutil
        
        return {
            "success": True,
            "cpu_percent": psutil.cpu_percent(interval=0.5),
            "ram_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "python_version": sys.version.split()[0],
            "cwd": os.getcwd(),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_env(key: str, default: str = "") -> dict:
    """Get environment variable."""
    value = os.getenv(key, default)
    return {"success": True, "key": key, "value": value, "exists": value != default}


def set_env(key: str, value: str) -> dict:
    """Set environment variable."""
    os.environ[key] = value
    return {"success": True, "key": key, "value": value}


def check_service(name: str) -> dict:
    """Check if a service is running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", name],
            capture_output=True,
            text=True,
        )
        running = result.returncode == 0
        return {"success": True, "service": name, "running": running}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# SKILLS DE LLM/OLLAMA
# =============================================================================

def list_ollama_models() -> dict:
    """List available Ollama models."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        models = []
        for line in result.stdout.split("\n")[1:]:
            if line.strip():
                parts = line.split()
                if parts:
                    models.append(parts[0])
        return {"success": True, "models": models, "count": len(models)}
    except FileNotFoundError:
        return {"success": False, "error": "Ollama not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def pull_ollama_model(model: str) -> dict:
    """Pull an Ollama model."""
    try:
        result = subprocess.run(
            ["ollama", "pull", model],
            capture_output=True,
            text=True,
            timeout=600,
        )
        return {
            "success": result.returncode == 0,
            "model": model,
            "output": result.stdout[:500],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# SKILLS DE HERRAMIENTAS
# =============================================================================

def execute_python(code: str) -> dict:
    """Execute Python code safely."""
    try:
        import io
        import contextlib
        
        stdout = io.StringIO()
        result = None
        error = None
        
        try:
            with contextlib.redirect_stdout(stdout):
                exec(code, {"__builtins__": __builtins__})
        except Exception as e:
            error = str(e)
        
        output = stdout.getvalue()
        return {
            "success": error is None,
            "output": output,
            "error": error,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def install_package(package: str) -> dict:
    """ Install a Python package."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            capture_output=True,
            text=True,
            timeout=300,
        )
        return {
            "success": result.returncode == 0,
            "package": package,
            "output": result.stdout[-500:] if result.stdout else "",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# SKILLS DE TIEMPO
# =============================================================================

def get_time() -> dict:
    """Get current time."""
    from datetime import datetime
    now = datetime.now()
    return {
        "success": True,
        "iso": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "timestamp": now.timestamp(),
    }


# Import datetime for create_wiki_note
from datetime import datetime