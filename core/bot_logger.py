"""BotLogger - Sistema de Logging Estructurado para Asubarnipal."""

import sys
import time
import logging
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from typing import Optional, Self, Any

import config


class BotLogger:
    """Logger estructurado con emojis, indentación y dual output."""

    _instance: Optional['BotLogger'] = None

    # Categorías con emojis y colores ANSI
    CATEGORIES = {
        "INCOMING": ("📥", "\033[94m"),   # Azul
        "OUT": ("📤", "\033[94m"),
        "LLM": ("🟡", "\033[93m"),        # Amarillo
        "RAG": ("🔍", "\033[95m"),        # Magenta
        "TOOL": ("🟢", "\033[92m"),        # Verde
        "THOUGHT": ("💭", "\033[97m"),    # Blanco
        "AGENT": ("🤖", "\033[96m"),      # Cyan
        "ERROR": ("🔴", "\033[91m"),      # Rojo
        "WARN": ("⚠️", "\033[93m"),
        "DEBUG": ("⚪", "\033[90m"),       # Gris
        "INFO": ("ℹ️", "\033[97m"),
        "SUCCESS": ("✅", "\033[92m"),
        "SPAN": ("  ", "\033[90m"),        # Indentación
    }

    RESET = "\033[0m"

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return

        self._initialized = True
        self._depth = 0
        self._use_color = sys.stdout.isatty()
        self._show_timestamps = True
        self._show_indent = True

        # Logger de archivo
        self._file_logger = logging.getLogger("asubarnipal")
        if not self._file_logger.handlers:
            self._file_logger.setLevel(logging.DEBUG)
            handler = logging.FileHandler(
                config.LOG_FILE,
                encoding="utf-8"
            )
            handler.setFormatter(logging.Formatter(
                "[%(asctime)s] [%(levelname)s] %(message)s",
                datefmt="%H:%M:%S"
            ))
            self._file_logger.addHandler(handler)

        # Terminal handler
        self._terminal_handler = logging.StreamHandler(sys.stdout)
        self._terminal_handler.setFormatter(logging.Formatter("%(message)s"))
        self._terminal_logger = logging.getLogger("terminal")
        self._terminal_logger.setLevel(logging.INFO)
        self._terminal_logger.propagate = False
        if not self._terminal_logger.handlers:
            self._terminal_logger.addHandler(self._terminal_handler)

        # Live activity tracker
        self._activity_tracker = None

    def _get_tracker(self) -> Any:
        """Obtiene el tracker de actividad."""
        if self._activity_tracker is None:
            try:
                from core.live_activity import get_tracker
                self._activity_tracker = get_tracker()
            except Exception:
                pass
        return self._activity_tracker
    
    def _format(self, category: str, message: str, depth_boost: int = 0) -> str:
        """Formatea mensaje con emoji, timestamp e indentación."""
        emoji, color = self.CATEGORIES.get(category, ("📝", "\033[97m"))
        depth = self._depth + depth_boost
        
        # Indentación con树干 visuales
        if self._show_indent and depth > 0:
            indent = "  │   " * (depth - 1)
            if depth > 1:
                indent += "  ├── "
            else:
                indent += "  └─ "
        else:
            indent = ""
        
        timestamp = ""
        if self._show_timestamps:
            timestamp = f"\033[90m[{datetime.now().strftime('%H:%M:%S')}]\033[0m "
        
        msg = f"{timestamp}{color}{emoji} {indent}{message}{self.RESET if self._use_color else ''}"
        return msg
    
    def _log(self, category: str, message: str, level: str = "INFO", depth_boost: int = 0) -> None:
        """Log a terminal y archivo."""
        formatted = self._format(category, message, depth_boost)

        # Terminal
        self._terminal_logger.info(formatted)

        # Archivo
        clean_msg = self._strip_ansi(message)
        log_category = category if category in ["ERROR", "WARN", "DEBUG"] else "INFO"
        self._file_logger.log(
            getattr(logging, level),
            f"[{category}] {clean_msg}"
        )

        # Live activity
        tracker = self._get_tracker()
        if tracker:
            activity_type = {
                "INCOMING": "ingest" if "ingest" in message.lower() else "query",
                "OUT": "chat",
                "LLM": "chat",
                "RAG": "query",
                "TOOL": "tool",
                "ERROR": "error",
                "WARN": "error",
                "SUCCESS": "system",
                "INFO": "system",
            }.get(category, "system")

            status = "error" if category in ["ERROR"] else "completed"

            tracker.add_entry(
                type=activity_type,
                message=clean_msg[:100],
                status=status
            )
    
    @staticmethod
    def _strip_ansi(text: str) -> str:
        """Elimina códigos ANSI para archivo."""
        import re
        return re.sub(r'\x1b\[[0-9;]*m', '', text)
    
    # =========================================================================
    # MÉTODOS PÚBLICOS POR CATEGORÍA
    # =========================================================================
    
    def incoming(self, message: str) -> None:
        """📥 Mensaje entrante (comando o texto)."""
        self._log("INCOMING", message)
    
    def outgoing(self, message: str) -> None:
        """📤 Respuesta saliente."""
        self._log("OUT", message)
    
    def llm(self, message: str) -> None:
        """🟡 Llamada o respuesta del LLM."""
        self._log("LLM", message)
    
    def llm_start(self, model: str, prompt_preview: str = "") -> None:
        """🟡 Inicio de llamada LLM."""
        preview = f": {prompt_preview[:50]}..." if prompt_preview else ""
        self._log("LLM", f"→ {model}{preview}")
    
    def llm_end(self, response_preview: str = "", duration: float = 0) -> None:
        """🟡 Fin de llamada LLM."""
        duration_str = f" ({duration:.2f}s)" if duration else ""
        preview = f": {response_preview[:50]}..." if response_preview else ""
        self._log("LLM", f"← {preview}{duration_str}")
    
    def rag(self, message: str) -> None:
        """🔍 Búsqueda RAG."""
        self._log("RAG", message)
    
    def rag_search(self, query: str, results_count: int) -> None:
        """🔍 Búsqueda RAG con resultados."""
        self._log("RAG", f'Buscar: "{query[:30]}..." → {results_count} docs')
    
    def tool(self, name: str, args: str = "", result: str = "") -> None:
        """🟢 Ejecución de tool/skill."""
        args_str = f"({args})" if args else ""
        msg = f"🔧 {name}{args_str}"
        self._log("TOOL", msg)
        if result:
            result_preview = result[:80] if len(result) > 80 else result
            self._log("TOOL", f"   └→ {result_preview}", depth_boost=1)
    
    def tool_start(self, name: str, args: str = "") -> None:
        """🟢 Inicio de ejecución de tool."""
        args_str = f"({args})" if args else ""
        self._log("TOOL", f"🔧 {name}{args_str}...")
    
    def tool_end(self, name: str, success: bool = True, result: str = "") -> None:
        """🟢 Fin de ejecución de tool."""
        status = "✅" if success else "❌"
        msg = f"   └→ {status} {name}"
        self._log("TOOL", msg, depth_boost=1)
        if result:
            result_preview = result[:60] + "..." if len(result) > 60 else result
            self._log("TOOL", f"      {result_preview}", depth_boost=2)
    
    def thought(self, message: str) -> None:
        """💭 Pensamiento del agente."""
        self._log("THOUGHT", message)
    
    def agent(self, task: str) -> None:
        """🤖 Inicio de tarea autónoma."""
        self._log("AGENT", f"🎯 Tarea: {task}")
    
    def agent_step(self, step: str) -> None:
        """🤖 Paso del agente."""
        self._log("AGENT", f"   └→ {step}", depth_boost=1)
    
    def agent_end(self, result_preview: str = "") -> None:
        """🤖 Fin de tarea autónoma."""
        preview = f": {result_preview[:50]}..." if result_preview else ""
        self._log("AGENT", f"✓ Completado{preview}")
    
    def error(self, message: str, exc: Optional[Exception] = None) -> None:
        """🔴 Error."""
        msg = f"❌ {message}"
        if exc:
            msg += f" | {str(exc)[:100]}"
        self._log("ERROR", msg, level="ERROR")
    
    def warn(self, message: str) -> None:
        """⚠️ Warning."""
        self._log("WARN", f"⚠️ {message}", level="WARNING")
    
    def warning(self, message: str) -> None:
        """⚠️ Warning (alias for warn)."""
        self.warn(message)
    
    def debug(self, message: str) -> None:
        """⚪ Debug."""
        self._log("DEBUG", f"   {message}", level="DEBUG")
    
    def info(self, message: str) -> None:
        """ℹ️ Info general."""
        self._log("INFO", message)
    
    def success(self, message: str) -> None:
        """✅ Éxito."""
        self._log("SUCCESS", f"✅ {message}")
    
    # =========================================================================
    # CONTEXT MANAGER PARA GRUPOS ANIDADOS
    # =========================================================================
    
    @contextmanager
    def group(self, title: str, category: str = "INFO") -> None:
        """Grupo indentado de mensajes. Usage: with logger.group("Título"):"""
        emoji, color = self.CATEGORIES.get(category, ("📝", "\033[97m"))
        self._log(category, f"┌─ {title}")
        self._depth += 1
        try:
            yield self
        finally:
            self._depth -= 1
            self._log(category, f"└─ {title} [fin]")
    
    @contextmanager
    def step(self, label: str) -> None:
        """Paso indentado simple. Usage: with logger.step("Procesando..."):"""
        self._log("SPAN", f"├→ {label}")
        self._depth += 1
        try:
            yield self
        finally:
            self._depth -= 1
    
    # =========================================================================
    # PROGRESS BAR SIMULADO
    # =========================================================================
    
    def progress(self, label: str, current: int, total: int, width: int = 30) -> None:
        """Muestra barra de progreso."""
        filled = int(width * current / total) if total > 0 else width
        bar = "█" * filled + "░" * (width - filled)
        pct = int(100 * current / total) if total > 0 else 100
        self._log("INFO", f"{label} |{bar}| {pct}%")
    
    # =========================================================================
    # CONFIGURACIÓN
    # =========================================================================
    
    def set_color(self, enabled: bool) -> None:
        """Activa/desactiva colores ANSI."""
        self._use_color = enabled
    
    def set_timestamps(self, enabled: bool) -> None:
        """Activa/desactiva timestamps."""
        self._show_timestamps = enabled
    
    def set_indent(self, enabled: bool) -> None:
        """Activa/desactiva indentación."""
        self._show_indent = enabled
    
    def reset_depth(self) -> None:
        """Resetea la profundidad de indentación."""
        self._depth = 0


# Instancia global
logger = BotLogger()
