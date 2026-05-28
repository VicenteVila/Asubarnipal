"""Tab 12: LIFE-HARNESS & HASP - Runtime harness and skill programs visualization."""

import pandas as pd
import plotly.express as px
import streamlit as st


def render_tab_harness() -> None:
    """Render LIFE-HARNESS and HASP dashboard tab."""
    st.subheader("🛡️ LIFE-HARNESS & HASP")
    st.caption("Runtime harness de 4 capas + Program Functions (arXiv:2605.22166, arXiv:2605.22306)")

    try:
        from core.runtime_harness import get_harness
        from core.skill_programs import get_pf_registry

        harness = get_harness()
        registry = get_pf_registry()
        stats = harness.get_stats()
    except ImportError:
        st.error("LIFE-HARNESS no disponible. Módulos no instalados.")
        return
    except Exception as e:
        st.error(f"Error inicializando harness: {e}")
        return

    contract = stats.get("contract_layer", {})
    skill = stats.get("skill_layer", {})
    action = stats.get("action_layer", {})
    trajectory = stats.get("trajectory_layer", {})

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📋 Contratos", contract.get("cached_contracts", 0))
    with col2:
        st.metric("🧠 Skills", skill.get("total_skills", 0))
    with col3:
        st.metric("✅ Validaciones", action.get("validated_actions", 0))
    with col4:
        st.metric("🔄 Intervenciones", stats.get("total_interventions", 0))

    st.divider()

    col_l1, col_l2 = st.columns(2)

    with col_l1:
        st.markdown("### Layer 1: Environment Contract")
        st.caption("Calibra definiciones de herramientas antes de enviarlas al LLM")
        st.metric("Contratos cacheados", contract.get("cached_contracts", 0))
        st.metric("Correcciones aplicadas", contract.get("corrections_applied", 0))

        with st.expander("📊 Detalle"):
            st.json(contract)

    with col_l2:
        st.markdown("### Layer 2: Procedural Skill")
        st.caption("Inyecta procedimientos reutilizables desde trayectorias pasadas")
        st.metric("Skills registradas", skill.get("total_skills", 0))
        st.metric("Historial de fallos", skill.get("failure_history", 0))

        skills_list = skill.get("skills", [])
        if skills_list:
            st.markdown("**Skills activas:**")
            for s in skills_list[:5]:
                st.markdown(
                    f"- `{s['name']}` — rate: {s.get('success_rate', 0):.1%}, "
                    f"invocations: {s.get('invocations', 0)}"
                )

        with st.expander("📊 Detalle"):
            st.json(skill)

    st.divider()

    col_l3, col_l4 = st.columns(2)

    with col_l3:
        st.markdown("### Layer 3: Action Realization")
        st.caption("Valida y canonicaliza acciones antes de ejecutarlas")

        validated = action.get("validated_actions", 0)
        rejected = action.get("rejected_actions", 0)
        total_actions = validated + rejected

        if total_actions > 0:
            pass_rate = validated / total_actions
            fig = px.pie(
                values=[validated, rejected],
                names=["Validadas", "Rechazadas"],
                title=f"Pass Rate: {pass_rate:.1%}",
                hole=0.4,
                color_discrete_sequence=["#2ecc71", "#e74c3c"],
            )
            fig.update_layout(
                paper_bgcolor="#161b22",
                font_color="#c9d1d9",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay acciones registradas aún")

        with st.expander("📊 Detalle"):
            st.json(action)

    with col_l4:
        st.markdown("### Layer 4: Trajectory Regulation")
        st.caption("Monitorea dinámicas post-ejecución y activa recuperación")

        traj_config = trajectory.get("config", {})
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Trayectorias activas", trajectory.get("active_trajectories", 0))
            st.metric("Recuperaciones", trajectory.get("recoveries_triggered", 0))
        with col_b:
            st.metric("Max estancamiento", traj_config.get("max_stagnation", "N/A"))
            st.metric("Max acciones", traj_config.get("max_actions", "N/A"))

        with st.expander("📊 Detalle"):
            st.json(trajectory)

    st.divider()

    st.markdown("### 📋 Program Functions (HASP)")
    st.caption("Funciones ejecutables que se activan en estados propensos a fallo")

    pfs = registry.list_pfs()

    if pfs:
        pf_data = []
        for pf in pfs:
            pf_data.append({
                "Nombre": pf["name"],
                "Prioridad": pf["priority"],
                "Invocaciones": pf["invocations"],
                "Éxitos": pf["success_count"],
                "Descripción": pf["description"][:60] + "..." if len(pf.get("description", "")) > 60 else pf.get("description", ""),
            })

        df_pfs = pd.DataFrame(pf_data)
        st.dataframe(df_pfs, use_container_width=True, hide_index=True)

        fig = px.bar(
            df_pfs, x="Nombre", y="Invocaciones",
            title="Invocaciones por Program Function",
            color="Invocaciones", color_continuous_scale="Viridis",
        )
        fig.update_layout(
            paper_bgcolor="#161b22",
            plot_bgcolor="#161b22",
            font_color="#c9d1d9",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No hay Program Functions registradas")

    st.divider()

    st.markdown("### 🧪 Probar PF")
    col_sel, col_state = st.columns([1, 2])

    with col_sel:
        pf_names = [pf["name"] for pf in pfs] if pfs else []
        selected_pf = st.selectbox("Seleccionar PF:", pf_names)

    with col_state:
        state_json = st.text_area(
            "Estado (JSON):",
            value='{"last_action": {"status": "error"}, "attempt_count": 1}',
            height=100,
        )

    if selected_pf and st.button("▶️ Ejecutar PF"):
        import json
        try:
            state = json.loads(state_json)
        except json.JSONDecodeError as e:
            st.error(f"JSON inválido: {e}")
            state = None

        if state is not None:
            try:
                result = registry.execute_pf(selected_pf, state)
                if result is None:
                    st.warning("PF no encontrado o precondiciones no cumplidas")
                else:
                    st.success(f"PF `{selected_pf}` ejecutado")
                    st.json(result)
            except Exception as e:
                st.error(f"Error ejecutando PF: {e}")

    st.divider()

    if st.button("🔄 Resetear estadísticas"):
        try:
            harness.reset_stats()
            st.success("Estadísticas reseteadas")
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
