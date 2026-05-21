"""Research Proposal Memory - Registry for investigation proposals."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

import config

logger = logging.getLogger(__name__)


class ProposalMemory:
    """Registry for research proposals with preference tracking."""

    MEMORY_FILE = config.DATA_DIR / "research_proposals.json"
    PREFERENCES_FILE = config.DATA_DIR / "research_preferences.json"

    def __init__(self) -> None:
        self.proposals = self._load_proposals()
        self.preferences = self._load_preferences()

    def _load_proposals(self) -> list:
        """Load proposals from JSON file."""
        if self.MEMORY_FILE.exists():
            try:
                data = json.loads(self.MEMORY_FILE.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Could not load proposals: {e}")
                return []
        return []

    def _save_proposals(self) -> None:
        """Save proposals to JSON file."""
        try:
            self.MEMORY_FILE.write_text(
                json.dumps(self.proposals, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Could not save proposals: {e}")

    def _load_preferences(self) -> dict:
        """Load user preferences from JSON file."""
        if self.PREFERENCES_FILE.exists():
            try:
                return json.loads(self.PREFERENCES_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Could not load preferences: {e}")
                return {}
        return {}

    def _save_preferences(self) -> None:
        """Save user preferences to JSON file."""
        try:
            self.PREFERENCES_FILE.write_text(
                json.dumps(self.preferences, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Could not save preferences: {e}")

    def save(self, pregunta: str, respuesta: str, propuesta: str,
             modo: str, refs: list[dict[str, Any]], tags: Optional[list[str]] = None) -> dict[str, Any]:
        """
        Save a new research proposal.

        Args:
            pregunta: Original user question
            respuesta: Full answer from the large model
            propuesta: Research proposal section
            modo: "estructurada" or "exploratoria"
            refs: List of reference dicts
            tags: Optional tags

        Returns:
            dict with proposal data and ID
        """
        proposal_id = str(uuid.uuid4())[:8]

        proposal = {
            "id": proposal_id,
            "timestamp": datetime.now().isoformat(),
            "pregunta_original": pregunta,
            "respuesta": respuesta,
            "propuesta": propuesta,
            "modo": modo,
            "refs": refs,
            "tags": tags or [],
            "status": "active",
        }

        self.proposals.insert(0, proposal)
        self._save_proposals()

        logger.info(f"Proposal saved: {proposal_id}")
        return proposal

    def save_to_standby(self, pregunta: str, respuesta: str, propuesta: str,
                       modo: str, refs: list[dict[str, Any]]) -> dict[str, Any]:
        """Save proposal to standby (not active, for later review)."""
        proposal_id = str(uuid.uuid4())[:8]

        proposal = {
            "id": proposal_id,
            "timestamp": datetime.now().isoformat(),
            "pregunta_original": pregunta,
            "respuesta": respuesta,
            "propuesta": propuesta,
            "modo": modo,
            "refs": refs,
            "tags": ["standby"],
            "status": "standby",
        }

        self.proposals.insert(0, proposal)
        self._save_proposals()

        logger.info(f"Proposal saved to standby: {proposal_id}")
        return proposal

    def list(self, status: str = "active") -> list:
        """List proposals by status (active, standby, archived)."""
        if status == "all":
            return self.proposals
        return [p for p in self.proposals if p.get("status") == status]

    def get(self, proposal_id: str) -> Optional[dict]:
        """Get proposal by ID."""
        for p in self.proposals:
            if p.get("id") == proposal_id:
                return p
        return None

    def archive(self, proposal_id: str) -> bool:
        """Archive a proposal (mark as archived, don't delete)."""
        for p in self.proposals:
            if p.get("id") == proposal_id:
                p["status"] = "archived"
                p["archived_at"] = datetime.now().isoformat()
                self._save_proposals()
                return True
        return False

    def restore(self, proposal_id: str) -> bool:
        """Restore an archived proposal to active."""
        for p in self.proposals:
            if p.get("id") == proposal_id:
                p["status"] = "active"
                if "archived_at" in p:
                    del p["archived_at"]
                self._save_proposals()
                return True
        return False

    def delete(self, proposal_id: str) -> bool:
        """Permanently delete a proposal."""
        original_len = len(self.proposals)
        self.proposals = [p for p in self.proposals if p.get("id") != proposal_id]
        if len(self.proposals) < original_len:
            self._save_proposals()
            return True
        return False

    def get_preference(self) -> str:
        """Get preferred mode for proposals."""
        return self.preferences.get("modo", "estructurada")

    def set_preference(self, modo: str) -> str:
        """Set preferred mode (estructurada/exploratoria)."""
        if modo in ("estructurada", "exploratoria"):
            self.preferences["modo"] = modo
            self._save_preferences()
            logger.info(f"Mode preference set: {modo}")
        return self.preferences.get("modo", "estructurada")

    def stats(self) -> dict:
        """Get statistics about proposals."""
        active = len([p for p in self.proposals if p.get("status") == "active"])
        standby = len([p for p in self.proposals if p.get("status") == "standby"])
        archived = len([p for p in self.proposals if p.get("status") == "archived"])
        total = len(self.proposals)

        return {
            "total": total,
            "active": active,
            "standby": standby,
            "archived": archived,
            "preferred_modo": self.preferences.get("modo", "estructurada"),
        }

    def search_proposals(self, query: str, limit: int = 10) -> list:
        """Search proposals by question or content."""
        query_lower = query.lower()
        results = []

        for p in self.proposals:
            if query_lower in p.get("pregunta_original", "").lower():
                results.append(p)
            elif query_lower in p.get("propuesta", "").lower():
                results.append(p)
            elif query_lower in p.get("respuesta", "").lower():
                results.append(p)

        return results[:limit]


def get_proposal_memory() -> ProposalMemory:
    """Get ProposalMemory singleton instance."""
    if not getattr(get_proposal_memory, "_instance", None):
        get_proposal_memory._instance = ProposalMemory()
    return get_proposal_memory._instance


class EnhancedMemory:
    """Persistent memory system with categories and priority (legacy)."""

    MEMORY_FILE = config.DATA_DIR / "memories.json"

    def __init__(self) -> None:
        self.memories = self._load()
        self._next_id = max([m.get("id", 0) for m in self.memories], default=0) + 1

    def _load(self) -> list:
        if self.MEMORY_FILE.exists():
            try:
                data = json.loads(self.MEMORY_FILE.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
            except (json.JSONDecodeError, Exception) as e:
                logger.warning(f"Could not load memories: {e}")
                return []
        return []

    def _save(self) -> None:
        try:
            self.MEMORY_FILE.write_text(
                json.dumps(self.memories, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"Could not save memories: {e}")

    def add(self, content: str, category: str = "fact", priority: int = 5,
            importance: str = "normal", tags: Optional[list[str]] = None) -> dict[str, Any]:
        """Add a memory entry."""
        mem_id = self._next_id
        self._next_id += 1

        entry = {
            "id": mem_id,
            "content": content,
            "category": category,
            "priority": priority,
            "importance": importance,
            "tags": tags or [],
            "timestamp": datetime.now().isoformat(),
            "access_count": 0,
        }
        self.memories.insert(0, entry)
        self._save()
        return entry

    def get_stats(self) -> dict:
        """Get memory statistics."""
        total = len(self.memories)
        by_category = {}
        last_memory = None

        for m in self.memories:
            cat = m.get("category", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1

        if self.memories:
            last_memory = self.memories[0].get("content", "")

        return {
            "total": total,
            "by_category": by_category,
            "last_memory": last_memory,
        }

    def search(self, query: str, limit: int = 10) -> list:
        """Search memories by content."""
        q = query.lower()
        results = []
        for m in self.memories:
            if q in m.get("content", "").lower():
                results.append(m)
                if len(results) >= limit:
                    break
        return results

    def get_recent(self, limit: int = 10, category: str = None) -> list:
        """Get recent memories, optionally filtered by category."""
        if category:
            return [m for m in self.memories if m.get("category") == category][:limit]
        return self.memories[:limit]

    def clear(self) -> int:
        """Clear all memories. Returns count deleted."""
        count = len(self.memories)
        self.memories = []
        self._save()
        return count

    def consolidate(self) -> dict:
        """Remove duplicate memories by content."""
        seen = set()
        original_len = len(self.memories)
        self.memories = [m for m in self.memories if m.get("content") not in seen
                         and not seen.add(m.get("content", ""))]
        self._save()
        return {"removed_duplicates": original_len - len(self.memories)}