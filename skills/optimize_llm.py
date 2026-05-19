"""TurboQuant LLM Optimization Skills."""

import time
import logging
from typing import Dict, Any, Optional

import config

logger = logging.getLogger(__name__)


def optimize_llm(mode: str) -> Dict[str, Any]:
    """
    Apply TurboQuant settings for a specific chat mode.

    Args:
        mode: One of "libre", "consultor", "devil", "socratico", "lateral"

    Returns:
        Dict with success status and applied configuration
    """
    try:
        from core.turboquant_engine import apply_chat_mode, get_engine

        engine = get_engine()
        result = engine.apply_mode(mode)

        if result.get("success"):
            logger.info(f"LLM optimized for mode: {mode}")
            return {
                "success": True,
                "mode": mode,
                "context": result["config_applied"]["context"],
                "cache_k": result["config_applied"]["cache_k"],
                "cache_v": result["config_applied"]["cache_v"],
                "model": result.get("model"),
                "gguf_compatible": result.get("gguf_compatible", False),
            }
        else:
            return {"success": False, "error": result.get("error", "Unknown error")}

    except ImportError:
        return {"success": False, "error": "TurboQuant not available"}
    except Exception as e:
        logger.error(f"optimize_llm failed: {e}", exc=e)
        return {"success": False, "error": str(e)}


def show_turbo_status() -> Dict[str, Any]:
    """
    Get current TurboQuant status and settings.

    Returns:
        Dict with current configuration and system status
    """
    try:
        from core.turboquant_engine import get_turbo_status, get_engine

        engine = get_engine()
        status = engine.get_current_settings()
        settings = engine.get_optimized_params()

        return {
            "success": True,
            "current_mode": status.get("mode", "none"),
            "current_model": status.get("model"),
            "context": settings.get("context"),
            "cache_k": settings.get("turbo", {}).get("cache_k"),
            "cache_v": settings.get("turbo", {}).get("cache_v"),
            "quality_estimate": settings.get("meta", {}).get("quality_estimate"),
            "ollama_available": status.get("ollama_available", False),
            "gguf_models": status.get("gguf_models", []),
            "last_applied": status.get("last_applied"),
        }

    except ImportError:
        return {"success": False, "error": "TurboQuant not available"}
    except Exception as e:
        logger.error(f"show_turbo_status failed: {e}", exc=e)
        return {"success": False, "error": str(e)}


def benchmark_llm() -> Dict[str, Any]:
    """
    Run a basic benchmark of current LLM settings.

    Returns:
        Dict with benchmark results (latency, throughput estimates)
    """
    try:
        from core.turboquant_engine import get_engine

        engine = get_engine()
        result = engine.benchmark()

        if result.get("success"):
            logger.info(f"Benchmark completed: {result.get('latency')}s")
            return {
                "success": True,
                "model": result.get("model"),
                "latency_seconds": result.get("latency"),
                "context": result.get("context"),
                "cache_k": result.get("cache_k"),
                "cache_v": result.get("cache_v"),
                "gguf_compatible": result.get("gguf_compatible", False),
                "estimated_tokens_per_sec": round(50 / result.get("latency", 1), 1),
            }
        else:
            return {"success": False, "error": result.get("error", "Benchmark failed")}

    except ImportError:
        return {"success": False, "error": "TurboQuant not available"}
    except Exception as e:
        logger.error(f"benchmark_llm failed: {e}", exc=e)
        return {"success": False, "error": str(e)}


def get_recommended_context(model: str) -> Dict[str, Any]:
    """
    Get recommended context size for a model based on available RAM.

    Args:
        model: Model name (e.g., "qwen3.5:4b")

    Returns:
        Dict with recommended context and model info
    """
    try:
        from core.turboquant_config import get_model_config, estimate_context_limit

        model_cfg = get_model_config(model)

        if not model_cfg:
            return {
                "success": False,
                "error": f"Model {model} not found in config"
            }

        try:
            import psutil
            available_ram = psutil.virtual_memory().available / (1024**3)
        except:
            available_ram = 8.0

        recommended = estimate_context_limit(model, available_ram)

        return {
            "success": True,
            "model": model,
            "model_size_gb": model_cfg.size_gb,
            "max_context": model_cfg.context_max,
            "recommended_context": recommended,
            "available_ram_gb": round(available_ram, 1),
            "cache_k": model_cfg.cache_k,
            "cache_v": model_cfg.cache_v,
        }

    except Exception as e:
        logger.error(f"get_recommended_context failed: {e}", exc=e)
        return {"success": False, "error": str(e)}


def list_available_modes() -> Dict[str, Any]:
    """
    List all available TurboQuant modes and their configurations.

    Returns:
        Dict with all mode configurations
    """
    try:
        from core.turboquant_modes import get_all_modes, CHAT_MODE_TURBO

        modes = {}
        for mode_name, mode_cfg in CHAT_MODE_TURBO.items():
            modes[mode_name] = {
                "name": mode_cfg.name,
                "emoji": mode_cfg.emoji,
                "context": mode_cfg.context,
                "cache_k": mode_cfg.cache_k,
                "cache_v": mode_cfg.cache_v,
                "priority": mode_cfg.priority,
                "description": mode_cfg.description,
            }

        return {
            "success": True,
            "modes": modes,
            "count": len(modes),
        }

    except ImportError:
        return {"success": False, "error": "TurboQuant not available"}
    except Exception as e:
        logger.error(f"list_available_modes failed: {e}", exc=e)
        return {"success": False, "error": str(e)}