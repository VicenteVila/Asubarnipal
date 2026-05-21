"""Tab 1: Skills - Available functions and tools."""

import streamlit as st


def render_tab_skills() -> None:
    """Render skills section with available tools."""
    st.divider()

    with st.expander("🛠️ 🔧 Skills Activas", expanded=True):
        from core.skill_registry import SkillRegistry
        registry = SkillRegistry()
        skills = registry.list_skills()
        st.metric("Total", len(skills))
        for skill in skills[:8]:
            st.code(skill, language="python")
        if len(skills) > 8:
            st.caption(f"+ {len(skills)-8} funciones...")

    with st.expander("📡 ⚡ Feeds Activos"):
        from core.feed_tracker import FeedTracker
        tracker = FeedTracker()
        feeds = tracker.get_subscriptions()
        st.metric("Suscritos", len(feeds))
        alerts = tracker.get_alerts(unread_only=True)
        st.metric("🔔 Nuevas", len(alerts), delta_color="inverse" if alerts else "normal")

    with st.expander("💓 ⏰ Cron Jobs"):
        st.markdown("""
        | Ritual | ⏱️ Intervalo | Estado |
        |--------|----------|--------|
        | 💓 Heartbeat | 60s | ✅ Activo |
        | 💉 Suture | 600s | ✅ Activo |
        | 🕸️ Graph | 1800s | ✅ Activo |
        | 🕸️ Graphify | 1800s | ✅ Activo |
        """)

    with st.expander("💾 🧠 Memoria"):
        from core.memory import EnhancedMemory
        memory = EnhancedMemory()
        mem_stats = memory.get_stats()
        st.metric("Memorias", mem_stats.get("total", 0))
        by_cat = mem_stats.get("by_category", {})
        if by_cat:
            st.caption(f"Categorías: {', '.join(by_cat.keys())}")

    st.divider()

    st.markdown("### 🤖 🤖 ESTADO DEL AGENTE")

    agente_status = st.session_state.get("agente_status", {})

    if agente_status.get("running"):
        st.success(f"✅ Activo (PID {agente_status['pid']})")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("💾 RAM", f"{agente_status.get('memory_mb', 0):.0f} MB")
        with col2:
            st.metric("⚡ CPU", f"{agente_status.get('cpu', 0):.0f}%")

        col_t1, col_t2, col_t3 = st.columns(3)
        with col_t1:
            st.metric("🔢 Tokens", "0", delta="sesión")
        with col_t2:
            st.metric("💬 Msgs", st.session_state.get("message_count", 0))
        with col_t3:
            uptime = agente_status.get("uptime")
            if uptime:
                st.metric("⏱️ uptime", str(uptime).split('.')[0])
    else:
        st.error("❌ Agente Offline")
        st.caption("Ejecuta: `python -m interface.telegram_bot`")

    st.divider()

    st.markdown("### 📊 📈 MÉTRICAS")

    stats = st.session_state.get("wiki_stats", {})
    m1, m2 = st.columns(2)
    with m1:
        st.metric("📄 Wiki", stats.get("total_wiki", 0))
    with m2:
        st.metric("📑 Raw", stats.get("total_raw", 0))

    m3, m4 = st.columns(2)
    with m3:
        st.metric("🔗 Links", stats.get("total_links", 0))
    with m4:
        st.metric("🏛️ Hubs", stats.get("entities", 0))

    st.divider()

    if st.button("↻ Reíniciar Dashboard"):
        st.rerun()

    st.caption(f"🌳 v5.0 | {datetime.now().strftime('%Y-%m-%d')}")


from datetime import datetime
