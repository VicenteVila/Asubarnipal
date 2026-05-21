"""Tab 9: Feeds - RSS subscriptions and alerts."""

import streamlit as st


def render_tab_feeds() -> None:
    """Render RSS feeds section."""
    st.subheader("📡 Suscripciones RSS")

    try:
        from core.feed_tracker import FeedTracker

        tracker = FeedTracker()
        feeds = tracker.get_subscriptions()
        alerts = tracker.get_alerts(unread_only=True)

        cols = st.columns(2)
        with cols[0]:
            st.metric("Suscritos", len(feeds))
        with cols[1]:
            st.metric(
                "🔔 Nuevas alertas",
                len(alerts),
                delta_color="inverse" if alerts else "normal",
            )

        if feeds:
            st.divider()
            for feed in feeds[:20]:
                url = feed.get("url", "N/A")
                last_check = feed.get("last_check", "N/A")
                st.markdown(f"• **{url}** — última verificación: {last_check}")
        else:
            st.info("No hay suscripciones RSS configuradas.")

    except Exception as e:
        st.warning(f"Error cargando feeds: {e}")
