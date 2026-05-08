import json
import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def run_command(command: str) -> dict:
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except Exception as e:
        return {"error": str(e)}


def read_file(path: str) -> dict:
    """Read a file and return its contents."""
    try:
        p = Path(path)
        if not p.exists():
            return {"error": f"File not found: {path}"}
        return {"content": p.read_text(encoding="utf-8")}
    except Exception as e:
        return {"error": str(e)}


def write_file(path: str, content: str) -> dict:
    """Write content to a file."""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return {"success": True, "path": path}
    except Exception as e:
        return {"error": str(e)}


def list_files(pattern: str = "*") -> dict:
    """List files matching a pattern."""
    try:
        files = list(Path(".").glob(pattern))
        return {"files": [str(f) for f in files]}
    except Exception as e:
        return {"error": str(e)}


def search_in_files(pattern: str, path: str = ".") -> dict:
    """Search for a pattern in files."""
    try:
        import re
        results = []
        for p in Path(path).rglob("*.py"):
            try:
                content = p.read_text(encoding="utf-8")
                for i, line in enumerate(content.split("\n"), 1):
                    if re.search(pattern, line):
                        results.append({"file": str(p), "line": i, "text": line.strip()})
            except:
                pass
        return {"results": results[:50]}
    except Exception as e:
        return {"error": str(e)}


def create_project_knowledge_graph(source_dir: str) -> dict:
    """Create a knowledge graph from project files."""
    try:
        from core.graph_enhancer import ProjectGrapher
        grapher = ProjectGrapher()
        graph = grapher.build_graph(source_dir)
        return {"nodes": len(graph["nodes"]), "edges": len(graph["edges"])}
    except Exception as e:
        return {"error": str(e)}


def analyze_research(query: str) -> dict:
    """Analyze research topics."""
    try:
        from core.research_analyzer import ResearchAnalyzer
        analyzer = ResearchAnalyzer()
        return analyzer.analyze(query)
    except Exception as e:
        return {"error": str(e)}