"""Dashboard tabs package."""

from dashboard.tabs.tab_dashboard import render_tab_dashboard
from dashboard.tabs.tab_skills import render_tab_skills
from dashboard.tabs.tab_wiki import render_tab_wiki
from dashboard.tabs.tab_raw import render_tab_raw
from dashboard.tabs.tab_grafico import render_tab_grafico
from dashboard.tabs.tab_logs import render_tab_logs
from dashboard.tabs.tab_salud import render_tab_salud
from dashboard.tabs.tab_schema import render_tab_schema
from dashboard.tabs.tab_latido import render_tab_latido
from dashboard.tabs.tab_feeds import render_tab_feeds
from dashboard.tabs.tab_analytics import render_tab_analytics
from dashboard.tabs.tab_hmem import render_tab_hmem

__all__ = [
    "render_tab_dashboard",
    "render_tab_skills",
    "render_tab_wiki",
    "render_tab_raw",
    "render_tab_grafico",
    "render_tab_logs",
    "render_tab_salud",
    "render_tab_schema",
    "render_tab_latido",
    "render_tab_feeds",
    "render_tab_analytics",
    "render_tab_hmem",
]
