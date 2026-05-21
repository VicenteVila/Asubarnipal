"""Tab 8: Latido - Cron jobs and heartbeat status."""

import json
from datetime import datetime

import streamlit as st

import config
from dashboard.config import AppConfig


def render_tab_latido(config_app: AppConfig) -> None:
    """Render heartbeat and cron jobs section."""
    st.subheader("💓 Latido del Sistema")

    _render_heartbeat_section()

    st.divider()

    st.subheader("⏰ Cron Jobs")

    st.markdown("""
    | Ritual | ⏱️ Intervalo | Función |
    |--------|----------|---------|
    | 💓 Heartbeat | 60s | Registra CPU/RAM |
    | 💉 Suture | 10min | Limpia huérfanas del wiki |
    | 🕸️ Graph | 30min | Reconstruye grafo vectorial |
    | 🕸️ Graphify | 30min | Reconstruye grafo de conocimiento |
    | 🌳 H-Mem | 30min | Consolida memoria híbrida |
    """)

    st.divider()

    st.subheader("📊 Estado de Background Manager")
    _render_bg_status()


def _render_heartbeat_section() -> None:
    """Render heartbeat data."""
    try:
        if config.HEARTBEAT_FILE.exists():
            data = json.loads(config.HEARTBEAT_FILE.read_text())

            cols = st.columns(3)
            with cols[0]:
                st.metric("CPU", f"{data.get('cpu_percent', 0):.1f}%")
            with cols[1]:
                st.metric("RAM", f"{data.get('memory_percent', 0):.1f}%")
            with cols[2]:
                st.metric("Disco", f"{data.get('disk_percent', 0):.1f}%")

            st.caption(f"Último latido: {data.get('timestamp', 'N/A')}")
        else:
            st.info("No hay datos de heartbeat. Inicia el bot primero.")
    except Exception as e:
        st.warning(f"Error leyendo heartbeat: {e}")


def _render_bg_status() -> None:
    """Render background manager status."""
    try:
        from core.background_manager import BackgroundManager

        bg = BackgroundManager()
        status = bg.get_status()

        st.json({
            "running": status.get("running", False),
            "last_heartbeat": status.get("last_heartbeat", {}).get("timestamp", "N/A"),
            "last_suture": status.get("last_suture", {}).get("timestamp", "N/A"),
            "last_graph": status.get("last_graph", {}).get("timestamp", "N/A"),
            "last_graphify": status.get("last_graphify", {}).get("timestamp", "N/A"),
            "last_hmem": status.get("last_hmem", {}).get("timestamp", "N/A"),
        })
    except Exception as e:
        st.info(f"Background manager no disponible: {e}")
