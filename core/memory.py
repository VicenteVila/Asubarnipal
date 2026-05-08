"""Enhanced Memory System - Persistent memory with semantic search."""

import json
import logging
import re
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import config

logger = logging.getLogger(__name__)


class EnhancedMemory:
    """Memoria persistente mejorada con estructura y búsqueda."""
    
    CATEGORIES = [
        "conversation", "fact", "idea", "task", "preference", 
        "learning", "error", "plan", "context", "person"
    ]
    
    def __init__(self, max_memories: int = 500):
        self.memory_file = config.STORAGE_DIR / "memory.json"
        self.max_memories = max_memories
        self._load()
    
    def _load(self):
        """Cargar memorias."""
        self.memories = []
        if self.memory_file.exists():
            try:
                self.memories = json.loads(self.memory_file.read_text())
            except Exception as e:
                logger.warning(f"Error loading memory: {e}")
                self.memories = []
    
    def _save(self):
        """Guardar memorias."""
        config.STORAGE_DIR.mkdir(exist_ok=True)
        self._cleanup()
        self.memory_file.write_text(
            json.dumps(self.memories, indent=2, ensure_ascii=False)
        )
    
    def _cleanup(self):
        """Limpiar memorias antiguas si excede el límite."""
        if len(self.memories) > self.max_memories:
            sorted_memories = sorted(
                self.memories, 
                key=lambda m: (m.get("priority", 0), m.get("timestamp", "")),
                reverse=True
            )
            self.memories = sorted_memories[:self.max_memories]
    
    def add(
        self, 
        content: str, 
        category: str = "general",
        priority: int = 5,
        metadata: Optional[dict] = None,
        importance: str = "normal"
    ) -> dict:
        """Añadir memoria."""
        if category not in self.CATEGORIES:
            category = "general"
        
        memory = {
            "id": f"mem_{len(self.memories)}_{int(time.time())}",
            "content": content,
            "category": category,
            "priority": priority,
            "importance": importance,
            "timestamp": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "access_count": 0,
            "metadata": metadata or {},
            "tags": self._extract_tags(content),
        }
        
        self.memories.append(memory)
        self._save()
        logger.info(f"💾 Memory added: {category} - {content[:50]}")
        return memory
    
    def _extract_tags(self, content: str) -> list:
        """Extraer tags del contenido."""
        tags = []
        words = re.findall(r'#\w+', content)
        tags.extend([w[1:] for w in words])
        return list(set(tags))
    
    def get(
        self, 
        memory_id: str, 
        access: bool = True
    ) -> Optional[dict]:
        """Obtener memoria por ID."""
        for mem in self.memories:
            if mem.get("id") == memory_id:
                if access:
                    mem["access_count"] = mem.get("access_count", 0) + 1
                    mem["last_accessed"] = datetime.now().isoformat()
                    self._save()
                return mem
        return None
    
    def get_recent(
        self, 
        limit: int = 10,
        category: Optional[str] = None
    ) -> list:
        """Obtener memorias recientes."""
        result = self.memories
        if category:
            result = [m for m in result if m.get("category") == category]
        return result[-limit:]
    
    def get_important(
        self, 
        limit: int = 10,
        min_importance: str = "high"
    ) -> list:
        """Obtener memorias importantes."""
        importance_order = ["critical", "high", "normal", "low"]
        min_idx = importance_order.index(min_importance) if min_importance in importance_order else 2
        
        result = [
            m for m in self.memories 
            if importance_order.index(m.get("importance", "normal")) >= min_idx
        ]
        return sorted(result, key=lambda m: m.get("priority", 0), reverse=True)[:limit]
    
    def search(
        self, 
        query: str,
        category: Optional[str] = None,
        limit: int = 10
    ) -> list:
        """Búsqueda en memorias."""
        query_lower = query.lower()
        results = []
        
        for mem in self.memories:
            if category and mem.get("category") != category:
                continue
            
            content = mem.get("content", "").lower()
            tags = [t.lower() for t in mem.get("tags", [])]
            
            if query_lower in content or query_lower in tags:
                results.append(mem)
            
            if len(results) >= limit:
                break
        
        return results
    
    def update(
        self, 
        memory_id: str, 
        **kwargs
    ) -> bool:
        """Actualizar memoria."""
        for mem in self.memories:
            if mem.get("id") == memory_id:
                mem.update(kwargs)
                mem["updated_at"] = datetime.now().isoformat()
                self._save()
                return True
        return False
    
    def delete(self, memory_id: str) -> bool:
        """Eliminar memoria."""
        self.memories = [
            m for m in self.memories if m.get("id") != memory_id
        ]
        self._save()
        return True
    
    def clear(self, before: Optional[str] = None) -> int:
        """Limpiar memorias."""
        if not before:
            count = len(self.memories)
            self.memories = []
        else:
            before_date = datetime.fromisoformat(before)
            original_count = len(self.memories)
            self.memories = [
                m for m in self.memories
                if datetime.fromisoformat(m.get("timestamp", "2020-01-01")) >= before_date
            ]
            count = original_count - len(self.memories)
        
        self._save()
        return count
    
    def get_stats(self) -> dict:
        """Estadísticas de memorias."""
        categories = Counter(m.get("category") for m in self.memories)
        importance = Counter(m.get("importance") for m in self.memories)
        
        return {
            "total": len(self.memories),
            "by_category": dict(categories),
            "by_importance": dict(importance),
            "most_accessed": sorted(
                self.memories, 
                key=lambda m: m.get("access_count", 0),
                reverse=True
            )[:5],
            "first_memory": self.memories[0].get("timestamp") if self.memories else None,
            "last_memory": self.memories[-1].get("timestamp") if self.memories else None,
        }
    
    def consolidate(self) -> dict:
        """Consolidar memorias relacionadas."""
        consolidated = []
        seen_content = set()
        
        for mem in self.memories:
            content = mem.get("content", "").lower().strip()
            if content not in seen_content:
                consolidated.append(mem)
                seen_content.add(content)
        
        removed = len(self.memories) - len(consolidated)
        self.memories = consolidated
        self._save()
        
        return {
            "original": len(self.memories) + removed,
            "consolidated": len(consolidated),
            "removed_duplicates": removed,
        }
    
    def export(self, path: Path) -> bool:
        """Exportar memorias."""
        try:
            path.write_text(
                json.dumps(self.memories, indent=2, ensure_ascii=False)
            )
            return True
        except Exception as e:
            logger.error(f"Export error: {e}")
            return False
    
    def import_(self, path: Path, merge: bool = True) -> dict:
        """Importar memorias."""
        try:
            imported = json.loads(path.read_text())
            if not isinstance(imported, list):
                return {"error": "Invalid format"}
            
            if merge:
                existing_ids = {m.get("id") for m in self.memories}
                new_memories = [
                    m for m in imported if m.get("id") not in existing_ids
                ]
                self.memories.extend(new_memories)
                added = len(new_memories)
            else:
                self.memories = imported
                added = len(imported)
            
            self._save()
            return {"added": added, "total": len(self.memories)}
        except Exception as e:
            logger.error(f"Import error: {e}")
            return {"error": str(e)}


# Shortcut functions for direct use
def remember(
    content: str,
    category: str = "fact",
    priority: int = 5
) -> dict:
    """Función rápida para recordar algo."""
    memory = EnhancedMemory()
    return memory.add(content, category, priority)


def recall(
    query: str,
    limit: int = 5
) -> list:
    """Función rápida para recordar."""
    memory = EnhancedMemory()
    return memory.search(query, limit=limit)


def what_remembered() -> list:
    """Obtener últimas memorias."""
    memory = EnhancedMemory()
    return memory.get_recent(10)


def memory_stats() -> dict:
    """Estadísticas de memoria."""
    memory = EnhancedMemory()
    return memory.get_stats()


if __name__ == "__main__":
    memory = EnhancedMemory()
    print("💾 Enhanced Memory System")
    print(f"  Total: {len(memory.memories)} memorias")
    print(f"  Categorías: {memory.get_stats()['by_category']}")