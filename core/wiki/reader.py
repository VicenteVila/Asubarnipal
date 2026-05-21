"""Wiki reader module - Read-only wiki access."""

import sqlite3

import config


class WikiReader:
    """Read-only wiki access."""

    def __init__(self) -> None:
        self.wiki_path = config.WIKI_PATH
        self.conn = None

    def _connect(self) -> None:
        if not self.conn:
            self.conn = sqlite3.connect(str(self.wiki_path))
            self.conn.row_factory = sqlite3.Row

    def search(self, query: str) -> list:
        """Search entities by name or content."""
        self._connect()
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT name, content FROM entities
            WHERE name LIKE ? OR content LIKE ? LIMIT 20
        """, (f"%{query}%", f"%{query}%"))
        return [{"name": r[0], "content": r[1]} for r in cursor.fetchall()]

    def get_all(self, limit: int = 100) -> list:
        """Get all entities."""
        self._connect()
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT name, tipo, content FROM entities LIMIT {limit}")
        return [{"name": r[0], "tipo": r[1], "content": r[2][:500]} for r in cursor.fetchall()]
