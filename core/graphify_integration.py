"""Graphify Integration - Knowledge graph builder for Asubarnipal.

Wraps graphifyy CLI to build, query, and maintain knowledge graphs
from wiki notes, raw sources, and Obsidian vault content.

Output:
    graphify-out/
    ├── graph.html          Interactive visualization
    ├── GRAPH_REPORT.md     Summary report
    └── graph.json          Full queryable graph
"""

import json
import logging
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import config

logger = logging.getLogger(__name__)

GRAPHIFY_OUTPUT_DIR = config.OBSIDIAN_PATH / "graphify-out"
GRAPH_JSON = GRAPHIFY_OUTPUT_DIR / "graph.json"
GRAPH_HTML = GRAPHIFY_OUTPUT_DIR / "graph.html"
GRAPH_REPORT = GRAPHIFY_OUTPUT_DIR / "GRAPH_REPORT.md"


def _check_graphify() -> bool:
    """Check if graphify CLI is available."""
    try:
        result = subprocess.run(
            ["graphify", "--version"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _run_graphify(args: List[str], timeout: int = 600) -> Dict[str, Any]:
    """Run graphify CLI command and return result."""
    cmd = ["graphify"] + args
    logger.info(f"Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(config.OBSIDIAN_PATH)
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        logger.error(f"Graphify command timed out after {timeout}s")
        return {"success": False, "stdout": "", "stderr": "Timeout", "returncode": -1}
    except Exception as e:
        logger.error(f"Graphify command failed: {e}")
        return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}


def build_graph(
    target_path: Optional[str] = None,
    mode: str = "default",
    backend: str = "ollama",
    no_viz: bool = False,
    force: bool = False,
) -> Dict[str, Any]:
    """Build knowledge graph from wiki/raw content.

    Args:
        target_path: Directory to scan (default: OBSIDIAN_PATH/wiki)
        mode: Extraction mode (default, deep)
        backend: LLM backend (ollama, gemini, openai)
        no_viz: Skip HTML visualization
        force: Force rebuild even with fewer nodes

    Returns:
        Dict with success status, node count, edge count, paths
    """
    path = target_path or str(config.OBSIDIAN_PATH / "wiki")

    if not _check_graphify():
        return {
            "success": False,
            "error": "graphify CLI not found. Install: pip install graphifyy",
        }

    args = ["extract", path, "--backend", backend]

    if mode == "deep":
        args.append("--mode")
        args.append("deep")

    if no_viz:
        args.append("--no-viz")

    if force:
        args.append("--force")

    result = _run_graphify(args)

    if result["success"]:
        stats = get_graph_stats()
        return {
            "success": True,
            "message": "Graph built successfully",
            "stats": stats,
            "graph_json": str(GRAPH_JSON),
            "graph_html": str(GRAPH_HTML),
            "graph_report": str(GRAPH_REPORT),
        }
    else:
        return {
            "success": False,
            "error": result.get("stderr", "Unknown error"),
            "stdout": result.get("stdout", ""),
        }


def query_graph(question: str, graph_path: Optional[str] = None) -> Dict[str, Any]:
    """Query the knowledge graph with a natural language question.

    Args:
        question: Natural language question
        graph_path: Path to graph.json (default: graphify-out/graph.json)

    Returns:
        Dict with answer and related nodes
    """
    gpath = graph_path or str(GRAPH_JSON)

    if not GRAPH_JSON.exists():
        return {"success": False, "error": "No graph available. Run /graphify first."}

    if not _check_graphify():
        return {"success": False, "error": "graphify CLI not found."}

    args = ["query", question, "--graph", gpath]
    result = _run_graphify(args, timeout=120)

    return {
        "success": result["success"],
        "answer": result.get("stdout", "").strip(),
        "stderr": result.get("stderr", ""),
    }


def get_graph_stats() -> Dict[str, Any]:
    """Get statistics from the built graph.

    Returns:
        Dict with nodes, edges, communities, hubs, file sizes
    """
    stats = {
        "exists": GRAPH_JSON.exists(),
        "html_exists": GRAPH_HTML.exists(),
        "report_exists": GRAPH_REPORT.exists(),
        "nodes": 0,
        "edges": 0,
        "communities": 0,
        "hubs": [],
        "file_size_kb": 0,
        "last_built": None,
    }

    if not GRAPH_JSON.exists():
        return stats

    try:
        with open(GRAPH_JSON, "r", encoding="utf-8") as f:
            graph = json.load(f)

        nodes = graph.get("nodes", [])
        edges = graph.get("edges", [])

        stats["nodes"] = len(nodes)
        stats["edges"] = len(edges)
        stats["file_size_kb"] = GRAPH_JSON.stat().st_size / 1024

        mtime = GRAPH_JSON.stat().st_mtime
        stats["last_built"] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

        # Count communities
        communities = set()
        for node in nodes:
            comm = node.get("community", node.get("cluster"))
            if comm:
                communities.add(comm)
        stats["communities"] = len(communities)

        # Find hubs (highest degree nodes)
        degree = {}
        for edge in edges:
            src = edge.get("source", edge.get("from"))
            tgt = edge.get("target", edge.get("to"))
            degree[src] = degree.get(src, 0) + 1
            degree[tgt] = degree.get(tgt, 0) + 1

        sorted_hubs = sorted(degree.items(), key=lambda x: x[1], reverse=True)[:10]
        stats["hubs"] = [{"name": name, "connections": count} for name, count in sorted_hubs]

    except Exception as e:
        logger.error(f"Error reading graph stats: {e}")
        stats["error"] = str(e)

    return stats


def get_graph_report() -> str:
    """Read the GRAPH_REPORT.md content.

    Returns:
        Report content as string
    """
    if not GRAPH_REPORT.exists():
        return ""

    try:
        return GRAPH_REPORT.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        logger.error(f"Error reading graph report: {e}")
        return ""


def get_graph_html_path() -> Optional[str]:
    """Get path to graph HTML for dashboard embedding.

    Returns:
        Path to graph.html or None
    """
    if GRAPH_HTML.exists():
        return str(GRAPH_HTML)
    return None


def copy_graph_to_dashboard() -> Optional[str]:
    """Copy graph.html to dashboard-accessible location.

    Returns:
        Path to copied file or None
    """
    if not GRAPH_HTML.exists():
        return None

    dashboard_graph = config.DATA_DIR / "graph.html"
    try:
        shutil.copy2(GRAPH_HTML, dashboard_graph)
        return str(dashboard_graph)
    except Exception as e:
        logger.error(f"Error copying graph to dashboard: {e}")
        return None


def add_url_to_graph(url: str, author: str = None) -> Dict[str, Any]:
    """Add a URL (paper, video, article) to the graph.

    Args:
        url: URL to add
        author: Optional author name

    Returns:
        Dict with success status
    """
    if not _check_graphify():
        return {"success": False, "error": "graphify CLI not found."}

    args = ["add", url]
    if author:
        args.extend(["--author", author])

    result = _run_graphify(args, timeout=300)

    return {
        "success": result["success"],
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
    }


def update_graph(target_path: Optional[str] = None) -> Dict[str, Any]:
    """Update graph with changed files only (faster than full rebuild).

    Args:
        target_path: Directory to scan

    Returns:
        Dict with success status
    """
    path = target_path or str(config.OBSIDIAN_PATH / "wiki")

    if not _check_graphify():
        return {"success": False, "error": "graphify CLI not found."}

    args = ["extract", path, "--update", "--backend", "ollama"]
    result = _run_graphify(args)

    if result["success"]:
        return {
            "success": True,
            "message": "Graph updated",
            "stats": get_graph_stats(),
        }
    else:
        return {
            "success": False,
            "error": result.get("stderr", "Unknown error"),
        }


def export_graph(format: str = "html") -> Dict[str, Any]:
    """Export graph in different formats.

    Args:
        format: html, svg, graphml, wiki, callflow-html

    Returns:
        Dict with success status and output path
    """
    if not GRAPH_JSON.exists():
        return {"success": False, "error": "No graph available."}

    if not _check_graphify():
        return {"success": False, "error": "graphify CLI not found."}

    if format == "wiki":
        args = ["extract", str(config.OBSIDIAN_PATH / "wiki"), "--wiki"]
    elif format == "callflow-html":
        args = ["export", "callflow-html"]
    elif format == "svg":
        args = ["extract", str(config.OBSIDIAN_PATH / "wiki"), "--svg"]
    elif format == "graphml":
        args = ["extract", str(config.OBSIDIAN_PATH / "wiki"), "--graphml"]
    else:
        return {"success": False, "error": f"Unknown format: {format}"}

    result = _run_graphify(args)

    return {
        "success": result["success"],
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
    }


def install_graphify_hook() -> Dict[str, Any]:
    """Install git post-commit hook for auto-rebuild.

    Returns:
        Dict with success status
    """
    if not _check_graphify():
        return {"success": False, "error": "graphify CLI not found."}

    result = _run_graphify(["hook", "install"])

    return {
        "success": result["success"],
        "stdout": result.get("stdout", ""),
        "stderr": result.get("stderr", ""),
    }
