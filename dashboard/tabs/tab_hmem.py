"""Tab 11: H-Mem - Hybrid memory system visualization."""

import pandas as pd
import plotly.express as px
import streamlit as st


def render_tab_hmem() -> None:
    """Render H-Mem memory system dashboard tab."""
    st.subheader("🌳 H-Mem: Sistema de Memoria Híbrida")
    st.caption("Memoria temporal-semántica con grafo de entidades (basado en arXiv:2605.15701)")

    try:
        from core.hybrid_retriever import get_hmem_manager

        hmem = get_hmem_manager()
        stats = hmem.stats()
    except ImportError:
        st.error("H-Mem no disponible. Asegúrate de que los módulos están instalados.")
        return
    except Exception as e:
        st.error(f"Error inicializando H-Mem: {e}")
        return

    tree_stats = stats.get("tree", {})
    graph_stats = stats.get("graph", {})

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📦 Nodos Total", tree_stats.get("total_nodes", 0))
    with col2:
        st.metric("🔗 Entidades", graph_stats.get("total_entities", 0))
    with col3:
        st.metric("🔀 Relaciones", graph_stats.get("total_relations", 0))
    with col4:
        last = tree_stats.get("last_insert", "Nunca")
        if last and last != "Nunca":
            last = last[:16]
        st.metric("⏰ Último Nodo", last)

    st.divider()

    col_t, col_g = st.columns(2)

    with col_t:
        st.markdown("### 🌲 Árbol Temporal-Semántico")
        levels = tree_stats.get("by_level", {})

        if levels:
            level_data = []
            for k, v in levels.items():
                parts = k.split("_", 1)
                if len(parts) == 2:
                    level_data.append({"Nivel": parts[0], "Nombre": parts[1], "Nodos": v})

            if level_data:
                df_levels = pd.DataFrame(level_data)
                fig = px.bar(
                    df_levels, x="Nombre", y="Nodos",
                    title="Nodos por Nivel del Árbol",
                    color="Nodos", color_continuous_scale="Blues",
                )
                fig.update_layout(
                    paper_bgcolor="#161b22",
                    plot_bgcolor="#161b22",
                    font_color="#c9d1d9",
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay nodos en el árbol. Usa /recordar para añadir memorias.")

        with st.expander("📊 Detalle de Niveles"):
            st.json(tree_stats)

    with col_g:
        st.markdown("### 🔗 Grafo de Entidades")
        entities_by_type = graph_stats.get("by_type", {})

        if entities_by_type:
            type_data = [{"Tipo": k, "Cantidad": v} for k, v in entities_by_type.items()]
            df_types = pd.DataFrame(type_data)
            fig = px.pie(
                df_types, values="Cantidad", names="Tipo",
                title="Entidades por Tipo",
                hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_layout(
                paper_bgcolor="#161b22",
                font_color="#c9d1d9",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay entidades. Las memorias se extraen automáticamente.")

        with st.expander("📊 Detalle del Grafo"):
            st.json(graph_stats)

    st.divider()

    with st.expander("⚙️ Pesos de Ranking"):
        weights = stats.get("weights", {})
        st.json(weights)
        st.caption("""
        - **θ₁ (Semántico)**: Importancia de la similaridad de contenido
        - **θ₂ (Temporal)**: Importancia de la relevancia temporal
        - **θ₃ (Robustez)**: Importancia del factor Ebbinghaus (memorias recientes/recurrentes)
        """)

    col_q, col_r = st.columns(2)

    with col_q:
        st.markdown("### 🔍 Probar Retrieval")
        query = st.text_input("Buscar en memoria:", placeholder="Ej: ¿Qué sé sobre...")

        if query and st.button("🔎 Buscar"):
            with st.spinner("Consultando H-Mem..."):
                try:
                    result = hmem.recall(query)
                    evidence = result.get("ranked_evidence", [])

                    if evidence:
                        st.success(f"Encontrados {len(evidence)} resultados")
                        for i, ev in enumerate(evidence[:5]):
                            node = ev.get("node", {})
                            content = (node.get("summary") or node.get("content", ""))[:200]
                            level = node.get("level", 0)
                            score = ev.get("combined_score", 0)
                            ts = node.get("timestamp", "")[:10]

                            st.markdown(
                                f"**{i+1}. [{ts}] L{level}** (score: {score:.2f})\n> {content}..."
                            )
                    else:
                        st.info("No se encontraron resultados")
                except Exception as e:
                    st.error(f"Error en búsqueda: {e}")

    with col_r:
        st.markdown("### 💾 Añadir Memoria")
        new_memory = st.text_area(
            "Nueva memoria:", placeholder="Escribe algo para recordar..."
        )

        if st.button("💾 Guardar") and new_memory:
            try:
                result = hmem.remember(new_memory, metadata={"source": "dashboard"})
                st.success(
                    f"Guardada en L{result.get('tree_level', 0)}: "
                    f"{result.get('tree_node_id', '')[:30]}..."
                )
            except Exception as e:
                st.error(f"Error: {e}")
