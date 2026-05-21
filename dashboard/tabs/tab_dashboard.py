"""Tab 0: Dashboard - System telemetry, activity heatmap, wiki composition."""

from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

from dashboard.config import AppConfig


class TelemetryEngine:
    """System telemetry snapshot and history manager."""

    def __init__(self, max_history: int = 60):
        self.max_history = max_history

    def snapshot(self) -> Dict[str, float]:
        import psutil
        return {
            "cpu": psutil.cpu_percent(interval=0.1),
            "ram": psutil.virtual_memory().percent,
            "disk": psutil.disk_usage("/").percent,
            "timestamp": datetime.now(),
        }

    def update_history(self, history: List[Dict], new_value: Dict) -> List[Dict]:
        history.append(new_value)
        if len(history) > self.max_history:
            history.pop(0)
        return history


def render_tab_dashboard(
    config: AppConfig,
    wiki: Any,
    stats: Dict[str, Any],
    agente_status: Dict[str, Any],
) -> None:
    """Render the main dashboard tab with telemetry and charts."""
    col_left, col_right = st.columns([2, 1])

    with col_left:
        _render_system_charts()
        st.subheader("📈 Actividad del Agente")
        _render_activity_heatmap(wiki)

    with col_right:
        st.subheader("Composición del Wiki")
        _render_wiki_composition(wiki)

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


def _render_system_charts() -> None:
    """Render CPU/RAM telemetry charts."""
    import psutil

    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().percent

    cols = st.columns(3)
    with cols[0]:
        st.metric("CPU", f"{cpu}%")
    with cols[1]:
        st.metric("RAM", f"{ram}%")
    with cols[2]:
        disk = psutil.disk_usage("/").percent
        st.metric("Disco", f"{disk}%")

    history = st.session_state.get("cpu_history", [])
    telemetry = TelemetryEngine()
    snapshot = telemetry.snapshot()
    st.session_state["cpu_history"] = telemetry.update_history(
        st.session_state.get("cpu_history", []), snapshot
    )
    st.session_state["ram_history"] = telemetry.update_history(
        st.session_state.get("ram_history", []), snapshot
    )

    cpu_hist = st.session_state.get("cpu_history", [])
    if len(cpu_hist) > 1:
        df = pd.DataFrame(cpu_hist)
        df["time"] = pd.to_datetime(df["timestamp"])

        fig = px.line(
            df, x="time", y=["cpu", "ram"],
            title="Telemetría del Sistema",
            labels={"value": "%", "time": "Hora"},
        )
        fig.update_layout(
            paper_bgcolor="#161b22", plot_bgcolor="#161b22",
            font_color="#c9d1d9", legend_title_text="Métrica",
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_activity_heatmap(wiki: Any) -> None:
    """Render agent activity heatmap from log data."""
    try:
        activity = wiki.get_log_activity()
        if activity.empty:
            st.info("No hay datos de actividad disponibles.")
            return

        df = activity.melt(id_vars=["date"], value_vars=["ingests", "queries", "lints"],
                           var_name="tipo", value_name="count")

        fig = px.density_heatmap(
            df, x="date", y="tipo", z="count",
            title="Mapa de Calor de Actividad",
            color_continuous_scale="Viridis",
        )
        fig.update_layout(
            paper_bgcolor="#161b22", plot_bgcolor="#161b22",
            font_color="#c9d1d9",
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"No se pudo renderizar el heatmap: {e}")


def _render_wiki_composition(wiki: Any) -> None:
    """Render wiki composition pie chart."""
    try:
        df = wiki.get_tipo_distribution()
        if df.empty:
            st.info("No hay notas en el wiki.")
            return

        fig = px.pie(
            df, values="count", names="label",
            title="Composición del Wiki",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Set3,
        )
        fig.update_layout(
            paper_bgcolor="#161b22", font_color="#c9d1d9",
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"No se pudo renderizar la composición: {e}")
