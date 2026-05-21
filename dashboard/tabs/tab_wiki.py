"""Tab 2: Wiki - Note inventory and timeline."""

from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st


def render_tab_wiki(wiki: Any) -> None:
    """Render wiki inventory table and timeline."""
    _render_wiki_table(wiki)
    st.divider()
    _render_wiki_timeline(wiki)


def _render_wiki_table(wiki: Any) -> None:
    """Render wiki notes as a filterable table."""
    try:
        notes = wiki.notes if hasattr(wiki, "notes") else []
        if not notes:
            st.info("No hay notas en el wiki.")
            return

        df = pd.DataFrame(notes)
        cols_to_show = ["filename", "tipo", "titulo", "estado", "fecha_ingesta", "word_count"]
        available_cols = [c for c in cols_to_show if c in df.columns]

        if available_cols:
            st.dataframe(df[available_cols], use_container_width=True, hide_index=True)
        else:
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.caption(f"Total: {len(df)} notas")
    except Exception as e:
        st.warning(f"Error cargando tabla wiki: {e}")


def _render_wiki_timeline(wiki: Any) -> None:
    """Render wiki ingestion timeline."""
    try:
        timeline = wiki.get_timeline_data()
        if timeline.empty:
            st.info("No hay datos de timeline.")
            return

        fig = px.bar(
            timeline, x="date", y="count",
            title="Línea Temporal de Ingesta",
            labels={"date": "Fecha", "count": "Notas"},
        )
        fig.update_layout(
            paper_bgcolor="#161b22", plot_bgcolor="#161b22",
            font_color="#c9d1d9",
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"No se pudo renderizar el timeline: {e}")
