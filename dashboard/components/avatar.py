"""Avatar and header components for the dashboard."""

from pathlib import Path
from typing import Any, Dict, Optional

import config
import streamlit as st


def find_avatar_image() -> Optional[str]:
    """Find avatar image from known locations."""
    candidates = [
        Path(__file__).parent.parent.parent / "Asubarnipal.jpg",
        Path(__file__).parent.parent.parent / "asubarnipal.jpg",
        config.BASE_DIR / "Asubarnipal.jpg",
        config.BASE_DIR / "asubarnipal.jpg",
        config.OBSIDIAN_PATH / "Asubarnipal.jpg",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def render_agente_avatar(
    agente_status: Dict[str, Any],
    image_path: Optional[str],
) -> None:
    """Render agent avatar with status indicator."""
    if image_path:
        st.sidebar.image(image_path, use_container_width=True)

    if agente_status.get("running"):
        st.sidebar.success(f"🟢 ONLINE — PID {agente_status['pid']}")
    else:
        st.sidebar.error("🔴 OFFLINE")


def render_header(
    agente_status: Dict[str, Any],
    image_path: Optional[str],
) -> None:
    """Render dashboard header with agent status."""
    col_logo, col_title = st.columns([1, 4])

    with col_logo:
        if image_path:
            st.image(image_path, width=80)
        else:
            st.markdown("## 🤖")

    with col_title:
        status_emoji = "🟢" if agente_status.get("running") else "🔴"
        status_text = "ONLINE" if agente_status.get("running") else "OFFLINE"
        st.title(f"Asubarnipal Command Center {status_emoji} {status_text}")

        if agente_status.get("running"):
            cols = st.columns(3)
            with cols[0]:
                st.caption(f"PID: {agente_status['pid']}")
            with cols[1]:
                st.caption(f"RAM: {agente_status.get('memory_mb', 0):.0f} MB")
            with cols[2]:
                st.caption(f"CPU: {agente_status.get('cpu', 0):.0f}%")

    st.divider()
