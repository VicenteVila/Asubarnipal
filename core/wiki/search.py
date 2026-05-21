"""Wiki search module - FTS5 search, hubs, clusters, lint, health check."""

import json
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class WikiSearchMixin:
    """Mixin class with search, hubs, clusters, and lint methods."""

    def search(self, query: str, limit: int = 20) -> list:
        """Search wiki using FTS5 with token scoring and stop-word filtering."""
        self._ensure_fts5()

        raw_tokens = query.strip().lower().split()
        keywords = [t for t in raw_tokens if len(t) >= 3 and t not in self.STOP_WORDS]

        like_term = f"%{query}%"
        self.cursor.execute("""
            SELECT name, tipo, content, fecha_ingesta, fuente FROM entities
            WHERE name LIKE ? OR content LIKE ? LIMIT ?
        """, (like_term, like_term, limit))

        direct_results = [
            {"name": r[0], "tipo": r[1], "content": r[2],
             "fecha_ingesta": r[3], "fuente": r[4]}
            for r in self.cursor.fetchall()
        ]

        if keywords:
            name_matches = {}
            for token in keywords:
                try:
                    self.cursor.execute("""
                        SELECT name FROM entities_fts WHERE entities_fts MATCH ? LIMIT ?
                    """, (token, limit))

                    for r in self.cursor.fetchall():
                        name = r[0]
                        name_matches[name] = name_matches.get(name, 0) + 1
                except Exception as e:
                    logger.debug(f"FTS5 token search error for '{token}': {e}")

            if name_matches:
                sorted_names = sorted(name_matches.items(), key=lambda x: x[1], reverse=True)
                top_names = [n for n, _ in sorted_names[:limit]]

                placeholders = ",".join("?" * len(top_names))
                self.cursor.execute(f"""
                    SELECT name, tipo, content, fecha_ingesta, fuente FROM entities
                    WHERE name IN ({placeholders})
                """, top_names)

                name_to_result = {}
                for r in self.cursor.fetchall():
                    name_to_result[r[0]] = {
                        "name": r[0], "tipo": r[1], "content": r[2],
                        "fecha_ingesta": r[3] if len(r) > 3 else None,
                        "fuente": r[4] if len(r) > 4 else None,
                    }

                fts_results = [name_to_result[n] for n in top_names if n in name_to_result]

                direct_names = {r["name"] for r in direct_results}
                fts_names = {r["name"] for r in fts_results}
                shared = direct_names & fts_names

                results = [r for r in fts_results if r["name"] in shared]
                results += [r for r in fts_results if r["name"] not in shared]
                results += [r for r in direct_results if r["name"] not in fts_names]

                return results[:limit]

        return direct_results

    def get_hubs(self, limit: int = 10) -> list:
        """Get most connected entities (hubs)."""
        self.cursor.execute("SELECT name, relacionados FROM entities")
        results = []
        for row in self.cursor.fetchall():
            try:
                rels = json.loads(row[1]) if row[1] else []
                count = 0
                for r in rels:
                    if isinstance(r, dict):
                        if r.get("name"):
                            count += 1
                    elif isinstance(r, str) and r.strip():
                        count += 1
            except Exception:
                count = 0
            results.append({"name": row[0], "connections": count})
        results.sort(key=lambda x: x["connections"], reverse=True)
        return results[:limit]

    def get_clusters(self) -> list:
        """Get thematic clusters."""
        self.cursor.execute("SELECT tags FROM entities WHERE tags != '[]'")

        tag_counts = {}
        for row in self.cursor.fetchall():
            try:
                tags = json.loads(row[0])
                for tag in tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1
            except Exception:
                pass

        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"tag": t[0], "count": t[1]} for t in sorted_tags[:20]]

    def lint(self) -> dict:
        """Health check for wiki."""
        issues = []

        self.cursor.execute("SELECT name, relacionados FROM entities")
        for row in self.cursor.fetchall():
            name, relacionados = row[0], row[1]
            if not relacionados or relacionados == "[]":
                issues.append({"type": "orphan", "name": name})
                continue

            try:
                rels = json.loads(relacionados)
                for rel in rels:
                    rel = rel.strip("[]")
                    self.cursor.execute("SELECT id FROM entities WHERE name = ?", (rel,))
                    if not self.cursor.fetchone():
                        issues.append({"type": "broken_link", "name": name, "link": rel})
            except Exception:
                pass

        return {
            "total_entities": self.cursor.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
            "issues": issues,
            "health_score": max(0, 100 - len(issues) * 10)
        }

    def get_stats(self) -> dict:
        """Get wiki statistics."""
        total = self.cursor.execute("SELECT COUNT(*) FROM entities").fetchone()[0]
        orphans = 0
        drafts = 0
        finals = 0

        self.cursor.execute("SELECT estado, relacionados FROM entities")
        for row in self.cursor.fetchall():
            estado, relacionados = row[0], row[1]
            if estado == "draft":
                drafts += 1
            elif estado == "final":
                finals += 1
            if not relacionados or relacionados == "[]":
                orphans += 1

        return {
            "total": total,
            "orphans": orphans,
            "draft": drafts,
            "final": finals,
        }
