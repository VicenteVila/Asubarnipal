"""Tab 6: Salud - Wiki health diagnostics."""

from typing import Any

import streamlit as st


def render_tab_salud(wiki: Any) -> None:
    """Render wiki health dashboard."""
    st.subheader("Diagnóstico del Wiki Karpathy")
    _render_health_dashboard(wiki)


def _render_health_dashboard(wiki: Any) -> None:
    """Render wiki health metrics."""
    try:
        from core.wiki import Wiki

        w = Wiki()
        stats = w.get_stats() if hasattr(w, "get_stats") else {}

        total = stats.get("total", 0)
        orphans = stats.get("orphans", 0)
        draft = stats.get("draft", 0)
        final = stats.get("final", 0)

        cols = st.columns(4)
        with cols[0]:
            st.metric("Total notas", total)
        with cols[1]:
            st.metric("Huérfanas", orphans, delta_color="inverse" if orphans > 0 else "normal")
        with cols[2]:
            st.metric("Drafts", draft)
        with cols[3]:
            st.metric("Finales", final)

        st.divider()

        health_score = 100
        if total > 0:
            health_score -= (orphans / total) * 50
            health_score -= (draft / total) * 20

        st.metric("Salud del Wiki", f"{max(0, min(100, health_score)):.0f}%")

    except Exception as e:
        st.warning(f"No se pudo cargar diagnóstico: {e}")
