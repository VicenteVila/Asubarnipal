"""Asubarnipal V18 - Command Center Dashboard."""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from core.wiki_engine import WikiEngine, WikiVectorIndex
from core.background_manager import BackgroundManager, BraveCounter, MemorySkill
from core.dashboard_logic import DashboardManager


@dataclass
class AppConfig:
    base_dir: str = ""
    obsidian_path: str = ""
    
    @property
    def wiki_path(self) -> str:
        return str(config.OBSIDIAN_PATH / "wiki")
    
    @property
    def raw_path(self) -> str:
        return str(config.OBSIDIAN_PATH / "raw")
    
    @property
    def index_path(self) -> str:
        return str(config.OBSIDIAN_PATH / "index.md")
    
    @property
    def log_md_path(self) -> str:
        return str(config.OBSIDIAN_PATH / "log.md")
    
    @property
    def schema_path(self) -> str:
        return str(config.OBSIDIAN_PATH / "CLAUDE.md")


def find_agente_process(script_name: str = "agente.py") -> psutil.Process:
    """Find the agente process."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            cmdline = proc.info.get('cmdline') or []
            if any(script_name.lower() in arg.lower() for arg in cmdline):
                return psutil.Process(proc.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    return None


def get_agente_status(config: AppConfig) -> dict:
    """Get status of agente process."""
    proc = find_agente_process("agente.py") or find_agente_process("telegram_bot")
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


class WikiReader:
    """Lee la estructura del wiki."""
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.wiki_path = Path(config.wiki_path)
        self.raw_path = Path(config.raw_path)
        self.notes: list = []
        self.raw_sources: list = []
        self._scan()
    
    def _extraer_frontmatter(self, contenido: str):
        if contenido.startswith("---"):
            parts = contenido.split("---", 2)
            if len(parts) >= 3:
                try:
                    import yaml
                    return yaml.safe_load(parts[1]) or {}, parts[2]
                except:
                    return {}, contenido
        return {}, contenido
    
    def _scan(self):
        """Escanea wiki/ y raw/."""
        if self.wiki_path.exists():
            for file_path in self.wiki_path.rglob("*.md"):
                try:
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    fm, body = self._extraer_frontmatter(content)
                    self.notes.append({
                        "id": file_path.stem,
                        "path": str(file_path),
                        "tipo": fm.get("tipo", "unknown"),
                        "titulo": fm.get("titulo", file_path.stem),
                        "tags": fm.get("tags", []),
                        "relacionados": fm.get("relacionados", []),
                        "word_count": len(body.split()),
                    })
                except:
                    continue
        
        if self.raw_path.exists():
            for file_path in self.raw_path.rglob("*.md"):
                try:
                    stat = file_path.stat()
                    self.raw_sources.append({
                        "id": file_path.stem,
                        "path": str(file_path),
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime),
                    })
                except:
                    continue
    
    def get_hubs(self, limit: int = 10) -> list:
        """Get notas más conectadas."""
        hub_map = {}
        for nota in self.notes:
            for rel in nota.get("relacionados", []):
                key = str(rel).replace("[[", "").replace("]]", "")
                hub_map[key] = hub_map.get(key, 0) + 1
        
        hubs = [{"name": k, "connections": v} for k, v in hub_map.items()]
        return sorted(hubs, key=lambda x: x["connections"], reverse=True)[:limit]
    
    def get_clusters(self) -> list:
        """Get distribución por tags."""
        tag_map = {}
        for nota in self.notes:
            for tag in nota.get("tags", []):
                tag_map[str(tag)] = tag_map.get(str(tag), 0) + 1
        
        return [{"tag": k, "count": v} for k, v in tag_map.items()]


st.set_page_config(
    page_title="🏛️ Asubarnipal V18",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def load_heartbeat():
    if config.HEARTBEAT_FILE.exists():
        try:
            return json.loads(config.HEARTBEAT_FILE.read_text())
        except:
            return {}
    return {}


def load_brave_counter():
    return BraveCounter().get_left()


def load_wiki_stats():
    app_config = AppConfig()
    reader = WikiReader(app_config)
    hubs = reader.get_hubs(limit=20)
    clusters = reader.get_clusters()
    
    problemas = []
    all_ids = {n["id"] for n in reader.notes}
    linked_ids = set()
    for nota in reader.notes:
        for rel in nota.get("relacionados", []):
            linked_ids.add(str(rel).replace("[[", "").replace("]]", ""))
    
    for nota in reader.notes:
        if nota["id"] not in linked_ids and not nota.get("relacionados"):
            problemas.append(f"🏝️ HUÉRFANA: {nota['id']}")
        if not nota.get("tags"):
            problemas.append(f"🏷️ SIN_TAGS: {nota['id']}")
    
    return len(reader.notes), hubs, clusters, problemas


def load_memory():
    return MemorySkill().get_recent(limit=50)


def load_logs(lines=100):
    if config.LOG_FILE.exists():
        try:
            content = config.LOG_FILE.read_text(encoding="utf-8")
            return content.split("\n")[-lines:]
        except:
            return []
    return []


def load_telemetry():
    """Parse agent log for telemetry."""
    if not config.LOG_FILE.exists():
        return {}
    try:
        content = config.LOG_FILE.read_text(encoding="utf-8")
        lines = content.split("\n")
        
        updates_count = 0
        errors = 0
        started = None
        stopped = None
        
        for line in lines:
            if "Application started" in line:
                started = line[:19]
            elif "Application is stopping" in line:
                stopped = line[:19]
            elif "getUpdates" in line and "200 OK" in line:
                updates_count += 1
            elif "[ERROR]" in line or "[CRITICAL]" in line:
                errors += 1
        
        return {
            "started": started,
            "stopped": stopped,
            "requests": updates_count,
            "errors": errors,
        }
    except:
        return {}


st.title("🏛️ Asubarnipal V18 — Command Center")


col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("📊 Dashboard", width='stretch'):
        st.rerun()

with col2:
    if st.button("💓 Heartbeat", width='stretch'):
        st.rerun()

with col3:
    if st.button("📚 Wiki", width='stretch'):
        st.rerun()

with col4:
    if st.button("🕸️ Grafo", width='stretch'):
        st.rerun()

st.divider()

app_config = AppConfig()
agente_status = get_agente_status(app_config)

c1, c2, c3, c4 = st.columns(4)
with c1:
    status_icon = "🟢" if agente_status["running"] else "🔴"
    st.metric(f"{status_icon} Agente", str(agente_status.get("pid", "N/A")))
with c2:
    up = agente_status.get("uptime")
    up_str = f"{up.seconds // 3600}h{(up.seconds % 3600) // 60}m" if up else "N/A"
    st.metric("⏱️ Uptime", up_str)
with c3:
    st.metric("💻 CPU", f"{agente_status.get('cpu', 0):.1f}%")
with c4:
    st.metric("🧠 RAM", f"{agente_status.get('memory_mb', 0):.0f}MB")

hb = load_heartbeat()

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.metric("💓 CPU Sistema", f"{hb.get('cpu_percent', 0):.1f}%")
with c2:
    st.metric("🧠 RAM Sistema", f"{hb.get('memory_percent', 0):.1f}%")
with c3:
    st.metric("💾 Disk", f"{hb.get('disk_percent', 0):.1f}%")
with c4:
    brave_left = load_brave_counter()
    st.metric("🔍 Brave", f"{brave_left}/1500")

telemetry = load_telemetry()
tc1, tc2, tc3, tc4 = st.columns(4)
with tc1:
    st.metric("🆙 Started", telemetry.get("started", "N/A")[:16] if telemetry.get("started") else "N/A")
with tc2:
    st.metric("📥 Requests", telemetry.get("requests", 0))
with tc3:
    st.metric("❌ Errors", telemetry.get("errors", 0))
with tc4:
    st.metric("🛑 Status", "Running" if telemetry.get("started") and not telemetry.get("stopped") else "Stopped")

st.divider()

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📥 Ingesta", "🔎 Query", "🕸️ Grafo", 
    "🎭 Charla", "⚙️ Sistema", "📜 Logs"
])

with tab1:
    st.header("📥 Centro de Ingesta")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📄 Ingesta Manual")
        ingest_url = st.text_input("URL para ingestar:")
        if st.button("🌐 Ingestar Web", width='stretch'):
            wiki = WikiEngine()
            result = wiki.ingestar(fuente_nombre=ingest_url, contenido="Placeholder")
            if result.get("source_id"):
                st.success(f"✅ Ingirido: {result.get('source_id')}")
            else:
                st.error(f"❌ Error")
    
    with col2:
        st.subheader("📂 Sync Obsidian")
        vault_path = st.text_input("Ruta del Vault:", value=str(config.OBSIDIAN_PATH))
        if st.button("🔄 Sincronizar", width='stretch'):
            reader = WikiReader(app_config)
            st.success(f"✅ {len(reader.notes)} notas escaneadas")

with tab2:
    st.header("🔎 Centro de Query")
    
    query = st.text_input("Pregunta al wiki:")
    if st.button("🔍 Buscar", width='stretch'):
        wiki = WikiEngine()
        resultado = wiki.query_wiki(query)
        st.text_area("Resultado:", value=resultado, height=300)

with tab3:
    st.header("🕸️ Centro del Grafo")
    
    if st.button("🏗️ Indexar Wiki", width='stretch'):
        with st.spinner("Indexando..."):
            vec_index = WikiVectorIndex()
            result = vec_index.full_index()
            st.success(f"✅ Indexado: {result}")
    
    st.subheader("🏛️ Hubs Centrales")
    wiki_count, hubs, clusters, problemas = load_wiki_stats()
    if hubs:
        df_hubs = pd.DataFrame(hubs)
        fig = px.bar(df_hubs, x='connections', y='name', orientation='h',
                   title="Entidades más conectadas", color='connections')
        st.plotly_chart(fig)
        
        for h in hubs[:10]:
            st.write(f"• **{h['name']}** ({h['connections']} conexiones)")
    
    st.subheader("🔮 Clusters - Temas")
    if clusters:
        df_clusters = pd.DataFrame(clusters[:15])
        fig = px.pie(df_clusters, values='count', names='tag', 
                   title="Distribución de Temas")
        st.plotly_chart(fig)

with tab4:
    st.header("🎭 Centro de Charla")
    
    modes = ["Charla Libre", "Consultor Estratégico", "Devil's Advocate", "Modo Socrático", "Expansión Lateral"]
    mode = st.selectbox("Modo:", modes)
    topic = st.text_input("Tema:")
    if st.button("💬 Iniciar Charla", width='stretch'):
        st.info(f"Modo: {mode} | Tema: {topic}")
        st.text_area("Chat:", height=300)

with tab5:
    st.header("⚙️ Configuración del Sistema")
    
    st.subheader("🔑 Gemini Keys")
    for i, key in enumerate(config.GEMINI_KEYS or []):
        st.write(f"{i+1}. `{key[:20]}...`")
    
    st.subheader("📁 Rutas")
    st.write(f"OBSIDIAN_PATH: `{config.OBSIDIAN_PATH}`")
    st.write(f"WIKI: `{config.OBSIDIAN_PATH / 'wiki'}`")
    st.write(f"RAW: `{config.OBSIDIAN_PATH / 'raw'}`")
    st.write(f"GRAPH_STORE: `{config.OBSIDIAN_PATH / 'graph_store'}`")
    
    st.subheader("🧪 Test de Conexión")
    if st.button("🧪 Test Ollama", width='stretch'):
        try:
            import requests
            r = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
            st.success(f"Ollama: {r.status_code}")
        except Exception as e:
            st.error(f"Ollama: {e}")

with tab6:
    st.header("📜 Logs")
    
    lines = st.slider("Líneas:", 10, 500, 100)
    logs = load_logs(lines)
    log_text = "\n".join(logs[-lines:])
    st.text_area("Logs:", value=log_text, height=400, disabled=True)

st.divider()

st.caption(f"""
🏛️ **Asubarnipal V18 — Imperial Edition**
Última actualización: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")