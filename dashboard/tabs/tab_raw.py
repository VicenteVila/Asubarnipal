"""Tab 3: Raw - Raw sources table."""

from typing import Any

import pandas as pd
import streamlit as st


def render_tab_raw(wiki: Any) -> None:
    """Render raw sources table."""
    st.caption("Estas fuentes son la capa de verdad. El agente nunca las modifica.")
    _render_raw_table(wiki)


def _render_raw_table(wiki: Any) -> None:
    """Render raw sources as a table."""
    try:
        raw_sources = wiki.raw_sources if hasattr(wiki, "raw_sources") else []
        if not raw_sources:
            st.info("No hay fuentes raw.")
            return

        df = pd.DataFrame(raw_sources)
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"Total: {len(df)} fuentes raw")
    except Exception as e:
        st.warning(f"Error cargando fuentes raw: {e}")
