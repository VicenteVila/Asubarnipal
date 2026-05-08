"""Dashboard Streamlit - Imperial Edition."""

import json
import os
import sys
from pathlib import Path

import streamlit as st
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
from core.wiki import Wiki
from core.background_manager import BackgroundManager


def main():
    st.set_page_config(page_title="Asubarnipal Dashboard", layout="wide")
    
    st.title("🏛️ Asubarnipal V2 — Dashboard Imperial")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Wiki Entries", "0")
    
    with col2:
        st.metric("Brave Left", "0")
    
    with col3:
        st.metric("Memories", "0")
    
    st.divider()
    
    st.subheader("💓 Heartbeat")
    if config.HEARTBEAT_FILE.exists():
        hb = json.loads(config.HEARTBEAT_FILE.read_text())
        
        c1, c2, c3 = st.columns(3)
        c1.metric("CPU", f"{hb.get('cpu_percent', 0)}%")
        c2.metric("RAM", f"{hb.get('memory_percent', 0)}%")
        c3.metric("Disk", f"{hb.get('disk_percent', 0)}%")
        
        st.caption(f"Last update: {hb.get('timestamp', 'N/A')}")
    
    st.divider()
    
    st.subheader("🕸️ Knowledge Graph")
    
    st.info("Ejecuta: streamlit run dashboard.py")
    
    if st.button("🔄 Refresh"):
        st.rerun()


if __name__ == "__main__":
    main()