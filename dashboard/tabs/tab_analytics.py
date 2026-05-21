"""Tab 10: Analytics - Command history, memory, embeddings."""

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import config
from dashboard.config import AppConfig


def render_tab_analytics(config_app: AppConfig) -> None:
    """Render analytics section with command history and memory."""
    _render_command_stats_analytics()
    st.divider()
    _render_embeddings_status(config_app)
    st.divider()
    _render_memory_analytics()


def _render_command_stats_analytics() -> None:
    """Render command usage statistics."""
    st.subheader("📊 Historial de Comandos")

    try:
        from core.command_history import CommandHistory

        history = CommandHistory()
        commands = history.get_all(limit=100)

        if commands:
            df = pd.DataFrame(commands)
            st.dataframe(df, use_container_width=True, hide_index=True)

            if "command" in df.columns:
                cmd_counts = df["command"].value_counts().head(10)
                fig = px.bar(
                    x=cmd_counts.index, y=cmd_counts.values,
                    title="Top 10 Comandos",
                    labels={"x": "Comando", "y": "Veces usado"},
                )
                fig.update_layout(
                    paper_bgcolor="#161b22", plot_bgcolor="#161b22",
                    font_color="#c9d1d9",
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay historial de comandos.")
    except Exception as e:
        st.warning(f"Error cargando historial: {e}")


def _render_embeddings_status(config_app: AppConfig) -> None:
    """Render embedding index status."""
    st.subheader("🧠 Estado del Índice Vectorial")

    vector_index = Path(config_app.data_path) / "vector.index"
    if vector_index.exists():
        size_mb = vector_index.stat().st_size / 1024 / 1024
        st.metric("Índice FAISS", f"{size_mb:.1f} MB", delta="Activo")
    else:
        st.metric("Índice FAISS", "No generado", delta="Ejecuta /indexar_wiki", delta_color="off")


def _render_memory_analytics() -> None:
    """Render memory statistics."""
    st.subheader("🧠 Memoria del Agente")

    try:
        from core.memory import EnhancedMemory

        memory = EnhancedMemory()
        mem_stats = memory.get_stats()

        cols = st.columns(3)
        with cols[0]:
            st.metric("Total memorias", mem_stats.get("total", 0))
        with cols[1]:
            st.metric("Categorías", len(mem_stats.get("by_category", {})))
        with cols[2]:
            st.metric("Prioridad alta", mem_stats.get("high_priority", 0))

        by_cat = mem_stats.get("by_category", {})
        if by_cat:
            df = pd.DataFrame(list(by_cat.items()), columns=["Categoría", "Cantidad"])
            fig = px.bar(
                df, x="Categoría", y="Cantidad",
                title="Memorias por Categoría",
            )
            fig.update_layout(
                paper_bgcolor="#161b22", plot_bgcolor="#161b22",
                font_color="#c9d1d9",
            )
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Error cargando memoria: {e}")
