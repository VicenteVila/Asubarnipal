"""TurboQuant Engine - Auto-detection and settings application."""

import os
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

import config
from .turboquant_config import (
    ModelConfig, get_model_config, get_default_cpu_config,
    COMPRESSION_FORMATS
)
from .turboquant_modes import get_mode_config, CHAT_MODE_TURBO

logger = logging.getLogger(__name__)


@dataclass
class TurboState:
    """Current TurboQuant state."""
    mode: Optional[str] = None
    model: Optional[str] = None
    context: int = 32_768
    cache_k: str = "turbo4"
    cache_v: str = "turbo3"
    is_applied: bool = False
    last_applied: Optional[str] = None


class TurboQuantEngine:
    """Engine for managing TurboQuant settings auto-detection."""

    _instance: Optional['TurboQuantEngine'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.state = TurboState()
        self._ollama_available = self._check_ollama()
        self._gguf_models = self._detect_gguf_models()

    def _check_ollama(self) -> bool:
        """Check if Ollama is available."""
        try:
            import requests
            resp = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=3)
            return resp.status_code == 200
        except:
            return False

    def _detect_gguf_models(self) -> List[str]:
        """Detect models that support GGUF/llama.cpp optimizations."""
        if not self._ollama_available:
            return []

        try:
            import requests
            resp = requests.get(f"{config.OLLAMA_BASE_URL}/api/tags", timeout=5)
            if resp.status_code != 200:
                return []

            models = resp.json().get("models", [])
            return [m.get("name", "") for m in models if m.get("name")]
        except:
            return []

    def get_active_model(self) -> Optional[str]:
        """Get currently active model (first in list or configured)."""
        if not self._ollama_available:
            return None

        configured = getattr(config, "OLLAMA_MODEL", None)
        if configured:
            return configured

        return self._gguf_models[0] if self._gguf_models else None

    def apply_mode(self, mode: str, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Apply TurboQuant settings for a chat mode.
        Auto-detects model if not provided.
        """
        mode_cfg = get_mode_config(mode)
        if not mode_cfg:
            return {"success": False, "error": f"Unknown mode: {mode}"}

        target_model = model or self.get_active_model()
        model_cfg = get_model_config(target_model) if target_model else None

        result = {
            "success": True,
            "mode": mode,
            "model": target_model,
            "config_applied": {
                "context": mode_cfg.context,
                "cache_k": mode_cfg.cache_k,
                "cache_v": mode_cfg.cache_v,
            },
            "gguf_compatible": target_model in self._gguf_models if target_model else False,
        }

        if model_cfg:
            adjusted_context = min(mode_cfg.context, model_cfg.recommended_context)
            result["config_applied"]["context"] = adjusted_context
            result["model_config"] = {
                "size_gb": model_cfg.size_gb,
                "recommended_context": model_cfg.recommended_context,
            }

        self.state = TurboState(
            mode=mode,
            model=target_model,
            context=result["config_applied"]["context"],
            cache_k=mode_cfg.cache_k,
            cache_v=mode_cfg.cache_v,
            is_applied=True,
            last_applied=time.strftime("%Y-%m-%d %H:%M:%S")
        )

        logger.info(f"TQ applied: mode={mode}, model={target_model}, "
                   f"context={result['config_applied']['context']}")

        return result

    def apply_by_priority(self, priority: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Apply settings based on priority (speed/balanced/quality)."""
        priority_modes = {
            "speed": "libre",
            "balanced": "consultor",
            "quality": "devil"
        }
        mode = priority_modes.get(priority, "consultor")
        return self.apply_mode(mode, model)

    def get_current_settings(self) -> Dict[str, Any]:
        """Get current TurboQuant settings."""
        return {
            "mode": self.state.mode,
            "model": self.state.model,
            "context": self.state.context,
            "cache_k": self.state.cache_k,
            "cache_v": self.state.cache_v,
            "is_applied": self.state.is_applied,
            "last_applied": self.state.last_applied,
            "ollama_available": self._ollama_available,
            "gguf_models": self._gguf_models,
        }

    def get_optimized_params(self, mode: Optional[str] = None) -> Dict[str, Any]:
        """
        Get optimized parameters for LLM call.
        Returns dict with context, options, etc.
        """
        if mode:
            self.apply_mode(mode)

        if not self.state.is_applied:
            self.apply_mode("consultor")

        k_fmt = COMPRESSION_FORMATS.get(self.state.cache_k)
        v_fmt = COMPRESSION_FORMATS.get(self.state.cache_v)

        return {
            "context": self.state.context,
            "options": {
                "num_ctx": self.state.context,
                "temperature": 0.7,
                "top_p": 0.9,
            },
            "turbo": {
                "cache_k": self.state.cache_k,
                "cache_v": self.state.cache_v,
                "compression_k": k_fmt.bits if k_fmt else 8,
                "compression_v": v_fmt.bits if v_fmt else 8,
            },
            "meta": {
                "mode": self.state.mode,
                "model": self.state.model,
                "quality_estimate": (k_fmt.quality + v_fmt.quality) / 2 if k_fmt and v_fmt else 0.9,
            }
        }

    def benchmark(self) -> Dict[str, Any]:
        """Run basic benchmark of current settings."""
        if not self._ollama_available:
            return {"success": False, "error": "Ollama not available"}

        import requests

        model = self.get_active_model()
        if not model:
            return {"success": False, "error": "No model available"}

        start = time.time()
        try:
            resp = requests.post(
                f"{config.OLLAMA_BASE_URL}/api/generate",
                json={"model": model, "prompt": "Hello", "options": {"num_ctx": self.state.context}},
                timeout=30
            )
            duration = time.time() - start

            return {
                "success": True,
                "model": model,
                "latency": round(duration, 2),
                "context": self.state.context,
                "cache_k": self.state.cache_k,
                "cache_v": self.state.cache_v,
                "gguf_compatible": model in self._gguf_models,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "latency": time.time() - start}

    def reset(self) -> None:
        """Reset to default settings."""
        self.state = TurboState()


def get_engine() -> TurboQuantEngine:
    """Get singleton TurboQuant engine instance."""
    return TurboQuantEngine()


def apply_chat_mode(mode: str, model: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to apply settings for a chat mode."""
    return get_engine().apply_mode(mode, model)


def get_turbo_params(mode: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to get optimized params."""
    return get_engine().get_optimized_params(mode)


def get_turbo_status() -> Dict[str, Any]:
    """Convenience function to get current status."""
    return get_engine().get_current_settings()