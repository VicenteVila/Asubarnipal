"""Tab 7: Schema - CLAUDE.md viewer."""

from typing import Any

import streamlit as st


def render_tab_schema(wiki: Any) -> None:
    """Render CLAUDE.md schema viewer."""
    st.subheader("📋 CLAUDE.md - Schema del Wiki")
    st.caption("Este documento define las reglas de comportamiento del agente.")
    _render_schema_viewer(wiki)


def _render_schema_viewer(wiki: Any) -> None:
    """Render schema content."""
    try:
        schema_content = wiki.schema_content if hasattr(wiki, "schema_content") else ""
        if schema_content:
            st.code(schema_content, language="markdown")
        else:
            st.info("No se encontró CLAUDE.md")
    except Exception as e:
        st.warning(f"Error cargando schema: {e}")
