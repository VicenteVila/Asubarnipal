"""
Asubarnipal Command Center - Entry Point

Modular dashboard with 12 tabs. Each tab is a separate module in dashboard/tabs/.
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
import psutil
import streamlit as st

from dashboard.config import AppConfig
from dashboard.components.avatar import find_avatar_image, render_agente_avatar, render_header
from dashboard.tabs import (
    render_tab_analytics,
    render_tab_dashboard,
    render_tab_feeds,
    render_tab_grafico,
    render_tab_hmem,
    render_tab_latido,
    render_tab_logs,
    render_tab_raw,
    render_tab_salud,
    render_tab_schema,
    render_tab_skills,
    render_tab_wiki,
)


TAB_NAMES = [
    "Dashboard",
    "Skills",
    "Wiki",
    "Raw",
    "Grafo",
    "Logs",
    "Salud",
    "Schema",
    "Latido",
    "Feeds",
    "Analytics",
    "H-Mem",
]


def init_session_state() -> None:
    """Initialize Streamlit session state defaults."""
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
        "selected_view": 0,
        "message_count": 0,
        "wiki_stats": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_agente_status(cfg: AppConfig) -> dict:
    """Detect if the Telegram bot process is running."""
    script_name = cfg.agente_script_name
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            if any(script_name.lower() in arg.lower() for arg in cmdline):
                with proc.oneshot():
                    from datetime import timedelta
                    uptime = datetime.now() - datetime.fromtimestamp(proc.create_time())
                    return {
                        "running": True,
                        "pid": proc.pid,
                        "uptime": uptime,
                        "cpu": proc.cpu_percent(interval=0.1),
                        "memory_mb": proc.memory_info().rss / 1024 / 1024,
                        "threads": proc.num_threads(),
                        "status": proc.status(),
                    }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return {
        "running": False, "pid": None, "uptime": None,
        "cpu": 0.0, "memory_mb": 0.0, "threads": 0, "status": "OFFLINE",
    }


def main() -> None:
    """Main dashboard entry point."""
    st.set_page_config(
        page_title="Asubarnipal Command Center",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    init_session_state()
    cfg = st.session_state.config

    # Wiki reader
    from dashboard.config import AppConfig as DAC
    from core.wiki import WikiReader as CoreWikiReader

    class KarpathyWikiReader(CoreWikiReader):
        def __init__(self, app_cfg: DAC):
            super().__init__()
            self.config = app_cfg
            self.wiki_path = Path(app_cfg.wiki_path)
            self.raw_path = Path(app_cfg.raw_path)
            self.index_path = Path(app_cfg.index_path)
            self.log_md_path = Path(app_cfg.log_md_path)
            self.schema_path = Path(app_cfg.schema_path)
            self.notes = []
            self.raw_sources = []
            self.log_entries = []
            self.schema_content = ""
            self._scan()

        def _scan(self):
            import yaml
            from collections import Counter

            if self.wiki_path.exists():
                for fp in self.wiki_path.rglob("*.md"):
                    try:
                        content = fp.read_text(encoding="utf-8", errors="ignore")
                        fm, body = {}, content
                        if content.startswith("---"):
                            parts = content.split("---", 2)
                            if len(parts) >= 3:
                                try:
                                    fm = yaml.safe_load(parts[1]) or {}
                                    body = parts[2]
                                except Exception:
                                    pass
                        self.notes.append({
                            "id": fp.stem, "path": str(fp), "filename": fp.name,
                            "tipo": fm.get("tipo", "unknown"),
                            "titulo": fm.get("titulo", fp.stem),
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

            if self.raw_path.exists():
                for fp in self.raw_path.rglob("*.md"):
                    try:
                        stat = fp.stat()
                        self.raw_sources.append({
                            "filename": fp.name,
                            "size_kb": stat.st_size / 1024,
                            "modified": datetime.fromtimestamp(stat.st_mtime),
                            "tipo": fp.name.split("_")[0] if "_" in fp.name else "unknown",
                        })
                    except Exception:
                        continue

            if self.schema_path.exists():
                try:
                    self.schema_content = self.schema_path.read_text(
                        encoding="utf-8", errors="ignore"
                    )[:2000]
                except Exception:
                    pass

            if self.log_md_path.exists():
                import re
                try:
                    content = self.log_md_path.read_text(encoding="utf-8", errors="ignore")
                    pattern = r"##\s*\[(.*?)\]\s*(.*?)\s*\|\s*(.*)"
                    for match in re.finditer(pattern, content):
                        self.log_entries.append({
                            "timestamp": match.group(1),
                            "tipo": match.group(2).strip(),
                            "descripcion": match.group(3).strip(),
                        })
                except Exception:
                    pass

        def get_stats(self):
            from collections import Counter
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

        def get_tipo_distribution(self):
            import pandas as pd
            from collections import Counter
            if not self.notes:
                return pd.DataFrame(columns=["tipo", "count", "label"])
            tipos = Counter(n["tipo"] for n in self.notes)
            label_map = {
                "source": "📄 Fuentes", "entity": "🏛️ Entidades",
                "concept": "💡 Conceptos", "synthesis": "🔗 Síntesis",
                "moc": "🗺️ MOCs", "unknown": "❓ Desconocido",
            }
            data = [{"tipo": k, "count": v, "label": label_map.get(k, k)} for k, v in tipos.items()]
            return pd.DataFrame(data).sort_values("count", ascending=False)

        def get_timeline_data(self):
            import pandas as pd
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
            return df.groupby("date").size().reset_index(name="count").sort_values("date")

        def get_log_activity(self):
            import pandas as pd
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

    wiki = KarpathyWikiReader(cfg)
    stats = wiki.get_stats()
    st.session_state["wiki_stats"] = stats

    agente_status = get_agente_status(cfg)
    st.session_state["agente_status"] = agente_status
    image_path = find_avatar_image()

    # Sidebar
    render_agente_avatar(agente_status, image_path)
    st.sidebar.divider()

    view = st.sidebar.radio(
        "Vista:",
        TAB_NAMES,
        index=st.session_state.get("selected_view", 0),
        key="view_selector",
    )
    st.session_state["selected_view"] = TAB_NAMES.index(view)

    # Header
    render_header(agente_status, image_path)

    # Tab content
    selected = st.session_state["selected_view"]

    if selected == 0:
        render_tab_dashboard(cfg, wiki, stats, agente_status)
    elif selected == 1:
        render_tab_skills()
    elif selected == 2:
        st.subheader("Inventario del Wiki")
        render_tab_wiki(wiki)
    elif selected == 3:
        st.subheader("Fuentes Crudas (Inmutables)")
        st.caption("Estas fuentes son la capa de verdad. El agente nunca las modifica.")
        render_tab_raw(wiki)
    elif selected == 4:
        st.subheader("🧠 Grafo de Conocimiento")
        st.caption("Grafo vectorial + Graphify knowledge graph")
        render_tab_grafico(cfg)
    elif selected == 5:
        render_tab_logs(cfg)
    elif selected == 6:
        render_tab_salud(wiki)
    elif selected == 7:
        render_tab_schema(wiki)
    elif selected == 8:
        render_tab_latido(cfg)
    elif selected == 9:
        render_tab_feeds()
    elif selected == 10:
        render_tab_analytics(cfg)
    elif selected == 11:
        render_tab_hmem()

    st.divider()
    st.caption(
        f"🛰️ Última sincronización: {datetime.now().strftime('%H:%M:%S')} | "
        f"Wiki: {stats['total_wiki']} notas | Raw: {stats['total_raw']} fuentes | "
        f"Agente: {'ONLINE' if agente_status['running'] else 'OFFLINE'}"
    )


if __name__ == "__main__":
    main()
