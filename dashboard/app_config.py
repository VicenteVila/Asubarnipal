"""Dashboard configuration for Asubarnipal."""

import os
from dataclasses import dataclass
from pathlib import Path

import config


@dataclass
class AppConfig:
    """Dashboard application configuration."""
    obsidian_path: str = ""
    refresh_interval: int = 0
    max_log_lines: int = 100
    theme_color: str = "#58a6ff"
    agente_script_name: str = "telegram_bot"

    def __post_init__(self):
        self.obsidian_path = str(config.OBSIDIAN_PATH)

    @property
    def wiki_path(self) -> str:
        return os.path.join(self.obsidian_path, "wiki")

    @property
    def raw_path(self) -> str:
        return os.path.join(self.obsidian_path, "raw")

    @property
    def log_file(self) -> str:
        return str(config.LOG_FILE)

    @property
    def index_path(self) -> str:
        return os.path.join(self.obsidian_path, "index.md")

    @property
    def log_md_path(self) -> str:
        return os.path.join(self.obsidian_path, "log.md")

    @property
    def schema_path(self) -> str:
        return os.path.join(self.obsidian_path, "CLAUDE.md")

    @property
    def graph_store_path(self) -> str:
        return os.path.join(self.obsidian_path, "graph_store")

    @property
    def data_path(self) -> str:
        return os.path.join(str(config.BASE_DIR), "data")
