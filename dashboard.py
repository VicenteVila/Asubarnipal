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
        self.obsidian_path = str(config.OBSIDIAN_PATH)
    
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
    candidates = [
        Path(__file__).parent / "Asubarnipal.jpg",
        Path(__file__).parent / "asubarnipal.jpg",
        config.BASE_DIR / "Asubarnipal.jpg",
        config.BASE_DIR / "asubarnipal.jpg",
        config.OBSIDIAN_PATH / "Asubarnipal.jpg",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate.resolve())
    return None

# =============================================================================
# MOTOR DE WIKI - LECTOR DE ESTRUCTURA KARPATHY
# =============================================================================

from core.wiki import WikiReader as CoreWikiReader

class KarpathyWikiReader(CoreWikiReader):
    """Extends core WikiReader with Karpathy pattern analysis."""
    
    def __init__(self, app_config: AppConfig):
        super().__init__()
        self.config = app_config
        self.wiki_path = Path(app_config.wiki_path)
        self.raw_path = Path(app_config.raw_path)
        self.index_path = Path(app_config.index_path)
        self.log_md_path = Path(app_config.log_md_path)
        self.schema_path = Path(app_config.schema_path)
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

def render_kpi_cards(wiki: KarpathyWikiReader, telemetry: TelemetryEngine):
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

def render_wiki_composition(wiki: KarpathyWikiReader):
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

def render_wiki_timeline(wiki: KarpathyWikiReader):
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

def render_activity_heatmap(wiki: KarpathyWikiReader):
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

def render_wiki_table(wiki: KarpathyWikiReader):
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

    st.divider()
    st.subheader("💾 Preferencias de Propuesta")
    try:
        from core.memory import get_proposal_memory
        pm = get_proposal_memory()
        pref = pm.get_preference()
        stats = pm.stats()
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("📊 Activas", stats["active"])
        with col2:
            st.metric("⏸️ Standby", stats["standby"])
        with col3:
            st.metric("📦 Archivadas", stats["archived"])
        with col4:
            st.metric("🎯 Preferido", pref.capitalize())
        
        modo_cols = st.columns([1, 1])
        with modo_cols[0]:
            if st.button("📊 Estructurada", key="modo_estructurada"):
                pm.set_preference("estructurada")
                st.rerun()
        with modo_cols[1]:
            if st.button("🧭 Exploratoria", key="modo_exploratoria"):
                pm.set_preference("exploratoria")
                st.rerun()
    except Exception as e:
        st.warning(f"No se pudo cargar preferencias: {e}")
    
    st.divider()
    st.subheader("📋 Propuestas Guardadas")
    
    try:
        from core.memory import get_proposal_memory
        pm = get_proposal_memory()
        
        tab1, tab2, tab3 = st.tabs(["Activas", "Standby", "Archivadas"])
        
        with tab1:
            active = pm.list("active")
            if active:
                for p in active[:10]:
                    with st.expander(f"📌 [{p['id'][:8]}] {p['pregunta_original'][:60]}"):
                        modo_emoji = "📊" if p.get("modo") == "estructurada" else "🧭"
                        st.caption(f"{modo_emoji} {p['modo']} | {p['timestamp'][:10]}")
                        
                        propuesta = p.get("propuesta", "") or p.get("respuesta", "")[:500]
                        st.markdown(f"**Propuesta:**\n{propuesta[:300]}...")
                        
                        cols_buttons = st.columns([1, 1, 1])
                        if cols_buttons[0].button("📦 Archivar", key=f"arch_{p['id']}"):
                            pm.archive(p["id"])
                            st.rerun()
                        if cols_buttons[1].button("📝 Wiki", key=f"wiki_{p['id']}"):
                            from core.wiki import Wiki
                            wiki = Wiki()
                            wiki.save_research_proposal(
                                pregunta=p.get("pregunta_original", ""),
                                propuesta=propuesta,
                                modo=p.get("modo", "estructurada"),
                                refs=p.get("refs", [])
                            )
                            st.info("Guardada en wiki!")
                        if cols_buttons[2].button("🗑️ Eliminar", key=f"del_{p['id']}"):
                            pm.delete(p["id"])
                            st.rerun()
            else:
                st.info("No hay propuestas activas")
        
        with tab2:
            standby = pm.list("standby")
            if standby:
                for p in standby[:10]:
                    with st.expander(f"⏸️ [{p['id'][:8]}] {p['pregunta_original'][:60]}"):
                        st.caption(p.get("timestamp", "")[:10])
                        st.markdown(p.get("propuesta", "")[:300])
                        cols_s = st.columns([1, 1])
                        if cols_s[0].button("✅ Activar", key=f"act_{p['id']}"):
                            pm.restore(p["id"])
                            st.rerun()
                        if cols_s[1].button("🗑️ Eliminar", key=f"dels_{p['id']}"):
                            pm.delete(p["id"])
                            st.rerun()
            else:
                st.info("No hay propuestas en standby")
        
        with tab3:
            archived = pm.list("archived")
            if archived:
                for p in archived[:10]:
                    with st.expander(f"📦 [{p['id'][:8]}] {p['pregunta_original'][:60]}"):
                        st.caption(f"Archivada: {p.get('archived_at', p.get('timestamp', ''))[:10]}")
                        if st.button("✅ Restaurar", key=f"res_{p['id']}"):
                            pm.restore(p["id"])
                            st.rerun()
            else:
                st.info("No hay propuestas archivadas")
                
    except Exception as e:
        st.warning(f"No se pudieron cargar propuestas: {e}")

def render_raw_table(wiki: KarpathyWikiReader):
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

def render_schema_viewer(wiki: KarpathyWikiReader):
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
    """Muestra el estado del grafo vectorial - usa Obsidian graph_store."""
    graph_store = Path(config.obsidian_path) / "graph_store"
    meta_path = graph_store / "metadata.json"

    if meta_path.exists():
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            
            nodes = meta.get('total_nodos', meta.get('total_nodes', 0))
            edges = meta.get('total_aristas', meta.get('total_edges', 0))
            comunidades = meta.get('comunidades', meta.get('communities', {}))
            num_comunidades = len(set(comunidades.values())) if comunidades else 0
            hubs = meta.get('hubs', [])
            
            st.success(f"📊 Grafo vectorial cargado: **{nodes} nodos**, **{edges} conexiones**")
            
            cols = st.columns(4)
            with cols[0]:
                st.metric("🕸️ Nodos", nodes)
            with cols[1]:
                st.metric("🔗 Conexiones", edges)
            with cols[2]:
                st.metric("📊 Comunidades", num_comunidades)
            with cols[3]:
                st.metric("🏛️ Hubs", len(hubs))
            
            return
        except Exception as e:
            st.warning(f"Error leyendo metadata: {e}")
    
    st.warning("🕸️ Grafo no encontrado. Ejecuta `/indexar_wiki`.")

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
    """Visualiza comunidades y hubs desde metadata.json del Obsidian graph_store."""
    meta_path = Path(config.obsidian_path) / "graph_store" / "metadata.json"
    
    if not meta_path.exists():
        st.info("No hay datos del grafo. Ejecuta `/indexar_wiki`.")
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
            comunidades = meta.get("comunidades", {})
            num_comunidades = len(set(comunidades.values())) if comunidades else 0
            st.metric("📊 Comunidades", num_comunidades)
        with cols[3]:
            st.metric("🏛️ Hubs", len(meta.get("hubs", [])))

        st.divider()

        # Hubs
        hubs = meta.get("hubs", [])
        if hubs:
            st.subheader("🏛️ Hubs Centrales (Top 10)")
            hub_data = []
            for i, (node, score) in enumerate(hubs[:10], 1):
                hub_data.append({
                    "Rank": i,
                    "Nodo": node,
                    "Score": f"{score:.4f}"
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
            for comm_id, nodes in sorted(comm_groups.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
                comm_data.append({
                    "Comunidad": comm_id,
                    "Nodos": len(nodes),
                    "Ejemplos": ", ".join(nodes[:3])
                })
            st.dataframe(pd.DataFrame(comm_data), hide_index=True, width="stretch")

    except Exception as e:
        st.error(f"Error: {e}")

def render_command_stats(wiki: KarpathyWikiReader):
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

def render_health_dashboard(wiki: KarpathyWikiReader):
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

        st.divider()
        render_quality_dashboard()


def render_quality_dashboard():
    """Render ingest quality metrics."""
    st.subheader("📊 Calidad de Ingestas")

    try:
        from core.wiki import Wiki
        wiki = Wiki()
        quality = wiki.get_ingest_quality(20)
        alerts = wiki.get_quality_alerts()
    except Exception as e:
        st.error(f"Error cargando métricas: {e}")
        return

    cols = st.columns(4)
    with cols[0]:
        st.metric("📦 Total", quality.get("total", 0))
    with cols[1]:
        st.metric("📈 Score Promedio", f"{quality.get('avg_score', 0):.0f}/100")
    with cols[2]:
        st.metric("⚠️ Baja Calidad", quality.get("low_quality_count", 0), 
                  delta_color="inverse" if quality.get("low_quality_count", 0) > 0 else "normal")
    with cols[3]:
        st.metric("🔔 Alertas", len(alerts), delta_color="inverse" if len(alerts) > 0 else "normal")

    if quality.get("by_type"):
        st.caption("**Por tipo:**")
        type_cols = st.columns(3)
        for i, (t, data) in enumerate(quality["by_type"].items()):
            emoji = {"pdf": "📄", "youtube": "🎬", "url": "🌐"}.get(t, "📦")
            with type_cols[i % 3]:
                st.metric(f"{emoji} {t}", f"{data['count']}", delta=f"avg: {data['avg_score']:.0f}")

    if quality.get("recent"):
        st.caption("**Recientes:**")
        recent_data = quality["recent"][-10:]
        for e in recent_data:
            score = e.get("quality_score", 0)
            color = "🔴" if score < 50 else ("🟡" if score < 75 else "🟢")
            name = e.get("name", "N/A")[:40]
            st.write(f"{color} `{score}/100` - {name}")

    if alerts:
        st.caption("**⚠️ Alertas de baja calidad:**")
        for a in alerts[:5]:
            st.warning(f"• {a.get('name', 'N/A')[:50]} (score: {a.get('quality_score', 0)})")


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
    wiki = KarpathyWikiReader(config)
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
            ("🌳", "H-Mem", "Memoria híbrida"),
        ]
        
        st.markdown("### ⌨️ NAVEGACIÓN")
        
        for i, (emoji, title, desc) in enumerate(nav_options):
            btn_key = f"nav_btn_{i}"
            label = f"{emoji} {title}"
            if st.button(label, key=btn_key, width="stretch"):
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
                st.metric("💬 Msgs", st.session_state.get("message_count", 0))
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

    if "selected_view" not in st.session_state:
        st.session_state.selected_view = 0
    else:
        st.session_state.selected_view = int(st.session_state.selected_view)

    selected = st.session_state.selected_view

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

    elif selected == 3:
        st.subheader("Fuentes Crudas (Inmutables)")
        st.caption("Estas fuentes son la capa de verdad. El agente nunca las modifica.")
        render_raw_table(wiki)

    elif selected == 4:
        st.subheader("🧠 Grafo de Conocimiento")
        st.caption("Grafo vectorial + Graphify knowledge graph")

        graph_source = st.radio(
            "Fuente del grafo:",
            ["Graphify (Interactivo)", "Graph Store (Métricas)"],
            index=0,
            horizontal=True,
            key="graph_source_selector"
        )

        st.divider()

        if graph_source == "Graphify (Interactivo)":
            from core.graphify_integration import (
                get_graph_stats as gf_stats,
                get_graph_html_path,
                get_graph_report,
                build_graph,
            )

            stats = gf_stats()

            if stats.get("exists"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🕸️ Nodos", stats.get("nodes", 0))
                with col2:
                    st.metric("🔗 Conexiones", stats.get("edges", 0))
                with col3:
                    st.metric("📊 Comunidades", stats.get("communities", 0))
                with col4:
                    st.metric("🕐 Última vez", stats.get("last_built", "N/A"))

                if stats.get("hubs"):
                    st.subheader("🏛️ Top Hubs")
                    hub_cols = st.columns(min(5, len(stats["hubs"])))
                    for i, hub in enumerate(stats["hubs"][:5]):
                        with hub_cols[i]:
                            st.metric(hub["name"][:20], hub["connections"])

                st.divider()

                html_path = get_graph_html_path()
                if html_path:
                    st.subheader("🕸️ Visualización Interactiva del Grafo")
                    st.caption("Haz clic en los nodos, filtra por comunidad, busca conceptos")

                    try:
                        with open(html_path, "r", encoding="utf-8") as f:
                            html_content = f.read()

                        st.markdown("""
                        <style>
                        .graph-container {
                            width: 100%;
                            height: 850px;
                            border: 2px solid #30363d;
                            border-radius: 12px;
                            overflow: hidden;
                            background: #0d1117;
                        }
                        .graph-container iframe {
                            width: 100%;
                            height: 100%;
                            border: none;
                        }
                        </style>
                        """, unsafe_allow_html=True)

                        st.components.v1.html(
                            html_content,
                            height=850,
                            scrolling=True
                        )

                        st.caption(f"📁 Archivo: {html_path} — Ábrelo en tu navegador para pantalla completa")

                    except Exception as e:
                        st.warning(f"No se pudo cargar graph.html: {e}")
                        st.info("Abre el archivo manualmente: `graphify-out/graph.html`")
                else:
                    st.info("Visualización HTML no disponible. Construye el grafo con `/graphify`.")

                st.divider()
                st.subheader("📄 Reporte del Grafo")
                report = get_graph_report()
                if report:
                    st.markdown(f"""
                    <style>
                    .graph-report {{
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
                    }}
                    </style>
                    """, unsafe_allow_html=True)
                    st.markdown(
                        f'<div class="graph-report">{report.replace(chr(10), "<br>")}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.info("No hay reporte disponible.")
            else:
                st.warning("🕸️ No hay grafo de Graphify disponible.")
                st.info("Construye el grafo con:")
                st.code("graphify extract /mnt/c/Obsidian/wiki --backend ollama")
                st.code("# O desde Telegram: /graphify")

                if st.button("🔨 Construir grafo ahora", key="build_graphify_btn"):
                    with st.spinner("Construyendo grafo con Graphify..."):
                        result = build_graph(backend="ollama")
                        if result.get("success"):
                            st.success(f"✅ Grafo construido: {result.get('stats', {}).get('nodes', 0)} nodos")
                            st.rerun()
                        else:
                            st.error(f"❌ Error: {result.get('error', 'Desconocido')}")

        else:
            try:
                col1, col2, col3, col4 = st.columns(4)
                graph_store = Path(config.obsidian_path) / "graph_store"
                meta_path = graph_store / "metadata.json"

                if not meta_path.exists():
                    st.info("🕸️ Grafo no encontrado. Generando automáticamente...")
                    with st.spinner("Construyendo grafo de conocimiento..."):
                        try:
                            from core.graph_builder import GraphBuilder
                            builder = GraphBuilder()
                            result = builder.build_graph()
                            st.success(f"✅ Grafo construido: {result.get('nodes', 0)} nodos, {result.get('edges', 0)} conexiones")
                        except Exception as ge:
                            st.warning(f"No se pudo construir grafo: {ge}")

                if meta_path.exists():
                    import json as _json
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = _json.load(f)
                    with col1:
                        st.metric("🕸️ Nodos", meta.get("total_nodos", 0))
                    with col2:
                        st.metric("🔗 Conexiones", meta.get("total_aristas", 0))
                    comunidades = meta.get("comunidades", {})
                    with col3:
                        st.metric("📊 Comunidades", len(set(comunidades.values())) if comunidades else 0)
                    with col4:
                        st.metric("🏛️ Hubs", len(meta.get("hubs", [])))
                else:
                    for c in [col1, col2, col3, col4]:
                        with c:
                            st.metric("Grafo", "No disponible")
            except Exception as e:
                st.warning(f"Error: {e}")

            st.divider()

            try:
                col_g1, col_g2 = st.columns([1, 1])
                with col_g1:
                    render_communities_and_hubs(config)
                with col_g2:
                    emb_path = Path(config.obsidian_path) / "graph_store" / "embeddings.pkl"
                    if emb_path.exists():
                        size_mb = emb_path.stat().st_size / 1024 / 1024
                        st.metric("🧠 Embeddings", f"{size_mb:.1f} MB", delta="Persistidos", delta_color="normal")
                    else:
                        st.metric("🧠 Embeddings", "No generados", delta="Ejecuta /indexar_wiki", delta_color="off")
            except Exception as e:
                st.warning(f"Error cargando comunidades: {e}")

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

    elif selected == 11:
        def render_hmem_section():
            try:
                from core.hybrid_retriever import get_hmem_manager
                hmem = get_hmem_manager()
                stats = hmem.stats()
            except ImportError:
                st.error("H-Mem no disponible.")
                return
            except Exception as e:
                st.error(f"Error H-Mem: {e}")
                return
            tree_stats = stats.get("tree", {})
            graph_stats = stats.get("graph", {})
            cols = st.columns(4)
            with cols[0]: st.metric("📦 Nodos", tree_stats.get("total_nodes", 0))
            with cols[1]: st.metric("🔗 Entidades", graph_stats.get("total_entities", 0))
            with cols[2]: st.metric("🔀 Relaciones", graph_stats.get("total_relations", 0))
            with cols[3]:
                last = tree_stats.get("last_insert", "Nunca")
                if last and last != "Nunca": last = last[:16]
                st.metric("⏰ Último", last)
            st.divider()
            col_q, col_r = st.columns(2)
            with col_q:
                st.markdown("### 🔍 Probar Retrieval")
                query = st.text_input("Buscar en memoria:", placeholder="Ej: ¿Qué sé sobre...")
                if query and st.button("🔎 Buscar"):
                    with st.spinner("Consultando H-Mem..."):
                        try:
                            result = hmem.recall(query)
                            evidence = result.get("ranked_evidence", [])
                            if evidence:
                                st.success(f"Encontrados {len(evidence)} resultados")
                                for i, ev in enumerate(evidence[:5]):
                                    node = ev.get("node", {})
                                    content = (node.get("summary") or node.get("content", ""))[:200]
                                    level = node.get("level", 0)
                                    score = ev.get("combined_score", 0)
                                    ts = node.get("timestamp", "")[:10]
                                    st.markdown(f"**{i+1}. [{ts}] L{level}** (score: {score:.2f})\n> {content}...")
                            else:
                                st.info("No se encontraron resultados")
                        except Exception as e:
                            st.error(f"Error: {e}")
            with col_r:
                st.markdown("### 💾 Añadir Memoria")
                new_memory = st.text_area("Nueva memoria:", placeholder="Escribe algo para recordar...")
                if st.button("💾 Guardar") and new_memory:
                    try:
                        result = hmem.remember(new_memory, metadata={"source": "dashboard"})
                        st.success(f"Guardada en L{result.get('tree_level', 0)}")
                    except Exception as e:
                        st.error(f"Error: {e}")
        render_hmem_section()

    st.divider()
    st.caption(f"🛰️ Última sincronización: {datetime.now().strftime('%H:%M:%S')} | "
               f"Wiki: {stats['total_wiki']} notas | Raw: {stats['total_raw']} fuentes | "
               f"Agente: {'ONLINE' if agente_status['running'] else 'OFFLINE'}")

if __name__ == "__main__":
    main()


# =============================================================================
# H-MEM SECTION
# =============================================================================

def render_hmem_section():
    """Render H-Mem memory system dashboard tab."""
    st.subheader("🌳 H-Mem: Sistema de Memoria Híbrida")
    st.caption("Memoria temporal-semántica con grafo de entidades (basado en arXiv:2605.15701)")
    
    try:
        from core.hybrid_retriever import get_hmem_manager
        hmem = get_hmem_manager()
        stats = hmem.stats()
    except ImportError:
        st.error("H-Mem no disponible. Asegúrate de que los módulos están instalados.")
        return
    except Exception as e:
        st.error(f"Error inicializando H-Mem: {e}")
        return
    
    tree_stats = stats.get("tree", {})
    graph_stats = stats.get("graph", {})
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Nodos Total", tree_stats.get("total_nodes", 0))
    with col2:
        st.metric("🔗 Entidades", graph_stats.get("total_entities", 0))
    with col3:
        st.metric("🔀 Relaciones", graph_stats.get("total_relations", 0))
    with col4:
        last = tree_stats.get("last_insert", "Nunca")
        if last and last != "Nunca":
            last = last[:16]
        st.metric("⏰ Último Nodo", last)
    
    st.divider()
    
    col_t, col_g = st.columns(2)
    
    with col_t:
        st.markdown("### 🌲 Árbol Temporal-Semántico")
        levels = tree_stats.get("by_level", {})
        
        if levels:
            level_data = []
            for k, v in levels.items():
                parts = k.split("_", 1)
                if len(parts) == 2:
                    level_data.append({"Nivel": parts[0], "Nombre": parts[1], "Nodos": v})
            
            if level_data:
                df_levels = pd.DataFrame(level_data)
                fig = px.bar(
                    df_levels, x="Nombre", y="Nodos", 
                    title="Nodos por Nivel del Árbol",
                    color="Nodos", color_continuous_scale="Blues"
                )
                fig.update_layout(
                    paper_bgcolor="#161b22",
                    plot_bgcolor="#161b22",
                    font_color="#c9d1d9",
                )
                st.plotly_chart(fig, width="stretch")
        else:
            st.info("No hay nodos en el árbol. Usa /recordar para añadir memorias.")
        
        with st.expander("📊 Detalle de Niveles"):
            st.json(tree_stats)
    
    with col_g:
        st.markdown("### 🔗 Grafo de Entidades")
        entities_by_type = graph_stats.get("by_type", {})
        
        if entities_by_type:
            type_data = [{"Tipo": k, "Cantidad": v} for k, v in entities_by_type.items()]
            df_types = pd.DataFrame(type_data)
            fig = px.pie(
                df_types, values="Cantidad", names="Tipo",
                title="Entidades por Tipo",
                hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_layout(
                paper_bgcolor="#161b22",
                font_color="#c9d1d9",
            )
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No hay entidades. Las memorias se extraen automáticamente.")
        
        with st.expander("📊 Detalle del Grafo"):
            st.json(graph_stats)
    
    st.divider()
    
    with st.expander("⚙️ Pesos de Ranking"):
        weights = stats.get("weights", {})
        st.json(weights)
        st.caption("""
        - **θ₁ (Semántico)**: Importancia de la similaridad de contenido
        - **θ₂ (Temporal)**: Importancia de la relevancia temporal
        - **θ₃ (Robustez)**: Importancia del factor Ebbinghaus (memorias recientes/recurrentes)
        """)
    
    col_q, col_r = st.columns(2)
    
    with col_q:
        st.markdown("### 🔍 Probar Retrieval")
        query = st.text_input("Buscar en memoria:", placeholder="Ej: ¿Qué sé sobre...")
        
        if query and st.button("🔎 Buscar"):
            with st.spinner("Consultando H-Mem..."):
                try:
                    result = hmem.recall(query)
                    evidence = result.get("ranked_evidence", [])
                    
                    if evidence:
                        st.success(f"Encontrados {len(evidence)} resultados")
                        for i, ev in enumerate(evidence[:5]):
                            node = ev.get("node", {})
                            content = (node.get("summary") or node.get("content", ""))[:200]
                            level = node.get("level", 0)
                            score = ev.get("combined_score", 0)
                            ts = node.get("timestamp", "")[:10]
                            
                            st.markdown(f"""
                            **{i+1}. [{ts}] L{level}** (score: {score:.2f})
                            > {content}...
                            """)
                    else:
                        st.info("No se encontraron resultados")
                except Exception as e:
                    st.error(f"Error en búsqueda: {e}")
    
    with col_r:
        st.markdown("### 💾 Añadir Memoria")
        new_memory = st.text_area("Nueva memoria:", placeholder="Escribe algo para recordar...")
        
        if st.button("💾 Guardar") and new_memory:
            try:
                result = hmem.remember(new_memory, metadata={"source": "dashboard"})
                st.success(f"Guardada en L{result.get('tree_level', 0)}: {result.get('tree_node_id', '')[:30]}...")
            except Exception as e:
                st.error(f"Error: {e}")
