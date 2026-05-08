"""
ASUBARNIPAL COMMAND CENTER V5.0
Dashboard profesional adaptado a la arquitectura Karpathy Wiki Pattern.
Lee estructura: /wiki/, /raw/, index.md, log.md, CLAUDE.md
Autor: Asubarnipal Architect
Requiere: streamlit plotly pandas psutil pyyaml
"""

import os
import re
import json
import yaml
import time
import sys
import psutil
import logging
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

sys.path.insert(0, str(Path(__file__).parent))

import config
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# No banner import - only in agent

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

@dataclass
class AppConfig:
    obsidian_path: str = ""
    refresh_interval: int = 0  # 0 = disabled
    max_log_lines: int = 100
    theme_color: str = "#58a6ff"
    agente_script_name: str = "telegram_bot"
    
    def __post_init__(self):
        # Use Windows path c:\Obsidian
        self.obsidian_path = r"c:\Obsidian"
        if not os.path.exists(self.obsidian_path):
            self.obsidian_path = r"C:\Obsidian"
    
    @property
    def wiki_path(self) -> str:
        return os.path.join(self.obsidian_path, "wiki")
    
    @property
    def raw_path(self) -> str:
        return os.path.join(self.obsidian_path, "raw")
    
    @property
    def log_file(self) -> str:
        return str(config.LOG_FILE)
    
    @property
    def index_path(self) -> str:
        return os.path.join(self.obsidian_path, "index.md")
    
    @property
    def log_md_path(self) -> str:
        return os.path.join(self.obsidian_path, "log.md")
    
    @property
    def schema_path(self) -> str:
        return os.path.join(self.obsidian_path, "CLAUDE.md")
    
    @property
    def graph_store_path(self) -> str:
        return os.path.join(self.obsidian_path, "graph_store")
    
    @property
    def data_path(self) -> str:
        return os.path.join(str(config.BASE_DIR), "data")

# =============================================================================
# ESTADO DE SESIÓN
# =============================================================================

def init_session_state():
    defaults = {
        "config": AppConfig(),
        "last_refresh": datetime.now(),
        "cpu_history": [],
        "ram_history": [],
        "notes_history": [],
        "paused": False,
        "selected_note": None,
        "log_filter": "ALL",
        "search_query": "",
        "active_tab": "dashboard",
        "system_boot": datetime.now(),
        "alerts": [],
        "dark_mode": True,
        "agente_status": False,
        "agente_pid": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# =============================================================================
# DETECCIÓN DE PROCESO AGENTE
# =============================================================================

def find_agente_process(script_name: str = "agente1.py") -> Optional[psutil.Process]:
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            cmdline = proc.info.get('cmdline') or []
            if any(script_name.lower() in arg.lower() for arg in cmdline):
                return psutil.Process(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None

def get_agente_status(config: AppConfig) -> Dict[str, Any]:
    proc = find_agente_process(config.agente_script_name)
    if proc is None:
        return {
            "running": False, "pid": None, "uptime": None,
            "cpu": 0.0, "memory_mb": 0.0, "threads": 0, "status": "OFFLINE"
        }
    try:
        with proc.oneshot():
            uptime = datetime.now() - datetime.fromtimestamp(proc.create_time())
            return {
                "running": True, "pid": proc.pid, "uptime": uptime,
                "cpu": proc.cpu_percent(interval=0.1),
                "memory_mb": proc.memory_info().rss / 1024 / 1024,
                "threads": proc.num_threads(),
                "status": proc.status()
            }
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return {"running": False, "pid": None, "uptime": None, "cpu": 0.0,
                "memory_mb": 0.0, "threads": 0, "status": "OFFLINE"}

def find_avatar_image() -> Optional[str]:
    script_dir = Path(__file__).parent if "__file__" in dir() else Path.cwd()
    candidates = [
        script_dir / "Asubarnipal.jpg", script_dir / "asubarnipal.jpg",
        Path("Asubarnipal.jpg"), Path("asubarnipal.jpg"),
        Path(r"C:\\AGENTE TELEGRAM\\Asubarnipal.jpg"),
        Path(r"C:\\Obsidian\\Asubarnipal.jpg"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())
    return None

# =============================================================================
# MOTOR DE WIKI - LECTOR DE ESTRUCTURA KARPATHY
# =============================================================================

class WikiReader:
    """Lee y analiza la estructura Karpathy del wiki."""

    def __init__(self, config: AppConfig):
        self.config = config
        self.wiki_path = Path(config.wiki_path)
        self.raw_path = Path(config.raw_path)
        self.index_path = Path(config.index_path)
        self.log_md_path = Path(config.log_md_path)
        self.schema_path = Path(config.schema_path)
        self.notes: List[Dict] = []
        self.raw_sources: List[Dict] = []
        self.log_entries: List[Dict] = []
        self.schema_content = ""
        self._scan()

    def _extraer_frontmatter(self, contenido: str) -> Tuple[Dict, str]:
        if contenido.startswith("---"):
            parts = contenido.split("---", 2)
            if len(parts) >= 3:
                try:
                    return yaml.safe_load(parts[1]) or {}, parts[2]
                except yaml.YAMLError:
                    return {}, contenido
        return {}, contenido

    def _scan(self):
        """Escanea wiki/, raw/, index.md, log.md, CLAUDE.md"""
        # Escanear wiki/
        if self.wiki_path.exists():
            for file_path in self.wiki_path.rglob("*.md"):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    fm, body = self._extraer_frontmatter(content)
                    self.notes.append({
                        "id": file_path.stem,
                        "path": str(file_path),
                        "filename": file_path.name,
                        "tipo": fm.get("tipo", "unknown"),
                        "titulo": fm.get("titulo", file_path.stem),
                        "fuente": fm.get("fuente", "N/A"),
                        "fecha_ingesta": fm.get("fecha_ingesta", ""),
                        "fecha_actualizacion": fm.get("fecha_actualizacion", ""),
                        "estado": fm.get("estado", "unknown"),
                        "tags": fm.get("tags", []),
                        "relacionados": fm.get("relacionados", []),
                        "word_count": len(body.split()),
                        "line_count": len(body.splitlines()),
                        "content_preview": body[:500] + "..." if len(body) > 500 else body,
                    })
                except Exception:
                    continue

        # Escanear raw/
        if self.raw_path.exists():
            for file_path in self.raw_path.rglob("*.md"):
                try:
                    stat = file_path.stat()
                    self.raw_sources.append({
                        "filename": file_path.name,
                        "size_kb": stat.st_size / 1024,
                        "modified": datetime.fromtimestamp(stat.st_mtime),
                        "tipo": file_path.name.split("_")[0] if "_" in file_path.name else "unknown",
                    })
                except Exception:
                    continue

        # Leer schema
        if self.schema_path.exists():
            try:
                self.schema_content = self.schema_path.read_text(encoding="utf-8", errors="ignore")[:2000]
            except Exception:
                pass

        # Parsear log.md
        if self.log_md_path.exists():
            try:
                content = self.log_md_path.read_text(encoding="utf-8", errors="ignore")
                # Parsear entradas ## [fecha] tipo | descripcion
                pattern = r"##\s*\[(.*?)\]\s*(.*?)\s*\|\s*(.*)"
                for match in re.finditer(pattern, content):
                    self.log_entries.append({
                        "timestamp": match.group(1),
                        "tipo": match.group(2).strip(),
                        "descripcion": match.group(3).strip(),
                    })
            except Exception:
                pass

    def get_stats(self) -> Dict[str, Any]:
        """Estadísticas del wiki Karpathy."""
        tipos = Counter(n["tipo"] for n in self.notes)
        return {
            "total_wiki": len(self.notes),
            "total_raw": len(self.raw_sources),
            "sources": tipos.get("source", 0),
            "entities": tipos.get("entity", 0),
            "concepts": tipos.get("concept", 0),
            "synthesis": tipos.get("synthesis", 0),
            "mocs": tipos.get("moc", 0),
            "unknown": tipos.get("unknown", 0),
            "draft": sum(1 for n in self.notes if n["estado"] == "draft"),
            "final": sum(1 for n in self.notes if n["estado"] == "final"),
            "total_words": sum(n["word_count"] for n in self.notes),
            "total_links": sum(len(n["relacionados"]) for n in self.notes),
            "orphans": sum(1 for n in self.notes if not n["relacionados"]),
            "log_entries": len(self.log_entries),
            "last_ingest": self.log_entries[-1]["timestamp"] if self.log_entries else "N/A",
        }

    def get_tipo_distribution(self) -> pd.DataFrame:
        if not self.notes:
            return pd.DataFrame(columns=["tipo", "count", "label"])

        tipos = Counter(n["tipo"] for n in self.notes)
        if not tipos:
            return pd.DataFrame(columns=["tipo", "count", "label"])

        label_map = {
            "source": "📄 Fuentes", "entity": "🏛️ Entidades",
            "concept": "💡 Conceptos", "synthesis": "🔗 Síntesis",
            "moc": "🗺️ MOCs", "unknown": "❓ Desconocido"
        }

        data = []
        for k, v in tipos.items():
            data.append({"tipo": k, "count": v, "label": label_map.get(k, k)})

        df = pd.DataFrame(data)
        return df.sort_values("count", ascending=False)

    def get_timeline_data(self) -> pd.DataFrame:
        if not self.notes:
            return pd.DataFrame(columns=["date", "count"])

        dates = []
        for note in self.notes:
            fecha = note.get("fecha_ingesta") or note.get("fecha_actualizacion")
            if fecha and isinstance(fecha, str):
                try:
                    dates.append(datetime.strptime(fecha, "%Y-%m-%d"))
                except (ValueError, TypeError):
                    pass

        if not dates:
            return pd.DataFrame(columns=["date", "count"])

        df = pd.DataFrame({"date": dates})
        df["date"] = pd.to_datetime(df["date"]).dt.date
        result = df.groupby("date").size().reset_index(name="count")
        return result.sort_values("date")

    def get_tag_distribution(self) -> pd.DataFrame:
        all_tags = []
        for note in self.notes:
            all_tags.extend(note.get("tags", []))
        if not all_tags:
            return pd.DataFrame(columns=["tag", "count"])
        tag_counts = Counter(all_tags)
        return pd.DataFrame(tag_counts.most_common(20), columns=["tag", "count"])

    def get_raw_timeline(self) -> pd.DataFrame:
        if not self.raw_sources:
            return pd.DataFrame(columns=["date", "count"])

        dates = [s.get("modified") for s in self.raw_sources if s.get("modified")]
        if not dates:
            return pd.DataFrame(columns=["date", "count"])

        df = pd.DataFrame({"date": dates})
        df["date"] = pd.to_datetime(df["date"]).dt.date
        result = df.groupby("date").size().reset_index(name="count")
        return result.sort_values("date")

    def get_log_activity(self) -> pd.DataFrame:
        if not self.log_entries:
            return pd.DataFrame(columns=["date", "ingests", "queries", "lints"])

        df = pd.DataFrame(self.log_entries)
        df["date"] = pd.to_datetime(df["timestamp"], errors="coerce").dt.date

        activity = []
        for date, group in df.groupby("date"):
            ingests = sum(1 for t in group["tipo"] if "ingest" in t.lower())
            queries = sum(1 for t in group["tipo"] if "query" in t.lower())
            lints = sum(1 for t in group["tipo"] if "lint" in t.lower())
            activity.append({"date": date, "ingests": ingests, "queries": queries, "lints": lints})

        return pd.DataFrame(activity).sort_values("date")

# =============================================================================
# TELEMETRÍA
# =============================================================================

class TelemetryEngine:
    def __init__(self, max_history: int = 60):
        self.max_history = max_history

    def snapshot(self) -> Dict[str, float]:
        return {
            "cpu": psutil.cpu_percent(interval=0.1),
            "ram": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage("/").percent if os.name != "nt" else 0,
            "timestamp": datetime.now(),
        }

    def update_history(self, history: List[Dict], new_value: Dict):
        history.append(new_value)
        if len(history) > self.max_history:
            history.pop(0)
        return history

    def get_process_info(self) -> Dict:
        proc = psutil.Process()
        return {
            "pid": proc.pid, "threads": proc.num_threads(),
            "memory_mb": proc.memory_info().rss / 1024 / 1024,
            "cpu_percent": proc.cpu_percent(interval=0.1),
            "status": proc.status(),
        }

# =============================================================================
# PARSERS
# =============================================================================

def parse_logs(log_path: str, max_lines: int = 100,
               level_filter: str = "ALL", search: str = "") -> pd.DataFrame:
    if not os.path.exists(log_path):
        return pd.DataFrame(columns=["timestamp", "level", "message"])
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-max_lines:]
    except Exception:
        return pd.DataFrame(columns=["timestamp", "level", "message"])

    parsed = []
    log_pattern = re.compile(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+)\s+-\s+\[(\w+)\]\s+-\s+(.*)")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = log_pattern.match(line)
        if match:
            ts, level, msg = match.groups()
            if level_filter != "ALL" and level != level_filter:
                continue
            if search and search.lower() not in msg.lower():
                continue
            parsed.append({"timestamp": ts, "level": level, "message": msg})
        else:
            if search and search.lower() not in line.lower():
                continue
            parsed.append({"timestamp": "", "level": "INFO", "message": line})

    return pd.DataFrame(parsed)

def get_level_color(level: str) -> str:
    colors = {"DEBUG": "gray", "INFO": "#58a6ff", "WARNING": "#d29922",
              "ERROR": "#f85149", "CRITICAL": "#da3633"}
    return colors.get(level, "white")

# =============================================================================
# COMPONENTES DE UI
# =============================================================================

def render_agente_avatar(agente_status: Dict[str, Any], image_path: Optional[str]):
    """Renderiza el avatar del agente con el Árbol de la Sabiduría asirio."""
    is_online = agente_status["running"]
    status_color = "#238636" if is_online else "#f85149"
    status_text = "● ONLINE" if is_online else "● OFFLINE"
    status_bg = "rgba(35,134,54,0.15)" if is_online else "rgba(248,81,73,0.15)"

    # Efecto visual: pulso cuando online, sepia cuando offline
    pulse = "animation: pulse 2s infinite" if is_online else ""
    filter_css = "none" if is_online else "sepia(60%) brightness(0.7) contrast(1.2)"
    glow = "0 0 25px rgba(35,134,54,0.5), 0 0 50px rgba(35,134,54,0.2)" if is_online else "none"

    # CSS global - animaciones y estilo profesional
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&display=swap');
        
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(35,134,54,0.4); }
            70% { box-shadow: 0 0 0 15px rgba(35,134,54,0); }
            100% { box-shadow: 0 0 0 0 rgba(35,134,54,0); }
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes glow {
            0%, 100% { box-shadow: 0 0 5px rgba(88,166,255,0.3); }
            50% { box-shadow: 0 0 20px rgba(88,166,255,0.6); }
        }
        
        .avatar-container {
            position: relative;
            display: inline-block;
        }
        
        .avatar-container img {
            transition: all 0.8s ease;
        }
        
        .status-ring {
            position: absolute;
            bottom: 3px;
            right: 3px;
            width: 20px;
            height: 20px;
            background: {status_color};
            border-radius: 50%;
            border: 3px solid #0d1117;
            z-index: 10;
        }
        
        /* Botones profesionales con relieve */
        .stButton > button {
            transition: all 0.3s ease !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
        }
        
        .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 4px 15px rgba(88,166,255,0.4) !important;
        }
        
        .stButton > button:active {
            transform: translateY(0) !important;
            box-shadow: 0 1px 4px rgba(0,0,0,0.3) !important;
        }
        
        /* Tarjetas con efecto relieve */
        [data-testid="stMetric"] {
            transition: all 0.3s ease;
            border-radius: 12px;
        }
        
        [data-testid="stMetric"]:hover {
            transform: scale(1.02);
            box-shadow: 0 4px 20px rgba(88,166,255,0.3);
        }
        
        /* Sidebar profesional */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%) !important;
        }
        
        /* Expander estilizado */
        .streamlit-expanderHeader {
            border-radius: 8px !important;
            background: rgba(88,166,255,0.1) !important;
        }
        
        /* Dataframe profesional */
        .stDataFrame {
            border-radius: 8px !important;
        }
        
        /* Animación de entrada */
        .main-content {
            animation: slideIn 0.5s ease;
        }
        </style>
    """.replace("{status_color}", status_color), unsafe_allow_html=True)

    agente_metrics = ""
    if is_online:
        uptime_str = str(agente_status["uptime"]).split(".")[0] if agente_status["uptime"] else "N/A"
        agente_metrics = f"""
        <div style="margin-top:10px; font-size:0.78rem; color:#8b949e; line-height:1.5; font-family:'JetBrains Mono', monospace;">
            <div style="display:flex; gap:12px; flex-wrap:wrap;">
                <span>🖥️ PID: <b style="color:#58a6ff">{agente_status['pid']}</b></span>
                <span>🧵 Threads: <b style="color:#58a6ff">{agente_status['threads']}</b></span>
            </div>
            <div style="display:flex; gap:12px; flex-wrap:wrap; margin-top:4px;">
                <span>🧠 RAM: <b style="color:#58a6ff">{agente_status['memory_mb']:.1f} MB</b></span>
                <span>⚡ CPU: <b style="color:#58a6ff">{agente_status['cpu']:.1f}%</b></span>
            </div>
            <div style="margin-top:4px;">⏱️ Uptime: <b style="color:#d29922">{uptime_str}</b></div>
        </div>
        """

    if image_path and os.path.exists(image_path):
        import base64
        with open(image_path, "rb") as img_file:
            img_b64 = base64.b64encode(img_file.read()).decode()

        html = f"""
        <div style="display:flex; align-items:center; gap:20px;">
            <div class="avatar-container">
                <img src="data:image/jpeg;base64,{img_b64}" 
                     style="width:100px; height:100px; object-fit:cover; border-radius:50%; 
                            border:3px solid {status_color}; box-shadow:{glow};
                            filter:{filter_css}; {pulse};" />
                <div class="status-ring"></div>
            </div>
            <div>
                <div style="background:{status_bg}; color:{status_color}; padding:5px 14px; 
                            border-radius:20px; font-size:0.8rem; font-weight:700; 
                            display:inline-block; letter-spacing:0.08em;
                            border: 1px solid {status_color};">
                    {status_text}
                </div>
                <div style="margin-top:6px; font-size:0.85rem; color:#8b949e; font-weight:500;">
                    🌳 Árbol de la Sabiduría Asirio
                </div>
                <div style="font-size:0.75rem; color:#6e7681; margin-top:2px;">
                    Asubarnipal V18 Karpathy Wiki
                </div>
                {agente_metrics}
            </div>
        </div>
        """
        st.markdown(html, unsafe_allow_html=True)
    else:
        # Fallback con emoji 🌳
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:12px;">
            <div style="width:60px; height:60px; border-radius:50%; background:{status_color}; 
                        display:flex; align-items:center; justify-content:center; font-size:1.5rem;">
                🌳
            </div>
            <div>
                <div style="color:{status_color}; font-weight:bold;">{status_text}</div>
                <div style="color:#8b949e; font-size:0.8rem;">Árbol de la Sabiduría</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if not image_path:
            st.caption("💡 Coloca 'Arbol de la sabiduria.jpg' en la misma carpeta que este script.")

def render_header(agente_status: Dict[str, Any], image_path: Optional[str]):
    col_t1, col_t2, col_t3 = st.columns([2, 1.2, 1])

    with col_t1:
        st.markdown("""
            <h1 style="margin-bottom:0; color:#58a6ff; font-family:'Segoe UI',sans-serif; font-size:1.8rem;">
                🌳 ASUBARNIPAL
            </h1>
            <p style="margin-top:0; color:#8b949e; font-size:0.85rem;">
                Karpathy Wiki Pattern Command Center
            </p>
        """, unsafe_allow_html=True)

    with col_t2:
        render_agente_avatar(agente_status, image_path)

    with col_t3:
        uptime = datetime.now() - st.session_state.system_boot
        st.metric(
            label="⏱️ UPTIME DASHBOARD",
            value=f"{int(uptime.total_seconds() // 3600)}h {int((uptime.total_seconds() % 3600) // 60)}m",
            delta="Online", delta_color="normal"
        )
        st.metric(
            label="🔄 REFRESH",
            value=f"{st.session_state.config.refresh_interval}s",
            delta="Auto" if not st.session_state.paused else "Paused",
            delta_color="off" if st.session_state.paused else "normal"
        )

def render_kpi_cards(wiki: WikiReader, telemetry: TelemetryEngine):
    stats = wiki.get_stats()
    snap = telemetry.snapshot()

    st.session_state.cpu_history = telemetry.update_history(
        st.session_state.cpu_history, {"value": snap["cpu"], "time": snap["timestamp"]}
    )
    st.session_state.ram_history = telemetry.update_history(
        st.session_state.ram_history, {"value": snap["ram"], "time": snap["timestamp"]}
    )

    cols = st.columns(4)

    with cols[0]:
        delta_notes = stats["total_wiki"] - (st.session_state.notes_history[-1]["value"]
                    if st.session_state.notes_history else 0)
        st.session_state.notes_history = telemetry.update_history(
            st.session_state.notes_history, {"value": stats["total_wiki"], "time": datetime.now()}
        )
        st.metric("📄 WIKI", value=stats["total_wiki"],
                  delta=f"+{delta_notes}" if delta_notes > 0 else f"{delta_notes}",
                  delta_color="normal")

    with cols[1]:
        st.metric("📥 RAW SOURCES", value=stats["total_raw"],
                  delta=f"Entities: {stats['entities']}", delta_color="normal")

    with cols[2]:
        st.metric("⚡ CPU", value=f"{snap['cpu']:.1f}%",
                  delta=f"RAM: {snap['ram']:.1f}%",
                  delta_color="inverse" if snap["cpu"] > 80 else "normal")

    with cols[3]:
        orphan_pct = (stats["orphans"] / stats["total_wiki"] * 100) if stats["total_wiki"] > 0 else 0
        st.metric("🏝️ HUÉRFANAS", value=stats["orphans"],
                  delta=f"{orphan_pct:.1f}% del wiki",
                  delta_color="inverse" if orphan_pct > 20 else "normal")

def render_system_charts():
    if not st.session_state.cpu_history:
        st.info("📊 Recolectando datos de telemetría...")
        return

    fig = make_subplots(rows=1, cols=2, subplot_titles=("CPU Usage %", "RAM Usage %"))

    cpu_df = pd.DataFrame(st.session_state.cpu_history)
    ram_df = pd.DataFrame(st.session_state.ram_history)

    fig.add_trace(go.Scatter(x=cpu_df["time"], y=cpu_df["value"],
                             mode="lines+markers", name="CPU",
                             line=dict(color="#58a6ff", width=2),
                             fill="tozeroy", fillcolor="rgba(88,166,255,0.1)"), row=1, col=1)
    fig.add_trace(go.Scatter(x=ram_df["time"], y=ram_df["value"],
                             mode="lines+markers", name="RAM",
                             line=dict(color="#238636", width=2),
                             fill="tozeroy", fillcolor="rgba(35,134,54,0.1)"), row=1, col=2)

    fig.update_layout(
        height=250, margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#c9d1d9"), showlegend=False,
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", range=[0, 100]),
        xaxis2=dict(showgrid=False, zeroline=False),
        yaxis2=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", range=[0, 100]),
    )
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

def render_wiki_composition(wiki: WikiReader):
    """Gráfico de composición del wiki por tipo."""
    df = wiki.get_tipo_distribution()
    if df.empty:
        st.info("No hay notas en el wiki.")
        return

    colors_map = {"📄 Fuentes": "#58a6ff", "🏛️ Entidades": "#f0883e",
                  "💡 Conceptos": "#238636", "🔗 Síntesis": "#a371f7",
                  "🗺️ MOCs": "#d29922", "❓ Desconocido": "#8b949e"}

    df["color"] = df["label"].map(colors_map).fillna("#8b949e")

    fig = go.Figure(data=[go.Pie(
        labels=df["label"], values=df["count"],
        hole=0.5, marker_colors=df["color"],
        textinfo="label+percent", textfont_size=12,
        hovertemplate="%{label}<br>Notas: %{value}<br>Porcentaje: %{percent}<extra></extra>"
    )])

    fig.update_layout(
        height=350, paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#c9d1d9"), margin=dict(l=20, r=20, t=30, b=20),
        showlegend=False,
        annotations=[dict(text=f"{df['count'].sum()}<br>notas", x=0.5, y=0.5,
                         font_size=20, showarrow=False, font_color="#c9d1d9")]
    )
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

def render_wiki_timeline(wiki: WikiReader):
    """Timeline de ingesta del wiki."""
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📈 Wiki Timeline")
        timeline = wiki.get_timeline_data()
        if not timeline.empty:
            fig = px.bar(timeline, x="date", y="count", color="count",
                        color_continuous_scale="blues",
                        labels={"date": "Fecha", "count": "Notas creadas"})
            fig.update_layout(
                height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#c9d1d9"), margin=dict(l=20, r=20, t=30, b=20),
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
            )
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        else:
            st.info("Sin datos de timeline.")

    with col2:
        st.subheader("📥 Raw Sources Timeline")
        raw_timeline = wiki.get_raw_timeline()
        if not raw_timeline.empty:
            fig = px.bar(raw_timeline, x="date", y="count", color="count",
                        color_continuous_scale="Greens",
                        labels={"date": "Fecha", "count": "Fuentes ingresadas"})
            fig.update_layout(
                height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#c9d1d9"), margin=dict(l=20, r=20, t=30, b=20),
                xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
            )
            st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})
        else:
            st.info("Sin fuentes crudas.")

def render_activity_heatmap(wiki: WikiReader):
    """Heatmap de actividad del agente (ingests/queries/lints)."""
    activity = wiki.get_log_activity()
    if activity.empty:
        st.info("Sin datos de actividad.")
        return

    fig = go.Figure()
    fig.add_trace(go.Bar(x=activity["date"], y=activity["ingests"],
                         name="Ingests", marker_color="#58a6ff"))
    fig.add_trace(go.Bar(x=activity["date"], y=activity["queries"],
                         name="Queries", marker_color="#a371f7"))
    fig.add_trace(go.Bar(x=activity["date"], y=activity["lints"],
                         name="Lints", marker_color="#d29922"))

    fig.update_layout(
        barmode="stack", height=280,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#c9d1d9"), margin=dict(l=20, r=20, t=30, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
    )
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

def render_wiki_table(wiki: WikiReader):
    """Tabla interactiva del wiki."""
    if not wiki.notes:
        st.info("No hay notas en el wiki.")
        return

    df = pd.DataFrame(wiki.notes)
    df = df[["titulo", "tipo", "estado", "word_count", "fecha_ingesta", "fecha_actualizacion", "tags", "relacionados"]]
    df["tags"] = df["tags"].apply(lambda x: ", ".join(x[:3]) + "..." if len(x) > 3 else ", ".join(x))
    df["relacionados"] = df["relacionados"].apply(lambda x: len(x))
    df = df.rename(columns={
        "titulo": "Título", "tipo": "Tipo", "estado": "Estado",
        "word_count": "Palabras", "fecha_ingesta": "Ingesta",
        "fecha_actualizacion": "Actualización", "tags": "Tags", "relacionados": "Links"
    })

    st.dataframe(df, width='stretch', hide_index=True,
                 column_config={
                     "Título": st.column_config.TextColumn(width="medium"),
                     "Tipo": st.column_config.TextColumn(width="small"),
                     "Estado": st.column_config.TextColumn(width="small"),
                     "Palabras": st.column_config.NumberColumn(width="small"),
                 })

def render_raw_table(wiki: WikiReader):
    """Tabla de fuentes crudas."""
    if not wiki.raw_sources:
        st.info("No hay fuentes crudas.")
        return

    df = pd.DataFrame(wiki.raw_sources)
    df["modified"] = pd.to_datetime(df["modified"]).dt.strftime("%Y-%m-%d %H:%M")
    df = df.rename(columns={
        "filename": "Archivo", "size_kb": "Tamaño (KB)",
        "modified": "Modificado", "tipo": "Tipo"
    })
    st.dataframe(df, width='stretch', hide_index=True)

def render_schema_viewer(wiki: WikiReader):
    """Muestra el schema CLAUDE.md."""
    if wiki.schema_content:
        st.markdown("""
        <style>
        .schema-box {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            line-height: 1.5;
            color: #c9d1d9;
            max-height: 500px;
            overflow-y: auto;
        }
        .schema-box h1 { color: #58a6ff; font-size: 1.2rem; }
        .schema-box h2 { color: #f0883e; font-size: 1rem; }
        .schema-box h3 { color: #a371f7; font-size: 0.9rem; }
        .schema-box code { background: #21262d; padding: 2px 6px; border-radius: 4px; }
        </style>
        """, unsafe_allow_html=True)
        st.markdown(f'<div class="schema-box">{wiki.schema_content.replace(chr(10), "<br>")}</div>',
                     unsafe_allow_html=True)
    else:
        st.warning("No se encontró CLAUDE.md en el vault.")

# =============================================================================
# VISUALIZACIÓN DEL GRAFO VECTORIAL
# =============================================================================

def render_graph_store_status(config: AppConfig):
    """Muestra el estado del grafo vectorial generado por /indexar_wiki."""
    graph_store = Path(config.obsidian_path) / "graph_store"

    if not graph_store.exists():
        st.warning("🕸️ Grafo vectorial no encontrado. Ejecuta `/indexar_wiki` en el bot.")
        return

    files = {
        "Grafo": graph_store / "wiki_graph.pkl",
        "Embeddings": graph_store / "embeddings.pkl",
        "Metadatos": graph_store / "metadata.json",
        "Reporte": graph_store / "graph_report.md",
    }

    cols = st.columns(4)
    for i, (label, path) in enumerate(files.items()):
        exists = path.exists()
        with cols[i]:
            st.metric(
                label=label,
                value="✅" if exists else "❌",
                delta=f"{path.stat().st_size / 1024:.1f} KB" if exists else "No existe",
                delta_color="normal" if exists else "inverse"
            )

def render_graph_report(config: AppConfig):
    """Lee y muestra el reporte del grafo."""
    report_path = Path(config.obsidian_path) / "graph_store" / "graph_report.md"
    if not report_path.exists():
        st.info("No hay reporte de grafo disponible.")
        return

    try:
        content = report_path.read_text(encoding="utf-8", errors="ignore")
        st.markdown("""
        <style>
        .graph-report {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 16px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            line-height: 1.5;
            color: #c9d1d9;
            max-height: 600px;
            overflow-y: auto;
        }
        .graph-report h1 { color: #58a6ff; font-size: 1.2rem; }
        .graph-report h2 { color: #f0883e; font-size: 1rem; }
        .graph-report h3 { color: #a371f7; font-size: 0.9rem; }
        .graph-report strong { color: #58a6ff; }
        </style>
        """, unsafe_allow_html=True)
        st.markdown(f'<div class="graph-report">{content.replace(chr(10), "<br>")}</div>', 
                    unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error leyendo reporte: {e}")

def render_communities_and_hubs(config: AppConfig):
    """Visualiza comunidades y hubs desde metadata.json."""
    meta_path = Path(config.obsidian_path) / "graph_store" / "metadata.json"
    if not meta_path.exists():
        st.info("No hay metadatos del grafo. Ejecuta `/indexar_wiki`.")
        return

    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        # Estadísticas del grafo
        cols = st.columns(4)
        with cols[0]:
            st.metric("🕸️ Nodos", meta.get("total_nodos", 0))
        with cols[1]:
            st.metric("🔗 Aristas", meta.get("total_aristas", 0))
        with cols[2]:
            st.metric("📊 Comunidades", len(set(meta.get("comunidades", {}).values())))
        with cols[3]:
            st.metric("🏛️ Hubs", len(meta.get("hubs", [])))

        st.divider()

        # Hubs
        hubs = meta.get("hubs", [])
        if hubs:
            st.subheader("🏛️ Hubs Centrales (Top 10)")
            hub_data = []
            for i, (node, score) in enumerate(hubs, 1):
                hub_data.append({
                    "Rank": i,
                    "Nodo": node,
                    "Score": f"{score:.4f}",
                    "Visual": "█" * int(score * 50)
                })
            st.dataframe(pd.DataFrame(hub_data), hide_index=True, width='stretch')

        # Comunidades
        comunidades = meta.get("comunidades", {})
        if comunidades:
            st.subheader("📊 Comunidades Temáticas")
            comm_groups = defaultdict(list)
            for node, comm_id in comunidades.items():
                comm_groups[comm_id].append(node)

            comm_data = []
            for comm_id, nodes in sorted(comm_groups.items()):
                comm_data.append({
                    "Comunidad": f"Comunidad {comm_id}",
                    "Nodos": len(nodes),
                    "Miembros (top 5)": ", ".join(nodes[:5]) + ("..." if len(nodes) > 5 else "")
                })
            st.dataframe(pd.DataFrame(comm_data), hide_index=True, width='stretch')

    except Exception as e:
        st.error(f"Error cargando metadatos: {e}")

def render_command_stats(wiki: WikiReader):
    """Muestra estadísticas de uso de comandos desde log.md."""
    if not wiki.log_entries:
        st.info("No hay entradas de log para analizar.")
        return

    # Contar tipos de comandos
    cmd_counts = Counter()
    for entry in wiki.log_entries:
        tipo = entry.get("tipo", "").lower()
        if "ingest" in tipo or "investigar" in tipo:
            cmd_counts["/investigar"] += 1
        elif "query" in tipo and "vectorial" not in tipo:
            cmd_counts["/query"] += 1
        elif "lint" in tipo:
            cmd_counts["/lint"] += 1
        elif "charlar" in tipo or "brainstorm" in tipo:
            cmd_counts["/charlar"] += 1
        elif "indexar" in tipo or "index" in tipo:
            cmd_counts["/indexar_wiki"] += 1
        elif "vectorial" in tipo:
            cmd_counts["/query_vectorial"] += 1

    if not cmd_counts:
        st.info("No se detectaron comandos en los logs.")
        return

    st.subheader("📊 Uso de Comandos")

    # Gráfico de barras
    df_cmds = pd.DataFrame(cmd_counts.most_common(), columns=["Comando", "Usos"])
    fig = px.bar(df_cmds, x="Comando", y="Usos", color="Usos",
                 color_continuous_scale="blues",
                 labels={"Comando": "", "Usos": "Veces usado"})
    fig.update_layout(
        height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#c9d1d9"), margin=dict(l=20, r=20, t=30, b=20),
        xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
    )
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})

    # Tabla detallada
    cols = st.columns(len(cmd_counts))
    for i, (cmd, count) in enumerate(cmd_counts.most_common()):
        with cols[i]:
            st.metric(label=cmd, value=count)

def render_embeddings_status(config: AppConfig):
    """Muestra el estado del modelo de embeddings."""
    try:
        emb_path = Path(config.obsidian_path) / "graph_store" / "embeddings.pkl"
        if emb_path.exists():
            size_mb = emb_path.stat().st_size / 1024 / 1024
            st.metric("🧠 Embeddings", f"{size_mb:.1f} MB", delta="Persistidos", delta_color="normal")
        else:
            st.metric("🧠 Embeddings", "No generados", delta="Ejecuta /indexar_wiki", delta_color="off")
    except Exception:
        pass

def render_health_dashboard(wiki: WikiReader):
    """Panel de salud del wiki Karpathy."""
    stats = wiki.get_stats()

    cols = st.columns(4)
    with cols[0]:
        st.metric("🏝️ Huérfanas", stats["orphans"])
    with cols[1]:
        st.metric("📝 Drafts", stats["draft"])
    with cols[2]:
        st.metric("✅ Finales", stats["final"])
    with cols[3]:
        st.metric("🔗 Total Links", stats["total_links"])

    st.divider()

    cols2 = st.columns(3)

    with cols2[0]:
        st.subheader("🔗 Hubs (más conectados)")
        link_counts = Counter()
        for note in wiki.notes:
            for rel in note.get("relacionados", []):
                link_counts[rel] += 1
        for note_id, count in link_counts.most_common(5):
            clean_id = note_id.replace("[[", "").replace("]]", "")
            st.progress(min(count / 10, 1.0), text=f"{clean_id} ({count} refs)")

    with cols2[1]:
        st.subheader("⚠️ Notas sin tags")
        sin_tags = [n for n in wiki.notes if not n.get("tags")]
        if sin_tags:
            for note in sin_tags[:5]:
                st.warning(f"🏷️ [[{note['id']}]]", icon="🏷️")
        else:
            st.success("Todas las notas tienen tags.")

    with cols2[2]:
        st.subheader("⏰ Stale (>30 días)")
        hoy = datetime.now()
        stale = []
        for note in wiki.notes:
            try:
                fecha = datetime.strptime(note.get("fecha_actualizacion", "2020-01-01"), "%Y-%m-%d")
                if (hoy - fecha).days > 30 and note["tipo"] in ["entity", "concept"]:
                    stale.append(note)
            except Exception:
                pass
        if stale:
            for note in stale[:5]:
                st.info(f"⏰ [[{note['id']}]]", icon="⏰")
        else:
            st.success("Todo actualizado.")


def render_heartbeat_section():
    """Render heartbeat and cron jobs section."""
    import json
    from pathlib import Path

    st.subheader("💓 Latido del Agente")
    st.caption("Configuración de trabajos en segundo plano (cron jobs)")

    heartbeat_file = Path(config.DATA_DIR) / "heartbeat.json"
    state_file = Path(config.DATA_DIR) / "agent_state.json"

    col_h1, col_h2, col_h3 = st.columns(3)

    with col_h1:
        st.metric("💓 Heartbeat", "Activo" if config.ENABLE_HEARTBEAT else "Inactivo",
                delta=f"Intervalo: {config.HEARTBEAT_INTERVAL}s", delta_color="normal" if config.ENABLE_HEARTBEAT else "off")
    with col_h2:
        st.metric("💉 Suture", f"{config.SUTURE_INTERVAL}s", delta="Cada 10 min", delta_color="normal")
    with col_h3:
        st.metric("🕸️ Graph", f"{config.GRAPH_INTERVAL}s", delta="Cada 30 min", delta_color="normal")

    st.divider()

    st.subheader("⚙️ Editar Intervalos")

    with st.expander("✏️ Editar Cron Jobs"):
        new_heartbeat = st.number_input("Heartbeat (segundos)", min_value=10, max_value=3600,
                            value=config.HEARTBEAT_INTERVAL, key="edit_heartbeat")
        new_suture = st.number_input("Suture (segundos)", min_value=60, max_value=7200,
                              value=config.SUTURE_INTERVAL, key="edit_suture")
        new_graph = st.number_input("Graph (segundos)", min_value=60, max_value=14400,
                          value=config.GRAPH_INTERVAL, key="edit_graph")
        enable_heartbeat = st.toggle("Habilitar Heartbeat", value=config.ENABLE_HEARTBEAT, key="edit_enable_hb")

        col_btns1, col_btns2 = st.columns(2)
        with col_btns1:
            if st.button("💾 Guardar Cambios"):
                import os
                os.environ["HEARTBEAT_INTERVAL"] = str(new_heartbeat)
                os.environ["SUTURE_INTERVAL"] = str(new_suture)
                os.environ["GRAPH_INTERVAL"] = str(new_graph)
                os.environ["ENABLE_HEARTBEAT"] = str(enable_heartbeat).lower()
                st.success("✅ Configuración guardada")
                st.rerun()
        with col_btns2:
            if st.button("🔄 Recargar"):
                st.rerun()

    st.divider()

    st.subheader("📊 Estado Actual")

    if heartbeat_file.exists():
        try:
            hb = json.loads(heartbeat_file.read_text())
            cols_hb = st.columns(4)
            with cols_hb[0]:
                st.metric("Último Heartbeat", hb.get("timestamp", "N/A")[:19] if hb.get("timestamp") else "N/A")
            with cols_hb[1]:
                st.metric("CPU", f"{hb.get('cpu_percent', 0):.1f}%")
            with cols_hb[2]:
                st.metric("RAM", f"{hb.get('memory_percent', 0):.1f}%")
            with cols_hb[3]:
                st.metric("Disk", f"{hb.get('disk_percent', 0):.1f}%")
        except Exception as e:
            st.warning(f"No se pudo leer heartbeat: {e}")
    else:
        st.info(" heartbeat.json no encontrado. El agente debe estar ejecutándose.")

    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
            st.caption(f"**Último alive:** {state.get('last_alive', 'N/A')[:19] if state.get('last_alive') else 'N/A'}")
            st.caption(f"**Fallos:** {state.get('failure_count', 0)} | **Éxitos:** {state.get('success_count', 0)}")
        except Exception:
            pass

    st.divider()

    st.subheader("🕐 Próximas Ejecuciones")

    cols_next = st.columns(3)
    with cols_next[0]:
        st.info(f"💓 Heartbeat: cada {config.HEARTBEAT_INTERVAL}s")
    with cols_next[1]:
        st.info(f"💉 Suture: cada {config.SUTURE_INTERVAL // 60} min")
    with cols_next[2]:
        st.info(f"🕸️ Graph: cada {config.GRAPH_INTERVAL // 60} min")

    st.divider()
    st.caption("💡 Los cambios en los intervalos se guardan en memoria. Para persistir, exporta las variables al .env")


def render_feeds_section():
    """Render feed subscriptions and alerts."""
    from core.feed_tracker import FeedTracker
    
    tracker = FeedTracker()
    subscriptions = tracker.get_subscriptions()
    alerts = tracker.get_alerts(unread_only=True)
    
    st.subheader("📡 Suscripciones RSS")
    st.caption("Feeds seguidos para alertas de actualización")
    
    cols_f1, cols_f2 = st.columns(2)
    
    with cols_f1:
        with st.expander("➕ Añadir Feed"):
            feed_url = st.text_input("URL del Feed", key="new_feed_url")
            feed_name = st.text_input("Nombre (opcional)", key="new_feed_name")
            if st.button("📥 Suscribirse"):
                if feed_url:
                    result = tracker.subscribe(feed_url, feed_name)
                    if result:
                        st.success(f"✅ Suscrito a {feed_name or feed_url}")
                        st.rerun()
                    else:
                        st.warning("Ya estás suscrito o feed inválido")
    
    with cols_f2:
        if subscriptions:
            st.metric("📡 Feeds", len(subscriptions))
        else:
            st.metric("📡 Feeds", 0)
        st.metric("🔔 Alertas", len(alerts), delta="sin leer", delta_color="inverse" if len(alerts) > 0 else "normal")
    
    if subscriptions:
        st.divider()
        st.subheader("📋 Lista de Feeds")
        feed_list = []
        for sub in subscriptions:
            feed_list.append({
                "Nombre": sub.get("name", "Sin nombre"),
                "URL": sub.get("url", ""),
                "Agregado": sub.get("added", "")[:10],
            })
        st.dataframe(pd.DataFrame(feed_list), hide_index=True, width='stretch')
    
    st.divider()
    st.subheader("🔔 Últimas Alertas")
    
    all_alerts = tracker.get_alerts()
    if all_alerts:
        for i, alert in enumerate(all_alerts[-10:]):
            read_status = "" if alert.get("read") else "🔴"
            st.markdown(f"**{read_status} {alert.get('title', 'Sin título')[:60]}**")
            st.caption(f"📡 {alert.get('feed', '')} | {alert.get('published', '')[:19]}")
            if alert.get("link"):
                st.caption(f"[Leer más]({alert.get('link')})")
    else:
        st.info("No hay alertas.")
    
    st.divider()
    
    if st.button("🔄 Verificar Feeds"):
        with st.spinner("Verificando..."):
            updates = tracker.check_updates()
            if updates:
                st.success(f"🔔 {len(updates)} actualizaciones!")
            else:
                st.info("Sin actualizaciones")
            st.rerun()


def render_analytics_section():
    """Render command history and analytics."""
    from core.command_history import CommandHistory, get_command_analytics
    
    history = CommandHistory()
    stats = history.get_stats()
    
    st.subheader("📊 Historial de Comandos")
    st.caption("Analytics del uso del agente")
    
    cols_a1, cols_a2, cols_a3, cols_a4 = st.columns(4)
    
    with cols_a1:
        st.metric("📝 Total", stats.get("total", 0))
    with cols_a2:
        st.metric("🔄 Únicos", stats.get("unique_commands", 0))
    with cols_a3:
        first = stats.get("first_command", "")[:10] if stats.get("first_command") else "N/A"
        st.metric("📅 Primero", first)
    with cols_a4:
        last = stats.get("last_command", "")[:10] if stats.get("last_command") else "N/A"
        st.metric("⏱️ Último", last)
    
    if stats.get("top_commands"):
        st.divider()
        st.subheader("🔝 Top Comandos")
        top_data = []
        for cmd in stats["top_commands"][:10]:
            top_data.append({
                "Comando": cmd["cmd"][:50],
                "Usos": cmd["count"],
            })
        st.dataframe(pd.DataFrame(top_data), hide_index=True, width='stretch')
    
    st.divider()
    st.subheader("📜 Últimos Comandos")
    
    recent = history.get(20)
    if recent:
        for cmd in reversed(recent):
            ts = cmd.get("timestamp", "")[:19]
            cmd_text = cmd.get("command", "")[:60]
            st.code(f"[{ts}] {cmd_text}")
    else:
        st.info("Sin comandos ejecutados")
    
    st.divider()
    
    if st.button("🗑️ Limpiar Historial"):
        history.clear()
        st.success("Historial limpiado")
        st.rerun()
    
    st.divider()
    st.subheader("💾 Memoria Persistente")
    st.caption("Sistema de memoria con categorías y prioridad")
    
    try:
        from core.memory import EnhancedMemory
        memory = EnhancedMemory()
        mem_stats = memory.get_stats()
        
        cols_m1, cols_m2, cols_m3 = st.columns(3)
        
        with cols_m1:
            st.metric("💾 Total", mem_stats.get("total", 0))
        with cols_m2:
            by_cat = mem_stats.get("by_category", {})
            st.metric("📁 Categorías", len(by_cat))
        with cols_m3:
            last_mem = mem_stats.get("last_memory", "N/A")[:10] if mem_stats.get("last_memory") else "N/A"
            st.metric("⏱️ Última", last_mem)
        
        st.divider()
        
        with st.expander("➕ Añadir Memoria"):
            mem_content = st.text_area("Contenido", key="new_memory_content")
            mem_category = st.selectbox("Categoría", 
                ["fact", "idea", "task", "preference", "learning", "error", "plan", "conversation"],
                key="new_memory_category"
            )
            mem_priority = st.slider("Prioridad", 1, 10, 5, key="new_memory_priority")
            mem_importance = st.selectbox("Importancia", ["low", "normal", "high", "critical"], key="new_memory_importance")
            
            if st.button("💾 Guardar Memoria"):
                if mem_content:
                    memory.add(mem_content, mem_category, mem_priority, importance=mem_importance)
                    st.success("�� Memoria guardada")
                    st.rerun()
        
        st.divider()
        
        st.subheader("🔍 Buscar Memorias")
        
        mem_search = st.text_input("Buscar en memorias", key="mem_search")
        if mem_search:
            results = memory.search(mem_search, limit=10)
            st.write(f"**{len(results)} resultados:**")
            for r in results:
                st.markdown(f"**[{r.get('category')}]** {r.get('content', '')[:80]}")
        
        st.divider()
        
        st.subheader("📋 Memorias Recientes")
        
        recent_mem = memory.get_recent(10)
        if recent_mem:
            for m in recent_mem:
                importance_emoji = {"critical": "🔴", "high": "🟠", "normal": "🟢", "low": "⚪"}.get(m.get("importance"), "🟢")
                st.markdown(f"{importance_emoji} **[{m.get('category')}]** {m.get('content', '')[:60]}...")
                st.caption(f"⏱️ {m.get('timestamp', '')[:19]} | Accesos: {m.get('access_count', 0)}")
        else:
            st.info("Sin memorias guardadas")
        
        st.divider()
        
        col_mb1, col_mb2 = st.columns(2)
        
        with col_mb1:
            if st.button("🗑️ Limpiar Memorias"):
                count = memory.clear()
                st.success(f"Eliminadas {count} memorias")
                st.rerun()
        
        with col_mb2:
            if st.button("🔄 Consolidar"):
                result = memory.consolidate()
                st.success(f"Duplicados eliminados: {result.get('removed_duplicates', 0)}")
                st.rerun()
                
    except Exception as e:
        st.error(f"Error con memoria: {e}")


def render_skills_section():
    """Render skills and tools available in the agent."""
    try:
        from core.skill_registry import SkillRegistry
        registry = SkillRegistry()
        skills = registry.list_skills()
        tools = registry.get_tools()
    except Exception as e:
        st.error(f"Error loading skills: {e}")
        return

    st.subheader("🛠️ Skills Disponibles")
    st.caption(f"El agente tiene acceso a {len(skills)} funciones ejecutables.")

    if not skills:
        st.info("No hay skills cargados.")
        return

    cols = st.columns(4)
    for i, skill in enumerate(skills):
        with cols[i % 4]:
            st.success(f"🔧 {skill}")

    st.divider()
    st.subheader("📋 Definiciones de Herramientas (Tool Definitions)")

    tool_data = []
    for tool in tools:
        func = tool.get("function", {})
        params = func.get("parameters", {})
        required = params.get("required", [])
        tool_data.append({
            "Nombre": func.get("name", "unknown"),
            "Descripción": func.get("description", "N/A"),
            "Parámetros": ", ".join(params.get("properties", {}).keys()) if params.get("properties") else "-",
            "Requeridos": ", ".join(required) if required else "-",
        })

    if tool_data:
        df_tools = pd.DataFrame(tool_data)
        st.dataframe(df_tools, width='stretch', hide_index=True,
                   column_config={
                       "Nombre": st.column_config.TextColumn(width="medium"),
                       "Descripción": st.column_config.TextColumn(width="large"),
                       "Parámetros": st.column_config.TextColumn(width="medium"),
                       "Requeridos": st.column_config.TextColumn(width="small"),
                   })

    st.divider()
    st.subheader("🧩 Categorías de Skills")

    categories = {
        "Archivo": ["run_command", "read_file", "write_file", "list_files", "search_in_files"],
        "Wiki": ["generate_project_knowledge_graph", "heal_orphans"],
        "RSS/Podcasts": ["subscribe_podcast", "subscribe_rss", "fetch_new_articles", "list_subscribed_podcasts"],
        "LLM/Ollama": ["list_ollama_models", "quantize_ollama_model", "get_quantization_info"],
        "Quant": ["run_polar_quant_demo", "get_turboquant_capabilities", "suggest_quantization_strategy"],
        "Recordatorio": ["add_reminder", "list_reminders", "delete_reminder", "check_due_reminders", "snooze_reminder"],
        "Webhooks": ["register_webhook", "unregister_webhook", "list_webhooks", "trigger_webhook"],
        "Varios": ["clone_repo", "translate", "detect_language", "search_arxiv", "get_audio_summary"],
    }

    for category, funcs in categories.items():
        present = [f for f in funcs if f in skills]
        if present:
            with st.expander(f"📁 {category} ({len(present)})"):
                for f in present:
                    st.code(f, language="python")

    st.divider()
    st.caption("💡 Los skills se cargan desde skills/default_skills.py y se registran en SkillRegistry.")


def render_logs_section(config: AppConfig):
    # Also print to terminal (CMD)
    try:
        with open(config.log_file, "r", encoding="utf-8", errors="ignore") as f:
            recent_logs = f.readlines()[-10:]
        print("\n" + "="*50)
        print("📜 RECENT LOGS:")
        print("="*50)
        for line in recent_logs:
            print(line.strip())
        print("="*50 + "\n")
    except Exception as e:
        pass
    
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        search = st.text_input("🔍 Buscar en logs",
                              value=st.session_state.search_query, key="log_search")
        st.session_state.search_query = search
    with col2:
        level = st.selectbox("Nivel", ["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                            index=0, key="log_level")
        st.session_state.log_filter = level
    with col3:
        lines = st.number_input("Líneas", min_value=10, max_value=500,
                               value=config.max_log_lines, key="log_lines")

    logs_df = parse_logs(config.log_file, lines, level, search)
    if logs_df.empty:
        st.info("No se encontraron logs.")
        return

    for _, row in logs_df.tail(50).iterrows():
        color = get_level_color(row["level"])
        ts = f"<span style='color:#8b949e;font-size:0.8em'>[{row['timestamp']}]</span>" if row["timestamp"] else ""
        st.markdown(
            f"{ts} <span style='color:{color};font-weight:bold'>[{row['level']}]</span> "
            f"<span style='color:#c9d1d9'>{row['message']}</span>",
            unsafe_allow_html=True
        )

# =============================================================================
# LAYOUT PRINCIPAL
# =============================================================================

def main():
    st.set_page_config(
        page_title="ASUBARNIPAL COMMAND CENTER",
        page_icon="🛰️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # No banner - only shows in agent
    
    init_session_state()
    config = st.session_state.config

    agente_status = get_agente_status(config)
    st.session_state.agente_status = agente_status["running"]
    st.session_state.agente_pid = agente_status["pid"]

    image_path = find_avatar_image()

    # CSS Global
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --border-color: #30363d;
            --text-primary: #c9d1d9;
            --text-secondary: #8b949e;
            --accent: #58a6ff;
            --success: #238636;
            --warning: #d29922;
            --danger: #f85149;
        }

        .stApp {
            background-color: var(--bg-primary);
            font-family: 'Inter', sans-serif;
        }

        [data-testid="stSidebar"] {
            background-color: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
        }

        [data-testid="stMetric"] {
            background-color: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }
        [data-testid="stMetricLabel"] {
            color: var(--text-secondary) !important;
            font-size: 0.75rem !important;
            font-weight: 600 !important;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }
        [data-testid="stMetricValue"] {
            color: var(--text-primary) !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-size: 1.5rem !important;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: transparent;
        }
        .stTabs [data-baseweb="tab"] {
            background-color: var(--bg-secondary);
            border-radius: 8px 8px 0 0;
            border: 1px solid var(--border-color);
            border-bottom: none;
            color: var(--text-secondary);
            padding: 10px 20px;
            font-weight: 500;
        }
        .stTabs [aria-selected="true"] {
            background-color: var(--bg-tertiary) !important;
            color: var(--accent) !important;
            border-top: 2px solid var(--accent);
        }

        .stDataFrame {
            border: 1px solid var(--border-color);
            border-radius: 8px;
        }

        .stTextInput input, .stSelectbox div[data-baseweb="select"],
        .stNumberInput input {
            background-color: var(--bg-secondary) !important;
            border-color: var(--border-color) !important;
            color: var(--text-primary) !important;
            border-radius: 8px !important;
        }

        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }
        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 4px;
        }

        .stProgress > div > div {
            background-color: var(--accent);
        }
        </style>
    """, unsafe_allow_html=True)

    # =============================================================================
    # SIDEBAR
    # =============================================================================
    wiki = WikiReader(config)
    stats = wiki.get_stats()
    telemetry = TelemetryEngine()
    
    with st.sidebar:
        # Theme toggle
        if "dark_mode" not in st.session_state:
            st.session_state.dark_mode = True
        
        col_theme, _ = st.columns([1, 1])
        with col_theme:
            dark_mode = st.toggle("🌙 Modo Oscuro", value=st.session_state.dark_mode, key="theme_toggle")
            if dark_mode != st.session_state.dark_mode:
                st.session_state.dark_mode = dark_mode
                st.rerun()

        st.markdown("""
        <div style="text-align:center; margin-bottom:24px; padding:20px; 
            background:linear-gradient(135deg,#1a1a2e,#16213e); 
            border-radius:16px; box-shadow:0 8px 32px rgba(0,0,0,0.3);">
            <div style="font-size:3.5rem; margin-bottom:8px; animation:glow 2s infinite;">🌳</div>
            <div style="font-weight:700; color:#58a6ff; font-size:1.5rem; 
                text-shadow:0 0 10px rgba(88,166,255,0.5);">ASUBARNIPAL</div>
            <div style="color:#8b949e; font-size:0.85rem; letter-spacing:0.1em;">KARPATHY WIKI</div>
            <div style="margin-top:12px; padding:6px 16px; background:rgba(35,134,54,0.2); 
                border-radius:20px; display:inline-block; color:#238636; font-weight:600;">
                ● EN LÍNEA
            </div>
        </div>
        """, unsafe_allow_html=True)

        if "selected_view" not in st.session_state:
            st.session_state.selected_view = 0

        # Navigation con iconos grandes
        nav_options = [
            ("📊", "Dashboard", "Panel de control"),
            ("🛠️", "Skills", "Herramientas"),
            ("🕸️", "Wiki", f"{stats['total_wiki']} notas"),
            ("📥", "Raw", f"{stats['total_raw']} fuentes"),
            ("🧠", "Grafo", "Grafo vectorial"),
            ("📜", "Logs", "Registro de actividad"),
            ("🏥", "Salud", "Diagnóstico"),
            ("📋", "Schema", "Configuración"),
            ("💓", "Latido", "Tareas programadas"),
            ("📡", "Feeds", "Suscripciones RSS"),
            ("📈", "Analytics", "Estadísticas"),
        ]
        
        st.markdown("### ⌨️ NAVEGACIÓN")
        
        for i, (emoji, title, desc) in nav_options:
            btn_key = f"nav_btn_{i}"
            label = f"{emoji} {title}"
            if st.button(label, key=btn_key, use_container_width=True):
                st.session_state.selected_view = i
                st.rerun()
        
        # Resaltar selección actual
        current = st.session_state.selected_view
        st.caption(f"Vista actual: {nav_options[current][1]} {nav_options[current][2]}")

        st.divider()

        with st.expander("🛠️ 🔧 Skills Activas", expanded=True):
            from core.skill_registry import SkillRegistry
            registry = SkillRegistry()
            skills = registry.list_skills()
            st.metric("Total", len(skills))
            for skill in skills[:8]:
                st.code(skill, language="python")
            if len(skills) > 8:
                st.caption(f"+ {len(skills)-8} funciones...")

        with st.expander("📡 ⚡ Feeds Activos"):
            from core.feed_tracker import FeedTracker
            tracker = FeedTracker()
            feeds = tracker.get_subscriptions()
            st.metric("Suscritos", len(feeds))
            alerts = tracker.get_alerts(unread_only=True)
            st.metric("🔔 Nuevas", len(alerts), delta_color="inverse" if alerts else "normal")

        with st.expander("💓 ⏰ Cron Jobs"):
            st.markdown("""
            | Ritual | ⏱️ Intervalo | Estado |
            |--------|----------|--------|
            | 💓 Heartbeat | 60s | ✅ Activo |
            | 💉 Suture | 600s | ✅ Activo |
            | 🕸️ Graph | 1800s | ✅ Activo |
            """)

        with st.expander("💾 🧠 Memoria"):
            from core.memory import EnhancedMemory
            memory = EnhancedMemory()
            mem_stats = memory.get_stats()
            st.metric("Memorias", mem_stats.get("total", 0))
            by_cat = mem_stats.get("by_category", {})
            if by_cat:
                st.caption(f"Categorías: {', '.join(by_cat.keys())}")

        st.divider()

        st.markdown("### 🤖 🤖 ESTADO DEL AGENTE")
        
        if agente_status["running"]:
            st.success(f"✅ Activo (PID {agente_status['pid']})")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("💾 RAM", f"{agente_status['memory_mb']:.0f} MB")
            with col2:
                st.metric("⚡ CPU", f"{agente_status['cpu']:.0f}%")
            
            # Token counter simulado (en producción vendría del LLM)
            col_t1, col_t2, col_t3 = st.columns(3)
            with col_t1:
                st.metric("🔢 Tokens", "0", delta="sesión")
            with col_t2:
                st.metric("💬 Msgs", session.get("message_count", 0))
            with col_t3:
                st.metric("⏱️ uptime", str(agente_status['uptime']).split('.')[0])
        else:
            st.error("❌ Agente Offline")
            st.caption("Ejecuta: `python -m interface.telegram_bot`")

        st.divider()

        st.markdown("### 📊 📈 MÉTRICAS")
        
        m1, m2 = st.columns(2)
        with m1:
            st.metric("📄 Wiki", stats["total_wiki"])
        with m2:
            st.metric("📑 Raw", stats["total_raw"])
        
        m3, m4 = st.columns(2)
        with m3:
            st.metric("🔗 Links", stats["total_links"])
        with m4:
            st.metric("🏛️ Hubs", stats.get("entities", 0))

        st.divider()
        
        if st.button("↻ Reíniciar Dashboard"):
            st.rerun()
        
        st.caption(f"🌳 v5.0 | {datetime.now().strftime('%Y-%m-%d')}")

    # =============================================================================
    # CONTENIDO PRINCIPAL
    # =============================================================================
    render_header(agente_status, image_path)

    telemetry = TelemetryEngine()

    render_kpi_cards(wiki, telemetry)
    st.divider()

    selected = st.session_state.get("selected_view", 0)

    if selected == 0:
        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.subheader("Telemetría del Sistema")
            render_system_charts()

            st.subheader("📈 Actividad del Agente")
            render_activity_heatmap(wiki)

        with col_right:
            st.subheader("Composición del Wiki")
            render_wiki_composition(wiki)

            st.subheader("Estadísticas Rápidas")
            st.json({
                "Wiki": stats["total_wiki"],
                "Raw Sources": stats["total_raw"],
                "Fuentes": stats["sources"],
                "Entidades": stats["entities"],
                "Conceptos": stats["concepts"],
                "Síntesis": stats["synthesis"],
                "Drafts": stats["draft"],
                "Finales": stats["final"],
                "Palabras totales": stats["total_words"],
                "Links totales": stats["total_links"],
                "Última ingesta": stats["last_ingest"],
            })

    elif selected == 1:
        render_skills_section()

    elif selected == 2:
        st.subheader("Inventario del Wiki")
        render_wiki_table(wiki)
        st.divider()
        st.subheader("Timeline de Conocimiento")
        render_wiki_timeline(wiki)

    elif selected == 3:
        st.subheader("Fuentes Crudas (Inmutables)")
        st.caption("Estas fuentes son la capa de verdad. El agente nunca las modifica.")
        render_raw_table(wiki)

    elif selected == 4:
        st.subheader("🧠 Grafo Vectorial del Wiki")
        st.caption("Visualización del grafo híbrido generado por /indexar_wiki")

        render_graph_store_status(config)
        st.divider()

        col_g1, col_g2 = st.columns([1, 1])

        with col_g1:
            render_communities_and_hubs(config)

        with col_g2:
            render_embeddings_status(config)
            st.divider()
            render_command_stats(wiki)

        st.divider()
        st.subheader("📄 Reporte del Grafo")
        render_graph_report(config)

    elif selected == 5:
        st.subheader("Flujo de Conciencia del Agente")
        render_logs_section(config)

    elif selected == 6:
        st.subheader("Diagnóstico del Wiki Karpathy")
        render_health_dashboard(wiki)

    elif selected == 7:
        st.subheader("📋 CLAUDE.md - Schema del Wiki")
        st.caption("Este documento define las reglas de comportamiento del agente.")
        render_schema_viewer(wiki)

    elif selected == 8:
        render_heartbeat_section()

    elif selected == 9:
        render_feeds_section()

    elif selected == 10:
        render_analytics_section()

    st.divider()
    st.caption(f"🛰️ Última sincronización: {datetime.now().strftime('%H:%M:%S')} | "
               f"Wiki: {stats['total_wiki']} notas | Raw: {stats['total_raw']} fuentes | "
               f"Agente: {'ONLINE' if agente_status['running'] else 'OFFLINE'}")

if __name__ == "__main__":
    main()
