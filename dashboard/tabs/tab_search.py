"""Search dashboard tab - hybrid search telemetry and analytics."""

import pandas as pd
import streamlit as st


def _render_search_stats(telemetry):
    stats = telemetry.get_stats()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Queries", stats.total_queries or 0)
    with col2:
        avg = stats.avg_latency_ms or 0
        st.metric("Avg Latency", f"{avg:.0f}ms")
    with col3:
        avg_res = stats.avg_results_per_query or 0
        st.metric("Avg Results", f"{avg_res:.1f}")
    with col4:
        avg_score = stats.avg_score or 0
        st.metric("Avg Score", f"{avg_score:.2f}")

    if stats.by_method:
        st.subheader("By Method")
        method_df = pd.DataFrame(
            [{"method": k, "count": v} for k, v in stats.by_method.items()]
        ).sort_values("count", ascending=False)
        st.dataframe(method_df, use_container_width=True, hide_index=True)


def _render_recent_queries(telemetry):
    st.subheader("Recent Queries")
    recent = telemetry.get_recent(20)
    if not recent:
        st.caption("No queries recorded yet.")
        return

    rows = []
    for m in recent:
        q = m.query[:60] + "..." if len(m.query) > 60 else m.query
        rows.append({
            "time": m.timestamp.strftime("%H:%M:%S") if m.timestamp else "",
            "query": q,
            "results": m.num_results,
            "latency_ms": f"{m.timing_ms.get('total_ms', 0):.0f}",
            "method": m.method or "N/A",
            "avg_score": f"{m.avg_score:.2f}" if m.avg_score else "",
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_timing_breakdown(telemetry):
    st.subheader("Timing Breakdown")
    recent = telemetry.get_recent(50)
    if not recent:
        st.caption("Not enough data.")
        return

    import plotly.graph_objects as go

    timestamps = []
    total_times = []
    for m in recent:
        ts = m.timestamp
        if ts:
            timestamps.append(ts.strftime("%H:%M:%S"))
            total_times.append(m.timing_ms.get("total_ms", 0))

    if timestamps:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=timestamps, y=total_times, mode="lines+markers",
            name="Total Latency (ms)", line=dict(color="#58a6ff"),
        ))
        fig.update_layout(
            height=250, margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor="#161b22", plot_bgcolor="#161b22",
            font_color="#c9d1d9", xaxis_title="Time", yaxis_title="ms",
        )
        st.plotly_chart(fig, use_container_width=True)


def render_tab_search():
    st.subheader("Hybrid Search Telemetry")
    st.caption("Ensemble classifier + multi-source retrieval analytics")

    try:
        from core.search.telemetry import get_telemetry
        telemetry = get_telemetry()
    except Exception as e:
        st.error(f"Could not load search telemetry: {e}")
        return

    _render_search_stats(telemetry)
    st.divider()
    _render_timing_breakdown(telemetry)
    st.divider()
    _render_recent_queries(telemetry)

    st.divider()
    st.subheader("Classifier Weights")
    try:
        from core.search.ensemble import DEFAULT_WEIGHTS
        st.code(
            "\n".join(f"{k}: {v:.2f}" for k, v in DEFAULT_WEIGHTS.items()),
            language="text",
        )
    except Exception:
        pass

    if st.button("Clear Telemetry"):
        telemetry.clear()
        st.rerun()
