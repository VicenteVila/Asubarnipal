"""Tab 13: Calidad - Ingest quality validation dashboard."""

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

import config
from core.wiki import Wiki


def render_tab_calidad() -> None:
    """Render quality dashboard."""
    st.subheader("📊 Calidad de Ingestas")
    st.caption("Métricas de calidad, validaciones de schema y verificación de citas")

    try:
        wiki = Wiki()
        quality = wiki.get_ingest_quality(limit=100)
    except Exception as e:
        st.error(f"Error cargando datos de calidad: {e}")
        return

    if quality["total"] == 0:
        st.info("No hay datos de calidad de ingesta aún. Realiza algunas ingestas primero.")
        return

    _render_summary_metrics(quality)
    st.divider()
    _render_quality_by_type(quality)
    st.divider()
    _render_recent_ingests(quality)
    st.divider()
    _render_quality_alerts(wiki)
    st.divider()
    _render_quality_timeline(wiki)


def _render_summary_metrics(quality: dict) -> None:
    """Render summary metric cards."""
    cols = st.columns(4)
    with cols[0]:
        st.metric("Total ingestas", quality["total"])
    with cols[1]:
        st.metric("Score promedio", f"{quality['avg_score']:.0f}/100")
    with cols[2]:
        delta = f"-{quality['low_quality_count']}" if quality['low_quality_count'] > 0 else "0"
        st.metric("⚠️ Baja calidad", quality["low_quality_count"], delta=delta)
    with cols[3]:
        by_type = quality.get("by_type", {})
        st.metric("Tipos distintos", len(by_type))


def _render_quality_by_type(quality: dict) -> None:
    """Render quality breakdown by type."""
    st.subheader("Calidad por tipo")

    by_type = quality.get("by_type", {})
    if not by_type:
        st.info("No hay datos por tipo.")
        return

    emoji_map = {"pdf": "📄", "youtube": "🎬", "url": "🌐"}
    rows = []
    for t, data in by_type.items():
        rows.append({
            "Tipo": f"{emoji_map.get(t, '📦')} {t}",
            "Cantidad": data["count"],
            "Score promedio": round(data["avg_score"], 1),
        })

    df = pd.DataFrame(rows)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.dataframe(df, use_container_width=True, hide_index=True)
    with col2:
        fig = px.bar(
            df, x="Tipo", y="Score promedio",
            color="Tipo", text_auto=".0f",
            title="Score promedio por tipo de ingesta",
            color_discrete_sequence=px.colors.qualifier.Set2,
        )
        fig.update_layout(
            paper_bgcolor="#161b22", plot_bgcolor="#161b22",
            font_color="#c9d1d9", showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)


def _render_recent_ingests(quality: dict) -> None:
    """Render recent ingests table."""
    st.subheader("Ingestas recientes")

    recent = quality.get("recent", [])
    if not recent:
        st.info("No hay ingestas recientes.")
        return

    rows = []
    for e in reversed(recent):
        score = e["quality_score"]
        emoji = "✅" if score >= 70 else "⚠️" if score >= 40 else "❌"
        rows.append({
            " ": emoji,
            "Score": f"{score}/100",
            "Tipo": e.get("type", "?"),
            "Nombre": e.get("name", "")[:50],
            "Contenido": f"{e.get('content_length', 0):,} chars",
            "Páginas": e.get("pages_total", "-"),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_quality_alerts(wiki: Wiki) -> None:
    """Render quality alerts."""
    st.subheader("⚠️ Alertas de baja calidad")

    try:
        alerts = wiki.get_quality_alerts()
    except Exception:
        alerts = []

    if not alerts:
        st.success("No hay alertas de baja calidad.")
        return

    for a in alerts:
        score = a.get("quality_score", 0)
        name = a.get("name", "unknown")[:60]
        ts = a.get("timestamp", "")[:19]
        st.warning(f"**{name}** — Score: {score}/100 — {ts}")


def _render_quality_timeline(wiki: Wiki) -> None:
    """Render quality score timeline chart."""
    st.subheader("Evolución de calidad")

    try:
        history = wiki._load_quality_history()
    except Exception:
        history = []

    if not history or len(history) < 2:
        st.info("No hay suficientes datos históricos para mostrar evolución.")
        return

    df = pd.DataFrame(history)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df = df.dropna(subset=["timestamp", "quality_score"]).sort_values("timestamp")

    if len(df) < 2:
        st.info("Datos insuficientes para el gráfico de evolución.")
        return

    df["label"] = df["name"].str[:30]

    fig = px.scatter(
        df, x="timestamp", y="quality_score",
        color="type", hover_data=["name", "content_length"],
        title="Evolución del score de calidad",
        labels={"timestamp": "Fecha", "quality_score": "Score", "type": "Tipo"},
        color_discrete_map={"pdf": "#4ECDC4", "youtube": "#FF6B6B", "url": "#45B7D1"},
    )
    fig.add_hline(y=50, line_dash="dash", line_color="red", annotation_text="Umbral baja calidad")
    fig.update_layout(
        paper_bgcolor="#161b22", plot_bgcolor="#161b22",
        font_color="#c9d1d9",
    )
    st.plotly_chart(fig, use_container_width=True)
