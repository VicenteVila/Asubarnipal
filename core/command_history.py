"""Command History - Historial y analytics de comandos."""

import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

import config

logger = logging.getLogger(__name__)


class CommandHistory:
    """Control de historial de comandos ejecutados."""
    
    def __init__(self):
        self.history_file = config.DATA_DIR / "command_history.json"
        self._load()
    
    def _load(self):
        """Cargar historial."""
        if self.history_file.exists():
            try:
                self.history = json.loads(self.history_file.read_text())
            except Exception:
                self.history = []
        else:
            self.history = []
    
    def _save(self):
        """Guardar historial."""
        config.DATA_DIR.mkdir(exist_ok=True)
        self.history_file.write_text(json.dumps(self.history[-500:], indent=2), encoding="utf-8")
    
    def add(self, command: str, user_id: Optional[str] = None):
        """Añadir comando al historial."""
        entry = {
            "command": command,
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
        }
        self.history.append(entry)
        self._save()
        logger.debug(f"📝 Historial: {command[:50]}")
    
    def get(self, limit: int = 50) -> list[dict]:
        """Obtener historial."""
        return self.history[-limit:]
    
    def get_by_user(self, user_id: str, limit: int = 50) -> list[dict]:
        """Obtener historial por usuario."""
        user_commands = [
            c for c in self.history if c.get("user_id") == user_id
        ]
        return user_commands[-limit:]
    
    def get_stats(self) -> dict:
        """Obtener estadísticas."""
        if not self.history:
            return {
                "total": 0,
                "unique_commands": 0,
                "top_commands": [],
                "by_date": {},
            }
        
        commands = [c["command"] for c in self.history]
        top = Counter(commands).most_common(10)
        
        by_date = Counter()
        for c in self.history:
            ts = c.get("timestamp", "")[:10]
            by_date[ts] += 1
        
        return {
            "total": len(self.history),
            "unique_commands": len(set(commands)),
            "top_commands": [{"cmd": k, "count": v} for k, v in top],
            "by_date": dict(by_date.most_common(30)),
            "first_command": self.history[0].get("timestamp", "") if self.history else None,
            "last_command": self.history[-1].get("timestamp", "") if self.history else None,
        }
    
    def clear(self, before: Optional[str] = None):
        """Limpiar historial."""
        if before:
            self.history = [
                c for c in self.history if c.get("timestamp", "") >= before
            ]
        else:
            self.history = []
        self._save()
    
    def search(self, query: str) -> list[dict]:
        """Buscar en historial."""
        return [
            c for c in self.history 
            if query.lower() in c.get("command", "").lower()
        ]


# Analytics
def get_command_analytics() -> dict:
    """Obtener analytics completo."""
    history = CommandHistory()
    stats = history.get_stats()
    
    if not stats["total"]:
        return {"error": "No hay historial"}
    
    last_24h = [
        c for c in history.history 
        if c.get("timestamp", "") > datetime.now().isoformat()[:10]
    ]
    
    return {
        "stats": stats,
        "commands_last_24h": len(last_24h),
        "avg_per_day": stats["total"] / max(1, len(stats["by_date"])),
    }


if __name__ == "__main__":
    history = CommandHistory()
    stats = history.get_stats()
    
    print("📊 Command Analytics")
    print(f"  Total comandos: {stats['total']}")
    print(f"  Comandos únicos: {stats['unique_commands']}")
    print("\n🔝 Top 5 comandos:")
    for cmd in stats["top_commands"][:5]:
        print(f"  - {cmd['cmd'][:40]}: {cmd['count']}")