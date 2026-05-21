"""Live Activity Tracker - Sistema de actividad en tiempo real."""

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict
from dataclasses import dataclass, asdict
from collections import deque

import config


@dataclass
class ActivityEntry:
    """Entrada de actividad."""
    timestamp: str
    type: str  # ingest, query, chat, error, system
    message: str
    status: str  # pending, running, completed, error
    progress: Optional[int] = None  # 0-100
    details: Optional[str] = None


class LiveActivityTracker:
    """
    Tracker de actividad en tiempo real para dashboard y bot.
    Singleton para compartir estado entre procesos via archivo JSON.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls) -> Self:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        
        self._initialized = True
        self.max_entries = 100
        self._entries = deque(maxlen=self.max_entries)
        self._current_activity: Optional[ActivityEntry] = None
        self._activity_file = config.STORAGE_DIR / "live_activity.json"
        self._update_lock = threading.Lock()
        
        self._load_from_file()
    
    def _load_from_file(self) -> None:
        """Carga historial desde archivo."""
        if self._activity_file.exists():
            try:
                data = json.loads(self._activity_file.read_text())
                self._entries = deque([
                    ActivityEntry(**e) for e in data.get("entries", [])
                ], maxlen=self.max_entries)
            except Exception:
                self._entries = deque(maxlen=self.max_entries)
    
    def _save_to_file(self) -> None:
        """Guarda historial a archivo."""
        config.STORAGE_DIR.mkdir(exist_ok=True)
        data = {
            "entries": [asdict(e) for e in list(self._entries)],
            "current": asdict(self._current_activity) if self._current_activity else None,
            "updated": datetime.now().isoformat()
        }
        self._activity_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    
    def add_entry(
        self,
        type: str,
        message: str,
        status: str = "pending",
        progress: Optional[int] = None,
        details: Optional[str] = None
    ) -> ActivityEntry:
        """Añade una nueva entrada de actividad."""
        entry = ActivityEntry(
            timestamp=datetime.now().isoformat(),
            type=type,
            message=message,
            status=status,
            progress=progress,
            details=details
        )
        
        with self._update_lock:
            self._entries.append(entry)
            self._current_activity = entry
            self._save_to_file()
        
        return entry
    
    def update_progress(self, progress: int, message: Optional[str] = None, details: Optional[str] = None) -> None:
        """Actualiza el progreso de la actividad actual."""
        with self._update_lock:
            if self._current_activity:
                self._current_activity.progress = progress
                if message:
                    self._current_activity.message = message
                if details:
                    self._current_activity.details = details
                self._save_to_file()
    
    def complete_current(self, status: str = "completed", details: Optional[str] = None) -> None:
        """Marca la actividad actual como completada."""
        with self._update_lock:
            if self._current_activity:
                self._current_activity.status = status
                self._current_activity.progress = 100
                if details:
                    self._current_activity.details = details
                self._current_activity = None
                self._save_to_file()
    
    def get_recent(self, limit: int = 20) -> List[Dict]:
        """Obtiene las últimas entradas."""
        entries = list(self._entries)[-limit:]
        return [asdict(e) for e in entries]
    
    def get_current(self) -> Optional[Dict]:
        """Obtiene la actividad actual."""
        if self._current_activity:
            return asdict(self._current_activity)
        return None
    
    def clear(self) -> None:
        """Limpia todo el historial."""
        with self._update_lock:
            self._entries.clear()
            self._current_activity = None
            self._save_to_file()
    
    def ingest_start(self, url: str) -> ActivityEntry:
        """Inicia seguimiento de ingest."""
        return self.add_entry(
            type="ingest",
            message=f"Ingestando: {url[:50]}...",
            status="running",
            progress=0
        )
    
    def ingest_step(self, step: str, progress: int) -> None:
        """Actualiza paso de ingest."""
        step_messages = {
            10: "Descargando contenido...",
            30: "Limpiando HTML...",
            50: "Detectando idioma...",
            60: "Traduciendo...",
            70: "Generando resumen...",
            80: "Extrayendo conceptos...",
            90: "Guardando en wiki...",
        }
        self.update_progress(
            progress,
            message=step_messages.get(progress, step),
            details=step
        )
    
    def ingest_complete(self, success: bool = True, details: Optional[str] = None) -> None:
        """Completa seguimiento de ingest."""
        self.complete_current(
            status="completed" if success else "error",
            details=details
        )


def get_tracker() -> LiveActivityTracker:
    """Obtiene instancia del tracker."""
    return LiveActivityTracker()
