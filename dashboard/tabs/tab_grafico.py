"""Tab 4: Grafo - Knowledge graph visualization (Graphify + Graph Store)."""

from pathlib import Path
from typing import Any

import streamlit as st

import config
from dashboard.config import AppConfig


def render_tab_grafico(config_app: AppConfig) -> None:
    """Render graph tab with Graphify and Graph Store views."""
    graph_source = st.radio(
        "Fuente del grafo:",
        ["Graphify (Interactivo)", "Graph Store (Métricas)"],
        index=0,
        horizontal=True,
        key="graph_source_selector",
    )

    st.divider()

    if graph_source == "Graphify (Interactivo)":
        _render_graphify_view()
    else:
        _render_graph_store_view(config_app)


def _render_graphify_view() -> None:
    """Render Graphify interactive graph view."""
    from core.graphify_integration import (
        get_graph_stats as gf_stats,
        get_graph_html_path,
        get_graph_report,
        build_graph,
    )

    stats = gf_stats()

    if stats.get("exists"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("🕸️ Nodos", stats.get("nodes", 0))
        with col2:
            st.metric("🔗 Conexiones", stats.get("edges", 0))
        with col3:
            st.metric("📊 Comunidades", stats.get("communities", 0))
        with col4:
            st.metric("🕐 Última vez", stats.get("last_built", "N/A"))

        if stats.get("hubs"):
            st.subheader("🏛️ Top Hubs")
            hub_cols = st.columns(min(5, len(stats["hubs"])))
            for i, hub in enumerate(stats["hubs"][:5]):
                with hub_cols[i]:
                    st.metric(hub["name"][:20], hub["connections"])

        st.divider()

        html_path = get_graph_html_path()
        if html_path:
            st.subheader("🕸️ Visualización Interactiva del Grafo")
            st.caption("Haz clic en los nodos, filtra por comunidad, busca conceptos")

            try:
                with open(html_path, "r", encoding="utf-8") as f:
                    html_content = f.read()

                st.components.v1.html(
                    html_content,
                    height=850,
                    scrolling=True,
                )

                st.caption(
                    f"📁 Archivo: {html_path} — "
                    f"Ábrelo en tu navegador para pantalla completa"
                )
            except Exception as e:
                st.warning(f"No se pudo cargar graph.html: {e}")
                st.info("Abre el archivo manualmente: `graphify-out/graph.html`")
        else:
            st.info("Visualización HTML no disponible. Construye el grafo con `/graphify`.")

        st.divider()
        st.subheader("📄 Reporte del Grafo")
        _render_graphify_report()
    else:
        st.warning("🕸️ No hay grafo de Graphify disponible.")
        st.info("Construye el grafo con:")
        st.code("graphify extract /mnt/c/Obsidian/wiki --backend ollama")
        st.code("# O desde Telegram: /graphify")

        if st.button("🔨 Construir grafo ahora", key="build_graphify_btn"):
            with st.spinner("Construyendo grafo con Graphify..."):
                result = build_graph(backend="ollama")
                if result.get("success"):
                    st.success(
                        f"✅ Grafo construido: "
                        f"{result.get('stats', {}).get('nodes', 0)} nodos"
                    )
                    st.rerun()
                else:
                    st.error(f"❌ Error: {result.get('error', 'Desconocido')}")


def _render_graphify_report() -> None:
    """Render Graphify report markdown."""
    from core.graphify_integration import get_graph_report

    report = get_graph_report()
    if report:
        st.markdown(
            """
            <style>
            .graph-report {
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 16px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                line-height: 1.5;
                color: #c9d1d9;
                max-height: 600px;
                overflow-y: auto;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="graph-report">{report.replace(chr(10), "<br>")}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("No hay reporte disponible.")


def _render_graph_store_view(config_app: AppConfig) -> None:
    """Render legacy Graph Store metrics view."""
    try:
        col1, col2, col3, col4 = st.columns(4)
        graph_store = Path(config_app.obsidian_path) / "graph_store"
        meta_path = graph_store / "metadata.json"

        if not meta_path.exists():
            st.info("🕸️ Grafo no encontrado. Generando automáticamente...")
            with st.spinner("Construyendo grafo de conocimiento..."):
                try:
                    from core.graph_builder import GraphBuilder
                    builder = GraphBuilder()
                    result = builder.build_graph()
                    st.success(
                        f"✅ Grafo construido: "
                        f"{result.get('nodes', 0)} nodos, "
                        f"{result.get('edges', 0)} conexiones"
                    )
                except Exception as ge:
                    st.warning(f"No se pudo construir grafo: {ge}")

        if meta_path.exists():
            import json as _json
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = _json.load(f)
            with col1:
                st.metric("🕸️ Nodos", meta.get("total_nodos", 0))
            with col2:
                st.metric("🔗 Conexiones", meta.get("total_aristas", 0))
            comunidades = meta.get("comunidades", {})
            with col3:
                st.metric(
                    "📊 Comunidades",
                    len(set(comunidades.values())) if comunidades else 0,
                )
            with col4:
                st.metric("🏛️ Hubs", len(meta.get("hubs", [])))
        else:
            for c in [col1, col2, col3, col4]:
                with c:
                    st.metric("Grafo", "No disponible")
    except Exception as e:
        st.warning(f"Error: {e}")

    st.divider()

    try:
        col_g1, col_g2 = st.columns([1, 1])
        with col_g1:
            _render_communities_and_hubs(config_app)
        with col_g2:
            emb_path = Path(config_app.obsidian_path) / "graph_store" / "embeddings.pkl"
            if emb_path.exists():
                size_mb = emb_path.stat().st_size / 1024 / 1024
                st.metric(
                    "🧠 Embeddings",
                    f"{size_mb:.1f} MB",
                    delta="Persistidos",
                    delta_color="normal",
                )
            else:
                st.metric(
                    "🧠 Embeddings",
                    "No generados",
                    delta="Ejecuta /indexar_wiki",
                    delta_color="off",
                )
    except Exception as e:
        st.warning(f"Error cargando comunidades: {e}")

    st.divider()
    st.subheader("📄 Reporte del Grafo")
    _render_graph_report(config_app)


def _render_communities_and_hubs(config_app: AppConfig) -> None:
    """Render communities and hubs from metadata.json."""
    meta_path = Path(config_app.obsidian_path) / "graph_store" / "metadata.json"

    if not meta_path.exists():
        st.info("No hay datos del grafo. Ejecuta `/indexar_wiki`.")
        return

    try:
        import json
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)

        st.subheader("🏛️ Hubs Principales")
        hubs = meta.get("hubs", [])
        if hubs:
            for hub in hubs[:10]:
                st.markdown(f"• **{hub}**")
        else:
            st.info("No hay hubs identificados.")

        st.divider()

        st.subheader("📊 Comunidades")
        comunidades = meta.get("comunidades", {})
        if comunidades:
            unique_comms = set(comunidades.values())
            st.markdown(f"**{len(unique_comms)}** comunidades detectadas")
        else:
            st.info("No hay comunidades detectadas.")
    except Exception as e:
        st.error(f"Error leyendo metadata: {e}")


def _render_graph_report(config_app: AppConfig) -> None:
    """Render graph report from graph_store."""
    report_path = Path(config_app.obsidian_path) / "graph_store" / "graph_report.md"
    if not report_path.exists():
        st.info("No hay reporte de grafo disponible.")
        return

    try:
        content = report_path.read_text(encoding="utf-8", errors="ignore")
        st.markdown(
            """
            <style>
            .graph-report {
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
                padding: 16px;
                font-family: 'JetBrains Mono', monospace;
                font-size: 0.85rem;
                line-height: 1.5;
                color: #c9d1d9;
                max-height: 600px;
                overflow-y: auto;
            }
            .graph-report h1 { color: #58a6ff; font-size: 1.2rem; }
            .graph-report h2 { color: #f0883e; font-size: 1rem; }
            .graph-report h3 { color: #a371f7; font-size: 0.9rem; }
            .graph-report strong { color: #58a6ff; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="graph-report">{content.replace(chr(10), "<br>")}</div>',
            unsafe_allow_html=True,
        )
    except Exception as e:
        st.error(f"Error leyendo reporte: {e}")
