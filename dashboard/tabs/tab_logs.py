"""Tab 5: Logs - Agent log viewer."""

import re
from typing import Any

import pandas as pd
import streamlit as st

from dashboard.config import AppConfig


def render_tab_logs(config: AppConfig) -> None:
    """Render logs section with filter and search."""
    st.subheader("Flujo de Conciencia del Agente")
    _render_logs_section(config)


def _render_logs_section(config: AppConfig) -> None:
    """Render agent logs with filtering."""
    log_filter = st.selectbox(
        "Filtrar por nivel:",
        ["ALL", "INFO", "WARNING", "ERROR", "DEBUG"],
        key="log_level_filter",
    )

    search_query = st.text_input(
        "Buscar en logs:",
        placeholder="Ej: ingest, query, error...",
        key="log_search",
    )

    max_lines = st.slider(
        "Líneas a mostrar:",
        min_value=10, max_value=500, value=100, step=10,
        key="log_max_lines",
    )

    df = _parse_logs(
        config.log_file,
        max_lines=max_lines,
        level_filter=log_filter,
        search=search_query,
    )

    if df.empty:
        st.info("No se encontraron logs.")
        return

    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"Mostrando {len(df)} entradas")


def _parse_logs(
    log_path: str,
    max_lines: int = 100,
    level_filter: str = "ALL",
    search: str = "",
) -> pd.DataFrame:
    """Parse log file into DataFrame."""
    import os

    if not os.path.exists(log_path):
        return pd.DataFrame(columns=["timestamp", "level", "message"])

    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-max_lines:]
    except Exception:
        return pd.DataFrame(columns=["timestamp", "level", "message"])

    parsed = []
    log_pattern = re.compile(
        r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2},\d+)\s+-\s+\[(\w+)\]\s+-\s+(.*)"
    )

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
