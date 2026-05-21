"""Operational Skills - Funciones ejecutables para el agente."""

import json
import logging
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

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


HMEM_AVAILABLE = False
try:
    from core.hybrid_retriever import get_hmem_manager, get_hybrid_retriever
    HMEM_AVAILABLE = True
except ImportError:
    pass


def hmem_remember(content: str, metadata: dict = None) -> dict:
    """Remember using H-Mem hybrid memory system."""
    if not HMEM_AVAILABLE:
        return {"success": False, "error": "H-Mem not available"}
    
    try:
        hmem = get_hmem_manager()
        result = hmem.remember(content, metadata)
        return {"success": True, **result}
    except Exception as e:
        return {"success": False, "error": str(e)}


def hmem_recall(query: str, time_range: tuple = None, max_results: int = 10) -> dict:
    """Recall from H-Mem memory system."""
    if not HMEM_AVAILABLE:
        return {"success": False, "error": "H-Mem not available"}
    
    try:
        hmem = get_hmem_manager()
        result = hmem.recall(query, time_range)
        evidence = result.get("ranked_evidence", [])
        return {
            "success": True,
            "count": len(evidence),
            "results": [
                {
                    "content": (e.get("node", {}).get("summary") or e.get("node", {}).get("content", ""))[:300],
                    "level": e.get("node", {}).get("level", 0),
                    "timestamp": e.get("node", {}).get("timestamp", ""),
                    "score": e.get("combined_score", 0),
                }
                for e in evidence[:max_results]
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def hmem_think(query: str, context: str = None) -> dict:
    """Full H-Mem query with answer generation."""
    if not HMEM_AVAILABLE:
        return {"success": False, "error": "H-Mem not available"}
    
    try:
        hmem = get_hmem_manager()
        answer = hmem.think(query, context)
        return {"success": True, "answer": answer}
    except Exception as e:
        return {"success": False, "error": str(e)}


def hmem_get_context(query: str, max_len: int = 2000) -> dict:
    """Get memory context for augmenting prompts."""
    if not HMEM_AVAILABLE:
        return {"success": False, "error": "H-Mem not available"}
    
    try:
        hmem = get_hmem_manager()
        context = hmem.get_context(query)
        return {"success": True, "context": context}
    except Exception as e:
        return {"success": False, "error": str(e)}


def hmem_get_stats() -> dict:
    """Get H-Mem system statistics."""
    if not HMEM_AVAILABLE:
        return {"success": False, "error": "H-Mem not available"}
    
    try:
        hmem = get_hmem_manager()
        stats = hmem.stats()
        return {"success": True, "stats": stats}
    except Exception as e:
        return {"success": False, "error": str(e)}


def hmem_get_recent(limit: int = 10) -> dict:
    """Get recent memories from H-Mem tree."""
    if not HMEM_AVAILABLE:
        return {"success": False, "error": "H-Mem not available"}
    
    try:
        hmem = get_hmem_manager()
        memories = hmem.get_recent_memories(limit=limit)
        return {
            "success": True,
            "count": len(memories),
            "memories": [
                {
                    "content": (m.get("content") or m.get("summary") or "")[:200],
                    "level": m.get("level", 0),
                    "timestamp": m.get("timestamp", ""),
                }
                for m in memories
            ],
        }
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
        import platform
        if platform.system() == "Windows":
            result = subprocess.run(
                ["tasklist", "/FI", f"IMAGENAME eq {name}*"],
                capture_output=True,
                text=True,
                shell=True,
            )
            running = name.lower() in result.stdout.lower()
        else:
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


# =============================================================================
# SKILLS DE FEEDBACK LOOP
# =============================================================================

def record_feedback(query: str, response: str, rating: int) -> dict:
    """Record user feedback for last response. Rating: 1 (bad) to 5 (excellent)."""
    try:
        import json
        from pathlib import Path
        from datetime import datetime

        feedback_file = Path(config.STORAGE_DIR) / "feedback.json"

        # Load existing feedback
        if feedback_file.exists():
            with open(feedback_file, 'r', encoding='utf-8') as f:
                feedback_data = json.load(f)
        else:
            feedback_data = {
                "ratings": [],
                "patterns": {"good": [], "bad": []},
                "last_response": {"query": None, "response": None, "timestamp": None},
                "stats": {"total_ratings": 0, "avg_rating": 0, "good_count": 0, "bad_count": 0}
            }

        # Clamp rating
        rating = max(1, min(5, rating))

        # Add new rating
        new_entry = {
            "query": query[:500] if query else "",
            "response": response[:2000] if response else "",
            "rating": rating,
            "timestamp": datetime.now().isoformat()
        }
        feedback_data["ratings"].append(new_entry)

        # Update patterns based on rating
        if rating >= 4:
            # Extract patterns from good responses
            if len(query) > 20:
                feedback_data["patterns"]["good"].append(query[:100])
        elif rating <= 2:
            if len(query) > 20:
                feedback_data["patterns"]["bad"].append(query[:100])

        # Keep only last 100 ratings
        feedback_data["ratings"] = feedback_data["ratings"][-100:]
        feedback_data["patterns"]["good"] = list(set(feedback_data["patterns"]["good"]))[-50:]
        feedback_data["patterns"]["bad"] = list(set(feedback_data["patterns"]["bad"]))[-50:]

        # Update stats
        feedback_data["stats"]["total_ratings"] = len(feedback_data["ratings"])
        all_ratings = [r["rating"] for r in feedback_data["ratings"]]
        feedback_data["stats"]["avg_rating"] = sum(all_ratings) / len(all_ratings) if all_ratings else 0
        feedback_data["stats"]["good_count"] = len([r for r in all_ratings if r >= 4])
        feedback_data["stats"]["bad_count"] = len([r for r in all_ratings if r <= 2])

        # Save
        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, indent=2, ensure_ascii=False)

        return {
            "success": True,
            "rating": rating,
            "stats": feedback_data["stats"]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def record_eval_feedback(user_feedback: str, query: str = None, response: str = None) -> dict:
    """Record user's sí/no/ms feedback for agent response."""
    try:
        import json
        from pathlib import Path
        from datetime import datetime

        feedback_file = Path(config.STORAGE_DIR) / "feedback.json"

        # Load existing
        if feedback_file.exists():
            with open(feedback_file, 'r', encoding='utf-8') as f:
                feedback_data = json.load(f)
        else:
            feedback_data = {"eval_responses": [], "stats": {"total_evaluated": 0, "accuracy_rate": 0, "avg_rating": 0}}

        # Normalize feedback
        fb = user_feedback.lower().strip()
        if fb in ["si", "sí", "yes", "y"]:
            feedback = "sí"
            numeric = 5
        elif fb in ["no", "n"]:
            feedback = "no"
            numeric = 1
        elif fb in ["ms", "más o menos", "mas o menos", "maybe"]:
            feedback = "más o menos"
            numeric = 3
        else:
            return {"success": False, "error": "Feedback inválido. Usa: sí, no, o más o menos"}

        # Get pending evaluation if no query provided
        pending = feedback_data.get("pending_eval", {})
        if not query and pending:
            query = pending.get("query", "")
            response = pending.get("response", "")

        # Add eval response
        eval_entry = {
            "query": (query or "")[:500],
            "response": (response or "")[:2000],
            "user_feedback": feedback,
            "numeric_rating": numeric,
            "timestamp": datetime.now().isoformat()
        }
        feedback_data.setdefault("eval_responses", []).append(eval_entry)

        # Update stats
        total = len(feedback_data["eval_responses"])
        yes_count = sum(1 for e in feedback_data["eval_responses"] if e.get("user_feedback") == "sí")
        ms_count = sum(1 for e in feedback_data["eval_responses"] if e.get("user_feedback") == "más o menos")

        # Accuracy: sí + (ms * 0.5) / total
        accuracy = (yes_count + ms_count * 0.5) / total if total > 0 else 0
        avg_rating = sum(e.get("numeric_rating", 0) for e in feedback_data["eval_responses"]) / total if total > 0 else 0

        feedback_data["stats"] = {
            "total_evaluated": total,
            "accuracy_rate": round(accuracy, 2),
            "avg_rating": round(avg_rating, 1),
            "yes_count": yes_count,
            "no_count": total - yes_count - ms_count,
            "ms_count": ms_count
        }

        # Clear pending
        feedback_data.pop("pending_eval", None)

        # Keep last 200
        feedback_data["eval_responses"] = feedback_data["eval_responses"][-200:]

        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, indent=2, ensure_ascii=False)

        return {"success": True, "feedback": feedback, "stats": feedback_data["stats"]}
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_pending_eval(query: str, response: str, context: str = "") -> dict:
    """Set a pending evaluation after agent response."""
    try:
        import json
        from pathlib import Path

        feedback_file = Path(config.STORAGE_DIR) / "feedback.json"

        if feedback_file.exists():
            with open(feedback_file, 'r', encoding='utf-8') as f:
                feedback_data = json.load(f)
        else:
            feedback_data = {"eval_responses": [], "stats": {}}

        feedback_data["pending_eval"] = {
            "query": query[:500],
            "response": response[:2000],
            "context": context,
            "timestamp": datetime.now().isoformat()
        }

        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(feedback_data, f, indent=2, ensure_ascii=False)

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_eval_stats(limit: int = 20) -> dict:
    """Get evaluation statistics."""
    try:
        import json
        from pathlib import Path

        feedback_file = Path(config.STORAGE_DIR) / "feedback.json"

        if not feedback_file.exists():
            return {"total": 0, "accuracy_rate": 0, "avg_rating": 0, "recent": []}

        with open(feedback_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        evals = data.get("eval_responses", [])
        recent = evals[-limit:] if evals else []

        return {
            "total": data.get("stats", {}).get("total_evaluated", 0),
            "accuracy_rate": data.get("stats", {}).get("accuracy_rate", 0),
            "avg_rating": data.get("stats", {}).get("avg_rating", 0),
            "stats": data.get("stats", {}),
            "recent": recent
        }
    except Exception as e:
        return {"error": str(e)}


def get_feedback_context() -> dict:
    """Get feedback context to include in agent prompts."""
    try:
        import json
        from pathlib import Path

        feedback_file = Path(config.STORAGE_DIR) / "feedback.json"

        if not feedback_file.exists():
            return {"success": True, "context": "", "stats": {}}

        with open(feedback_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Build context string
        context_parts = []

        if data["stats"]["total_ratings"] > 0:
            context_parts.append(f"Feedback stats: avg={data['stats']['avg_rating']:.1f}/5, total={data['stats']['total_ratings']}")

        # Recent good patterns
        good = data["patterns"]["good"][-5:]
        if good:
            context_parts.append(f"Good query patterns: {', '.join(good[:3])}")

        # Recent bad patterns
        bad = data["patterns"]["bad"][-5:]
        if bad:
            context_parts.append(f"Query patterns to avoid: {', '.join(bad[:3])}")

        # Low rated themes
        if data["stats"]["bad_count"] > 0:
            context_parts.append(f"⚠️ {data['stats']['bad_count']} responses rated as poor - be more careful with these topics")

        context = "\n".join(context_parts)

        return {
            "success": True,
            "context": context,
            "stats": data["stats"]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_last_response(query: str, response: str) -> dict:
    """Store last agent response for potential feedback."""
    try:
        import json
        from pathlib import Path
        from datetime import datetime

        feedback_file = Path(config.STORAGE_DIR) / "feedback.json"

        if feedback_file.exists():
            with open(feedback_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            return {"success": False, "error": "Feedback file not found"}

        data["last_response"] = {
            "query": query[:500] if query else "",
            "response": response[:2000] if response else "",
            "timestamp": datetime.now().isoformat()
        }

        with open(feedback_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_last_response() -> dict:
    """Get last agent response for feedback."""
    try:
        import json
        from pathlib import Path

        feedback_file = Path(config.STORAGE_DIR) / "feedback.json"

        if not feedback_file.exists():
            return {"success": True, "response": None}

        with open(feedback_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return {
            "success": True,
            "response": data.get("last_response")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# SKILLS DE GITHUB
# =============================================================================

def clone_repo(url: str, destination: str = None) -> dict:
    """Clone a GitHub repository."""
    import tempfile
    import shutil
    
    if not url.startswith("http"):
        url = f"https://github.com/{url}"
    
    if not destination:
        with tempfile.TemporaryDirectory() as tmpdir:
            destination = tmpdir
    
    try:
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, destination],
            capture_output=True,
            text=True,
            timeout=300,
        )
        
        if result.returncode == 0:
            files = list(Path(destination).rglob("*"))
            return {
                "success": True,
                "url": url,
                "destination": destination,
                "files_count": len([f for f in files if f.is_file()]),
            }
        else:
            return {"success": False, "error": result.stderr}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# SKILLS DE TRADUCCIÓN Y LANGUAGE
# =============================================================================

def detect_language(text: str) -> dict:
    """Detect language of text."""
    try:
        import langdetect
        from langdetect import detect_langs
        
        lang = detect_langs(text)[0]
        return {
            "success": True,
            "language": lang.lang,
            "confidence": lang.prob,
        }
    except ImportError:
        return {"success": False, "error": "langdetect not installed. Install with: pip install langdetect"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def translate(text: str, target: str = "en", source: str = "auto") -> dict:
    """Translate text using deep-translator."""
    try:
        from deep_translator import GoogleTranslator
        
        translator = GoogleTranslator(source=source, target=target)
        result = translator.translate(text)
        
        return {
            "success": True,
            "original": text[:500],
            "translated": result,
            "source": source,
            "target": target,
        }
    except ImportError:
        return {"success": False, "error": "deep-translator not installed. Run: pip install deep-translator"}
    except Exception as e:
        return {"success": False, "error": str(e)}


# =============================================================================
# SKILLS DE BÚSQUEDA Y AUDIO
# =============================================================================

def search_arxiv(query: str, max_results: int = 5) -> dict:
    """Search arXiv for papers."""
    try:
        import urllib.parse
        import urllib.request
        
        base_url = "http://export.arxiv.org/api/query"
        search_query = f"all:{urllib.parse.quote(query)}"
        url = f"{base_url}?search_query={search_query}&max_results={max_results}&sortBy=relevance"
        
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read().decode("utf-8")
        
        papers = []
        import re
        entries = re.findall(r"<entry>(.*?)</entry>", data, re.DOTALL)
        
        for entry in entries:
            title = re.search(r"<title>(.*?)</title>", entry, re.DOTALL)
            summary = re.search(r"<summary>(.*?)</summary>", entry, re.DOTALL)
            link = re.search(r"<id>(.*?)</id>", entry)
            
            if title and summary:
                papers.append({
                    "title": title.group(1).strip(),
                    "summary": summary.group(1).strip()[:300],
                    "link": link.group(1) if link else "",
                })
        
        return {
            "success": True,
            "query": query,
            "count": len(papers),
            "papers": papers,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_audio_summary(url: str) -> dict:
    """Get summary of YouTube audio/video (compatible with youtube-transcript-api>=1.0)."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        video_id = None
        if "youtube.com/watch" in url:
            import urllib.parse
            video_id = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("v", [None])[0]
        elif "youtu.be" in url:
            video_id = url.split("/")[-1].split("?")[0]

        if not video_id:
            return {"success": False, "error": "Could not extract video ID"}

        # API 1.0+: fetch() returns a FetchedTranscript iterable of snippet dicts
        ytt = YouTubeTranscriptApi()
        fetched = ytt.fetch(video_id, languages=["es", "en"])
        snippets = list(fetched)
        
        # Handle both object attributes (v1.0+) and dicts (older versions)
        text_parts = []
        for s in snippets:
            part = s.get("text", "") if isinstance(s, dict) else getattr(s, "text", "")
            if part:
                text_parts.append(str(part))
                
        full_text = " ".join(text_parts)

        return {
            "success": True,
            "video_id": video_id,
            "text": full_text[:5000],
            "chunks": len(snippets),
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# Import datetime for create_wiki_note
from datetime import datetime


# =============================================================================
# FEEDBACK SYSTEM - Calificar respuestas del agente
# =============================================================================

# NOTE: Las funciones set_last_response, get_last_response, record_feedback y
# get_feedback_context ya están definidas arriba con persistencia en archivo.
# Las versiones en memoria de abajo fueron eliminadas para evitar duplicados.

